package com.gz.gd.backend.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.gz.gd.backend.common.Result;
import com.gz.gd.backend.dto.AlgorithmResponse;
import com.gz.gd.backend.entity.AlgorithmTask;
import com.gz.gd.backend.service.AlgorithmService;
import com.gz.gd.backend.service.AlgorithmTaskService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

// 自动生成日志 + RESTAPI + 跨域
@Slf4j
@RestController
@CrossOrigin(origins = "*")
public class AlgorithmController {
    
    @Autowired
    private AlgorithmService algorithmService;
    
    @Autowired
    private AlgorithmTaskService algorithmTaskService;
    
    @Autowired
    private ObjectMapper objectMapper;
    
    /**
     * 调用算法求解（老同步方式）
     * POST /api/algorithm/solve
     */
    // @PostMapping("/api/algorithm/solve")
    // public Result<AlgorithmResponse> solve(@RequestBody Map<String, Object> request) {
    //     log.info("接收到算法求解请求: {}", request);
        
    //     try {
    //         Long scenarioId = Long.valueOf(request.get("scenarioId").toString());
    //         @SuppressWarnings("unchecked")
    //         Map<String, Object> params = (Map<String, Object>) request.get("params");
            
    //         AlgorithmResponse response = algorithmService.solve(scenarioId, params);
            
    //         if (response != null && response.getSuccess()) {
    //             return Result.success(response);
    //         } else {
    //             String errorMsg = response != null ? response.getError() : "算法求解失败";
    //             return Result.error(errorMsg);
    //         }
    //     } catch (Exception e) {
    //         log.error("算法求解异常", e);
    //         return Result.error("算法求解异常: " + e.getMessage());
    //     }
    // }
    
    /**
     * 提交异步算法任务
     * POST /api/algorithm/submit
     */
    @PostMapping("/api/algorithm/submit")
    public Result<Map<String, Object>> submitTask(@RequestBody Map<String, Object> request) {
        log.info("接收到算法任务提交请求: {}", request);
        
        try {
            Long scenarioId = Long.valueOf(request.get("scenarioId").toString());
            @SuppressWarnings("unchecked")
            Map<String, Object> params = (Map<String, Object>) request.get("params");
            
            AlgorithmTask task = algorithmTaskService.submitTask(scenarioId, params);
            
            Map<String, Object> result = new HashMap<>();
            result.put("taskId", task.getId());
            result.put("status", task.getStatus());
            result.put("message", "任务已提交，正在处理中");
            
            return Result.success(result);
        } catch (Exception e) {
            log.error("提交任务失败", e);
            return Result.error("提交任务失败: " + e.getMessage());
        }
    }
    
    /**
     * 查询任务状态
     * GET /api/algorithm/task/{taskId}
     */
    @GetMapping("/api/algorithm/task/{taskId}")
    public Result<Map<String, Object>> getTaskStatus(@PathVariable Long taskId) {
        try {
            AlgorithmTask task = algorithmTaskService.getById(taskId);
            
            if (task == null) {
                return Result.error("任务不存在");
            }
            
            Map<String, Object> result = new HashMap<>();
            result.put("taskId", task.getId());
            result.put("scenarioId", task.getScenarioId());
            result.put("algorithm", task.getAlgorithm());
            result.put("status", task.getStatus());
            result.put("progress", task.getProgress());
            result.put("createTime", task.getCreateTime());
            result.put("startTime", task.getStartTime());
            result.put("endTime", task.getEndTime());
            
            if ("COMPLETED".equals(task.getStatus()) && task.getResult() != null) {
                @SuppressWarnings("unchecked")
                Map<String, Object> resultData = objectMapper.readValue(task.getResult(), Map.class);
                result.put("result", resultData);
                result.put("totalCost", task.getTotalCost());
                result.put("computeTime", task.getComputeTime());
            }
            
            if ("FAILED".equals(task.getStatus())) {
                result.put("error", task.getError());
            }
            
            return Result.success(result);
        } catch (Exception e) {
            log.error("查询任务状态失败", e);
            return Result.error("查询任务状态失败: " + e.getMessage());
        }
    }
    
    /**
     * 查询所有任务
     * GET /api/algorithm/tasks
     */
    @GetMapping("/api/algorithm/tasks")
    public Result<List<AlgorithmTask>> getAllTasks() {
        try {
            List<AlgorithmTask> tasks = algorithmTaskService.listAll();
            return Result.success(tasks);
        } catch (Exception e) {
            log.error("查询任务列表失败", e);
            return Result.error("查询任务列表失败: " + e.getMessage());
        }
    }
    
    /**
     * 按场景查询任务
     * GET /api/algorithm/tasks/scenario/{scenarioId}
     */
    @GetMapping("/api/algorithm/tasks/scenario/{scenarioId}")
    public Result<List<AlgorithmTask>> getTasksByScenario(@PathVariable Long scenarioId) {
        try {
            List<AlgorithmTask> tasks = algorithmTaskService.listByScenarioId(scenarioId);
            return Result.success(tasks);
        } catch (Exception e) {
            log.error("查询场景任务列表失败", e);
            return Result.error("查询场景任务列表失败: " + e.getMessage());
        }
    }
    
    /**
     * 按状态查询任务
     * GET /api/algorithm/tasks/status/{status}
     */
    @GetMapping("/api/algorithm/tasks/status/{status}")
    public Result<List<AlgorithmTask>> getTasksByStatus(@PathVariable String status) {
        try {
            List<AlgorithmTask> tasks = algorithmTaskService.listByStatus(status);
            return Result.success(tasks);
        } catch (Exception e) {
            log.error("查询状态任务列表失败", e);
            return Result.error("查询状态任务列表失败: " + e.getMessage());
        }
    }
    
    /**
     * 删除任务
     * DELETE /api/algorithm/task/{taskId}
     */
    @DeleteMapping("/api/algorithm/task/{taskId}")
    public Result<Void> deleteTask(@PathVariable Long taskId) {
        try {
            algorithmTaskService.deleteById(taskId);
            return Result.success();
        } catch (Exception e) {
            log.error("删除任务失败", e);
            return Result.error(e.getMessage());
        }
    }
    
    /**
     * 批量删除任务
     * DELETE /api/algorithm/tasks/batch
     */
    @DeleteMapping("/api/algorithm/tasks/batch")
    public Result<Map<String, Object>> deleteTasks(@RequestBody List<Long> taskIds) {
        try {
            Map<String, Object> result = algorithmTaskService.deleteBatch(taskIds);
            return Result.success(result);
        } catch (Exception e) {
            log.error("批量删除任务失败", e);
            return Result.error("批量删除任务失败: " + e.getMessage());
        }
    }
    
    /**
     * 取消任务
     * POST /api/algorithm/task/{taskId}/cancel
     */
    @PostMapping("/api/algorithm/task/{taskId}/cancel")
    public Result<Void> cancelTask(@PathVariable Long taskId) {
        try {
            algorithmTaskService.cancelTask(taskId);
            return Result.success();
        } catch (Exception e) {
            log.error("取消任务失败", e);
            return Result.error(e.getMessage());
        }
    }
    
    /**
     * 重试任务
     * POST /api/algorithm/task/{taskId}/retry
     */
    @PostMapping("/api/algorithm/task/{taskId}/retry")
    public Result<Map<String, Object>> retryTask(@PathVariable Long taskId) {
        try {
            AlgorithmTask newTask = algorithmTaskService.retryTask(taskId);
            
            Map<String, Object> result = new HashMap<>();
            result.put("oldTaskId", taskId);
            result.put("newTaskId", newTask.getId());
            result.put("status", newTask.getStatus());
            result.put("message", "任务已重新提交");
            
            return Result.success(result);
        } catch (Exception e) {
            log.error("重试任务失败", e);
            return Result.error(e.getMessage());
        }
    }
    
    /**
     * 按场景删除所有任务
     * DELETE /api/algorithm/tasks/scenario/{scenarioId}
     */
    @DeleteMapping("/api/algorithm/tasks/scenario/{scenarioId}")
    public Result<Map<String, Object>> deleteTasksByScenario(@PathVariable Long scenarioId) {
        try {
            Map<String, Object> result = algorithmTaskService.deleteByScenarioId(scenarioId);
            return Result.success(result);
        } catch (Exception e) {
            log.error("删除场景任务失败", e);
            return Result.error("删除场景任务失败: " + e.getMessage());
        }
    }
    
    /**
     * 获取任务统计信息
     * GET /api/algorithm/tasks/statistics
     */
    @GetMapping("/api/algorithm/tasks/statistics")
    public Result<Map<String, Object>> getTaskStatistics() {
        try {
            Map<String, Object> statistics = algorithmTaskService.getStatistics();
            return Result.success(statistics);
        } catch (Exception e) {
            log.error("获取任务统计失败", e);
            return Result.error("获取任务统计失败: " + e.getMessage());
        }
    }
    
    /**
     * 重规划API - 代理到Flask算法服务
     * POST /api/replan
     */
    @PostMapping("/api/replan")
    public Result<Map<String, Object>> replan(@RequestBody Map<String, Object> request) {
        log.info("接收到重规划请求: {}", request);
        
        try {
            Map<String, Object> response = algorithmService.replan(request);
            return Result.success(response);
        } catch (Exception e) {
            log.error("重规划失败", e);
            return Result.error("重规划失败: " + e.getMessage());
        }
    }
}
