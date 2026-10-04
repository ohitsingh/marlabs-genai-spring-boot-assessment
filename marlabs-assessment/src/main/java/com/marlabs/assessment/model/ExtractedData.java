package com.marlabs.assessment.model;

import com.fasterxml.jackson.annotation.JsonProperty;

public record ExtractedData(

        String benefit,

        String amount,

        String currency,

        String reference,

        @JsonProperty("amount_ambiguous")
        boolean amountAmbiguous
) {
}