package com.marlabs.assessment.model;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

public record BatchResult(

        @JsonProperty("document_id")
        String documentId,

        @JsonProperty("processing_status")
        String processingStatus,

        ExtractedData extracted,

        @JsonProperty("field_evidence")
        List<Evidence> fieldEvidence,

        AnswerResponse policy,

        @JsonProperty("review_required")
        boolean reviewRequired,

        List<String> issues,

        @JsonProperty("duplicate_of")
        String duplicateOf,

        ErrorInfo error
) {
}