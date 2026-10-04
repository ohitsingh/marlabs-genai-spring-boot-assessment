package com.marlabs.assessment.model;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

public record BatchResponse(

        @JsonProperty("batch_id")
        String batchId,

        Summary summary,

        List<BatchResult> results
) {
}