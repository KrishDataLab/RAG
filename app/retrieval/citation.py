import re
from typing import List, Dict, Any, Tuple


class CitationValidator:
    REFUSAL_PHRASES = (
        "could not find enough evidence",
        "insufficient evidence",
        "not found in the indexed hld",
    )
    STOP_WORDS = {
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in",
        "is", "it", "of", "on", "or", "that", "the", "their", "this", "to",
        "via", "was", "were", "with",
    }

    @staticmethod
    def format_citations(evidence_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        citations = []
        for idx, chunk in enumerate(evidence_chunks, start=1):
            meta = chunk["metadata"]
            citations.append({
                "citation_id": f"Source {idx}",
                "document_id": meta.get("document_id", ""),
                "document_name": meta.get("document_name", ""),
                "version_label": meta.get("version_label", ""),
                "page": meta.get("page_number", 1),
                "section": meta.get("section", "General"),
                "chunk_id": meta.get("chunk_id", ""),
                "similarity_score": chunk.get("similarity_score", 0.0)
            })
        return citations

    @staticmethod
    def validate_grounding(answer: str, evidence_chunks: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        if not evidence_chunks:
            return False, ["No evidence chunks retrieved."]

        if any(phrase in answer.lower() for phrase in CitationValidator.REFUSAL_PHRASES):
            return True, ["System safely abstained due to insufficient evidence."]

        chunks_by_source = {
            str(index): chunk
            for index, chunk in enumerate(evidence_chunks, start=1)
        }
        answer = re.sub(r"\s+(\[Source\s+\d+\])", r"\1", answer)
        claims = [
            claim.strip(" \t-*\"'")
            for claim in re.split(r"(?<=[.!?])\s+|\n+", answer)
            if claim.strip(" \t-*\"'")
        ]
        if not claims:
            return False, ["Answer contains no verifiable claims."]

        for claim in claims:
            cited_source_ids = re.findall(r"\[Source\s+(\d+)\]", claim)
            if not cited_source_ids:
                return False, ["Warning: Answer is missing explicit [Source X] inline citation markers."]

            claim_text = re.sub(r"\[Source\s+\d+\]", "", claim).strip(" \t-*\"'")
            cited_chunks = [chunks_by_source.get(source_id) for source_id in cited_source_ids]
            if any(chunk is None for chunk in cited_chunks):
                return False, ["Answer cites a source that was not included in the retrieved evidence."]

            if not any(
                CitationValidator._claim_supported_by_chunk(claim_text, chunk)
                for chunk in cited_chunks
            ):
                return False, ["A cited retrieved passage does not lexically support an answer claim."]

        return True, [
            "Support is checked conservatively using cited-source matching and lexical overlap; semantic entailment is not guaranteed."
        ]

    @staticmethod
    def _claim_supported_by_chunk(claim: str, chunk: Dict[str, Any]) -> bool:
        evidence = str(chunk.get("text", ""))
        if claim.casefold() in evidence.casefold():
            return True

        claim_terms = set(re.findall(r"[a-z0-9_]+", claim.casefold()))
        evidence_terms = set(re.findall(r"[a-z0-9_]+", evidence.casefold()))
        meaningful_terms = claim_terms - CitationValidator.STOP_WORDS
        if len(meaningful_terms) < 2:
            return False

        identifiers = {
            term for term in meaningful_terms
            if "_" in term or any(character.isdigit() for character in term)
        }
        if not identifiers.issubset(evidence_terms):
            return False

        overlap = len(meaningful_terms & evidence_terms)
        return overlap >= 2 and overlap / len(meaningful_terms) >= 0.5
