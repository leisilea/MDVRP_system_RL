package com.gz.gd.backend.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.gz.gd.backend.dto.AlgorithmRequest;
import com.gz.gd.backend.dto.AlgorithmResponse;
import com.gz.gd.backend.entity.AlgorithmTask;
import com.gz.gd.backend.entity.Customer;
import com.gz.gd.backend.entity.Depot;
import com.gz.gd.backend.entity.Solution;
import com.gz.gd.backend.mapper.AlgorithmTaskMapper;
import com.gz.gd.backend.mapper.CustomerMapper;
import com.gz.gd.backend.mapper.DepotMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Slf4j
@Service
public class AsyncAlgorithmService {
    
    @Autowired
    private RestTemplate restTemplate;
    
    @Autowired
    private DepotMapper depotMapper;
    
    @Autowired
    private CustomerMapper customerMapper;
    
    @Autowired
    private AlgorithmTaskMapper algorithmTaskMapper;
    
    @Autowired
    private SolutionService solutionService;
    
    @Autowired
    private ObjectMapper objectMapper;
    
    @Value("${algorithm.service.url}")
    private String algorithmServiceUrl;
    
    /**
     * 异步执行算法任务
     */
    @Async("algorithmTaskExecutor")
    public void executeAlgorithmTask(Long taskId) {
        log.info("开始执行异步算法任务，任务ID: {}", taskId);
        
        AlgorithmTask task = algorithmTaskMapper.selectById(taskId);
        if (task == null) {
            log.error("任务不存在: {}", taskId);
            return;
        }
        
        try {
            // 更新任务状态为运行中
            task.setStatus("RUNNING");
            task.setStartTime(LocalDateTime.now());
            task.setProgress(0);
            algorithmTaskMapper.updateById(task);
            
            // 从数据库读取场景数据
            List<Depot> depots = depotMapper.selectByMap(
                Map.of("scenario_id", task.getScenarioId())
            );
            List<Customer> customers = customerMapper.selectByMap(
                Map.of("scenario_id", task.getScenarioId())
            );
            
            log.info("场景数据 - 仓库数: {}, 客户数: {}", depots.size(), customers.size());
            
            // 解析参数
            @SuppressWarnings("unchecked")
            Map<String, Object> params = objectMapper.readValue(task.getParams(), Map.class);
            
            // 构建请求
            AlgorithmRequest request = buildAlgorithmRequest(depots, customers, params);
            
            // 更新进度
            task.setProgress(10);
            algorithmTaskMapper.updateById(task);
            
            // 调用Python服务
            String url = algorithmServiceUrl + "/api/solve";
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            
            HttpEntity<AlgorithmRequest> httpRequest = new HttpEntity<>(request, headers);
            
            log.info("调用算法服务: {}", url);
            ResponseEntity<AlgorithmResponse> response = restTemplate.postForEntity(
                url, httpRequest, AlgorithmResponse.class
            );
            
            AlgorithmResponse result = response.getBody();
            
            if (result != null && result.getSuccess()) {
                // 任务成功
                task.setStatus("COMPLETED");
                task.setResult(objectMapper.writeValueAsString(result.getData()));
                task.setTotalCost(BigDecimal.valueOf(result.getData().getTotalCost()));
                task.setComputeTime(BigDecimal.valueOf(result.getData().getComputeTime()));
                task.setProgress(100);
                task.setEndTime(LocalDateTime.now());
                
                log.info("任务完成 - 任务ID: {}, 总成本: {}, 耗时: {}s", 
                    taskId, result.getData().getTotalCost(), result.getData().getComputeTime());
                
                // 【修复Bug】保存solution到solution表，供算法比较模块使用
                try {
                    String routesJson = objectMapper.writeValueAsString(result.getData().getRoutes());
                    Solution savedSolution = solutionService.saveSolution(
                        task.getScenarioId(),
                        task.getAlgorithm(),
                        routesJson,
                        task.getTotalCost(),
                        task.getComputeTime()
                    );
                    log.info("Solution已保存到数据库 - Solution ID: {}, 场景ID: {}, 算法: {}", 
                        savedSolution.getId(), task.getScenarioId(), task.getAlgorithm());
                } catch (Exception e) {
                    log.error("保存Solution到数据库失败 - 任务ID: {}", taskId, e);
                    // 不影响任务状态，只记录错误
                }
            } else {
                // 任务失败
                String errorMsg = result != null ? result.getError() : "算法求解失败";
                task.setStatus("FAILED");
                task.setError(errorMsg);
                task.setEndTime(LocalDateTime.now());
                
                log.error("任务失败 - 任务ID: {}, 错误: {}", taskId, errorMsg);
            }
            
            algorithmTaskMapper.updateById(task);
            
        } catch (Exception e) {
            log.error("任务执行异常 - 任务ID: {}", taskId, e);
            
            // 更新任务状态为失败
            task.setStatus("FAILED");
            task.setError("算法执行异常: " + e.getMessage());
            task.setEndTime(LocalDateTime.now());
            algorithmTaskMapper.updateById(task);
        }
    }
    
    private AlgorithmRequest buildAlgorithmRequest(
        List<Depot> depots, 
        List<Customer> customers, 
        Map<String, Object> params
    ) {
        AlgorithmRequest request = new AlgorithmRequest();
        
        // 转换仓库数据
        List<AlgorithmRequest.DepotDTO> depotDTOs = depots.stream()
            .map(d -> {
                AlgorithmRequest.DepotDTO dto = new AlgorithmRequest.DepotDTO();
                dto.setId(d.getId().intValue());
                dto.setX(d.getLongitude().doubleValue());
                dto.setY(d.getLatitude().doubleValue());
                dto.setVehicles(d.getVehicleCount());
                dto.setCapacity(d.getVehicleCapacity());
                dto.setMaxDistance(d.getVehicleMaxDistance());
                return dto;
            })
            .collect(Collectors.toList());
        
        // 转换客户数据
        List<AlgorithmRequest.CustomerDTO> customerDTOs = customers.stream()
            .map(c -> {
                AlgorithmRequest.CustomerDTO dto = new AlgorithmRequest.CustomerDTO();
                dto.setId(c.getId().intValue());
                dto.setX(c.getLongitude().doubleValue());
                dto.setY(c.getLatitude().doubleValue());
                dto.setDemand(c.getDemand());
                return dto;
            })
            .collect(Collectors.toList());
        
        request.setDepots(depotDTOs);
        request.setCustomers(customerDTOs);
        request.setParams(params);
        
        return request;
    }
}
