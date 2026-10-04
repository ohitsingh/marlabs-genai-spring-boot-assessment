package com.marlabs.assessment.service;

import com.marlabs.assessment.model.AnswerResponse;
import com.marlabs.assessment.model.PythonAnswerRequest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

@Service
public class PythonClient {

    private final RestClient restClient;

    private final String answerPath;

    public PythonClient(
            RestClient.Builder builder,
            @Value("${python.service.base-url}") String baseUrl,
            @Value("${python.service.answer-path}") String answerPath
    ) {
        this.restClient = builder
                .baseUrl(baseUrl)
                .build();

        this.answerPath = answerPath;
    }

    public AnswerResponse answer(PythonAnswerRequest request) {

        return restClient
                .post()
                .uri(answerPath)
                .contentType(MediaType.APPLICATION_JSON)
                .body(request)
                .retrieve()
                .body(AnswerResponse.class);
    }
}
