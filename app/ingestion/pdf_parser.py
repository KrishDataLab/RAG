import hashlib
from pathlib import Path
from typing import List, Dict, Any
import pypdf
from app.core.exceptions import DocumentProcessingError
from app.core.logging import logger

class PDFParser:
    def __init__(self, min_text_density: int = 50):
        self.min_text_density = min_text_density

    def compute_sha256(self, file_path: str) -> str:
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def parse_pdf(self, file_path: str) -> Dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            raise DocumentProcessingError(f"PDF file not found at path: {file_path}")

        try:
            reader = pypdf.PdfReader(file_path)
            num_pages = len(reader.pages)
            file_hash = self.compute_sha256(file_path)

            pages_data = []
            total_text_length = 0
            is_scanned_flag = False

            for i, page in enumerate(reader.pages):
                page_num = i + 1
                extracted_text = page.extract_text() or ""
                cleaned_text = extracted_text.strip()
                text_len = len(cleaned_text)
                total_text_length += text_len

                # Low text density detection
                low_text_density = text_len < self.min_text_density

                # Detect heading/sections
                lines = [line.strip() for line in cleaned_text.split("\n") if line.strip()]
                detected_section = "General Overview"
                for line in lines[:3]:
                    if line.startswith(("1.", "2.", "3.", "4.", "5.", "Section", "Chapter", "AUTOSAR")):
                        detected_section = line
                        break

                pages_data.append({
                    "page_number": page_num,
                    "text": cleaned_text,
                    "text_length": text_len,
                    "section": detected_section,
                    "low_text_density": low_text_density
                })

            # If average text density is very low, mark scanned
            avg_density = total_text_length / max(num_pages, 1)
            if avg_density < self.min_text_density:
                is_scanned_flag = True
                logger.warning(
                    f"Document {path.name} has low average text density "
                    f"({avg_density:.1f} chars/page); this release detects but does not OCR scanned pages."
                )

            return {
                "file_name": path.name,
                "file_path": str(path),
                "sha256": file_hash,
                "page_count": num_pages,
                "is_scanned": is_scanned_flag,
                "pages": pages_data
            }

        except Exception as e:
            logger.error(f"Failed to parse PDF {file_path}: {str(e)}")
            raise DocumentProcessingError(f"PDF parsing error: {str(e)}")
