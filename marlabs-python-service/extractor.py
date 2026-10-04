# from pathlib import Path

# from pypdf import PdfReader


# class DocumentExtractor:

#     def extract_text(self, file_path: str) -> str:
#         """
#         Extract text from a PDF document.
#         """

#         path = Path(file_path)

#         if not path.exists():
#             raise FileNotFoundError(f"File not found: {file_path}")

#         reader = PdfReader(str(path))

#         pages = []

#         for page_number, page in enumerate(reader.pages, start=1):

#             text = page.extract_text()

#             if text:
#                 pages.append(f"\n--- Page {page_number} ---\n{text}")

#         return "\n".join(pages)

#     def extract_chunks(self, file_path: str, chunk_size: int = 1000):
#         """
#         Extract text and split it into simple chunks.
#         """

#         text = self.extract_text(file_path)

#         chunks = []

#         for start in range(0, len(text), chunk_size):

#             chunk = text[start : start + chunk_size]

#             if chunk.strip():
#                 chunks.append(chunk.strip())

#         return chunks
from pathlib import Path

from pypdf import PdfReader


class DocumentExtractor:

    def extract_text(self, file_path: str) -> str:
        """
        Extract text from UTF-8 TXT or text-based PDF.
        """

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # ------------------------------------------
        # Empty file
        # ------------------------------------------

        if path.stat().st_size == 0:
            raise ValueError("EMPTY_FILE")

        # ------------------------------------------
        # TXT
        # ------------------------------------------

        if path.suffix.lower() == ".txt":

            text = path.read_text(encoding="utf-8")

            if not text.strip():
                raise ValueError("EMPTY_FILE")

            return text

        # ------------------------------------------
        # PDF
        # ------------------------------------------

        if path.suffix.lower() == ".pdf":

            reader = PdfReader(str(path))

            pages = []

            for page in reader.pages:

                text = page.extract_text()

                if text:
                    pages.append(text)

            result = "\n".join(pages).strip()

            if not result:
                raise ValueError("UNREADABLE_DOCUMENT")

            return result

        # ------------------------------------------
        # Unsupported file type
        # ------------------------------------------

        raise ValueError("UNSUPPORTED_FILE_TYPE")
