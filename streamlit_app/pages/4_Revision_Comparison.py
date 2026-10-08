import streamlit as st
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from app.db.repositories import DatabaseRepository, SessionLocal
from app.llm.client import LLMClient
from app.comparison.diff import RevisionComparator

st.set_page_config(page_title="Revision Comparison - AHITA", page_icon="🔄", layout="wide")

st.title("🔄 Revision Comparison & Inconsistency Detection")
st.markdown("Compare Version A vs Version B of AUTOSAR HLD documents, align entity inventories, detect added/removed components, and trigger deterministic inconsistency rules.")

db = SessionLocal()
repo = DatabaseRepository(db)
llm_client = LLMClient()

docs = repo.get_documents("P001")
if len(docs) < 2:
    st.warning("Please ingest at least two documents (e.g. `HLD_v1.0_EngineControl.pdf` and `HLD_v1.1_EngineControl.pdf`) to run comparison.")
    st.stop()

doc_map = {f"{d.name} ({d.version_label}) - ID: {d.id}": d.id for d in docs}
doc_keys = list(doc_map.keys())

col1, col2 = st.columns(2)

with col1:
    doc_a_name = st.selectbox("Baseline Revision (Version A)", doc_keys, index=0)
    doc_a_id = doc_map[doc_a_name]

with col2:
    doc_b_name = st.selectbox("Target Revision (Version B)", doc_keys, index=min(1, len(doc_keys)-1))
    doc_b_id = doc_map[doc_b_name]

if st.button("Run Revision Comparison", type="primary"):
    with st.spinner("Aligning revisions and executing inconsistency rules..."):
        comparator = RevisionComparator(repo, llm_client)
        res = comparator.compare_documents(doc_a_id, doc_b_id, project_id="P001")

    st.success(f"Comparison completed! Found {res['findings_count']} potential inconsistencies.")
    
    st.markdown("### 📊 Entity Alignment Breakdown")
    align = res["alignment"]

    m1, m2, m3 = st.columns(3)
    m1.metric("Added Entities", len(align["added"]), delta_color="normal")
    m2.metric("Removed Entities", len(align["removed"]), delta_color="inverse")
    m3.metric("Changed Attributes", len(align["changed"]))

    if align["added"]:
        st.markdown("**Added Entities in Version B:**")
        st.dataframe(align["added"])

    if align["removed"]:
        st.markdown("**Removed Entities from Version A:**")
        st.dataframe(align["removed"])

    st.markdown("---")
    st.markdown("### 🚨 Detected Inconsistency Findings")
    if res["findings"]:
        for f in res["findings"]:
            with st.expander(f"⚠️ [{f['severity']}] {f['type']}: {f['summary']}"):
                st.markdown(f"**Description & AI Reason:**\n{f['description']}")
                st.info("Finding logged into Review Queue. Go to **5_Findings_Review** to confirm or mark false positive.")
    else:
        st.info("No architectural inconsistencies detected between selected revisions.")
