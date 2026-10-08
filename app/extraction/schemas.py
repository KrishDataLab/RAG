from typing import List, Optional
from pydantic import BaseModel, Field

class EntityItem(BaseModel):
    type: str = Field(..., description="SoftwareComponent, Interface, Port, Signal, FunctionalFlow, Dependency")
    name: str = Field(..., description="Canonical entity name")
    aliases: List[str] = Field(default_factory=list)
    page_number: int = Field(default=1)
    section: str = Field(default="")
    confidence: float = Field(default=1.0)

class EntityExtractionResponse(BaseModel):
    entities: List[EntityItem] = Field(default_factory=list)

class RelationshipItem(BaseModel):
    source_name: str
    source_type: str
    target_name: str
    target_type: str
    relationship_type: str = Field(..., description="uses, provides, requires, owns, carries, depends_on, participates_in")
    confidence: float = Field(default=1.0)

class RelationshipExtractionResponse(BaseModel):
    relationships: List[RelationshipItem] = Field(default_factory=list)
