import re
from typing import Optional


class RequestExtractor:

    def extract(self, text: str) -> dict:
        """
        Extract structured information from the submitted document.

        The extractor only extracts facts from the document.
        It does NOT make any policy/payability decision.
        """

        amount = self._extract_amount(text)

        return {
            "benefit": self._extract_benefit(text),
            "amount": amount,
            "currency": self._extract_currency(text),
            "reference": self._extract_reference(text),
            "amount_ambiguous": self._is_amount_ambiguous(text),
        }

    # ============================================================
    # Benefit
    # ============================================================

    def _extract_benefit(self, text: str) -> Optional[str]:
        """
        Identify the benefit mentioned in the document.
        """

        value = text.lower()

        # Certification
        if "certification" in value:
            return "certification"

        # Home office
        if "home-office" in value or "home office" in value:
            return "home-office"

        # Training
        if "training" in value:
            return "training"

        # Wellness / gym
        if "gym membership" in value or "wellness" in value:
            return "wellness"

        return None

    # ============================================================
    # Amount
    # ============================================================

    def _extract_amount(self, text: str) -> Optional[float]:
        """
        Extract INR amount.

        Rules:
        - One unique INR amount -> return amount.
        - Same amount repeated -> return amount.
        - Multiple different amounts -> return None.
        - No amount -> return None.

        Example:

        INR 18000
            -> 18000

        Invoice says INR 22000.
        Reimbursement form says INR 28000.
            -> None
        """

        # --------------------------------------------------------
        # Explicit invoice/form ambiguity detection
        # --------------------------------------------------------

        invoice_amount = re.search(
            r"invoice\s+(?:says|amount\s+is)\s+INR\s*([\d,]+)",
            text,
            re.IGNORECASE,
        )

        form_amount = re.search(
            r"(?:reimbursement form|form)\s+" r"(?:says|amount\s+is)\s+INR\s*([\d,]+)",
            text,
            re.IGNORECASE,
        )

        if invoice_amount and form_amount:

            invoice_value = self._number(invoice_amount.group(1))

            form_value = self._number(form_amount.group(1))

            # Different amounts = ambiguous
            if invoice_value != form_value:
                return None

        # --------------------------------------------------------
        # General INR amount extraction
        # --------------------------------------------------------

        amounts = re.findall(
            r"INR\s*([\d,]+)",
            text,
            re.IGNORECASE,
        )

        if not amounts:
            return None

        values = [self._number(value) for value in amounts]

        unique_values = set(values)

        # Same amount repeated multiple times
        if len(unique_values) == 1:
            return values[0]

        # Multiple different amounts
        return None

    # ============================================================
    # Amount Ambiguity
    # ============================================================

    def _is_amount_ambiguous(self, text: str) -> bool:
        """
        Determine whether the document contains multiple
        different INR amounts.

        Example:

        Invoice says INR 22000.
        Reimbursement form says INR 28000.

        -> True

        Example:

        Requested amount INR 18000.
        Amount INR 18000.

        -> False
        """

        amounts = re.findall(
            r"INR\s*([\d,]+)",
            text,
            re.IGNORECASE,
        )

        if len(amounts) < 2:
            return False

        values = {self._number(value) for value in amounts}

        return len(values) > 1

    # ============================================================
    # Currency
    # ============================================================

    def _extract_currency(self, text: str) -> Optional[str]:
        """
        Extract currency.

        Currently the assessment uses INR.
        """

        if re.search(
            r"\bINR\b",
            text,
            re.IGNORECASE,
        ):
            return "INR"

        return None

    # ============================================================
    # Reference
    # ============================================================

    def _extract_reference(self, text: str) -> Optional[str]:
        """
        Extract request reference.

        Example:

        Reference: CERT-101

        -> CERT-101
        """

        match = re.search(
            r"Reference:\s*([A-Za-z0-9-]+)",
            text,
            re.IGNORECASE,
        )

        if match:
            return match.group(1)

        return None

    # ============================================================
    # Number Helper
    # ============================================================

    @staticmethod
    def _number(value: str) -> float:
        """
        Convert a formatted number into float.

        Example:

        "18,000" -> 18000.0
        "70000"  -> 70000.0
        """

        return float(value.replace(",", ""))
