package com.marlabs.assessment.model;

public record Summary(
        int total,
        int completed,
        int failed
) {
}
