import re
from typing import List, Dict, Any, Tuple

class CitationValidator:
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

        # Check if answer contains refusal or abstention
        refusal_phrases = [
            "could not find enough evidence",
            "insufficient evidence",
            "not found in the indexed hld"
        ]
        if any(phrase in answer.lower() for phrase in refusal_phrases):
            return True, ["System safely abstained due to insufficient evidence."]

        # This checks citation-like markers, not claim-to-passage support.
        has_citations = bool(re.search(r"\[Source \d+\]", answer)) or "Page" in answer or "Document:" in answer
        
        limitations = ["Retrieved passages are listed; claim-level citation support is not verified."]
        if not has_citations:
            limitations.append("Warning: Answer is missing explicit [Source X] inline citation markers.")

        return True, limitations
