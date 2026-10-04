import json
import tempfile
from datetime import date
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, ValidationError

from batch_processor import BatchProcessor
from policy_repository import PolicyRepository
from policy_engine import PolicyEngine

# ============================================================
# FastAPI Application
# ============================================================

app = FastAPI(
    title="MARLABS Policy Python Service",
    version="1.0.0",
)


# ============================================================
# Initialize Dependencies
# ============================================================

repository = PolicyRepository()
engine = PolicyEngine()


# ============================================================
# Answer Request Model
# ============================================================


class AnswerRequest(BaseModel):

    tenant: str

    role: str

    as_of: str

    question: str


# ============================================================
# Batch Metadata Models
# ============================================================


class DocumentManifest(BaseModel):

    document_id: str

    filename: str


class BatchMetadata(BaseModel):

    batch_id: str

    as_of: str

    documents: list[DocumentManifest]

    # These values come from trusted Spring Boot
    # caller context.
    tenant: str
    role: str


# ============================================================
# Benefit Extraction
# ============================================================


def extract_benefit(question: str) -> str | None:

    text = question.lower()

    if "certification" in text:
        return "certification"

    if "home-office" in text or "home office" in text:
        return "home-office"

    if "travel" in text or "rail" in text:
        return "travel"

    if "training" in text:
        return "training"

    if "gym membership" in text or "wellness" in text:
        return "wellness"

    return None


# ============================================================
# Health Check
# ============================================================


@app.get("/health")
def health():

    return {
        "status": "UP",
        "service": "python-policy-service",
    }


# ============================================================
# Answer Endpoint
# ============================================================


@app.post("/internal/answer")
def answer(request: AnswerRequest):

    # --------------------------------------------------------
    # Validate date
    # --------------------------------------------------------

    try:

        date.fromisoformat(request.as_of)

    except ValueError:

        raise HTTPException(
            status_code=400,
            detail="as_of must be in YYYY-MM-DD format",
        )

    # --------------------------------------------------------
    # Extract benefit from question
    # --------------------------------------------------------

    benefit = extract_benefit(request.question)

    if benefit is None:

        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "answer": None,
            "citations": [],
        }

    # --------------------------------------------------------
    # Retrieve eligible policies
    # --------------------------------------------------------

    policies = repository.find_eligible_policies(
        tenant=request.tenant,
        role=request.role,
        as_of=request.as_of,
    )

    # --------------------------------------------------------
    # Evaluate policies
    # --------------------------------------------------------

    result = engine.evaluate(
        policies=policies,
        benefit=benefit,
    )

    # --------------------------------------------------------
    # Return result
    # --------------------------------------------------------

    return result


# ============================================================
# Batch Endpoint
# ============================================================


@app.post("/internal/process")
async def process_batch(
    metadata: str = Form(...),
    files: list[UploadFile] = File(...),
):
    """
    Process a batch of documents.

    Multipart request contains:

        metadata:
            JSON string

        files:
            repeated uploaded files
    """

    # ========================================================
    # STEP 1 — Parse metadata JSON
    # ========================================================

    try:

        metadata_dict = json.loads(metadata)

    except json.JSONDecodeError:

        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_METADATA",
                "message": "Metadata must contain valid JSON.",
            },
        )

    # ========================================================
    # STEP 2 — Validate metadata structure
    # ========================================================

    try:

        batch_metadata = BatchMetadata.model_validate(metadata_dict)

    except ValidationError:

        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_METADATA",
                "message": "Batch metadata is invalid.",
            },
        )

    # ========================================================
    # STEP 3 — Validate as_of
    # ========================================================

    try:

        date.fromisoformat(batch_metadata.as_of)

    except ValueError:

        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_AS_OF",
                "message": ("as_of must be in YYYY-MM-DD format."),
            },
        )

    # ========================================================
    # STEP 4 — Validate manifest
    # ========================================================

    documents = batch_metadata.documents

    if not documents:

        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_METADATA",
                "message": "At least one document is required.",
            },
        )

    # --------------------------------------------------------
    # Validate document IDs
    # --------------------------------------------------------

    document_ids = [document.document_id for document in documents]

    if len(document_ids) != len(set(document_ids)):

        raise HTTPException(
            status_code=400,
            detail={
                "error": "DUPLICATE_MANIFEST_ID",
                "message": ("Manifest contains duplicate document IDs."),
            },
        )

    # --------------------------------------------------------
    # Validate manifest filenames
    # --------------------------------------------------------

    manifest_filenames = [document.filename for document in documents]

    if len(manifest_filenames) != len(set(manifest_filenames)):

        raise HTTPException(
            status_code=400,
            detail={
                "error": "DUPLICATE_MANIFEST_FILENAME",
                "message": ("Manifest contains duplicate filenames."),
            },
        )

    # ========================================================
    # STEP 5 — Validate uploaded files
    # ========================================================

    uploaded_filenames = []

    for file in files:

        # ----------------------------------------------------
        # UploadFile.filename is Optional[str]
        #
        # Explicitly validate it so that the remaining code
        # works with list[str] rather than list[str | None].
        # ----------------------------------------------------

        if not file.filename:

            raise HTTPException(
                status_code=400,
                detail={
                    "error": "INVALID_FILE_PART",
                    "message": ("Uploaded file must have a filename."),
                },
            )

        uploaded_filenames.append(file.filename)

    # ========================================================
    # STEP 6 — Duplicate uploaded filenames
    # ========================================================

    if len(uploaded_filenames) != len(set(uploaded_filenames)):

        raise HTTPException(
            status_code=400,
            detail={
                "error": "DUPLICATE_FILE_PART",
                "message": ("Multiple uploaded files have " "the same filename."),
            },
        )

    # ========================================================
    # STEP 7 — Compare manifest files and uploaded files
    # ========================================================

    manifest_filename_set = set(manifest_filenames)

    uploaded_filename_set = set(uploaded_filenames)

    # --------------------------------------------------------
    # Missing files
    # --------------------------------------------------------

    missing_files = manifest_filename_set - uploaded_filename_set

    if missing_files:

        raise HTTPException(
            status_code=400,
            detail={
                "error": "MISSING_FILE_PART",
                "message": ("One or more manifest files are missing."),
                "files": sorted(missing_files),
            },
        )

    # --------------------------------------------------------
    # Extra files
    # --------------------------------------------------------

    extra_files = uploaded_filename_set - manifest_filename_set

    if extra_files:

        raise HTTPException(
            status_code=400,
            detail={
                "error": "EXTRA_FILE_PART",
                "message": (
                    "One or more uploaded files are not " "present in the manifest."
                ),
                "files": sorted(extra_files),
            },
        )

    # ========================================================
    # STEP 8 — Map filename to UploadFile
    # ========================================================

    file_map = {file.filename: file for file in files}

    # ========================================================
    # STEP 9 — Create BatchProcessor
    # ========================================================
    #
    # One processor per batch.
    #
    # This keeps duplicate detection scoped to the current
    # batch.
    # ========================================================

    batch_processor = BatchProcessor()

    results = []

    # ========================================================
    # STEP 10 — Temporary directory
    # ========================================================

    with tempfile.TemporaryDirectory(prefix="marlabs-batch-") as temp_directory:

        temp_path = Path(temp_directory)

        # ----------------------------------------------------
        # Process documents in manifest order
        # ----------------------------------------------------

        for document in documents:

            upload = file_map.get(document.filename)

            # ------------------------------------------------
            # Defensive missing-file check
            # ------------------------------------------------

            if upload is None:

                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "MISSING_FILE_PART",
                        "message": (f"Missing file: " f"{document.filename}"),
                    },
                )

            # ------------------------------------------------
            # Prevent path traversal
            # ------------------------------------------------

            safe_filename = Path(document.filename).name

            destination = temp_path / safe_filename

            # ------------------------------------------------
            # Read uploaded bytes
            # ------------------------------------------------

            try:

                content = await upload.read()

                destination.write_bytes(content)

            except Exception:

                # A single file failure must not stop
                # the remaining documents.

                results.append(
                    {
                        "document_id": document.document_id,
                        "processing_status": "FAILED",
                        "extracted": {
                            "benefit": None,
                            "amount": None,
                            "currency": None,
                            "reference": None,
                            "amount_ambiguous": False,
                        },
                        "field_evidence": [],
                        "policy": None,
                        "review_required": True,
                        "issues": [],
                        "duplicate_of": None,
                        "error": {
                            "code": "FILE_READ_ERROR",
                            "message": ("Uploaded file could not be read."),
                        },
                    }
                )

                continue

            # ------------------------------------------------
            # Process document
            # ------------------------------------------------

            result = batch_processor.process(
                document_id=document.document_id,
                file_path=str(destination),
                tenant=batch_metadata.tenant,
                role=batch_metadata.role,
                as_of=batch_metadata.as_of,
            )

            results.append(result)

    # ========================================================
    # STEP 11 — Build summary
    # ========================================================

    total = len(results)

    completed = sum(
        1 for result in results if result["processing_status"] == "COMPLETED"
    )

    failed = sum(1 for result in results if result["processing_status"] == "FAILED")

    # ========================================================
    # STEP 12 — Return batch response
    # ========================================================

    return {
        "batch_id": batch_metadata.batch_id,
        "results": results,
        "summary": {
            "total": total,
            "completed": completed,
            "failed": failed,
        },
    }


# ============================================================
# Swagger / OpenAPI Compatibility
# ============================================================
#
# FastAPI currently generates the uploaded-file array as:
#
# type: array
#     items:
# type: string
#         contentMediaType: application/octet-stream
#
# Some Swagger UI versions do not render this as a
# "Choose File" control.
#
# Convert the file item representation to:
#
# type: string
#     format: binary
#
# This changes only the generated OpenAPI documentation.
# It does NOT change the actual /internal/process endpoint.
# ============================================================


def custom_openapi():

    if app.openapi_schema:

        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
    )

    components = schema.get(
        "components",
        {},
    ).get(
        "schemas",
        {},
    )

    for component in components.values():

        properties = component.get(
            "properties",
            {},
        )

        for property_schema in properties.values():

            # ------------------------------------------------
            # Handle array of uploaded files
            # ------------------------------------------------

            if property_schema.get("type") == "array" and isinstance(
                property_schema.get("items"),
                dict,
            ):

                items = property_schema["items"]

                if items.get("contentMediaType") == "application/octet-stream":

                    items.pop(
                        "contentMediaType",
                        None,
                    )

                    items["format"] = "binary"

            # ------------------------------------------------
            # Handle single uploaded file
            # ------------------------------------------------

            if (
                property_schema.get("type") == "string"
                and property_schema.get("contentMediaType")
                == "application/octet-stream"
            ):

                property_schema.pop(
                    "contentMediaType",
                    None,
                )

                property_schema["format"] = "binary"

    app.openapi_schema = schema

    return app.openapi_schema


# Override FastAPI's default OpenAPI generator
app.openapi = custom_openapi
