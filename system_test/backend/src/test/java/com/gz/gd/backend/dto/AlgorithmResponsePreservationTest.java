package com.gz.gd.backend.dto;

import com.fasterxml.jackson.databind.ObjectMapper;
import net.jqwik.api.*;
import net.jqwik.api.constraints.*;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Preservation Property Tests for Algorithm Response Timestamp Fix
 * 
 * **Validates: Requirements 3.1, 3.2, 3.3**
 * 
 * IMPORTANT: These tests follow observation-first methodology.
 * They capture the CURRENT behavior on UNFIXED code for responses
 * WITHOUT timestamp field in the data object.
 * 
 * EXPECTED OUTCOME: All tests PASS on unfixed code (confirms baseline behavior to preserve).
 * After fix implementation, these tests must continue to pass (no regressions).
 * 
 * NOTE: Requirement 3.4 (top-level timestamp) is not tested here because the current
 * code does NOT ignore top-level timestamp - it also causes UnrecognizedPropertyException.
 * The fix will need to address both top-level and data-level timestamp fields.
 */
public class AlgorithmResponsePreservationTest {

    private final ObjectMapper objectMapper = new ObjectMapper();

    /**
     * Property 1: Legacy Response Preservation
     * 
     * For any response without timestamp field in data object,
     * deserialization should succeed and extract all recognized fields correctly.
     * 
     * This property validates that existing field processing remains unchanged.
     */
    @Property
    @Label("Legacy responses without timestamp deserialize correctly")
    void legacyResponsesDeserializeCorrectly(
            @ForAll("legacySuccessResponses") String jsonResponse
    ) throws Exception {
        // Deserialize the response
        AlgorithmResponse response = objectMapper.readValue(jsonResponse, AlgorithmResponse.class);
        
        // Verify successful deserialization
        assertNotNull(response, "Response should be successfully deserialized");
        assertTrue(response.getSuccess(), "Success flag should be true");
        assertNotNull(response.getData(), "Data object should not be null");
        
        // Verify all recognized fields are accessible
        assertNotNull(response.getData().getRoutes(), "Routes should not be null");
        assertNotNull(response.getData().getTotalCost(), "TotalCost should not be null");
        
        // Verify data integrity
        assertTrue(response.getData().getTotalCost() >= 0, "TotalCost should be non-negative");
        if (response.getData().getNumRoutes() != null) {
            assertTrue(response.getData().getNumRoutes() >= 0, "NumRoutes should be non-negative");
        }
    }

    /**
     * Property 2: Error Response Preservation
     * 
     * For any error response (success=false), deserialization should succeed
     * and the error message should be accessible.
     * 
     * This validates that error handling remains unchanged.
     */
    @Property
    @Label("Error responses are handled correctly")
    void errorResponsesHandledCorrectly(
            @ForAll("errorResponses") String jsonResponse
    ) throws Exception {
        // Deserialize the error response
        AlgorithmResponse response = objectMapper.readValue(jsonResponse, AlgorithmResponse.class);
        
        // Verify successful deserialization
        assertNotNull(response, "Response should be successfully deserialized");
        assertFalse(response.getSuccess(), "Success flag should be false for error responses");
        assertNotNull(response.getError(), "Error message should not be null");
        assertFalse(response.getError().isEmpty(), "Error message should not be empty");
    }

    /**
     * Property 3: Partial Data Preservation
     * 
     * For any response with missing optional fields (but no timestamp in data),
     * deserialization should succeed and handle null/missing fields gracefully.
     * 
     * This validates that optional field handling remains unchanged.
     */
    @Property
    @Label("Responses with missing optional fields work correctly")
    void partialDataResponsesWork(
            @ForAll("partialDataResponses") String jsonResponse
    ) throws Exception {
        // Deserialize the response
        AlgorithmResponse response = objectMapper.readValue(jsonResponse, AlgorithmResponse.class);
        
        // Verify successful deserialization
        assertNotNull(response, "Response should be successfully deserialized");
        assertTrue(response.getSuccess(), "Success flag should be true");
        assertNotNull(response.getData(), "Data object should not be null");
        
        // Verify required fields are present
        assertNotNull(response.getData().getTotalCost(), "TotalCost should not be null");
        assertNotNull(response.getData().getRoutes(), "Routes should not be null");
        
        // Optional fields may be null - this is expected behavior
        // No assertions on optional fields like numRoutes, computeTime, algorithm, convergence
    }

    /**
     * Property 4: Field Order Independence
     * 
     * For any response with fields in different orders (but no timestamp in data),
     * deserialization should succeed and extract all fields correctly.
     * 
     * This validates that field order doesn't affect parsing.
     */
    @Property
    @Label("Field order does not affect deserialization")
    void fieldOrderIndependence(
            @ForAll("responsesWithDifferentFieldOrder") String jsonResponse
    ) throws Exception {
        // Deserialize the response
        AlgorithmResponse response = objectMapper.readValue(jsonResponse, AlgorithmResponse.class);
        
        // Verify successful deserialization
        assertNotNull(response, "Response should be successfully deserialized");
        assertTrue(response.getSuccess(), "Success flag should be true");
        assertNotNull(response.getData(), "Data object should not be null");
        
        // Verify data fields are correctly extracted
        assertNotNull(response.getData().getTotalCost(), "TotalCost should not be null");
        assertNotNull(response.getData().getRoutes(), "Routes should not be null");
    }

    /**
     * Property 5: All Recognized Fields Extraction
     * 
     * For any response with all recognized fields (but no timestamp in data),
     * all fields should be correctly extracted and accessible.
     * 
     * This validates comprehensive field processing remains unchanged.
     */
    @Property
    @Label("All recognized fields are extracted correctly")
    void allRecognizedFieldsExtracted(
            @ForAll("completeResponses") String jsonResponse
    ) throws Exception {
        // Deserialize the response
        AlgorithmResponse response = objectMapper.readValue(jsonResponse, AlgorithmResponse.class);
        
        // Verify successful deserialization
        assertNotNull(response, "Response should be successfully deserialized");
        assertTrue(response.getSuccess(), "Success flag should be true");
        
        // Verify all recognized fields are present and accessible
        AlgorithmResponse.SolutionData data = response.getData();
        assertNotNull(data, "Data object should not be null");
        assertNotNull(data.getNumRoutes(), "NumRoutes should not be null");
        assertNotNull(data.getTotalCost(), "TotalCost should not be null");
        assertNotNull(data.getComputeTime(), "ComputeTime should not be null");
        assertNotNull(data.getAlgorithm(), "Algorithm should not be null");
        assertNotNull(data.getRoutes(), "Routes should not be null");
        assertNotNull(data.getConvergence(), "Convergence should not be null");
        
        // Verify field values are reasonable
        assertTrue(data.getNumRoutes() >= 0, "NumRoutes should be non-negative");
        assertTrue(data.getTotalCost() >= 0, "TotalCost should be non-negative");
        assertTrue(data.getComputeTime() >= 0, "ComputeTime should be non-negative");
        assertFalse(data.getAlgorithm().isEmpty(), "Algorithm should not be empty");
    }

    // ========== Arbitraries (Test Data Generators) ==========

    @Provide
    Arbitrary<String> legacySuccessResponses() {
        return Combinators.combine(
                Arbitraries.integers().between(1, 10),
                Arbitraries.doubles().between(50.0, 500.0),
                Arbitraries.doubles().between(0.5, 10.0),
                Arbitraries.of("ACO", "GA", "PSO", "SA"),
                routes(),
                convergenceData()
        ).as((numRoutes, totalCost, computeTime, algorithm, routes, convergence) ->
                String.format("""
                    {
                        "success": true,
                        "data": {
                            "numRoutes": %d,
                            "totalCost": %.2f,
                            "computeTime": %.2f,
                            "algorithm": "%s",
                            "routes": %s,
                            "convergence": %s
                        }
                    }
                    """, numRoutes, totalCost, computeTime, algorithm, routes, convergence)
        );
    }

    @Provide
    Arbitrary<String> errorResponses() {
        return Arbitraries.of(
                "Invalid input parameters",
                "Algorithm execution failed",
                "Timeout exceeded",
                "No feasible solution found",
                "Internal server error"
        ).map(error ->
                String.format("""
                    {
                        "success": false,
                        "error": "%s"
                    }
                    """, error)
        );
    }

    @Provide
    Arbitrary<String> partialDataResponses() {
        return Combinators.combine(
                Arbitraries.doubles().between(50.0, 500.0),
                routes()
        ).as((totalCost, routes) ->
                String.format("""
                    {
                        "success": true,
                        "data": {
                            "totalCost": %.2f,
                            "routes": %s
                        }
                    }
                    """, totalCost, routes)
        );
    }

    @Provide
    Arbitrary<String> responsesWithDifferentFieldOrder() {
        return Combinators.combine(
                Arbitraries.integers().between(1, 10),
                Arbitraries.doubles().between(50.0, 500.0),
                routes()
        ).as((numRoutes, totalCost, routes) ->
                String.format("""
                    {
                        "data": {
                            "routes": %s,
                            "totalCost": %.2f,
                            "numRoutes": %d
                        },
                        "success": true
                    }
                    """, routes, totalCost, numRoutes)
        );
    }

    @Provide
    Arbitrary<String> completeResponses() {
        return Combinators.combine(
                Arbitraries.integers().between(1, 10),
                Arbitraries.doubles().between(50.0, 500.0),
                Arbitraries.doubles().between(0.5, 10.0),
                Arbitraries.of("ACO", "GA", "PSO", "SA"),
                routes(),
                convergenceData()
        ).as((numRoutes, totalCost, computeTime, algorithm, routes, convergence) ->
                String.format("""
                    {
                        "success": true,
                        "data": {
                            "numRoutes": %d,
                            "totalCost": %.2f,
                            "computeTime": %.2f,
                            "algorithm": "%s",
                            "routes": %s,
                            "convergence": %s
                        }
                    }
                    """, numRoutes, totalCost, computeTime, algorithm, routes, convergence)
        );
    }

    @Provide
    Arbitrary<String> routes() {
        return Arbitraries.integers().between(0, 5).flatMap(size -> {
            if (size == 0) {
                return Arbitraries.just("[]");
            }
            
            List<String> routeList = new ArrayList<>();
            for (int i = 0; i < size; i++) {
                routeList.add(String.format(
                    """
                    {
                        "vehicleId": %d,
                        "depotId": 1,
                        "path": [%d, %d, %d],
                        "cost": %.2f
                    }
                    """,
                    i + 1,
                    i * 3 + 1, i * 3 + 2, i * 3 + 3,
                    50.0 + i * 20.0
                ));
            }
            return Arbitraries.just("[" + String.join(",", routeList) + "]");
        });
    }

    @Provide
    Arbitrary<String> convergenceData() {
        return Arbitraries.integers().between(0, 10).flatMap(size -> {
            if (size == 0) {
                return Arbitraries.just("[]");
            }
            
            List<String> convergenceList = new ArrayList<>();
            double cost = 500.0;
            for (int i = 0; i < size; i++) {
                cost = cost * 0.9; // Simulate convergence
                convergenceList.add(String.format(
                    """
                    {"iteration": %d, "bestCost": %.2f}
                    """,
                    i + 1, cost
                ));
            }
            return Arbitraries.just("[" + String.join(",", convergenceList) + "]");
        });
    }
}
