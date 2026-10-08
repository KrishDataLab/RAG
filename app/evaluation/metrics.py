import math
from typing import List, Dict, Any, Tuple

class EvaluationMetricsCalculator:
    @staticmethod
    def calculate_retrieval_recall(retrieved_pages: List[int], expected_pages: List[int]) -> float:
        if not expected_pages:
            return 1.0  # Unanswerable case
        hits = len(set(retrieved_pages) & set(expected_pages))
        return hits / len(expected_pages)

    @staticmethod
    def calculate_precision_recall_f1(predicted_items: List[str], ground_truth_items: List[str]) -> Tuple[float, float, float]:
        pred_set = set([p.lower().strip() for p in predicted_items])
        gt_set = set([g.lower().strip() for g in ground_truth_items])

        if not gt_set and not pred_set:
            return 1.0, 1.0, 1.0
        if not gt_set or not pred_set:
            return 0.0, 0.0, 0.0

        tp = len(pred_set & gt_set)
        fp = len(pred_set - gt_set)
        fn = len(gt_set - pred_set)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        return round(precision, 4), round(recall, 4), round(f1, 4)

    @staticmethod
    def calculate_per_class_entity_metrics(predicted_entities: List[Dict[str, Any]], ground_truth_by_class: Dict[str, List[str]]) -> Dict[str, Dict[str, float]]:
        per_class_results = {}

        # Group predicted entities by type
        pred_by_class = {}
        for ent in predicted_entities:
            etype = ent.get("type", ent.get("entity_type", "SoftwareComponent"))
            name = ent.get("name", ent.get("canonical_name", ""))
            pred_by_class.setdefault(etype, []).append(name)

        all_classes = set(list(ground_truth_by_class.keys()) + list(pred_by_class.keys()))

        for cls_name in all_classes:
            gt_list = ground_truth_by_class.get(cls_name, [])
            pred_list = pred_by_class.get(cls_name, [])
            p, r, f1 = EvaluationMetricsCalculator.calculate_precision_recall_f1(pred_list, gt_list)
            per_class_results[cls_name] = {
                "precision": p,
                "recall": r,
                "f1": f1,
                "predicted_count": len(pred_list),
                "ground_truth_count": len(gt_list)
            }

        return per_class_results

    @staticmethod
    def calculate_negative_abstention_metrics(question_evals: List[Dict[str, Any]]) -> Dict[str, float]:
        unanswerable_q = [q for q in question_evals if not q.get("is_answerable", True)]
        if not unanswerable_q:
            return {"unsupported_answer_rate": 0.0, "hallucination_rate": 0.0, "abstention_accuracy": 100.0}

        correct_abstentions = 0
        hallucinated_answers = 0

        for q in unanswerable_q:
            ans = q.get("answer_snippet", "").lower()
            if "could not find" in ans or "insufficient evidence" in ans or "not found" in ans:
                correct_abstentions += 1
            else:
                hallucinated_answers += 1

        total_unans = len(unanswerable_q)
        abstention_acc = (correct_abstentions / total_unans) * 100.0
        hallucination_rate = (hallucinated_answers / total_unans) * 100.0

        return {
            "unsupported_answer_rate": round(hallucination_rate, 2),
            "hallucination_rate": round(hallucination_rate, 2),
            "abstention_accuracy": round(abstention_acc, 2),
            "total_unanswerable_tested": total_unans
        }

    @staticmethod
    def calculate_percentile_latencies(latencies: List[float]) -> Dict[str, float]:
        if not latencies:
            return {"mean": 0.0, "median": 0.0, "p95": 0.0}
        sorted_l = sorted(latencies)
        n = len(sorted_l)
        
        avg = sum(sorted_l) / n
        mid = n // 2
        median = sorted_l[mid] if n % 2 != 0 else (sorted_l[mid - 1] + sorted_l[mid]) / 2.0
        p95_idx = min(n - 1, math.ceil(0.95 * n) - 1)
        p95 = sorted_l[p95_idx]

        return {
            "mean": round(avg, 3),
            "median": round(median, 3),
            "p95": round(p95, 3)
        }
