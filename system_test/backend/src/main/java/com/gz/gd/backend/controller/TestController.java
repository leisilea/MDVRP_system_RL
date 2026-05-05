package com.gz.gd.backend.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;

import java.util.*;

/**
 * 测试Controller - 验证SpringBoot与Flask API的通信
 */
@Slf4j
@RestController
@RequestMapping("/api/test")
public class TestController {

    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;
    
    @Value("${algorithm.service.url}")
    private String algorithmServiceUrl;

    public TestController(RestTemplate restTemplate, ObjectMapper objectMapper) {
        this.restTemplate = restTemplate;
        this.objectMapper = objectMapper;
    }

    /**
     * 测试1: 健康检查
     * GET http://localhost:8080/api/test/health
     */
    @GetMapping("/health")
    public ResponseEntity<Map<String, Object>> testHealth() {
        log.info("=== 测试1: 健康检查 ===");
        
        try {
            String url = algorithmServiceUrl + "/health";
            log.info("请求URL: {}", url);
            
            ResponseEntity<Map> response = restTemplate.getForEntity(url, Map.class);
            
            Map<String, Object> result = new HashMap<>();
            result.put("test", "健康检查");
            result.put("flask_url", url);
            result.put("flask_status", response.getStatusCode().value());
            result.put("flask_response", response.getBody());
            result.put("success", true);
            
            log.info("Flask响应: {}", response.getBody());
            return ResponseEntity.ok(result);
            
        } catch (Exception e) {
            log.error("健康检查失败", e);
            Map<String, Object> error = new HashMap<>();
            error.put("success", false);
            error.put("error", e.getMessage());
            return ResponseEntity.status(500).body(error);
        }
    }

    /**
     * 测试2: 简单求解
     * GET http://localhost:8080/api/test/solve-simple
     */
    @GetMapping("/solve-simple")
    public ResponseEntity<Map<String, Object>> testSimpleSolve() {
        log.info("=== 测试2: 简单求解 ===");
        
        try {
            // 构建请求数据
            Map<String, Object> requestBody = new HashMap<>();
            
            // 仓库数据
            List<Map<String, Object>> depots = new ArrayList<>();
            Map<String, Object> depot1 = new HashMap<>();
            depot1.put("id", 1);
            depot1.put("x", 0.0);
            depot1.put("y", 0.0);
            depot1.put("vehicles", 3);
            depot1.put("capacity", 100);
            depots.add(depot1);
            
            // 客户数据
            List<Map<String, Object>> customers = new ArrayList<>();
            customers.add(createCustomer(1, 10, 20, 15));
            customers.add(createCustomer(2, 30, 40, 20));
            customers.add(createCustomer(3, 50, 60, 25));
            customers.add(createCustomer(4, 70, 80, 18));
            customers.add(createCustomer(5, 90, 10, 22));
            
            // 算法参数
            Map<String, String> params = new HashMap<>();
            params.put("algorithm", "genetic");
            
            requestBody.put("depots", depots);
            requestBody.put("customers", customers);
            requestBody.put("params", params);
            
            log.info("请求数据: 仓库数={}, 客户数={}", depots.size(), customers.size());
            
            // 发送请求
            String url = algorithmServiceUrl + "/api/solve";
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            
            HttpEntity<Map<String, Object>> request = new HttpEntity<>(requestBody, headers);
            
            long startTime = System.currentTimeMillis();
            ResponseEntity<Map> response = restTemplate.postForEntity(url, request, Map.class);
            long elapsed = System.currentTimeMillis() - startTime;
            
            Map<String, Object> flaskResponse = response.getBody();
            
            // 解析响应
            Map<String, Object> result = new HashMap<>();
            result.put("test", "简单求解");
            result.put("flask_url", url);
            result.put("request_time_ms", elapsed);
            result.put("success", flaskResponse.get("success"));
            
            if (Boolean.TRUE.equals(flaskResponse.get("success"))) {
                Map<String, Object> data = (Map<String, Object>) flaskResponse.get("data");
                
                result.put("total_cost", data.get("total_cost"));
                result.put("compute_time", data.get("compute_time"));
                result.put("num_routes", data.get("num_routes"));
                result.put("algorithm", data.get("algorithm"));
                result.put("routes", data.get("routes"));
                
                log.info("求解成功 - 总成本: {}, 计算时间: {}s, 路径数: {}", 
                    data.get("total_cost"), 
                    data.get("compute_time"), 
                    data.get("num_routes"));
            } else {
                result.put("error", flaskResponse.get("error"));
                log.error("求解失败: {}", flaskResponse.get("error"));
            }
            
            return ResponseEntity.ok(result);
            
        } catch (Exception e) {
            log.error("简单求解测试失败", e);
            Map<String, Object> error = new HashMap<>();
            error.put("success", false);
            error.put("error", e.getMessage());
            error.put("error_type", e.getClass().getSimpleName());
            return ResponseEntity.status(500).body(error);
        }
    }

    /**
     * 测试3: 自定义求解
     * POST http://localhost:8080/api/test/solve-custom
     * 
     * 请求体示例:
     * {
     *   "depots": [{"id": 1, "x": 0, "y": 0, "vehicles": 3, "capacity": 100}],
     *   "customers": [
     *     {"id": 1, "x": 10, "y": 20, "demand": 15},
     *     {"id": 2, "x": 30, "y": 40, "demand": 20}
     *   ],
     *   "algorithm": "genetic"
     * }
     */
    @PostMapping("/solve-custom")
    public ResponseEntity<Map<String, Object>> testCustomSolve(@RequestBody Map<String, Object> input) {
        log.info("=== 测试3: 自定义求解 ===");
        
        try {
            List<Map<String, Object>> depots = (List<Map<String, Object>>) input.get("depots");
            List<Map<String, Object>> customers = (List<Map<String, Object>>) input.get("customers");
            String algorithm = (String) input.getOrDefault("algorithm", "genetic");
            
            log.info("接收到请求 - 仓库数: {}, 客户数: {}, 算法: {}", 
                depots.size(), customers.size(), algorithm);
            
            // 构建Flask请求
            Map<String, Object> requestBody = new HashMap<>();
            requestBody.put("depots", depots);
            requestBody.put("customers", customers);
            
            Map<String, String> params = new HashMap<>();
            params.put("algorithm", algorithm);
            requestBody.put("params", params);
            
            // 发送请求
            String url = algorithmServiceUrl + "/api/solve";
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            
            HttpEntity<Map<String, Object>> request = new HttpEntity<>(requestBody, headers);
            
            long startTime = System.currentTimeMillis();
            ResponseEntity<Map> response = restTemplate.postForEntity(url, request, Map.class);
            long elapsed = System.currentTimeMillis() - startTime;
            
            Map<String, Object> flaskResponse = response.getBody();
            
            // 构建响应
            Map<String, Object> result = new HashMap<>();
            result.put("test", "自定义求解");
            result.put("request_time_ms", elapsed);
            result.put("flask_response", flaskResponse);
            
            log.info("求解完成 - 耗时: {}ms", elapsed);
            
            return ResponseEntity.ok(result);
            
        } catch (Exception e) {
            log.error("自定义求解测试失败", e);
            Map<String, Object> error = new HashMap<>();
            error.put("success", false);
            error.put("error", e.getMessage());
            return ResponseEntity.status(500).body(error);
        }
    }

    /**
     * 测试4: 错误处理
     * GET http://localhost:8080/api/test/error-handling
     */
    @GetMapping("/error-handling")
    public ResponseEntity<Map<String, Object>> testErrorHandling() {
        log.info("=== 测试4: 错误处理 ===");
        
        try {
            // 发送空请求，测试Flask的错误处理
            String url = algorithmServiceUrl + "/api/solve";
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            
            Map<String, Object> emptyRequest = new HashMap<>();
            HttpEntity<Map<String, Object>> request = new HttpEntity<>(emptyRequest, headers);
            
            ResponseEntity<Map> response = restTemplate.postForEntity(url, request, Map.class);
            
            Map<String, Object> result = new HashMap<>();
            result.put("test", "错误处理");
            result.put("expected", "应该返回400错误");
            result.put("actual_status", response.getStatusCode().value());
            result.put("flask_response", response.getBody());
            
            return ResponseEntity.ok(result);
            
        } catch (org.springframework.web.client.HttpClientErrorException e) {
            // 预期的400错误
            log.info("捕获到预期的客户端错误: {}", e.getStatusCode());
            
            Map<String, Object> result = new HashMap<>();
            result.put("test", "错误处理");
            result.put("success", true);
            result.put("message", "Flask正确返回了400错误");
            result.put("status_code", e.getStatusCode().value());
            result.put("error_body", e.getResponseBodyAsString());
            
            return ResponseEntity.ok(result);
            
        } catch (Exception e) {
            log.error("错误处理测试失败", e);
            Map<String, Object> error = new HashMap<>();
            error.put("success", false);
            error.put("error", e.getMessage());
            return ResponseEntity.status(500).body(error);
        }
    }

    /**
     * 测试5: 完整流程测试
     * GET http://localhost:8080/api/test/full-workflow
     */
    @GetMapping("/full-workflow")
    public ResponseEntity<Map<String, Object>> testFullWorkflow() {
        log.info("=== 测试5: 完整流程测试 ===");
        
        Map<String, Object> result = new HashMap<>();
        List<Map<String, Object>> tests = new ArrayList<>();
        
        try {
            // 1. 健康检查
            log.info("步骤1: 健康检查");
            String healthUrl = algorithmServiceUrl + "/health";
            ResponseEntity<Map> healthResponse = restTemplate.getForEntity(healthUrl, Map.class);
            
            Map<String, Object> test1 = new HashMap<>();
            test1.put("step", 1);
            test1.put("name", "健康检查");
            test1.put("status", healthResponse.getStatusCode().value());
            test1.put("success", healthResponse.getStatusCode().is2xxSuccessful());
            tests.add(test1);
            
            // 2. 获取算法列表
            log.info("步骤2: 获取算法列表");
            String algorithmsUrl = algorithmServiceUrl + "/api/algorithms";
            ResponseEntity<Map> algorithmsResponse = restTemplate.getForEntity(algorithmsUrl, Map.class);
            
            Map<String, Object> test2 = new HashMap<>();
            test2.put("step", 2);
            test2.put("name", "获取算法列表");
            test2.put("status", algorithmsResponse.getStatusCode().value());
            test2.put("success", algorithmsResponse.getStatusCode().is2xxSuccessful());
            test2.put("algorithms", algorithmsResponse.getBody());
            tests.add(test2);
            
            // 3. 求解问题
            log.info("步骤3: 求解MDVRP问题");
            Map<String, Object> solveRequest = buildTestRequest();
            
            String solveUrl = algorithmServiceUrl + "/api/solve";
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            HttpEntity<Map<String, Object>> request = new HttpEntity<>(solveRequest, headers);
            
            long startTime = System.currentTimeMillis();
            ResponseEntity<Map> solveResponse = restTemplate.postForEntity(solveUrl, request, Map.class);
            long elapsed = System.currentTimeMillis() - startTime;
            
            Map<String, Object> test3 = new HashMap<>();
            test3.put("step", 3);
            test3.put("name", "求解MDVRP");
            test3.put("status", solveResponse.getStatusCode().value());
            test3.put("success", solveResponse.getStatusCode().is2xxSuccessful());
            test3.put("request_time_ms", elapsed);
            test3.put("solution", solveResponse.getBody());
            tests.add(test3);
            
            // 汇总结果
            result.put("test", "完整流程测试");
            result.put("total_tests", tests.size());
            result.put("all_passed", tests.stream().allMatch(t -> Boolean.TRUE.equals(t.get("success"))));
            result.put("tests", tests);
            result.put("success", true);
            
            log.info("完整流程测试完成 - 所有测试通过: {}", result.get("all_passed"));
            
            return ResponseEntity.ok(result);
            
        } catch (Exception e) {
            log.error("完整流程测试失败", e);
            result.put("success", false);
            result.put("error", e.getMessage());
            result.put("completed_tests", tests);
            return ResponseEntity.status(500).body(result);
        }
    }

    // ==================== 辅助方法 ====================

    private Map<String, Object> createCustomer(int id, double x, double y, int demand) {
        Map<String, Object> customer = new HashMap<>();
        customer.put("id", id);
        customer.put("x", x);
        customer.put("y", y);
        customer.put("demand", demand);
        return customer;
    }

    private Map<String, Object> buildTestRequest() {
        Map<String, Object> request = new HashMap<>();
        
        // 仓库
        List<Map<String, Object>> depots = new ArrayList<>();
        Map<String, Object> depot = new HashMap<>();
        depot.put("id", 1);
        depot.put("x", 0.0);
        depot.put("y", 0.0);
        depot.put("vehicles", 2);
        depot.put("capacity", 100);
        depots.add(depot);
        
        // 客户
        List<Map<String, Object>> customers = new ArrayList<>();
        customers.add(createCustomer(1, 10, 20, 15));
        customers.add(createCustomer(2, 30, 40, 20));
        customers.add(createCustomer(3, 50, 60, 25));
        
        // 参数
        Map<String, String> params = new HashMap<>();
        params.put("algorithm", "genetic");
        
        request.put("depots", depots);
        request.put("customers", customers);
        request.put("params", params);
        
        return request;
    }
}
