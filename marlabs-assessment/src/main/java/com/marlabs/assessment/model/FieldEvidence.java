package com.marlabs.assessment.model;

public record FieldEvidence(
        Evidence benefit,
        Evidence amount,
        Evidence currency,
        Evidence reference
) {
}