from typing import List, Dict, Any

class RevisionAligner:
    @staticmethod
    def align_entities(entities_a: List[Dict[str, Any]], entities_b: List[Dict[str, Any]]) -> Dict[str, Any]:
        map_a = {e["name"].lower(): e for e in entities_a}
        map_b = {e["name"].lower(): e for e in entities_b}

        names_a = set(map_a.keys())
        names_b = set(map_b.keys())

        added = [map_b[k] for k in (names_b - names_a)]
        removed = [map_a[k] for k in (names_a - names_b)]
        common = [k for k in (names_a & names_b)]

        changed = []
        for k in common:
            ent_a = map_a[k]
            ent_b = map_b[k]
            if ent_a["type"] != ent_b["type"]:
                changed.append({"name": ent_a["name"], "from_type": ent_a["type"], "to_type": ent_b["type"]})

        return {
            "added": added,
            "removed": removed,
            "changed": changed,
            "common_count": len(common)
        }
