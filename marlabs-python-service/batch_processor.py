import copy
import hashlib
import re
from pathlib import Path

from extractor import DocumentExtractor
from request_extractor import RequestExtractor
from policy_repository import PolicyRepository
from policy_engine import PolicyEngine


class BatchProcessor:

    def __init__(self):

        self.document_extractor = DocumentExtractor()
        self.request_extractor = RequestExtractor()
        self.repository = PolicyRepository()
        self.engine = PolicyEngine()

        # --------------------------------------------------
        # Exact duplicate tracking
        #
        # SHA-256 hash -> successfully processed result
        #
        # We only store successfully processed documents.
        # --------------------------------------------------

        self.seen_files = {}

    # ======================================================
    # Process Document
    # ======================================================

    def process(
        self,
        document_id: str,
        file_path: str,
        tenant: str,
        role: str,
        as_of: str,
    ):

        try:

            # ==================================================
            # STEP 9 — EXACT DUPLICATE DETECTION
            # ==================================================
            #
            # Hash the ORIGINAL file bytes.
            #
            # We intentionally do not:
            # - compare filenames
            # - normalize text
            # - extract PDF text
            # - compare extracted text
            #
            # This gives us exact byte-level duplicate detection.
            # ==================================================

            file_hash = self._calculate_file_hash(file_path)

            # --------------------------------------------------
            # Check whether this exact file was already
            # successfully processed.
            # --------------------------------------------------

            if file_hash in self.seen_files:

                original_result = self.seen_files[file_hash]

                original_document_id = original_result["document_id"]

                duplicate_result = copy.deepcopy(original_result)

                duplicate_result["document_id"] = document_id

                duplicate_result["duplicate_of"] = original_document_id

                duplicate_result["issues"] = [
                    f"Exact duplicate of document {original_document_id}.",
                    "Human review is required before any payment decision.",
                ]

                return duplicate_result

            # ==================================================
            # STEP 1 — Extract document text
            # ==================================================

            text = self.document_extractor.extract_text(file_path)

            # ==================================================
            # STEP 2 — Extract request fields
            # ==================================================

            extracted = self.request_extractor.extract(text)

            benefit = extracted.get("benefit")
            amount = extracted.get("amount")

            # ==================================================
            # STEP 3 — Build field evidence
            # ==================================================

            field_evidence = self._build_field_evidence(
                text=text,
                extracted=extracted,
            )

            # ==================================================
            # STEP 4 — Build review issues
            # ==================================================

            issues = []

            # --------------------------------------------------
            # Amount issue
            # --------------------------------------------------

            if amount is None:

                if extracted.get("amount_ambiguous", False):

                    issues.append(
                        "Requested amount is ambiguous because "
                        "multiple different amounts were found."
                    )

                else:

                    issues.append("Requested amount is unavailable.")

            # --------------------------------------------------
            # Benefit issue
            # --------------------------------------------------

            if benefit is None:

                issues.append("Requested benefit could not be identified.")

            # ==================================================
            # STEP 5 — Policy evaluation
            # ==================================================

            policy_result = None

            if benefit:

                policies = self.repository.find_eligible_policies(
                    tenant=tenant,
                    role=role,
                    as_of=as_of,
                )

                policy_result = self.engine.evaluate(
                    policies=policies,
                    benefit=benefit,
                )

                # --------------------------------------------------
                # Policy conflict
                # --------------------------------------------------

                if policy_result["status"] == "CONFLICT":

                    issues.append("Applicable policies are in conflict.")

                # --------------------------------------------------
                # No applicable policy
                # --------------------------------------------------

                elif policy_result["status"] == "INSUFFICIENT_EVIDENCE":

                    issues.append(
                        "No applicable approved policy evidence " "was found."
                    )

            # ==================================================
            # STEP 6 — Human review
            # ==================================================
            #
            # Every submitted request requires human review.
            #
            # The system does not make a final payment decision.
            # ==================================================

            issues.append("Human review is required before any payment decision.")

            # ==================================================
            # STEP 7 — Build successful result
            # ==================================================

            result = {
                "document_id": document_id,
                "processing_status": "COMPLETED",
                "extracted": extracted,
                "field_evidence": field_evidence,
                "policy": policy_result,
                "review_required": True,
                "issues": issues,
                "duplicate_of": None,
                "error": None,
            }

            # ==================================================
            # STEP 8 — Register successful document
            # ==================================================
            #
            # IMPORTANT:
            # Only register the hash AFTER successful processing.
            #
            # Therefore:
            #
            # request-01 SUCCESS
            #       ↓
            # hash stored
            #
            # request-06 same bytes
            #       ↓
            # duplicate_of = request-01
            #
            # If request-01 FAILED, request-06 is processed normally.
            # ==================================================

            self.seen_files[file_hash] = copy.deepcopy(result)

            return result

        # ======================================================
        # Expected document processing errors
        # ======================================================

        except ValueError as exc:

            code = str(exc)

            return {
                "document_id": document_id,
                "processing_status": "FAILED",
                "extracted": self._empty_extracted(),
                "field_evidence": [],
                "policy": None,
                "review_required": True,
                "issues": [],
                "duplicate_of": None,
                "error": {
                    "code": code,
                    "message": self._safe_error(code),
                },
            }

        # ======================================================
        # Unexpected processing error
        # ======================================================

        except Exception:

            return {
                "document_id": document_id,
                "processing_status": "FAILED",
                "extracted": self._empty_extracted(),
                "field_evidence": [],
                "policy": None,
                "review_required": True,
                "issues": [],
                "duplicate_of": None,
                "error": {
                    "code": "PROCESSING_ERROR",
                    "message": "Document processing failed.",
                },
            }

    # ==========================================================
    # Build Field Evidence
    # ==========================================================

    def _build_field_evidence(
        self,
        text: str,
        extracted: dict,
    ) -> list:

        evidence = []

        # ------------------------------------------------------
        # Benefit evidence
        # ------------------------------------------------------

        benefit = extracted.get("benefit")

        if benefit:

            quote = self._find_benefit_quote(
                text=text,
                benefit=benefit,
            )

            evidence.append(
                {
                    "field": "benefit",
                    "value": benefit,
                    "quote": quote,
                }
            )

        # ------------------------------------------------------
        # Amount evidence
        # ------------------------------------------------------

        amount = extracted.get("amount")

        if amount is not None:

            quote = self._find_amount_quote(text)

            evidence.append(
                {
                    "field": "amount",
                    "value": str(amount),
                    "quote": quote,
                }
            )

        elif extracted.get("amount_ambiguous", False):

            # Do not choose one of the conflicting values.
            # Keep the source evidence showing the ambiguity.

            quote = self._find_all_amount_quotes(text)

            evidence.append(
                {
                    "field": "amount",
                    "value": None,
                    "quote": quote,
                }
            )

        # ------------------------------------------------------
        # Currency evidence
        # ------------------------------------------------------

        currency = extracted.get("currency")

        if currency:

            quote = self._find_currency_quote(text)

            evidence.append(
                {
                    "field": "currency",
                    "value": currency,
                    "quote": quote,
                }
            )

        # ------------------------------------------------------
        # Reference evidence
        # ------------------------------------------------------

        reference = extracted.get("reference")

        if reference:

            quote = self._find_reference_quote(text)

            evidence.append(
                {
                    "field": "reference",
                    "value": reference,
                    "quote": quote,
                }
            )

        return evidence

    # ==========================================================
    # Find Benefit Quote
    # ==========================================================

    @staticmethod
    def _find_benefit_quote(
        text: str,
        benefit: str,
    ):

        sentences = re.split(
            r"(?<=[.!?])\s+|\n+",
            text,
        )

        for sentence in sentences:

            lower_sentence = sentence.lower()

            if benefit == "certification":

                if "certification" in lower_sentence:
                    return sentence.strip()

            elif benefit == "home-office":

                if "home-office" in lower_sentence or "home office" in lower_sentence:
                    return sentence.strip()

            elif benefit == "training":

                if "training" in lower_sentence:
                    return sentence.strip()

            elif benefit == "wellness":

                if "wellness" in lower_sentence or "gym membership" in lower_sentence:
                    return sentence.strip()

        return None

    # ==========================================================
    # Find Amount Quote
    # ==========================================================

    @staticmethod
    def _find_amount_quote(text: str):

        sentences = re.split(
            r"(?<=[.!?])\s+|\n+",
            text,
        )

        for sentence in sentences:

            if re.search(
                r"\bINR\s*[\d,]+",
                sentence,
                re.IGNORECASE,
            ):
                return sentence.strip()

        return None

    # ==========================================================
    # Find All Amount Quotes
    # ==========================================================

    @staticmethod
    def _find_all_amount_quotes(text: str):

        sentences = re.split(
            r"(?<=[.!?])\s+|\n+",
            text,
        )

        matching_sentences = []

        for sentence in sentences:

            if re.search(
                r"\bINR\s*[\d,]+",
                sentence,
                re.IGNORECASE,
            ):
                matching_sentences.append(sentence.strip())

        if matching_sentences:

            return " ".join(matching_sentences)

        return None

    # ==========================================================
    # Find Currency Quote
    # ==========================================================

    @staticmethod
    def _find_currency_quote(text: str):

        sentences = re.split(
            r"(?<=[.!?])\s+|\n+",
            text,
        )

        for sentence in sentences:

            if re.search(
                r"\bINR\b",
                sentence,
                re.IGNORECASE,
            ):
                return sentence.strip()

        return None

    # ==========================================================
    # Find Reference Quote
    # ==========================================================

    @staticmethod
    def _find_reference_quote(text: str):

        sentences = re.split(
            r"(?<=[.!?])\s+|\n+",
            text,
        )

        for sentence in sentences:

            if re.search(
                r"Reference:\s*[A-Za-z0-9-]+",
                sentence,
                re.IGNORECASE,
            ):
                return sentence.strip()

        return None

    # ==========================================================
    # SHA-256 File Hash
    # ==========================================================

    @staticmethod
    def _calculate_file_hash(file_path: str) -> str:
        """
        Calculate SHA-256 from the original file bytes.
        """

        path = Path(file_path)

        sha256 = hashlib.sha256()

        with path.open("rb") as file:

            while True:

                chunk = file.read(1024 * 1024)

                if not chunk:
                    break

                sha256.update(chunk)

        return sha256.hexdigest()

    # ==========================================================
    # Empty Extracted Structure
    # ==========================================================

    @staticmethod
    def _empty_extracted():

        return {
            "benefit": None,
            "amount": None,
            "currency": None,
            "reference": None,
            "amount_ambiguous": False,
        }

    # ==========================================================
    # Safe Error Messages
    # ==========================================================

    @staticmethod
    def _safe_error(code: str):

        messages = {
            "EMPTY_FILE": "Document is empty.",
            "UNREADABLE_DOCUMENT": "Document could not be read.",
            "UNSUPPORTED_FILE_TYPE": "Unsupported document type.",
        }

        return messages.get(
            code,
            "Document processing failed.",
        )
