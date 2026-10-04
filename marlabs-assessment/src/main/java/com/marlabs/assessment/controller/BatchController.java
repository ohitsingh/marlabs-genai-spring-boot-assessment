package com.marlabs.assessment.controller;

import com.marlabs.assessment.model.BatchMetadata;
import com.marlabs.assessment.model.BatchResponse;
import com.marlabs.assessment.model.CallerContext;
import com.marlabs.assessment.service.BatchService;
import com.marlabs.assessment.service.CallerContextService;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import tools.jackson.databind.ObjectMapper;

@RestController
public class BatchController {

    private final CallerContextService callerContextService;
    private final BatchService batchService;
    private final ObjectMapper objectMapper;

    public BatchController(
            CallerContextService callerContextService,
            BatchService batchService,
            ObjectMapper objectMapper
    ) {
        this.callerContextService = callerContextService;
        this.batchService = batchService;
        this.objectMapper = objectMapper;
    }

    @PostMapping(
            value = "/batches",
            consumes = MediaType.MULTIPART_FORM_DATA_VALUE
    )
    public ResponseEntity<BatchResponse> processBatch(

            @RequestHeader("X-Caller-Id")
            String callerId,

            @RequestPart("metadata")
            String metadataJson,

            @RequestPart("files")
            MultipartFile[] files

    ) throws Exception {

        // 1. Resolve trusted caller
        CallerContext caller =
                callerContextService.getCaller(callerId);

        // 2. Parse metadata
        BatchMetadata metadata =
                objectMapper.readValue(
                        metadataJson,
                        BatchMetadata.class
                );

        // 3. Process batch
        BatchResponse response =
                batchService.process(
                        caller,
                        metadata,
                        files
                );

        return ResponseEntity.ok(response);
    }
}
