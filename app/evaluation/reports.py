import json
import pandas as pd
from pathlib import Path
from typing import Dict, Any
from app.core.config import BASE_DIR

class EvaluationReportExporter:
    @staticmethod
    def export_results(eval_results: Dict[str, Any], output_prefix: str = "T03"):
        output_dir = BASE_DIR / "Evaluation_Results"
        output_dir.mkdir(parents=True, exist_ok=True)

        json_path = output_dir / f"{output_prefix}_Benchmark_Results_v1.0.json"
        csv_path = output_dir / f"{output_prefix}_Metrics_v1.0.csv"

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(eval_results, f, indent=2)

        # Convert question details to DataFrame and save CSV
        df = pd.DataFrame(eval_results.get("question_details", []))
        df.to_csv(csv_path, index=False)

        return str(json_path), str(csv_path)
