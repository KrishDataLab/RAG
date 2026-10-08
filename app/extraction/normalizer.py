from typing import List, Dict, Any

class EntityNormalizer:
    @staticmethod
    def deduplicate_entities(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        deduped = {}
        for ent in entities:
            canonical = ent["name"].strip()
            # Normalize casing / spacing if required
            key = (ent["type"].lower(), canonical.lower())

            if key not in deduped:
                deduped[key] = {
                    "type": ent["type"],
                    "name": canonical,
                    "aliases": list(set(ent.get("aliases", []))),
                    "page_number": ent.get("page_number", 1),
                    "section": ent.get("section", ""),
                    "confidence": ent.get("confidence", 1.0)
                }
            else:
                # Merge aliases and keep highest confidence
                existing = deduped[key]
                existing["aliases"] = list(set(existing["aliases"] + ent.get("aliases", [])))
                existing["confidence"] = max(existing["confidence"], ent.get("confidence", 1.0))
        
        return list(deduped.values())
