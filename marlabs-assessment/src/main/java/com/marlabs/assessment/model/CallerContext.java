package com.marlabs.assessment.model;

public record CallerContext(
        String callerId,
        String tenant,
        String role
) {
}
