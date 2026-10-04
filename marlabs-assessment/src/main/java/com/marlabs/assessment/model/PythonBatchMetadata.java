package com.marlabs.assessment.model;

import java.util.List;

public record PythonBatchMetadata(
        String batch_id,
        String as_of,
        String tenant,
        String role,
        List<PythonDocument> documents
) {

        public record PythonDocument(
                String document_id,
                String filename
        ) {
        }
}