from typing import List, Optional
from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    project_id: str = "P001"
    question: str
    document_ids: Optional[List[str]] = None
    top_k: int = 8

class CitationItem(BaseModel):
    document_id: str
    page: int
    section: str
    chunk_id: str

class QueryResponse(BaseModel):
    answer: str
    citations: List[CitationItem]
    confidence: float = 0.90
    grounded: bool = True
    limitations: List[str] = Field(default_factory=list)

class CompareRequest(BaseModel):
    document_a_id: str
    document_b_id: str
    project_id: str = "P001"

class ReviewFindingRequest(BaseModel):
    status: str = Field(..., description="CONFIRMED | FALSE_POSITIVE | NEEDS_REVIEW")
    comment: str = ""
    reviewer_id: str = "architect_1"
