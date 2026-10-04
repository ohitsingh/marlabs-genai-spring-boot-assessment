from typing import Optional

from pydantic import BaseModel

# ============================================================
# Extracted document fields
# ============================================================


class ExtractedData(BaseModel):

    benefit: Optional[str] = None

    amount: Optional[float] = None

    currency: Optional[str] = None

    reference: Optional[str] = None

    amount_ambiguous: bool = False


# ============================================================
# Evidence for an extracted field
# ============================================================


class FieldEvidence(BaseModel):

    field: str

    value: Optional[str] = None

    quote: Optional[str] = None


# ============================================================
# Evidence container
# ============================================================


class Evidence(BaseModel):

    extracted: ExtractedData

    field_evidence: list[FieldEvidence]


# ============================================================
# Processing error
# ============================================================


class ErrorInfo(BaseModel):

    code: str

    message: str


# ============================================================
# Individual batch result
# ============================================================


class BatchItemResult(BaseModel):

    document_id: str

    processing_status: str

    extracted: ExtractedData

    field_evidence: list[FieldEvidence]

    policy: Optional[dict] = None

    review_required: bool

    issues: list[str]

    duplicate_of: Optional[str] = None

    error: Optional[ErrorInfo] = None
