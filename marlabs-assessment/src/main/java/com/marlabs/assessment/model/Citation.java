package com.marlabs.assessment.model;

import com.fasterxml.jackson.annotation.JsonProperty;

public record Citation(
        @JsonProperty("chunk_id")
        String chunkId,
        String quote
) {
}
