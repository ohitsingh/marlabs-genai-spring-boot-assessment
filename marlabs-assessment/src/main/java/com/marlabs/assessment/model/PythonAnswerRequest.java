package com.marlabs.assessment.model;

import com.fasterxml.jackson.annotation.JsonProperty;

public record PythonAnswerRequest(
        String question,
        @JsonProperty("as_of")
        String asOf,
        String tenant,
        String role
) {
}
