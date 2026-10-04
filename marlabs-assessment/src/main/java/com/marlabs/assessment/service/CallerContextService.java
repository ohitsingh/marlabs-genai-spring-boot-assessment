package com.marlabs.assessment.service;

import com.marlabs.assessment.model.CallerContext;
import org.springframework.stereotype.Service;

import java.util.Map;

@Service
public class CallerContextService {

    private final Map<String, CallerContext> callers = Map.of(
            "atlas-employee-01",
            new CallerContext(
                    "atlas-employee-01",
                    "Atlas",
                    "employee"
            ),

            "atlas-contractor-01",
            new CallerContext(
                    "atlas-contractor-01",
                    "Atlas",
                    "contractor"
            ),

            "boreal-employee-01",
            new CallerContext(
                    "boreal-employee-01",
                    "Boreal",
                    "employee"
            )
    );

    public CallerContext getCaller(String callerId) {

        if (callerId == null || callerId.isBlank()) {
            throw new IllegalArgumentException("X-Caller-Id is required");
        }

        CallerContext context = callers.get(callerId);

        if (context == null) {
            throw new IllegalArgumentException("Unknown caller");
        }

        return context;
    }
}
