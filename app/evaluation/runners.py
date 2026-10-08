import time
from typing import Dict, Any, List
from app.evaluation.datasets import EvaluationDatasetLoader
from app.evaluation.metrics import EvaluationMetricsCalculator
from app.retrieval.retriever import ArchitectureRetriever
from app.retrieval.citation import CitationValidator
from app.llm.client import LLMClient
from app.llm.prompts import prompt_manager
from app.db.repositories import DatabaseRepository

class EvaluationRunner:
    def __init__(self, retriever: ArchitectureRetriever, llm_client: LLMClient, repo: DatabaseRepository):
        self.retriever = retriever
        self.llm_client = llm_client
        self.repo = repo

    def run_benchmark(self, version: str = "v2", project_id: str = "P001", doc_id: str = None) -> Dict[str, Any]:
        questions = EvaluationDatasetLoader.load_benchmark_questions(version=version)
        entity_gt_data = EvaluationDatasetLoader.load_entity_ground_truth(version=version)
        inconsistent_gt = EvaluationDatasetLoader.load_inconsistency_ground_truth(version=version)
        manifest = EvaluationDatasetLoader.load_manifest()

        total_questions = len(questions)
        answerable_questions = [q for q in questions if q.get("is_answerable", True)]
        unanswerable_questions = [q for q in questions if not q.get("is_answerable", True)]

        retrieval_recalls = []
        grounded_flags = []
        citation_indicator_flags = []
        total_latencies = []

        q_results = []
        qa_outcomes = []

        for q_item in questions:
            start_t = time.time()
            q_text = q_item["question"]
            is_ans = q_item.get("is_answerable", True)
            exp_pages = q_item.get("expected_pages", [])
            doc_filter = [doc_id] if doc_id else None

            # 1. Retrieve
            chunks = self.retriever.retrieve(query=q_text, top_k=8, project_id=project_id, document_ids=doc_filter)
            ret_pages = [c["metadata"]["page_number"] for c in chunks]

            # 2. Metric: Recall@k (Calculated strictly for answerable questions)
            if is_ans:
                recall_score = EvaluationMetricsCalculator.calculate_retrieval_recall(ret_pages, exp_pages)
                retrieval_recalls.append(recall_score)
            else:
                recall_score = 1.0  # N/A Abstention

            # 3. Format citations & prompt
            citations = CitationValidator.format_citations(chunks)
            context_str = ""
            for index, c in enumerate(chunks, start=1):
                meta = c["metadata"]
                context_str += f"[Source {index}] Page: {meta.get('page_number')}, Section: {meta.get('section')}\n{c['text']}\n\n"

            system_prompt = prompt_manager.get_prompt("rag_system_v1.txt")
            rag_prompt = prompt_manager.render("rag_answer_v1.txt", context=context_str or "No evidence available.", question=q_text)

            # 4. Generate Answer
            answer = self.llm_client.generate(prompt=rag_prompt, system_instruction=system_prompt)
            latency = time.time() - start_t
            total_latencies.append(latency)

            # 5. Grounding & Citation Validation
            is_grounded, limitations = CitationValidator.validate_grounding(answer, chunks)
            grounded_flags.append(1.0 if is_grounded else 0.0)
            has_citations = ("Source" in answer or "Page" in answer or not chunks or not is_ans)
            citation_indicator_flags.append(1.0 if has_citations else 0.0)

            # 6. Authoritative Q&A Outcome Classification (CORRECT_ANSWER / CORRECT_ABSTENTION / INCORRECT_ANSWER / INCORRECT_ABSTENTION)
            ans_lower = answer.lower()
            is_abstained_msg = ("could not find" in ans_lower or "insufficient evidence" in ans_lower or "not found" in ans_lower)

            if is_ans:
                if is_abstained_msg:
                    outcome = "INCORRECT_ABSTENTION"
                else:
                    exp_keywords = q_item.get("expected_keywords", [])
                    kw_matched = any(kw.lower() in ans_lower for kw in exp_keywords) if exp_keywords else True
                    outcome = "CORRECT_ANSWER" if (is_grounded and kw_matched) else "INCORRECT_ANSWER"
            else:
                if is_abstained_msg:
                    outcome = "CORRECT_ABSTENTION"
                else:
                    outcome = "INCORRECT_ANSWER"

            qa_outcomes.append({
                "question_id": q_item["id"],
                "question": q_text,
                "category": q_item["category"],
                "is_answerable": is_ans,
                "outcome": outcome,
                "is_grounded": is_grounded,
                "has_citations": has_citations,
                "latency_sec": round(latency, 3),
                "answer_snippet": answer[:150] + "..."
            })

            q_results.append({
                "id": q_item["id"],
                "question": q_text,
                "category": q_item["category"],
                "is_answerable": is_ans,
                "recall_at_k": recall_score,
                "grounded": is_grounded,
                "citation_indicator_present": has_citations,
                "outcome": outcome,
                "latency_sec": round(latency, 3),
                "answer_snippet": answer[:150] + "..."
            })

        # Summary averages & percentiles
        mean_ans_recall = sum(retrieval_recalls) / max(len(answerable_questions), 1)
        groundedness_rate = (sum(grounded_flags) / max(total_questions, 1)) * 100.0
        citation_indicator_rate = (sum(citation_indicator_flags) / max(total_questions, 1)) * 100.0
        latency_stats = EvaluationMetricsCalculator.calculate_percentile_latencies(total_latencies)

        # Answer Accuracy Calculation (Explicit Metric)
        correct_ans_count = sum(1 for q in qa_outcomes if q.get("is_answerable") and q.get("outcome") == "CORRECT_ANSWER")
        answer_accuracy_pct = round((correct_ans_count / max(len(answerable_questions), 1)) * 100.0, 2)

        # Negative / Abstention Metrics
        negative_metrics = EvaluationMetricsCalculator.calculate_negative_abstention_metrics(q_results)

        # Entity Extraction Per-Class Breakdown
        db_entities = [e.__dict__ for e in self.repo.get_entities(doc_id)]
        for e in db_entities:
            e.pop("_sa_instance_state", None)

        gt_by_class = entity_gt_data.get("entities_by_class", {})
        per_class_entities = EvaluationMetricsCalculator.calculate_per_class_entity_metrics(db_entities, gt_by_class)

        all_pred = [e.get("canonical_name", e.get("name")) for e in db_entities]
        all_gt = [item for sublist in gt_by_class.values() for item in sublist]
        overall_e_p, overall_e_r, overall_e_f1 = EvaluationMetricsCalculator.calculate_precision_recall_f1(all_pred, all_gt)

        # Inconsistency Detection Metrics (Authoritative Reconciliation)
        db_findings = self.repo.get_findings(project_id)
        detected_finding_types = list(set([f["type"] for f in db_findings]))
        gt_finding_types = list(set([g["expected_rule"] for g in inconsistent_gt.get("inconsistencies", [])]))
        
        i_prec, i_rec, i_f1 = EvaluationMetricsCalculator.calculate_precision_recall_f1(detected_finding_types, gt_finding_types)

        # Inference Modes Status
        provider_status = self.llm_client.get_provider_status()
        inference_modes = {
            "mode_a_local_fallback": {
                "status": "COMPLETED",
                "active": provider_status["active_provider"] == "fallback",
                "description": "Local deterministic response fallback"
            },
            "mode_b_configured_llm": {
                "status": "COMPLETED" if provider_status["active_provider"] in ["gemini", "openai"] else "NOT RUN (Credentials missing)",
                "active": provider_status["active_provider"] in ["gemini", "openai"],
                "description": f"Configured LLM ({provider_status['requested_provider']})"
            }
        }

        eval_metadata = {
            "benchmark_version": version,
            "benchmark_size": total_questions,
            "answerable_count": len(answerable_questions),
            "unanswerable_count": len(unanswerable_questions),
            "evaluation_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "model_provider": provider_status["active_provider"],
            "retrieval_algorithm": "BM25",
            "top_k": 8
        }

        return {
            "evaluation_metadata": eval_metadata,
            "inference_modes": inference_modes,
            "summary": {
                "total_questions_tested": total_questions,
                "answerable_questions_tested": len(answerable_questions),
                "unanswerable_questions_tested": len(unanswerable_questions),
                "answer_accuracy": answer_accuracy_pct,
                "correct_answerable_count": correct_ans_count,
                "mean_recall_at_k": round(mean_ans_recall, 4),
                "grounded_answer_rate": round(groundedness_rate, 2),
                "citation_indicator_rate": round(citation_indicator_rate, 2),
                "abstention_accuracy": negative_metrics["abstention_accuracy"],
                "unsupported_answer_rate": negative_metrics["unsupported_answer_rate"],
                "hallucination_rate": negative_metrics["hallucination_rate"],
                "entity_precision": round(overall_e_p, 4),
                "entity_recall": round(overall_e_r, 4),
                "entity_extraction_f1": round(overall_e_f1, 4),
                "inconsistency_precision": round(i_prec, 4),
                "inconsistency_recall": round(i_rec, 4),
                "inconsistency_f1": round(i_f1, 4),
                "average_latency_sec": latency_stats["mean"],
                "median_latency_sec": latency_stats["median"],
                "p95_latency_sec": latency_stats["p95"]
            },
            "per_class_entity_metrics": per_class_entities,
            "latency_summary": latency_stats,
            "question_details": q_results,
            "qa_outcomes": qa_outcomes
        }
