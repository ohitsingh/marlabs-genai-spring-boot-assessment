package com.marlabs.assessment.model;

import java.util.List;

public record AnswerResponse(
        String status,
        String answer,
        List<Citation> citations
) {
}