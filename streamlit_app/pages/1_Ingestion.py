import streamlit as st
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from app.db.repositories import DatabaseRepository, SessionLocal
from app.retrieval.vector_store import MemoryVectorStore
from app.ingestion.pipeline import IngestionPipeline
from app.core.config import settings, BASE_DIR
from app.core.exceptions import DocumentProcessingError

st.set_page_config(page_title="Document Ingestion - AHITA", page_icon="📄", layout="wide")

st.title("📄 Document Ingestion Pipeline")
st.markdown("Upload AUTOSAR HLD PDFs, extract page-aware text and metadata, and index chunks for local BM25 retrieval. Low-text pages are detected but not OCR-processed.")

db = SessionLocal()
repo = DatabaseRepository(db)
vector_store = MemoryVectorStore(load_existing=True)

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Upload PDF Document")
    uploaded_file = st.file_uploader("Choose an AUTOSAR HLD PDF", type=["pdf"])
    version_label = st.text_input("Document Version Label", value="v1.0")
    project_id = st.text_input("Project ID", value="P001")

    if uploaded_file and st.button("Process & Index Document", type="primary"):
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        safe_filename = os.path.basename(uploaded_file.name.replace("\\", "/"))
        file_path = os.path.join(settings.UPLOAD_DIR, safe_filename)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        try:
            with st.spinner("Parsing PDF, chunking, and indexing for BM25 retrieval..."):
                pipeline = IngestionPipeline(repo, vector_store)
                res = pipeline.run(file_path=file_path, project_id=project_id, version_label=version_label)

            if res["status"] in ["SUCCESS", "ALREADY_EXISTS"]:
                st.success(f"Document processed successfully! ID: `{res['document_id']}`")
                st.json(res)
            else:
                st.error("Failed to process document.")
        except DocumentProcessingError as error:
            st.error(f"PDF processing failed: {error}")

with col2:
    st.subheader("Preset Sample HLD Documents")
    st.info("Quick option: Ingest pre-generated realistic sample AUTOSAR HLD PDFs for instant testing.")
    
    sample_dir = str(BASE_DIR.parent / "Input_Data")
    sample_files = [f for f in os.listdir(sample_dir) if f.endswith(".pdf")] if os.path.exists(sample_dir) else []

    selected_sample = st.selectbox("Select Sample PDF", sample_files if sample_files else ["None"])
    sample_ver = st.selectbox("Assign Version", ["v1.0", "v1.1"])

    if st.button("Ingest Selected Sample PDF"):
        if selected_sample and selected_sample != "None":
            sample_path = os.path.join(sample_dir, selected_sample)
            with st.spinner("Ingesting sample PDF..."):
                pipeline = IngestionPipeline(repo, vector_store)
                res = pipeline.run(file_path=sample_path, project_id="P001", version_label=sample_ver)
            st.success(f"Ingested {selected_sample} successfully!")
            st.json(res)

st.markdown("---")
st.subheader("Currently Ingested Documents")
docs = repo.get_documents("P001")
if docs:
    for d in docs:
        with st.expander(f"📌 {d.name} ({d.version_label}) - ID: {d.id}"):
            st.write(f"**Pages:** {d.page_count} | **Hash:** `{d.sha256[:16]}...` | **Status:** `{d.ingestion_status}`")
            chunks = repo.get_chunks_by_document(d.id)
            st.write(f"**Total Chunks:** {len(chunks)}")
            if chunks:
                st.markdown("**Sample Chunk Preview:**")
                st.code(f"Chunk ID: {chunks[0].chunk_id}\nSection: {chunks[0].section}\n\n{chunks[0].text[:250]}...")
