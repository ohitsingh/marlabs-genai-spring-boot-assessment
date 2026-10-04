package com.marlabs.assessment.service;

import com.marlabs.assessment.model.*;

import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.time.LocalDate;
import java.util.*;

@Service
public class BatchService {

    private final PythonBatchClient pythonBatchClient;

    public BatchService(PythonBatchClient pythonBatchClient) {
        this.pythonBatchClient = pythonBatchClient;
    }

    public BatchResponse process(
            CallerContext caller,
            BatchMetadata metadata,
            MultipartFile[] files
    ) {

        // -------------------------------------------------
        // 1. Validate caller
        // -------------------------------------------------

        if (caller == null) {
            throw new IllegalArgumentException(
                    "Caller context is required"
            );
        }

        // -------------------------------------------------
        // 2. Validate batch metadata
        // -------------------------------------------------

        validateMetadata(metadata);

        // -------------------------------------------------
        // 3. Validate files against manifest
        // -------------------------------------------------

        Map<String, MultipartFile> filesByName =
                validateAndMapFiles(metadata, files);

        // -------------------------------------------------
        // 4. Process every manifest entry
        // -------------------------------------------------

        List<BatchResult> results =
                new ArrayList<>();

        Map<String, String> contentHashToDocumentId =
                new HashMap<>();

        List<DocumentManifest> documentsToProcess =
                new ArrayList<>();

        List<MultipartFile> filesToProcess =
                new ArrayList<>();

        // -------------------------------------------------
        // First pass
        // -------------------------------------------------

        for (DocumentManifest document :
                metadata.documents()) {

            MultipartFile file =
                    filesByName.get(
                            document.filename()
                    );

            // ---------------------------------------------
            // Empty file
            // ---------------------------------------------

            if (file.isEmpty()) {

                results.add(
                        failedResult(
                                document.documentId(),
                                "EMPTY_FILE",
                                "Uploaded document is empty."
                        )
                );

                continue;
            }

            // ---------------------------------------------
            // Calculate SHA-256
            // ---------------------------------------------

            String hash;

            try {

                hash = calculateHash(file);

            } catch (IOException e) {

                results.add(
                        failedResult(
                                document.documentId(),
                                "FILE_READ_ERROR",
                                "Unable to read uploaded document."
                        )
                );

                continue;
            }

            // ---------------------------------------------
            // Exact duplicate detection
            // ---------------------------------------------

            String previousDocumentId =
                    contentHashToDocumentId.get(hash);

            if (previousDocumentId != null) {

                results.add(
                        duplicateResult(
                                document.documentId(),
                                previousDocumentId
                        )
                );

                continue;
            }

            // ---------------------------------------------
            // First occurrence of this content
            // ---------------------------------------------

            contentHashToDocumentId.put(
                    hash,
                    document.documentId()
            );

            documentsToProcess.add(document);
            filesToProcess.add(file);
        }

        // -------------------------------------------------
        // 5. Call FastAPI for unique documents
        // -------------------------------------------------

        Map<String, BatchResult> pythonResultsByDocumentId =
                new HashMap<>();

        if (!filesToProcess.isEmpty()) {

            // ---------------------------------------------
            // Convert DocumentManifest -> PythonDocument
            // ---------------------------------------------

            List<PythonBatchMetadata.PythonDocument>
                    pythonDocuments =
                    documentsToProcess.stream()
                            .map(document ->
                                    new PythonBatchMetadata.PythonDocument(
                                            document.documentId(),
                                            document.filename()
                                    )
                            )
                            .toList();

            // ---------------------------------------------
            // Build trusted Python metadata
            // ---------------------------------------------

            PythonBatchMetadata pythonMetadata =
                    new PythonBatchMetadata(
                            metadata.batchId(),
                            metadata.asOf(),
                            caller.tenant(),
                            caller.role(),
                            pythonDocuments
                    );

            try {

                // -----------------------------------------
                // Call FastAPI
                // -----------------------------------------

                BatchResponse pythonResponse =
                        pythonBatchClient.processBatch(
                                pythonMetadata,
                                filesToProcess
                        );

                // -----------------------------------------
                // Store Python results by document ID
                // -----------------------------------------

                if (pythonResponse != null
                        && pythonResponse.results() != null) {

                    for (BatchResult result :
                            pythonResponse.results()) {

                        if (result != null
                                && result.documentId() != null) {

                            pythonResultsByDocumentId.put(
                                    result.documentId(),
                                    result
                            );
                        }
                    }
                }

            } catch (Exception e) {

                e.printStackTrace();

                for (DocumentManifest document :
                        documentsToProcess) {

                    pythonResultsByDocumentId.put(
                            document.documentId(),
                            failedResult(
                                    document.documentId(),
                                    "PYTHON_SERVICE_ERROR",
                                    e.getMessage() != null
                                            ? e.getMessage()
                                            : "Document processing service failed."
                            )
                    );

//            } catch (Exception e) {
//
//                // -----------------------------------------
//                // Python service failure
//                // -----------------------------------------
//
//                for (DocumentManifest document :
//                        documentsToProcess) {
//
//                    pythonResultsByDocumentId.put(
//                            document.documentId(),
//                            failedResult(
//                                    document.documentId(),
//                                    "PYTHON_SERVICE_ERROR",
//                                    "Document processing service failed."
//                            )
//                    );
                }
            }
        }

        // -------------------------------------------------
        // 6. Build final results in manifest order
        // -------------------------------------------------

        List<BatchResult> finalResults =
                new ArrayList<>();

        for (DocumentManifest document :
                metadata.documents()) {

            // ---------------------------------------------
            // Check Python result
            // ---------------------------------------------

            BatchResult pythonResult =
                    pythonResultsByDocumentId.get(
                            document.documentId()
                    );

            if (pythonResult != null) {

                finalResults.add(pythonResult);

                continue;
            }

            // ---------------------------------------------
            // Check already-created result
            // EMPTY_FILE / DUPLICATE / FILE_READ_ERROR
            // ---------------------------------------------

            BatchResult existingResult =
                    results.stream()
                            .filter(result ->
                                    result.documentId()
                                            .equals(
                                                    document.documentId()
                                            )
                            )
                            .findFirst()
                            .orElse(null);

            if (existingResult != null) {

                finalResults.add(existingResult);

                continue;
            }

            // ---------------------------------------------
            // Safety fallback
            // ---------------------------------------------

            finalResults.add(
                    failedResult(
                            document.documentId(),
                            "MISSING_PROCESSING_RESULT",
                            "No processing result was returned for this document."
                    )
            );
        }

        // -------------------------------------------------
        // 7. Summary
        // -------------------------------------------------

        int total =
                finalResults.size();

        int failed =
                (int) finalResults.stream()
                        .filter(result ->
                                "FAILED".equals(
                                        result.processingStatus()
                                )
                        )
                        .count();

        int completed =
                total - failed;

        Summary summary =
                new Summary(
                        total,
                        completed,
                        failed
                );

        // -------------------------------------------------
        // 8. Final response
        // -------------------------------------------------

        return new BatchResponse(
                metadata.batchId(),
                summary,
                finalResults
        );
    }


    // =====================================================
    // Metadata validation
    // =====================================================

    private void validateMetadata(
            BatchMetadata metadata
    ) {

        if (metadata == null) {

            throw new IllegalArgumentException(
                    "Metadata is required"
            );
        }

        if (metadata.batchId() == null
                || metadata.batchId().isBlank()) {

            throw new IllegalArgumentException(
                    "batch_id is required"
            );
        }

        if (metadata.asOf() == null
                || metadata.asOf().isBlank()) {

            throw new IllegalArgumentException(
                    "as_of is required"
            );
        }

        try {

            LocalDate.parse(
                    metadata.asOf()
            );

        } catch (Exception e) {

            throw new IllegalArgumentException(
                    "as_of must use YYYY-MM-DD format"
            );
        }

        if (metadata.documents() == null
                || metadata.documents().isEmpty()) {

            throw new IllegalArgumentException(
                    "documents must not be empty"
            );
        }

        Set<String> documentIds =
                new HashSet<>();

        Set<String> filenames =
                new HashSet<>();

        for (DocumentManifest document :
                metadata.documents()) {

            if (document.documentId() == null
                    || document.documentId().isBlank()) {

                throw new IllegalArgumentException(
                        "document_id is required"
                );
            }

            if (document.filename() == null
                    || document.filename().isBlank()) {

                throw new IllegalArgumentException(
                        "filename is required"
                );
            }

            if (!documentIds.add(
                    document.documentId())) {

                throw new IllegalArgumentException(
                        "Duplicate document_id: "
                                + document.documentId()
                );
            }

            if (!filenames.add(
                    document.filename())) {

                throw new IllegalArgumentException(
                        "Duplicate filename: "
                                + document.filename()
                );
            }
        }
    }


    // =====================================================
    // Validate uploaded files
    // =====================================================

    private Map<String, MultipartFile> validateAndMapFiles(
            BatchMetadata metadata,
            MultipartFile[] files
    ) {

        if (files == null) {

            throw new IllegalArgumentException(
                    "Files are required"
            );
        }

        if (files.length != metadata.documents().size()) {

            throw new IllegalArgumentException(
                    "Number of uploaded files does not match manifest"
            );
        }

        Map<String, MultipartFile> filesByName =
                new HashMap<>();

        for (MultipartFile file : files) {

            if (file == null) {

                throw new IllegalArgumentException(
                        "Invalid file part"
                );
            }

            String filename =
                    file.getOriginalFilename();

            if (filename == null
                    || filename.isBlank()) {

                throw new IllegalArgumentException(
                        "Uploaded file must have a filename"
                );
            }

            boolean existsInManifest =
                    metadata.documents()
                            .stream()
                            .anyMatch(document ->
                                    document.filename()
                                            .equals(filename));

            if (!existsInManifest) {

                throw new IllegalArgumentException(
                        "Unexpected file: " + filename
                );
            }

            if (filesByName.containsKey(filename)) {

                throw new IllegalArgumentException(
                        "Duplicate uploaded filename: "
                                + filename
                );
            }

            filesByName.put(
                    filename,
                    file
            );
        }

        // -------------------------------------------------
        // Ensure every manifest file was uploaded
        // -------------------------------------------------

        for (DocumentManifest document :
                metadata.documents()) {

            if (!filesByName.containsKey(
                    document.filename())) {

                throw new IllegalArgumentException(
                        "Missing file: "
                                + document.filename()
                );
            }
        }

        return filesByName;
    }


    // =====================================================
    // SHA-256
    // =====================================================

    private String calculateHash(
            MultipartFile file
    ) throws IOException {

        try {

            java.security.MessageDigest digest =
                    java.security.MessageDigest
                            .getInstance("SHA-256");

            byte[] hash =
                    digest.digest(
                            file.getBytes()
                    );

            StringBuilder result =
                    new StringBuilder();

            for (byte b : hash) {

                result.append(
                        String.format(
                                "%02x",
                                b
                        )
                );
            }

            return result.toString();

        } catch (
                java.security.NoSuchAlgorithmException e
        ) {

            throw new IllegalStateException(
                    "SHA-256 algorithm is unavailable",
                    e
            );
        }
    }


    // =====================================================
    // FAILED result
    // =====================================================

    private BatchResult failedResult(
            String documentId,
            String code,
            String message
    ) {

        return new BatchResult(
                documentId,
                "FAILED",
                null,
                null,
                null,
                true,
                List.of(message),
                null,
                new ErrorInfo(
                        code,
                        message
                )
        );
    }


    // =====================================================
    // DUPLICATE result
    // =====================================================

    private BatchResult duplicateResult(
            String documentId,
            String duplicateOf
    ) {

        return new BatchResult(
                documentId,
                "COMPLETED",
                null,
                null,
                null,
                true,
                List.of(
                        "EXACT_DUPLICATE_OF:"
                                + duplicateOf
                ),
                duplicateOf,
                null
        );
    }
}