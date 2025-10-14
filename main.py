"""
Main module for resume processing - handles file reading and text extraction
"""

import PyPDF2
import docx
from typing import List
import logging
from pathlib import Path
from parser import ResumeParser

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ResumeExtractor:
    """Handles extraction of text and URLs from resume files (PDF, DOCX)."""

    @staticmethod
    def extract_urls_from_pdf(file_path: str) -> List[str]:
        """Extract URLs from PDF hyperlinks/annotations."""
        urls = []
        try:
            with open(file_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    # Check if page has annotations
                    if "/Annots" in page:
                        annotations = page["/Annots"]
                        for annotation in annotations:
                            obj = annotation.get_object()
                            # Check for Link annotations with URLs
                            if obj.get("/Subtype") == "/Link":
                                if "/A" in obj:  # Action
                                    action = obj["/A"]
                                    if "/URI" in action:
                                        url = action["/URI"]
                                        if url and url not in urls:
                                            urls.append(str(url))
        except Exception as e:
            logger.warning(f"Could not extract URLs from PDF: {e}")

        return urls

    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        """Extract text and URLs from PDF file."""
        with open(file_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"

            # Also extract URLs from hyperlinks
            urls = ResumeExtractor.extract_urls_from_pdf(file_path)
            if urls:
                text += "\n\nEXTRACTED URLS/LINKS:\n"
                for url in urls:
                    text += f"- {url}\n"

            return text

    @staticmethod
    def extract_urls_from_docx(file_path: str) -> List[str]:
        """Extract URLs from DOCX hyperlinks."""
        urls = []
        try:
            doc = docx.Document(file_path)
            # Get all hyperlinks from the document relationships
            rels = doc.part.rels
            for rel in rels.values():
                if "hyperlink" in rel.reltype:
                    url = rel.target_ref
                    if url and url not in urls:
                        # Filter out internal anchors (starting with #)
                        if not url.startswith("#"):
                            urls.append(url)
        except Exception as e:
            logger.warning(f"Could not extract URLs from DOCX: {e}")

        return urls

    @staticmethod
    def extract_text_from_docx(file_path: str) -> str:
        """Extract text and URLs from DOCX file."""
        doc = docx.Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])

        # Also extract URLs from hyperlinks
        urls = ResumeExtractor.extract_urls_from_docx(file_path)
        if urls:
            text += "\n\nEXTRACTED URLS/LINKS:\n"
            for url in urls:
                text += f"- {url}\n"

        return text

    @staticmethod
    def extract_text_from_file(file_path: str) -> str:
        """
        Extract text from a resume file (PDF or DOCX).
        Auto-detects file type based on extension.
        """
        file_path_obj = Path(file_path)

        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        extension = file_path_obj.suffix.lower()

        if extension == ".pdf":
            logger.info(f"Extracting text from PDF: {file_path}")
            return ResumeExtractor.extract_text_from_pdf(file_path)
        elif extension in [".docx", ".doc"]:
            logger.info(f"Extracting text from DOCX: {file_path}")
            return ResumeExtractor.extract_text_from_docx(file_path)
        else:
            raise ValueError(
                f"Unsupported file format: {extension}. Supported formats: .pdf, .docx, .doc"
            )


def parse_resume_file(file_path: str, output_json_path: str = None) -> dict:
    """
    Complete workflow: Extract text from file and parse resume.

    Args:
        file_path: Path to resume file (PDF or DOCX)
        output_json_path: Optional path to save parsed JSON

    Returns:
        Parsed resume as dictionary
    """
    # Step 1: Extract text from file
    extractor = ResumeExtractor()
    resume_text = extractor.extract_text_from_file(file_path)
    logger.info(f"Extracted {len(resume_text)} characters from {file_path}")

    # Step 2: Parse resume text using LLM
    parser = ResumeParser()
    parsed_resume = parser.parse_resume(resume_text)
    logger.info("Resume parsed successfully")

    # Step 3: Export to JSON if requested
    if output_json_path:
        parser.export_to_json(parsed_resume, output_json_path)
        logger.info(f"Resume exported to: {output_json_path}")

    # Return as dictionary
    return parsed_resume.model_dump(exclude_none=True)


if __name__ == "__main__":
    # Test the complete workflow
    print("=" * 60)
    print("Resume Parser - Complete Workflow")
    print("=" * 60)

    try:
        # Parse resume from file
        resume_file = "resume_f.pdf"  # Can be .pdf or .docx
        output_file = "parsed_resume.json"

        print(f"\n📄 Processing: {resume_file}")

        parsed_data = parse_resume_file(resume_file, output_file)


        print(f"\n✅ Results saved to: {output_file}")
        print("=" * 60)

    except FileNotFoundError:
        print(f"\n❌ Error: File not found")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()