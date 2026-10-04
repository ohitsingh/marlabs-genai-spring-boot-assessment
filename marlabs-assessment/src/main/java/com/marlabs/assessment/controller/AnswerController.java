package com.marlabs.assessment.controller;

import com.marlabs.assessment.model.AnswerRequest;
import com.marlabs.assessment.model.AnswerResponse;
import com.marlabs.assessment.model.CallerContext;
import com.marlabs.assessment.model.PythonAnswerRequest;
import com.marlabs.assessment.service.CallerContextService;
import com.marlabs.assessment.service.PythonClient;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;

@RestController
@RequestMapping
public class AnswerController {

    private final CallerContextService callerContextService;
    private final PythonClient pythonClient;

    public AnswerController(
            CallerContextService callerContextService,
            PythonClient pythonClient
    ) {
        this.callerContextService = callerContextService;
        this.pythonClient = pythonClient;
    }

    @PostMapping("/answer")
    public ResponseEntity<AnswerResponse> answer(

            @RequestHeader("X-Caller-Id")
            String callerId,

            @Valid
            @RequestBody
            AnswerRequest request
    ) {

        // 1. Resolve caller from trusted server-side lookup
        CallerContext caller =
                callerContextService.getCaller(callerId);

        // 2. Validate actual calendar date
        LocalDate asOf =
                LocalDate.parse(request.asOf());

        // 3. Create trusted request for Python
        PythonAnswerRequest pythonRequest =
                new PythonAnswerRequest(
                        request.question(),
                        asOf.toString(),
                        caller.tenant(),
                        caller.role()
                );

        // 4. Ask Python service
        AnswerResponse response =
                pythonClient.answer(pythonRequest);

        // 5. Return public response
        return ResponseEntity.ok(response);
    }
}