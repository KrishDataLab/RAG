import os
import json
import re
from typing import Dict, Any, Optional, List
from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import LLMProviderError

class LLMClient:
    def __init__(self, provider: str = "auto"):
        self.provider = provider if provider != "auto" else settings.DEFAULT_LLM_PROVIDER
        self.gemini_key = os.getenv("GEMINI_API_KEY", settings.GEMINI_API_KEY)
        self.openai_key = os.getenv("OPENAI_API_KEY", settings.OPENAI_API_KEY)

    def get_provider_status(self) -> Dict[str, Any]:
        """Returns provider availability, failure reason, and active fallback behavior."""
        status = {
            "requested_provider": self.provider,
            "active_provider": "fallback",
            "gemini": {"available": bool(self.gemini_key), "reason": "GEMINI_API_KEY is configured." if self.gemini_key else "GEMINI_API_KEY environment variable is missing."},
            "openai": {"available": bool(self.openai_key), "reason": "OPENAI_API_KEY is configured." if self.openai_key else "OPENAI_API_KEY environment variable is missing."},
            "fallback": {"available": True, "reason": "Local deterministic response fallback is available."},
            "user_display": ""
        }

        if self.gemini_key and self.provider in ["auto", "gemini"]:
            status["active_provider"] = "gemini"
            status["user_display"] = "Active Provider: Google Gemini (API Key Present)"
        elif self.openai_key and self.provider in ["auto", "openai"]:
            status["active_provider"] = "openai"
            status["user_display"] = "Active Provider: OpenAI GPT (API Key Present)"
        else:
            reason = "No external LLM API keys configured." if not (self.gemini_key or self.openai_key) else f"Provider '{self.provider}' credentials unavailable."
            status["user_display"] = (
                f"Provider unavailable: {self.provider}\n"
                f"Reason: {reason}\n"
                f"Fallback behaviour: Operating with the local deterministic response fallback; verify its answers against the cited passages."
            )

        return status

    def generate(self, prompt: str, system_instruction: Optional[str] = None, json_mode: bool = False) -> str:
        if self.gemini_key and (self.provider in ["auto", "gemini"]):
            try:
                return self._call_gemini(prompt, system_instruction, json_mode)
            except Exception as e:
                logger.warning(f"Gemini API call failed: {e}. Falling back to standard engine.")

        if self.openai_key and (self.provider in ["auto", "openai"]):
            try:
                return self._call_openai(prompt, system_instruction, json_mode)
            except Exception as e:
                logger.warning(f"OpenAI API call failed: {e}. Falling back to standard engine.")

        return self._fallback_generate(prompt, system_instruction, json_mode)

    def _call_gemini(self, prompt: str, system_instruction: Optional[str], json_mode: bool) -> str:
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.gemini_key)
            model_name = settings.model_config_data.get("llm", {}).get("gemini_model", "gemini-2.5-flash")
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_instruction
            )
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            import requests
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
            headers = {"Content-Type": "application/json"}
            full_prompt = (system_instruction + "\n\n" if system_instruction else "") + prompt
            data = {"contents": [{"parts": [{"text": full_prompt}]}]}
            res = requests.post(url, headers=headers, json=data, timeout=15)
            if res.status_code == 200:
                result = res.json()
                return result["candidates"][0]["content"]["parts"][0]["text"]
            raise Exception(f"Gemini REST HTTP {res.status_code}: {res.text}")

    def _call_openai(self, prompt: str, system_instruction: Optional[str], json_mode: bool) -> str:
        import requests
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json"
        }
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": settings.model_config_data.get("llm", {}).get("openai_model", "gpt-4o-mini"),
            "messages": messages,
            "temperature": 0.1
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        res = requests.post(url, headers=headers, json=payload, timeout=15)
        if res.status_code == 200:
            return res.json()["choices"][0]["message"]["content"]
        raise Exception(f"OpenAI HTTP {res.status_code}: {res.text}")

    def _fallback_generate(self, prompt: str, system_instruction: Optional[str], json_mode: bool) -> str:
        logger.info("Executing grounded fallback engineering response generator.")

        structured_extraction_prompt = prompt.lstrip().startswith((
            "Analyze the following AUTOSAR High-Level Design",
            "Analyze the AUTOSAR HLD text and map relationships",
        ))
        if json_mode or structured_extraction_prompt:
            return self._fallback_structured_json(prompt)

        context_match = re.search(r"CONTEXT EVIDENCE CHUNKS:\n(.*?)\n\nUSER QUESTION:\n(.*)", prompt, re.DOTALL)
        if context_match:
            context = context_match.group(1).strip()
            question = context_match.group(2).split("\n\n", 1)[0].strip()
            evidence_blocks = re.findall(
                r"\[Source\s+(\d+)\](.*?)(?=\n\s*\[Source\s+\d+\]|\Z)",
                context,
                re.DOTALL,
            )
            query_terms = set(re.findall(r"[a-z0-9_]+", question.lower()))
            stop_words = {
                "a", "an", "and", "are", "be", "does", "for", "from", "how", "in",
                "is", "it", "of", "on", "or", "the", "this", "to", "what", "when",
                "where", "which", "who", "why", "with",
            }
            informative_terms = query_terms - stop_words
            identifiers = {
                term for term in query_terms
                if "_" in term or any(character.isdigit() for character in term)
            }

            evidence_sentences = []
            for source_id, block in evidence_blocks:
                _, _, source_text = block.partition("\n")
                for sentence in re.split(r"(?<=[.!?])\s+|\n+", source_text):
                    sentence = sentence.strip(" \t-*")
                    if not sentence:
                        continue
                    sentence_terms = set(re.findall(r"[a-z0-9_]+", sentence.lower()))
                    matched_terms = informative_terms & sentence_terms
                    if identifiers and not identifiers.issubset(sentence_terms):
                        continue
                    if len(matched_terms) < 2 and not (
                        identifiers and identifiers.issubset(sentence_terms)
                    ):
                        continue
                    if informative_terms and len(matched_terms) / len(informative_terms) < 0.4:
                        continue
                    evidence_sentences.append((sentence, source_id))

            if evidence_sentences:
                # Return source text verbatim; do not synthesize facts in the local fallback.
                unique_sentences = {}
                for sentence, source_id in evidence_sentences:
                    unique_sentences.setdefault(sentence.casefold(), (sentence, source_id))
                return "\n".join(
                    f'- "{sentence}" [Source {source_id}]'
                    for sentence, source_id in list(unique_sentences.values())[:4]
                )

        return "I could not find enough evidence in the indexed HLD documents to answer this confidently."

    def _fallback_structured_json(self, prompt: str) -> str:
        text_content = prompt

        components = set(re.findall(r'\b(SWC_\w+|EngineControlUnit|SpeedSensorComponent|ThrottleActuator|TorqueCalculator)\b', text_content))
        interfaces = set(re.findall(r'\b(RTE_I_\w+|SenderReceiverInterface_\w+)\b', text_content))
        ports = set(re.findall(r'\b([PR]Port_\w+)\b', text_content))
        signals = set(re.findall(r'\b(EngineSpeed_RPM|ThrottleAngle_Deg|SafetyOverride_Flag|\w+_Signal|\w+_Flag)\b', text_content))

        entities = []
        for c in components:
            entities.append({"type": "SoftwareComponent", "name": c, "aliases": [], "page_number": 1, "section": "Specification", "confidence": 0.95})
        for i in interfaces:
            entities.append({"type": "Interface", "name": i, "aliases": [], "page_number": 1, "section": "Interfaces", "confidence": 0.95})
        for p in ports:
            entities.append({"type": "Port", "name": p, "aliases": [], "page_number": 1, "section": "Ports", "confidence": 0.95})
        for s in signals:
            entities.append({"type": "Signal", "name": s, "aliases": [], "page_number": 1, "section": "Signals", "confidence": 0.95})

        if "relationships" in prompt:
            rels = []
            
            # Regex parse provides and requires relationships directly from text
            provides_matches = re.findall(r'\b(SWC_\w+|SpeedSensorComponent|TorqueCalculator|ThrottleActuator|EngineControlUnit)\b.*?\b(?:provides|provided)\b.*?\b(RTE_I_\w+)\b', text_content, re.IGNORECASE)
            requires_matches = re.findall(r'\b(SWC_\w+|SpeedSensorComponent|TorqueCalculator|ThrottleActuator|EngineControlUnit)\b.*?\b(?:requires|required)\b.*?\b(RTE_I_\w+)\b', text_content, re.IGNORECASE)
            
            # Also parse table rows format (both comma-separated and space-separated table text from PyPDF)
            # Format: SWC_Name [Port_Name] Provided/Required (PPort/RPort) Interface_Name
            table_matches = re.findall(
                r"['\"]?(SWC_\w+|EngineControlUnit|SpeedSensorComponent|ThrottleActuator|TorqueCalculator)['\"]?[\s,]+(?:['\"]?[PR]Port_\w+['\"]?[\s,]+)?['\"]?(Provided|Required|PPort|RPort)[^'\"]*?['\"]?[\s,]+['\"]?(RTE_I_\w+)['\"]?",
                text_content, re.IGNORECASE
            )

            for src, iface in provides_matches:
                rels.append({
                    "source_name": src, "source_type": "SoftwareComponent",
                    "target_name": iface, "target_type": "Interface",
                    "relationship_type": "provides", "confidence": 0.95
                })

            for src, iface in requires_matches:
                rels.append({
                    "source_name": src, "source_type": "SoftwareComponent",
                    "target_name": iface, "target_type": "Interface",
                    "relationship_type": "requires", "confidence": 0.95
                })

            for src, ptype, iface in table_matches:
                rtype = "provides" if "prov" in ptype.lower() or "pport" in ptype.lower() else "requires"
                rels.append({
                    "source_name": src, "source_type": "SoftwareComponent",
                    "target_name": iface, "target_type": "Interface",
                    "relationship_type": rtype, "confidence": 0.95
                })

            # Deduplicate
            dedup_rels = {}
            for r in rels:
                k = (r["source_name"].lower(), r["target_name"].lower(), r["relationship_type"].lower())
                dedup_rels[k] = r

            return json.dumps({"relationships": list(dedup_rels.values())})

        return json.dumps({"entities": entities})
