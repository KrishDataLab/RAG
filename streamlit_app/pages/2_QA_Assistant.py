import streamlit as st
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from app.db.repositories import DatabaseRepository, SessionLocal
from app.retrieval.vector_store import MemoryVectorStore
from app.retrieval.retriever import ArchitectureRetriever
from app.retrieval.citation import CitationValidator
from app.llm.client import LLMClient
from app.llm.prompts import prompt_manager
from app.llm.guardrails import SafetyGuardrails

st.set_page_config(page_title="Q&A Assistant - AHITA", page_icon="💬", layout="wide")

st.title("💬 Evidence-Grounded Engineering Q&A")
st.markdown("Ask about AUTOSAR components, interfaces, ports, signals, and flows. Answers include references to retrieved passages; citations are not validated claim by claim.")

db = SessionLocal()
repo = DatabaseRepository(db)
vector_store = MemoryVectorStore(load_existing=True)
retriever = ArchitectureRetriever(vector_store)
llm_client = LLMClient()

# Filters
docs = repo.get_documents("P001")
doc_options = {"All Documents": None}
for d in docs:
    doc_options[f"{d.name} ({d.version_label})"] = d.id

st.sidebar.subheader("Retrieval Filters")
selected_doc_label = st.sidebar.selectbox("Filter Document Scope", list(doc_options.keys()))
doc_filter = [doc_options[selected_doc_label]] if doc_options[selected_doc_label] else None
top_k = st.sidebar.slider("Top-K Evidence Chunks", min_value=2, max_value=12, value=8)

# Preset Questions
preset_questions = [
    "Select a sample question...",
    "What software components communicate through the RTE_I_EngineSpeed interface?",
    "Which component owns signal EngineSpeed_RPM?",
    "What ports are associated with SWC_TorqueCalc?",
    "Summarise the functional flow FF_Torque_Control.",
    "Is there any component managing battery charging in this ECU?"
]

selected_preset = st.selectbox("Preset Example Questions", preset_questions)
user_query = st.text_input("Or enter your custom engineering question:", value="" if selected_preset == preset_questions[0] else selected_preset)

if st.button("Ask Assistant", type="primary") and user_query.strip():
    # Prompt injection check
    is_injection, msg = SafetyGuardrails.check_prompt_injection(user_query)
    if is_injection:
        st.error(f"⚠️ {msg}")
    else:
        with st.spinner("Retrieving evidence chunks & generating grounded answer..."):
            chunks = retriever.retrieve(query=user_query, top_k=top_k, project_id="P001", document_ids=doc_filter)

            if not chunks:
                st.warning("⚠️ I could not find enough evidence in the indexed HLD documents to answer this confidently.")
            else:
                citations = CitationValidator.format_citations(chunks)

                context_str = ""
                for idx, c in enumerate(chunks, start=1):
                    meta = c["metadata"]
                    context_str += f"[Source {idx}] Document: {meta.get('document_name')}, Version: {meta.get('version_label')}, Page: {meta.get('page_number')}, Section: {meta.get('section')}\n{c['text']}\n\n"

                system_prompt = prompt_manager.get_prompt("rag_system_v1.txt")
                rag_prompt = prompt_manager.render("rag_answer_v1.txt", context=context_str, question=user_query)

                answer = llm_client.generate(prompt=rag_prompt, system_instruction=system_prompt)
                is_grounded, limitations = CitationValidator.validate_grounding(answer, chunks)

                st.markdown("### 📌 Generated Answer")
                st.markdown(answer)

                st.markdown("---")
                st.markdown("### 🔍 Retrieved Source Passages")
                cit_cols = st.columns(min(len(citations), 4))
                for idx, cit in enumerate(citations):
                    with cit_cols[idx % 4]:
                        st.markdown(f"""
                        <div style="background: rgba(59, 130, 246, 0.1); border: 1px solid #3B82F6; padding: 10px; border-radius: 8px; margin-bottom: 10px;">
                            <strong>[{cit['citation_id']}]</strong><br/>
                            📄 {cit['document_name']} ({cit['version_label']})<br/>
                            📍 Page <strong>{cit['page']}</strong> | Section: <em>{cit['section']}</em><br/>
                            BM25 relevance: <code>{cit['similarity_score']}</code>
                        </div>
                        """, unsafe_allow_html=True)

                st.markdown("### ⚠️ Confidence & Limitations")
                conf_val = 0.88 if is_grounded else 0.40
                st.write(f"Confidence Score: **{conf_val * 100:.0f}%** | Grounded: **{'YES' if is_grounded else 'NO'}**")
                if limitations:
                    for lim in limitations:
                        st.info(f"• {lim}")

                with st.expander("📦 View Raw Retrieved Context Chunks"):
                    for c in chunks:
                        st.write(f"**Chunk ID:** `{c['metadata']['chunk_id']}` | **Page:** {c['metadata']['page_number']}")
                        st.text(c['text'])
                        st.markdown("---")
