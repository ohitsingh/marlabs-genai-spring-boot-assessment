package com.marlabs.assessment.model;

import jakarta.validation.constraints.NotBlank;

import java.util.List;

public record BatchMetadata(
        @NotBlank
        String batchId,

        @NotBlank
        String asOf,

        String tenant,

        String role,

        List<DocumentManifest> documents
) {
}
