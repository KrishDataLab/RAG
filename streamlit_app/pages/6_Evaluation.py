import streamlit as st
import json
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from app.db.repositories import DatabaseRepository, SessionLocal
from app.retrieval.vector_store import MemoryVectorStore
from app.retrieval.retriever import ArchitectureRetriever
from app.llm.client import LLMClient
from app.evaluation.runners import EvaluationRunner
from app.evaluation.reports import EvaluationReportExporter

st.set_page_config(page_title="Evaluation Dashboard - AHITA", page_icon="📈", layout="wide")

st.title("📈 System Evaluation & Benchmark Dashboard")
st.markdown("Run the benchmark suite for BM25 retrieval recall, answer-validator outcomes, citation-indicator presence, entity extraction, and response latency.")

db = SessionLocal()
repo = DatabaseRepository(db)
vector_store = MemoryVectorStore(load_existing=True)
retriever = ArchitectureRetriever(vector_store)
llm_client = LLMClient()

if st.button("🚀 Execute Capstone Evaluation Suite", type="primary"):
    with st.spinner("Running benchmark questions against indexed vector store..."):
        runner = EvaluationRunner(retriever, llm_client, repo)
        results = runner.run_benchmark(project_id="P001")
        json_path, csv_path = EvaluationReportExporter.export_results(results)

    st.success("Evaluation suite completed!")
    st.session_state["eval_results"] = results
    st.session_state["json_path"] = json_path
    st.session_state["csv_path"] = csv_path

if "eval_results" in st.session_state:
    res = st.session_state["eval_results"]
    summary = res["summary"]

    st.markdown("### 📊 Metrics Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Recall @ K", f"{summary['mean_recall_at_k'] * 100:.1f}%")
    c2.metric("Groundedness Rate", f"{summary['grounded_answer_rate']}%")
    c3.metric("Citation Indicator Rate", f"{summary['citation_indicator_rate']}%")
    c4.metric("Entity Extraction F1", f"{summary['entity_extraction_f1'] * 100:.1f}%")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Entity Precision", f"{summary['entity_precision'] * 100:.1f}%")
    c6.metric("Entity Recall", f"{summary['entity_recall'] * 100:.1f}%")
    c7.metric("Avg Latency", f"{summary['average_latency_sec']} sec")
    c8.metric("Test Questions", summary['total_questions_tested'])

    st.markdown("---")
    st.markdown("### 🔍 Benchmark Question Breakdown")
    q_df = res["question_details"]
    st.dataframe(q_df, use_container_width=True)

    st.markdown("---")
    st.markdown("### 📁 Export Evaluation Artifacts")
    e_col1, e_col2 = st.columns(2)
    with e_col1:
        st.write(f"JSON Output: `{st.session_state['json_path']}`")
        with open(st.session_state['json_path'], "rb") as f:
            st.download_button("Download JSON Results", f, file_name="T03_Benchmark_Results_v1.0.json")
    with e_col2:
        st.write(f"CSV Metrics: `{st.session_state['csv_path']}`")
        with open(st.session_state['csv_path'], "rb") as f:
            st.download_button("Download CSV Metrics", f, file_name="T03_Metrics_v1.0.csv")
else:
    st.info("Click 'Execute Capstone Evaluation Suite' to run the benchmark evaluation.")
