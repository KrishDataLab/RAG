import streamlit as st
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.db.repositories import DatabaseRepository, SessionLocal
from app.core.config import settings

st.set_page_config(
    page_title="AHITA - AUTOSAR Assistant",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Dark Glassmorphism & Automotive Theme)
st.markdown("""
<style>
    .main {
        background-color: #0F172A;
        color: #F8FAFC;
    }
    .stApp {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
    }
    .hero-box {
        background: rgba(30, 41, 59, 0.7);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 30px;
        margin-bottom: 25px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }
    .card-metric {
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.15) 0%, rgba(37, 99, 235, 0.05) 100%);
        border-left: 4px solid #3B82F6;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
    }
    .title-text {
        font-family: 'Inter', sans-serif;
        font-size: 32px;
        font-weight: 700;
        background: linear-gradient(90deg, #60A5FA 0%, #93C5FD 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .sub-text {
        color: #94A3B8;
        font-size: 16px;
    }
</style>
""", unsafe_allow_html=True)

db = SessionLocal()
repo = DatabaseRepository(db)

# Sidebar
st.sidebar.image("https://img.icons8.com/color/96/000000/car--v1.png", width=64)
st.sidebar.title("AHITA Navigation")
st.sidebar.markdown("**Project Workspace:** `P001`")
st.sidebar.info("System Status: **ACTIVE**\nVector Index: **READY**")

# Hero Banner
st.markdown("""
<div class="hero-box">
    <div class="title-text">AUTOSAR HLD Intelligence & Traceability Assistant (AHITA)</div>
    <p class="sub-text">Evidence-Grounded AI Engineering Assistant for Automotive High-Level Design (HLD) Extraction, Traceability & Revision Comparison.</p>
</div>
""", unsafe_allow_html=True)

# Metrics Row
col1, col2, col3, col4 = st.columns(4)

docs = repo.get_documents("P001")
findings = repo.get_findings("P001")
needs_review = [f for f in findings if f["status"] == "NEEDS_REVIEW"]
entities = repo.get_entities()

with col1:
    st.markdown(f"""
    <div class="card-metric">
        <h4 style="color: #94A3B8; margin:0;">Indexed Documents</h4>
        <h2 style="color: #60A5FA; margin:0;">{len(docs)}</h2>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="card-metric">
        <h4 style="color: #94A3B8; margin:0;">Extracted Entities</h4>
        <h2 style="color: #34D399; margin:0;">{len(entities)}</h2>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="card-metric">
        <h4 style="color: #94A3B8; margin:0;">Total Findings</h4>
        <h2 style="color: #FBBF24; margin:0;">{len(findings)}</h2>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="card-metric">
        <h4 style="color: #94A3B8; margin:0;">Needs Review</h4>
        <h2 style="color: #F87171; margin:0;">{len(needs_review)}</h2>
    </div>
    """, unsafe_allow_html=True)

st.markdown("### 🛠 Quick Workflows")
w_col1, w_col2, w_col3 = st.columns(3)

with w_col1:
    st.markdown("""
    #### 1️⃣ Document Ingestion
    Upload AUTOSAR HLD PDFs, extract page-aware text and metadata, and index chunks with local BM25 retrieval. Low-text pages are flagged; OCR is not performed in this release.
    """)
    if st.button("Go to Ingestion ➔"):
        st.switch_page("pages/1_Ingestion.py")

with w_col2:
    st.markdown("""
    #### 2️⃣ Engineering Q&A
    Ask natural-language questions grounded strictly in document evidence with page/section citations.
    """)
    if st.button("Go to Q&A Assistant ➔"):
        st.switch_page("pages/2_QA_Assistant.py")

with w_col3:
    st.markdown("""
    #### 3️⃣ Revision & Inconsistent Diff
    Compare Version A vs Version B HLDs, detect entity diffs, and review flagged inconsistencies.
    """)
    if st.button("Go to Comparison ➔"):
        st.switch_page("pages/4_Revision_Comparison.py")

st.markdown("---")
st.markdown("### 📋 Active Document Inventory")
if docs:
    doc_table = []
    for d in docs:
        doc_table.append({
            "Document ID": d.id,
            "Document Name": d.name,
            "Version": d.version_label,
            "Pages": d.page_count,
            "Status": d.ingestion_status,
            "Created At": d.created_at.strftime("%Y-%m-%d %H:%M")
        })
    st.dataframe(doc_table, use_container_width=True)
else:
    st.info("No documents uploaded yet. Go to **1_Ingestion** to upload `HLD_v1.0_EngineControl.pdf`.")
