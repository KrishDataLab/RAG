class AHITAException(Exception):
    """Base exception for AHITA application."""
    pass

class DocumentProcessingError(AHITAException):
    """Raised when document ingestion or PDF parsing fails."""
    pass

class LLMProviderError(AHITAException):
    """Raised when LLM service or structured output parsing fails."""
    pass

class VectorStoreError(AHITAException):
    """Raised when local retrieval-index operations fail."""
    pass

class ResourceNotFoundError(AHITAException):
    """Raised when requested entity/document is not found."""
    pass
