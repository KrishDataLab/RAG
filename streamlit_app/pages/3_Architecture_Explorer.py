import streamlit as st
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from app.db.repositories import DatabaseRepository, SessionLocal
from app.llm.client import LLMClient
from app.extraction.entities import EntityExtractor
from app.extraction.relationships import RelationshipExtractor

st.set_page_config(page_title="Architecture Explorer - AHITA", page_icon="🏗️", layout="wide")

st.title("🏗️ Architecture Explorer & Entity Inventory")
st.markdown("Explore extracted AUTOSAR components, interfaces, ports, signals, dependencies, and view interactive architecture diagrams.")

db = SessionLocal()
repo = DatabaseRepository(db)
llm_client = LLMClient()

docs = repo.get_documents("P001")
if not docs:
    st.warning("No ingested documents found. Please ingest a document first.")
    st.stop()

doc_options = {f"{d.name} ({d.version_label})": d.id for d in docs}
selected_doc_name = st.selectbox("Select Target Document for Extraction/View", list(doc_options.keys()))
selected_doc_id = doc_options[selected_doc_name]

col1, col2 = st.columns([1, 1])

with col1:
    if st.button("Extract Entities & Relationships", type="primary"):
        with st.spinner("Extracting AUTOSAR entities & mapping dependencies..."):
            chunks_rec = repo.get_chunks_by_document(selected_doc_id)
            chunks_data = [c.__dict__ for c in chunks_rec]
            for c in chunks_data:
                c.pop("_sa_instance_state", None)

            extractor = EntityExtractor(llm_client)
            entities = extractor.extract_from_chunks(chunks_data)

            rel_extractor = RelationshipExtractor(llm_client)
            rels = rel_extractor.extract_relationships(chunks_data, entities)

            repo.save_entities_and_relationships(selected_doc_id, entities, rels)

        st.success(f"Extraction complete! Extracted {len(entities)} entities and {len(rels)} relationships.")

entities_rec = repo.get_entities(selected_doc_id)
rels_rec = repo.get_relationships(selected_doc_id)

st.markdown("---")

tab1, tab2, tab3 = st.tabs(["🧩 Entity Inventory", "🔗 Relationships & Dependencies", "📊 Architecture Graph"])

with tab1:
    st.subheader("Extracted Entity Inventory")
    if entities_rec:
        type_filter = st.multiselect("Filter Entity Types", list(set([e.entity_type for e in entities_rec])), default=list(set([e.entity_type for e in entities_rec])))
        search_query = st.text_input("Search Entity Name", "")

        table_data = []
        for e in entities_rec:
            if e.entity_type in type_filter:
                if not search_query or search_query.lower() in e.canonical_name.lower():
                    table_data.append({
                        "Entity ID": e.id,
                        "Type": e.entity_type,
                        "Canonical Name": e.canonical_name,
                        "Confidence": f"{e.confidence * 100:.0f}%",
                        "Extraction Ver": e.extraction_version
                    })
        st.dataframe(table_data, use_container_width=True)
    else:
        st.info("No entities extracted yet for this document. Click 'Extract Entities & Relationships' above.")

with tab2:
    st.subheader("Component-to-Interface Dependencies")
    if rels_rec:
        st.dataframe(rels_rec, use_container_width=True)
    else:
        st.info("No relationships mapped yet.")

with tab3:
    st.subheader("Mermaid Architecture Graph")
    if rels_rec:
        mermaid_lines = ["graph TD"]
        for r in rels_rec:
            src = r["source_name"].replace(" ", "_")
            tgt = r["target_name"].replace(" ", "_")
            rtype = r["relationship_type"]
            mermaid_lines.append(f'    {src} -- "{rtype}" --> {tgt}')

        mermaid_code = "\n".join(mermaid_lines)
        st.code(mermaid_code, language="mermaid")
        st.caption("Copy & paste into any Mermaid diagram viewer or Github markdown.")
    else:
        st.info("Extract relationships to view the generated Mermaid architecture graph.")
