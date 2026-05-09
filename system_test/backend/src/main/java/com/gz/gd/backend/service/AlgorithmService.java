package com.gz.gd.backend.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.gz.gd.backend.dto.AlgorithmRequest;
import com.gz.gd.backend.dto.AlgorithmResponse;
import com.gz.gd.backend.entity.Customer;
import com.gz.gd.backend.entity.Depot;
import com.gz.gd.backend.entity.Solution;
import com.gz.gd.backend.mapper.CustomerMapper;
import com.gz.gd.backend.mapper.DepotMapper;
import com.gz.gd.backend.mapper.SolutionMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.retry.annotation.Backoff;
import org.springframework.retry.annotation.Retryable;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.HttpServerErrorException;

import java.math.BigDecimal;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Slf4j
@Service
public class AlgorithmService {
    
    @Autowired
    private RestTemplate restTemplate;
    
    @Autowired
    private DepotMapper depotMapper;
    
    @Autowired
    private CustomerMapper customerMapper;
    
    @Autowired
    private SolutionMapper solutionMapper;
    
    @Autowired
    private ObjectMapper objectMapper;
    
    @Value("${algorithm.service.url}")
    private String algorithmServiceUrl;
    
    /**
     * 调用Python算法服务求解MDVRP
     * 
     * 重试策略：
     * - 最多重试3次
     * - 每次重试间隔2秒
     * - 仅在网络错误或服务器错误时重试
     */
    @Retryable(
        value = {ResourceAccessException.class, HttpServerErrorException.class},
        maxAttempts = 3,
        backoff = @Backoff(delay = 2000)
    )
    // TAG : 转为异步后废弃接口
    // public AlgorithmResponse solve(Long scenarioId, Map<String, Object> params) {
    //     log.info("开始求解场景 ID: {}, 参数: {}", scenarioId, params);
        
    //     try {
    //         // 1. 从数据库读取场景数据
    //         List<Depot> depots = depotMapper.selectByMap(
    //             Map.of("scenario_id", scenarioId)
    //         );
    //         List<Customer> customers = customerMapper.selectByMap(
    //             Map.of("scenario_id", scenarioId)
    //         );
            
    //         log.info("场景数据 - 仓库数: {}, 客户数: {}", depots.size(), customers.size());
            
    //         // 2. 转换为算法服务需要的格式
    //         AlgorithmRequest request = buildAlgorithmRequest(depots, customers, params);
            
    //         // 3. 调用Python服务
    //         String url = algorithmServiceUrl + "/api/solve";
    //         HttpHeaders headers = new HttpHeaders();
    //         headers.setContentType(MediaType.APPLICATION_JSON);
            
    //         HttpEntity<AlgorithmRequest> httpRequest = new HttpEntity<>(request, headers);
            
    //         ResponseEntity<AlgorithmResponse> response = restTemplate.postForEntity(
    //             url, httpRequest, AlgorithmResponse.class
    //         );
            
    //         AlgorithmResponse result = response.getBody();
            
    //         // 4. 保存结果到数据库
    //         if (result != null && result.getSuccess()) {
    //             saveSolution(scenarioId, result);
    //             log.info("求解完成 - 总成本: {}, 耗时: {}s", 
    //                 result.getData().getTotalCost(), 
    //                 result.getData().getComputeTime());
    //         }
            
    //         return result;
            
    //     } catch (Exception e) {
    //         log.error("求解失败", e);
    //         AlgorithmResponse errorResponse = new AlgorithmResponse();
    //         errorResponse.setSuccess(false);
    //         errorResponse.setError("算法服务调用失败: " + e.getMessage());
    //         return errorResponse;
    //     }
    // }
    
    // private AlgorithmRequest buildAlgorithmRequest(
    //     List<Depot> depots, 
    //     List<Customer> customers, 
    //     Map<String, Object> params
    // ) {
    //     AlgorithmRequest request = new AlgorithmRequest();
        
    //     // 转换仓库数据
    //     List<AlgorithmRequest.DepotDTO> depotDTOs = depots.stream()
    //         .map(d -> {
    //             AlgorithmRequest.DepotDTO dto = new AlgorithmRequest.DepotDTO();
    //             dto.setId(d.getId().intValue());
    //             dto.setX(d.getLongitude().doubleValue());
    //             dto.setY(d.getLatitude().doubleValue());
    //             dto.setVehicles(d.getVehicleCount());
    //             dto.setCapacity(d.getVehicleCapacity());
    //             dto.setMaxDistance(d.getVehicleMaxDistance());
    //             return dto;
    //         })
    //         .collect(Collectors.toList());
        
    //     // 转换客户数据
    //     List<AlgorithmRequest.CustomerDTO> customerDTOs = customers.stream()
    //         .map(c -> {
    //             AlgorithmRequest.CustomerDTO dto = new AlgorithmRequest.CustomerDTO();
    //             dto.setId(c.getId().intValue());
    //             dto.setX(c.getLongitude().doubleValue());
    //             dto.setY(c.getLatitude().doubleValue());
    //             dto.setDemand(c.getDemand());
    //             return dto;
    //         })
    //         .collect(Collectors.toList());
        
    //     request.setDepots(depotDTOs);
    //     request.setCustomers(customerDTOs);
    //     request.setParams(params);
        
    //     return request;
    // }
    
    // private void saveSolution(Long scenarioId, AlgorithmResponse response) {
    //     try {
    //         Solution solution = new Solution();
    //         solution.setScenarioId(scenarioId);
    //         solution.setAlgorithm(response.getData().getAlgorithm());
    //         solution.setRoutes(objectMapper.writeValueAsString(response.getData().getRoutes()));
    //         solution.setTotalCost(BigDecimal.valueOf(response.getData().getTotalCost()));
    //         solution.setComputeTime(BigDecimal.valueOf(response.getData().getComputeTime()));
            
    //         solutionMapper.insert(solution);
    //         log.info("解决方案已保存，ID: {}", solution.getId());
    //     } catch (Exception e) {
    //         log.error("保存解决方案失败", e);
    //     }
    // }
    
    /**
     * 调用Python算法服务进行重规划
     */
    public Map<String, Object> replan(Map<String, Object> request) {
        log.info("开始重规划，参数: {}", request);
        
        try {
            // 调用Python服务的 /api/replan 端点
            String url = algorithmServiceUrl + "/api/replan";
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            
            HttpEntity<Map<String, Object>> httpRequest = new HttpEntity<>(request, headers);
            
            ResponseEntity<Map> response = restTemplate.postForEntity(
                url, httpRequest, Map.class
            );
            
            Map<String, Object> result = response.getBody();
            
            if (result != null && Boolean.TRUE.equals(result.get("success"))) {
                log.info("重规划完成");
                return (Map<String, Object>) result.get("data");
            } else {
                String error = result != null ? (String) result.get("error") : "未知错误";
                throw new RuntimeException("重规划失败: " + error);
            }
            
        } catch (Exception e) {
            log.error("重规划调用失败", e);
            throw new RuntimeException("重规划服务调用失败: " + e.getMessage(), e);
        }
    }
}
