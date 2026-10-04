package com.marlabs.assessment.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

public record AnswerRequest(

        @NotBlank(message = "question must not be empty")
        String question,
        @JsonProperty("as_of")
        @NotBlank(message = "as_of is required")
        @Pattern(
                regexp = "^\\d{4}-\\d{2}-\\d{2}$",
                message = "as_of must use YYYY-MM-DD format"
        )
        String asOf
) {
}
