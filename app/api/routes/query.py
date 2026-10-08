from fastapi import APIRouter, Depends
from app.api.schemas.requests import QueryRequest, QueryResponse, CitationItem
from app.api.deps import get_retriever, get_llm_client
from app.retrieval.retriever import ArchitectureRetriever
from app.retrieval.citation import CitationValidator
from app.llm.client import LLMClient
from app.llm.prompts import prompt_manager
from app.llm.guardrails import SafetyGuardrails

router = APIRouter()

@router.post("/query", response_model=QueryResponse)
def ask_question(
    req: QueryRequest,
    retriever: ArchitectureRetriever = Depends(get_retriever),
    llm_client: LLMClient = Depends(get_llm_client)
):
    # Prompt injection safety check
    is_injection, msg = SafetyGuardrails.check_prompt_injection(req.question)
    if is_injection:
        return QueryResponse(
            answer="Security Warning: Prompt injection pattern detected and blocked.",
            citations=[],
            confidence=0.0,
            grounded=False,
            limitations=[msg]
        )

    # Retrieval
    chunks = retriever.retrieve(
        query=req.question,
        top_k=req.top_k,
        project_id=req.project_id,
        document_ids=req.document_ids
    )

    if not chunks:
        return QueryResponse(
            answer="I could not find enough evidence in the indexed HLD documents to answer this confidently.",
            citations=[],
            confidence=0.0,
            grounded=True,
            limitations=["No relevant context retrieved from indexed document chunks."]
        )

    citations = CitationValidator.format_citations(chunks)

    # Format RAG prompt context
    context_str = ""
    for idx, c in enumerate(chunks, start=1):
        meta = c["metadata"]
        context_str += f"[Source {idx}] Document: {meta.get('document_name')}, Version: {meta.get('version_label')}, Page: {meta.get('page_number')}, Section: {meta.get('section')}\n{c['text']}\n\n"

    system_prompt = prompt_manager.get_prompt("rag_system_v1.txt")
    rag_prompt = prompt_manager.render("rag_answer_v1.txt", context=context_str, question=req.question)

    answer = llm_client.generate(prompt=rag_prompt, system_instruction=system_prompt)

    is_grounded, limitations = CitationValidator.validate_grounding(answer, chunks)

    citation_objs = [
        CitationItem(
            document_id=c["document_id"],
            page=c["page"],
            section=c["section"],
            chunk_id=c["chunk_id"]
        ) for c in citations
    ]

    return QueryResponse(
        answer=answer,
        citations=citation_objs,
        confidence=0.88 if is_grounded else 0.40,
        grounded=is_grounded,
        limitations=limitations
    )
