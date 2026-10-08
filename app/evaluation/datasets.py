import json
from pathlib import Path
from typing import List, Dict, Any
from app.core.config import BASE_DIR

class EvaluationDatasetLoader:
    @staticmethod
    def load_benchmark_questions(version: str = "v2") -> List[Dict[str, Any]]:
        filename = f"benchmark_questions_{version}.jsonl" if version != "v1" else "benchmark_questions.jsonl"
        path = BASE_DIR / "evaluation" / filename
        items = []
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        items.append(json.loads(line))
        return items

    @staticmethod
    def load_entity_ground_truth(version: str = "v2") -> Dict[str, Any]:
        filename = f"entity_ground_truth_{version}.json" if version != "v1" else "entity_ground_truth.json"
        path = BASE_DIR / "evaluation" / filename
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"entities_by_class": {}}

    @staticmethod
    def load_inconsistency_ground_truth(version: str = "v2") -> Dict[str, Any]:
        filename = f"inconsistency_ground_truth_{version}.json" if version != "v1" else "inconsistency_ground_truth.json"
        path = BASE_DIR / "evaluation" / filename
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"inconsistencies": []}

    @staticmethod
    def load_manifest() -> Dict[str, Any]:
        path = BASE_DIR / "evaluation" / "benchmark_manifest.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
