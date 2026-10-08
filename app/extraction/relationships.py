import json
from typing import List, Dict, Any
from app.llm.client import LLMClient
from app.llm.prompts import prompt_manager
from app.llm.structured_output import StructuredOutputParser
from app.extraction.schemas import RelationshipExtractionResponse
from app.core.logging import logger

class RelationshipExtractor:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def extract_relationships(self, chunks: List[Dict[str, Any]], entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        extracted_rels = []
        entities_json = json.dumps([{"name": e["name"], "type": e["type"]} for e in entities])

        for chunk in chunks:
            page_num = chunk.get("page_number", 1)
            section = chunk.get("section", "General")
            text = chunk.get("text", "")

            prompt = prompt_manager.render(
                "relationship_extraction_v1.txt",
                page_number=page_num,
                section=section,
                text=text,
                entities_json=entities_json
            )

            raw_res = self.llm_client.generate(prompt=prompt, json_mode=True)
            try:
                parsed = StructuredOutputParser.parse_json(raw_res, RelationshipExtractionResponse)
                for r in parsed.relationships:
                    r_dict = r.model_dump()
                    r_dict["source_page"] = page_num
                    extracted_rels.append(r_dict)
            except Exception as e:
                logger.error(f"Failed relationship parsing for chunk {chunk.get('chunk_id')}: {e}")

        # Deduplicate relationships
        deduped = {}
        for r in extracted_rels:
            key = (r["source_name"].lower(), r["target_name"].lower(), r["relationship_type"].lower())
            if key not in deduped:
                deduped[key] = r
        
        return list(deduped.values())
