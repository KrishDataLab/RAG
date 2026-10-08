import json
from typing import List, Dict, Any
from app.llm.client import LLMClient
from app.llm.prompts import prompt_manager
from app.llm.structured_output import StructuredOutputParser
from app.extraction.schemas import EntityExtractionResponse
from app.extraction.normalizer import EntityNormalizer
from app.db.repositories import DatabaseRepository
from app.core.logging import logger

class EntityExtractor:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def extract_from_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        extracted_all = []

        for chunk in chunks:
            page_num = chunk.get("page_number", 1)
            section = chunk.get("section", "General")
            text = chunk.get("text", "")

            prompt = prompt_manager.render(
                "entity_extraction_v1.txt",
                page_number=page_num,
                section=section,
                text=text
            )

            raw_res = self.llm_client.generate(prompt=prompt, json_mode=True)
            try:
                parsed = StructuredOutputParser.parse_json(raw_res, EntityExtractionResponse)
                for ent in parsed.entities:
                    ent_dict = ent.model_dump()
                    ent_dict["page_number"] = page_num
                    ent_dict["section"] = section
                    extracted_all.append(ent_dict)
            except Exception as e:
                logger.error(f"Failed entity parsing for chunk {chunk.get('chunk_id')}: {e}")

        # Deduplicate
        return EntityNormalizer.deduplicate_entities(extracted_all)
