package com.gz.gd.backend.dto;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Bug Condition Exploration Test for Algorithm Response Timestamp Fix
 * 
 * **Validates: Requirements 2.1, 2.2, 2.3**
 * 
 * CRITICAL: This test is EXPECTED TO FAIL on unfixed code.
 * The test failure confirms that Jackson throws UnrecognizedPropertyException
 * when encountering the "timestamp" field in the response data object.
 * 
 * The test assertions encode the EXPECTED BEHAVIOR (successful deserialization).
 * When the fix is implemented (@JsonIgnoreProperties annotation added),
 * this test will pass, confirming the bug is fixed.
 */
@SpringBootTest
public class AlgorithmResponseDeserializationTest {

    private final ObjectMapper objectMapper = new ObjectMapper();

    /**
     * Test Case 1: ACO Response with Timestamp
     * 
     * Simulates a JSON response from the Flask algorithm service with ACO algorithm
     * results including a timestamp field in the data object AND top-level timestamp.
     * 
     * EXPECTED ON UNFIXED CODE: UnrecognizedPropertyException
     * EXPECTED AFTER FIX: Successful deserialization with timestamp ignored
     */
    @Test
    public void testDeserializeAcoResponseWithTimestamp() throws Exception {
        String jsonResponse = """
            {
                "success": true,
                "data": {
                    "numRoutes": 3,
                    "totalCost": 150.5,
                    "computeTime": 2.3,
                    "algorithm": "ACO",
                    "timestamp": 1709123456.789,
                    "routes": [
                        {
                            "vehicleId": 1,
                            "depotId": 1,
                            "path": [1, 2, 3],
                            "cost": 50.5
                        }
                    ],
                    "convergence": [
                        {"iteration": 1, "bestCost": 200.0}
                    ]
                },
                "timestamp": 1709123456.789
            }
            """;

        // This assertion encodes the expected behavior after fix
        // On unfixed code, this will throw UnrecognizedPropertyException
        AlgorithmResponse response = objectMapper.readValue(jsonResponse, AlgorithmResponse.class);
        
        assertNotNull(response, "Response should be successfully deserialized");
        assertTrue(response.getSuccess(), "Success flag should be true");
        assertNotNull(response.getData(), "Data object should not be null");
        assertEquals(3, response.getData().getNumRoutes(), "NumRoutes should be 3");
        assertEquals(150.5, response.getData().getTotalCost(), "TotalCost should be 150.5");
        assertEquals(2.3, response.getData().getComputeTime(), "ComputeTime should be 2.3");
        assertEquals("ACO", response.getData().getAlgorithm(), "Algorithm should be ACO");
        assertNotNull(response.getData().getRoutes(), "Routes should not be null");
        assertEquals(1, response.getData().getRoutes().size(), "Should have 1 route");
        assertNotNull(response.getData().getConvergence(), "Convergence should not be null");
    }

    /**
     * Test Case 2: GA Response with Timestamp
     * 
     * Simulates a JSON response with Genetic Algorithm results including timestamp.
     * 
     * EXPECTED ON UNFIXED CODE: UnrecognizedPropertyException
     * EXPECTED AFTER FIX: Successful deserialization with timestamp ignored
     */
    @Test
    public void testDeserializeGaResponseWithTimestamp() throws Exception {
        String jsonResponse = """
            {
                "success": true,
                "data": {
                    "numRoutes": 2,
                    "totalCost": 200.0,
                    "computeTime": 1.5,
                    "algorithm": "GA",
                    "timestamp": 1709123500.123,
                    "routes": [
                        {
                            "vehicleId": 1,
                            "depotId": 1,
                            "path": [1, 2],
                            "cost": 100.0
                        },
                        {
                            "vehicleId": 2,
                            "depotId": 1,
                            "path": [3, 4],
                            "cost": 100.0
                        }
                    ],
                    "convergence": []
                }
            }
            """;

        AlgorithmResponse response = objectMapper.readValue(jsonResponse, AlgorithmResponse.class);
        
        assertNotNull(response, "Response should be successfully deserialized");
        assertTrue(response.getSuccess(), "Success flag should be true");
        assertNotNull(response.getData(), "Data object should not be null");
        assertEquals(2, response.getData().getNumRoutes(), "NumRoutes should be 2");
        assertEquals(200.0, response.getData().getTotalCost(), "TotalCost should be 200.0");
        assertEquals("GA", response.getData().getAlgorithm(), "Algorithm should be GA");
        assertEquals(2, response.getData().getRoutes().size(), "Should have 2 routes");
    }

    /**
     * Test Case 3: PSO Response with Timestamp
     * 
     * Simulates a JSON response with Particle Swarm Optimization results including timestamp.
     * 
     * EXPECTED ON UNFIXED CODE: UnrecognizedPropertyException
     * EXPECTED AFTER FIX: Successful deserialization with timestamp ignored
     */
    @Test
    public void testDeserializePsoResponseWithTimestamp() throws Exception {
        String jsonResponse = """
            {
                "success": true,
                "data": {
                    "numRoutes": 4,
                    "totalCost": 180.0,
                    "computeTime": 3.0,
                    "algorithm": "PSO",
                    "timestamp": 1709123600.456,
                    "routes": [
                        {
                            "vehicleId": 1,
                            "depotId": 1,
                            "path": [1],
                            "cost": 45.0
                        }
                    ],
                    "convergence": [
                        {"iteration": 1, "bestCost": 250.0},
                        {"iteration": 2, "bestCost": 180.0}
                    ]
                }
            }
            """;

        AlgorithmResponse response = objectMapper.readValue(jsonResponse, AlgorithmResponse.class);
        
        assertNotNull(response, "Response should be successfully deserialized");
        assertTrue(response.getSuccess(), "Success flag should be true");
        assertEquals(4, response.getData().getNumRoutes(), "NumRoutes should be 4");
        assertEquals(180.0, response.getData().getTotalCost(), "TotalCost should be 180.0");
        assertEquals("PSO", response.getData().getAlgorithm(), "Algorithm should be PSO");
        assertEquals(2, response.getData().getConvergence().size(), "Should have 2 convergence points");
    }

    /**
     * Test Case 4: Minimal Response with Timestamp
     * 
     * Simulates a minimal JSON response with only required fields plus timestamp.
     * 
     * EXPECTED ON UNFIXED CODE: UnrecognizedPropertyException
     * EXPECTED AFTER FIX: Successful deserialization with timestamp ignored
     */
    @Test
    public void testDeserializeMinimalResponseWithTimestamp() throws Exception {
        String jsonResponse = """
            {
                "success": true,
                "data": {
                    "totalCost": 100.0,
                    "timestamp": 1709123700.789,
                    "routes": []
                }
            }
            """;

        AlgorithmResponse response = objectMapper.readValue(jsonResponse, AlgorithmResponse.class);
        
        assertNotNull(response, "Response should be successfully deserialized");
        assertTrue(response.getSuccess(), "Success flag should be true");
        assertNotNull(response.getData(), "Data object should not be null");
        assertEquals(100.0, response.getData().getTotalCost(), "TotalCost should be 100.0");
        assertNotNull(response.getData().getRoutes(), "Routes should not be null");
        assertEquals(0, response.getData().getRoutes().size(), "Routes should be empty");
    }
}
