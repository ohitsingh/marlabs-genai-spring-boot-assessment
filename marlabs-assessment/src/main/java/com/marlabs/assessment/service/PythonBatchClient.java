package com.marlabs.assessment.service;

import com.marlabs.assessment.model.BatchResponse;
import com.marlabs.assessment.model.PythonBatchMetadata;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestClient;
import org.springframework.web.multipart.MultipartFile;

import tools.jackson.core.JacksonException;
import tools.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.util.List;

@Service
public class PythonBatchClient {

    private final RestClient restClient;

    private final ObjectMapper objectMapper;

    private final String batchPath;

    public PythonBatchClient(
            RestClient.Builder builder,
            ObjectMapper objectMapper,
            @Value("${python.service.base-url}") String baseUrl,
            @Value("${python.service.batch-path}") String batchPath) {

        this.restClient = builder
                .baseUrl(baseUrl)
                .build();

        this.objectMapper = objectMapper;

        this.batchPath = batchPath;
    }

    public BatchResponse processBatch(
            PythonBatchMetadata metadata,
            List<MultipartFile> files) {

        try {

            // --------------------------------------------------
            // Convert metadata object to JSON
            // --------------------------------------------------

            String metadataJson =
                    objectMapper.writeValueAsString(metadata);

            // --------------------------------------------------
            // Build multipart request
            // --------------------------------------------------

            MultiValueMap<String, Object> body =
                    new LinkedMultiValueMap<>();

            // --------------------------------------------------
            // Metadata part
            // --------------------------------------------------

            body.add(
                    "metadata",
                    metadataJson
            );

            // --------------------------------------------------
            // File parts
            // --------------------------------------------------

            for (MultipartFile file : files) {

                ByteArrayResource resource =
                        new ByteArrayResource(
                                file.getBytes()
                        ) {

                            @Override
                            public String getFilename() {

                                return file.getOriginalFilename();
                            }
                        };

                body.add(
                        "files",
                        resource
                );
            }

            // --------------------------------------------------
            // Call Python
            // --------------------------------------------------

            return restClient
                    .post()
                    .uri(batchPath)
                    .contentType(
                            MediaType.MULTIPART_FORM_DATA
                    )
                    .body(body)
                    .retrieve()
                    .body(BatchResponse.class);

        } catch (JacksonException e) {

            throw new IllegalStateException(
                    "Failed to serialize batch metadata.",
                    e
            );

        } catch (IOException e) {

            throw new IllegalStateException(
                    "Failed to read uploaded batch files.",
                    e
            );
        }
    }
}