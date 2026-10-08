from typing import Dict, Any, List
from app.ingestion.pdf_parser import PDFParser
from app.ingestion.chunker import ContextAwareChunker
from app.ingestion.metadata import MetadataExtractor
from app.db.repositories import DatabaseRepository
from app.core.logging import logger

class IngestionPipeline:
    def __init__(self, repo: DatabaseRepository, vector_store=None):
        self.repo = repo
        self.parser = PDFParser()
        self.chunker = ContextAwareChunker()
        self.vector_store = vector_store

    def run(self, file_path: str, project_id: str = "P001", version_label: str = "v1.0") -> Dict[str, Any]:
        logger.info(f"Starting ingestion pipeline for {file_path}")
        
        # 1. Parse PDF
        parsed_pdf = self.parser.parse_pdf(file_path)

        # 2. Check duplicate sha256 in project
        existing_docs = self.repo.get_documents(project_id)
        for doc in existing_docs:
            if doc.sha256 == parsed_pdf["sha256"]:
                logger.info(f"Document with hash {parsed_pdf['sha256']} already exists as {doc.id}")
                if self.vector_store:
                    db_chunks = self.repo.get_chunks_by_document(doc.id)
                    if db_chunks:
                        chunks_for_vs = [{
                            "chunk_id": c.chunk_id,
                            "text": c.text,
                            "document_id": c.document_id,
                            "document_name": doc.name,
                            "version_label": doc.version_label,
                            "page_number": c.page_number,
                            "section": c.section,
                            "project_id": doc.project_id,
                            "source_type": "HLD"
                        } for c in db_chunks]
                        self.vector_store.add_chunks(chunks_for_vs)
                return {
                    "status": "ALREADY_EXISTS",
                    "document_id": doc.id,
                    "document_name": doc.name,
                    "page_count": doc.page_count,
                    "message": "Document already ingested."
                }

        # 3. Create metadata & DB record
        meta = MetadataExtractor.create_document_metadata(
            project_id=project_id,
            file_name=parsed_pdf["file_name"],
            version_label=version_label,
            sha256=parsed_pdf["sha256"],
            page_count=parsed_pdf["page_count"]
        )

        doc_rec = self.repo.create_document(
            doc_id=meta["document_id"],
            project_id=project_id,
            name=meta["document_name"],
            version_label=version_label,
            sha256=meta["sha256"],
            page_count=meta["page_count"]
        )

        # 4. Chunking
        chunks = self.chunker.chunk_document(parsed_pdf, doc_rec.id, version_label)
        for c in chunks:
            c["project_id"] = project_id

        # 5. Save chunks to SQLite DB
        self.repo.save_chunks(chunks)

        # 6. Index in the in-memory retrieval store if provided
        if self.vector_store:
            self.vector_store.add_chunks(chunks)

        # Update status
        self.repo.update_document_status(doc_rec.id, "INDEXED")

        logger.info(f"Ingestion complete for {doc_rec.id}: {len(chunks)} chunks indexed.")
        return {
            "status": "SUCCESS",
            "document_id": doc_rec.id,
            "document_name": doc_rec.name,
            "version_label": doc_rec.version_label,
            "page_count": doc_rec.page_count,
            "chunk_count": len(chunks),
            "is_scanned": parsed_pdf["is_scanned"]
        }
