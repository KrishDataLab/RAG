import re
from typing import List, Dict, Any
from app.core.config import settings

class ContextAwareChunker:
    def __init__(self, chunk_size: int = 250):
        self.chunk_size = settings.retrieval_config.get("retrieval", {}).get("chunk_size", chunk_size)

    def chunk_document(self, parsed_pdf: Dict[str, Any], doc_id: str, version_label: str) -> List[Dict[str, Any]]:
        chunks = []
        
        for page in parsed_pdf.get("pages", []):
            page_num = page["page_number"]
            page_section = page.get("section", "General")
            text = page.get("text", "")

            if not text:
                continue

            # Split by section headers or double linebreaks (Architectural boundaries)
            sub_sections = re.split(r'\n(?=\d+\.|\bSection\b|\bTable\b|\bFunctional Flow\b)', text)
            
            chunk_idx = 1
            for subsec in sub_sections:
                subsec_clean = subsec.strip()
                if not subsec_clean:
                    continue

                # Detect heading inside subsection
                lines = subsec_clean.split("\n")
                current_section = page_section
                if len(lines[0]) < 60 and any(h in lines[0] for h in ["Overview", "Specification", "Interface", "Flow", "Dependency"]):
                    current_section = lines[0].strip()

                # Extract entity context in chunk if present
                components = re.findall(r'\b(SWC_\w+|EngineControlUnit|SpeedSensorComponent|ThrottleActuator|TorqueCalculator)\b', subsec_clean)
                interfaces = re.findall(r'\b(RTE_I_\w+)\b', subsec_clean)
                ports = re.findall(r'\b([PR]Port_\w+)\b', subsec_clean)
                signals = re.findall(r'\b(EngineSpeed_RPM|ThrottleAngle_Deg|SafetyOverride_Flag)\b', subsec_clean)

                entity_ctx = list(set(components + interfaces + ports + signals))

                # Split further if text exceeds chunk_size
                if len(subsec_clean) <= self.chunk_size * 1.5:
                    chunk_id = f"{doc_id}-P{page_num:02d}-C{chunk_idx:02d}"
                    chunks.append({
                        "chunk_id": chunk_id,
                        "document_id": doc_id,
                        "document_name": parsed_pdf["file_name"],
                        "version_label": version_label,
                        "page_number": page_num,
                        "section": current_section,
                        "text": subsec_clean,
                        "entity_context": entity_ctx,
                        "source_type": "HLD"
                    })
                    chunk_idx += 1
                else:
                    # Paragraph splitting
                    paragraphs = [p.strip() for p in subsec_clean.split("\n\n") if p.strip()]
                    current_text = ""
                    for p in paragraphs:
                        if len(current_text) + len(p) <= self.chunk_size:
                            current_text += ("\n\n" if current_text else "") + p
                        else:
                            if current_text:
                                chunk_id = f"{doc_id}-P{page_num:02d}-C{chunk_idx:02d}"
                                chunks.append({
                                    "chunk_id": chunk_id,
                                    "document_id": doc_id,
                                    "document_name": parsed_pdf["file_name"],
                                    "version_label": version_label,
                                    "page_number": page_num,
                                    "section": current_section,
                                    "text": current_text.strip(),
                                    "entity_context": entity_ctx,
                                    "source_type": "HLD"
                                })
                                chunk_idx += 1
                                current_text = p
                            else:
                                current_text = p
                    
                    if current_text.strip():
                        chunk_id = f"{doc_id}-P{page_num:02d}-C{chunk_idx:02d}"
                        chunks.append({
                            "chunk_id": chunk_id,
                            "document_id": doc_id,
                            "document_name": parsed_pdf["file_name"],
                            "version_label": version_label,
                            "page_number": page_num,
                            "section": current_section,
                            "text": current_text.strip(),
                            "entity_context": entity_ctx,
                            "source_type": "HLD"
                        })
                        chunk_idx += 1

        return chunks
