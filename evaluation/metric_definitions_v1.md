# AHITA Evaluation Metric Definitions (v1.0)

This document describes the metrics calculated by the current release. Groundedness and citation indicators are code-level heuristics, not human-verified factual-support measures.

---

## 1. Q&A Answer Correctness Metrics

### 1.1 Answer Accuracy (Answerable Questions)
- **Definition**: The percentage of answerable benchmark questions where the generated system answer is factually correct, grounded in retrieved HLD evidence, and matches expected architectural keywords/entities.
- **Formula**:
  $$\text{Answer Accuracy} = \frac{\text{Count of Answerable Questions with CORRECT\_ANSWER}}{\text{Total Answerable Questions in Benchmark}} \times 100\%$$
- **Denominator**: Total Answerable Questions ($N_{\text{ans}} = 15$ for development benchmark, $N_{\text{ans}} = 9$ for holdout benchmark).
- **Note**: This metric is reported **separately** from Grounded Answer Rate and is NEVER substituted by groundedness.

---

## 2. Retrieval Recall Metrics

Retrieval metrics are evaluated strictly on **answerable questions** ($N_{\text{ans}}$). Unanswerable questions are excluded from retrieval recall calculations.

### 2.1 Cumulative Hits@K & Recall@K ($K \in \{1, 3, 5, 8\}$)
- **Definition**: The percentage of answerable questions for which at least one expected ground-truth document page is retrieved within the top $K$ context chunks.
- **Formula**:
  $$\text{Recall@K} = \frac{\text{Hits@K}}{N_{\text{ans}}} = \frac{\sum_{i=1}^{N_{\text{ans}}} \mathbb{I}(\text{RetrievedPages}_i[:K] \cap \text{ExpectedPages}_i \neq \emptyset)}{N_{\text{ans}}} \times 100\%$$
- **Denominator**: $N_{\text{ans}}$ (Total Answerable Questions).

### 2.2 Mean Recall@8 (Per-Question Arithmetic Mean)
- **Definition**: The arithmetic mean of the per-question fractional page overlap at $K=8$.
- **Formula**:
  $$\text{Mean Recall@8} = \frac{1}{N_{\text{ans}}} \sum_{i=1}^{N_{\text{ans}}} \frac{|\text{RetrievedPages}_i[:8] \cap \text{ExpectedPages}_i|}{|\text{ExpectedPages}_i|}$$
- **Denominator**: $N_{\text{ans}}$ (Total Answerable Questions).

---

## 3. Grounding, Citation & Abstention Safety Metrics

### 3.1 Grounding-Validator Pass Rate
- **Definition**: The percentage of responses for which `CitationValidator.validate_grounding` returns true. The validator treats any non-empty retrieved passage set as grounded; it does not compare claims with evidence.
- **Formula**:
  $$\text{Grounded Answer Rate} = \frac{\text{Count of Grounded Responses}}{\text{Total Questions Tested}} \times 100\%$$
- **Denominator**: Total Questions Tested ($N_{\text{total}} = 20$).

### 3.2 Citation-Indicator Rate
- **Definition**: The percentage of responses where the evaluator's simple marker test succeeds (`Source` or `Page` appears, or the case is unanswerable/has no chunks). This is not citation accuracy and does not verify source IDs, page mappings, or claim support.
- **Formula**:
  $$\text{Citation Accuracy} = \frac{\text{Count of Validly Cited Responses}}{\text{Total Questions Tested}} \times 100\%$$
- **Denominator**: Total Questions Tested ($N_{\text{total}} = 20$).

### 3.3 Abstention Accuracy (Unanswerable Safety)
- **Definition**: The percentage of out-of-scope / unanswerable questions where the system correctly abstains and explicitly states that sufficient evidence is not present in the indexed HLDs.
- **Formula**:
  $$\text{Abstention Accuracy} = \frac{\text{Count of Correct Abstentions}}{\text{Total Unanswerable Questions}} \times 100\%$$
- **Denominator**: Total Unanswerable Questions ($N_{\text{unans}} = 5$ for development benchmark, $N_{\text{unans}} = 3$ for holdout benchmark).

### 3.4 Non-Abstention Rate on Unanswerable Questions
- **Definition**: The percentage of unanswerable benchmark questions where the response does not contain one of the configured abstention phrases. This string-based proxy cannot establish whether a response is factually fabricated.
- **Formula**:
  $$\text{Hallucination Rate} = \frac{\text{Count of Fabricated Answers on Unanswerable Qs}}{\text{Total Unanswerable Questions}} \times 100\%$$
- This is a response-pattern metric, not a semantic hallucination detector.

---

## 4. Revision Inconsistency Detection Metrics

Evaluates the rule engine's ability to detect architectural conflicts across document revisions (e.g., `INTERFACE_MISMATCH`, `REMOVED_COMPONENT`, `UNMAPPED_INTERFACE`).

$$\text{Precision} = \frac{TP}{TP + FP}, \quad \text{Recall} = \frac{TP}{TP + FN}, \quad \text{F1} = \frac{2 \times \text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$$

- **True Positives ($TP$)**: Expected inconsistency rules correctly flagged in the database.
- **False Positives ($FP$)**: Spurious inconsistency rules incorrectly flagged.
- **False Negatives ($FN$)**: Expected inconsistency rules missed by the comparator engine.
