package com.gz.gd.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.gz.gd.backend.entity.AlgorithmTask;
import com.gz.gd.backend.event.TaskCreatedEvent;
import com.gz.gd.backend.mapper.AlgorithmTaskMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 算法任务服务层
 * 提供任务的增删改查和业务逻辑
 */
@Slf4j
@Service
public class AlgorithmTaskService {
    
    @Autowired
    private AlgorithmTaskMapper algorithmTaskMapper;
    
    @Autowired
    private AsyncAlgorithmService asyncAlgorithmService;
    
    @Autowired
    private ObjectMapper objectMapper;
    
    @Autowired
    private ApplicationEventPublisher eventPublisher;
    
    /**
     * 创建任务
     */
    @Transactional
    public AlgorithmTask createTask(Long scenarioId, String algorithm, Map<String, Object> params) {
        try {
            AlgorithmTask task = new AlgorithmTask();
            task.setScenarioId(scenarioId);
            task.setAlgorithm(algorithm);
            task.setStatus("PENDING");
            task.setParams(objectMapper.writeValueAsString(params));
            task.setProgress(0);
            task.setCreateTime(LocalDateTime.now());
            
            algorithmTaskMapper.insert(task);
            log.info("创建任务成功 - 任务ID: {}, 场景ID: {}, 算法: {}", task.getId(), scenarioId, algorithm);
            
            return task;
        } catch (Exception e) {
            log.error("创建任务失败", e);
            throw new RuntimeException("创建任务失败: " + e.getMessage());
        }
    }
    
    /**
     * 提交任务并异步执行
     */
    @Transactional
    public AlgorithmTask submitTask(Long scenarioId, Map<String, Object> params) {
        String algorithm = params.getOrDefault("algorithm", "genetic").toString();
        AlgorithmTask task = createTask(scenarioId, algorithm, params);
        
        // 发布任务创建事件，在事务提交后执行异步任务
        // 这样可以确保异步方法执行时，任务已经真正保存到数据库
        eventPublisher.publishEvent(new TaskCreatedEvent(task.getId()));
        log.info("提交任务成功 - 任务ID: {}", task.getId());
        
        return task;
    }
    
    /**
     * 根据ID查询任务
     */
    public AlgorithmTask getById(Long id) {
        log.info("查询任务 - ID: {}", id);
        AlgorithmTask task = algorithmTaskMapper.selectById(id);
        if (task == null) {
            log.warn("任务不存在 - ID: {}", id);
        }
        return task;
    }
    
    /**
     * 查询所有任务
     */
    public List<AlgorithmTask> listAll() {
        log.info("查询所有任务");
        QueryWrapper<AlgorithmTask> queryWrapper = new QueryWrapper<>();
        queryWrapper.orderByDesc("create_time");
        return algorithmTaskMapper.selectList(queryWrapper);
    }
    
    /**
     * 按场景ID查询任务
     */
    public List<AlgorithmTask> listByScenarioId(Long scenarioId) {
        log.info("查询场景任务 - 场景ID: {}", scenarioId);
        QueryWrapper<AlgorithmTask> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("scenario_id", scenarioId)
                    .orderByDesc("create_time");
        return algorithmTaskMapper.selectList(queryWrapper);
    }
    
    /**
     * 按状态查询任务
     */
    public List<AlgorithmTask> listByStatus(String status) {
        log.info("查询状态任务 - 状态: {}", status);
        QueryWrapper<AlgorithmTask> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("status", status)
                    .orderByDesc("create_time");
        return algorithmTaskMapper.selectList(queryWrapper);
    }
    
    /**
     * 按算法查询任务
     */
    public List<AlgorithmTask> listByAlgorithm(String algorithm) {
        log.info("查询算法任务 - 算法: {}", algorithm);
        QueryWrapper<AlgorithmTask> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("algorithm", algorithm)
                    .orderByDesc("create_time");
        return algorithmTaskMapper.selectList(queryWrapper);
    }
    
    /**
     * 按场景和算法查询任务
     */
    public List<AlgorithmTask> listByScenarioAndAlgorithm(Long scenarioId, String algorithm) {
        log.info("查询场景算法任务 - 场景ID: {}, 算法: {}", scenarioId, algorithm);
        QueryWrapper<AlgorithmTask> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("scenario_id", scenarioId)
                    .eq("algorithm", algorithm)
                    .orderByDesc("create_time");
        return algorithmTaskMapper.selectList(queryWrapper);
    }
    
    /**
     * 更新任务状态
     */
    @Transactional
    public boolean updateStatus(Long id, String status) {
        log.info("更新任务状态 - ID: {}, 状态: {}", id, status);
        AlgorithmTask task = algorithmTaskMapper.selectById(id);
        if (task == null) {
            log.warn("任务不存在 - ID: {}", id);
            return false;
        }
        
        task.setStatus(status);
        int rows = algorithmTaskMapper.updateById(task);
        return rows > 0;
    }
    
    /**
     * 更新任务进度
     */
    @Transactional
    public boolean updateProgress(Long id, Integer progress) {
        log.info("更新任务进度 - ID: {}, 进度: {}%", id, progress);
        AlgorithmTask task = algorithmTaskMapper.selectById(id);
        if (task == null) {
            log.warn("任务不存在 - ID: {}", id);
            return false;
        }
        
        task.setProgress(progress);
        int rows = algorithmTaskMapper.updateById(task);
        return rows > 0;
    }
    
    /**
     * 删除任务
     * 只能删除已完成、失败或待处理的任务
     * 不能删除正在运行的任务
     */
    @Transactional
    public boolean deleteById(Long id) {
        log.info("删除任务 - ID: {}", id);
        AlgorithmTask task = algorithmTaskMapper.selectById(id);
        
        if (task == null) {
            log.warn("任务不存在 - ID: {}", id);
            return false;
        }
        
        // 只保护正在运行的任务
        if ("RUNNING".equals(task.getStatus())) {
            log.warn("无法删除运行中的任务 - ID: {}", id);
            throw new RuntimeException("无法删除运行中的任务，请先取消任务");
        }
        
        int rows = algorithmTaskMapper.deleteById(id);
        if (rows > 0) {
            log.info("删除任务成功 - ID: {}", id);
            return true;
        }
        return false;
    }
    
    /**
     * 批量删除任务
     */
    @Transactional
    public Map<String, Object> deleteBatch(List<Long> ids) {
        log.info("批量删除任务 - 数量: {}", ids.size());
        
        int successCount = 0;
        int failCount = 0;
        StringBuilder errors = new StringBuilder();
        
        for (Long id : ids) {
            try {
                boolean result = deleteById(id);
                if (result) {
                    successCount++;
                } else {
                    failCount++;
                }
            } catch (Exception e) {
                failCount++;
                errors.append("任务").append(id).append(": ").append(e.getMessage()).append("; ");
            }
        }
        
        Map<String, Object> result = new HashMap<>();
        result.put("total", ids.size());
        result.put("success", successCount);
        result.put("fail", failCount);
        if (errors.length() > 0) {
            result.put("errors", errors.toString());
        }
        
        log.info("批量删除任务完成 - 成功: {}, 失败: {}", successCount, failCount);
        return result;
    }
    
    /**
     * 取消任务
     */
    @Transactional
    public boolean cancelTask(Long id) {
        log.info("取消任务 - ID: {}", id);
        AlgorithmTask task = algorithmTaskMapper.selectById(id);
        
        if (task == null) {
            log.warn("任务不存在 - ID: {}", id);
            return false;
        }
        
        if ("COMPLETED".equals(task.getStatus()) || "FAILED".equals(task.getStatus())) {
            log.warn("任务已结束，无法取消 - ID: {}", id);
            throw new RuntimeException("任务已结束，无法取消");
        }
        
        task.setStatus("FAILED");
        task.setError("任务已被用户取消");
        task.setEndTime(LocalDateTime.now());
        
        int rows = algorithmTaskMapper.updateById(task);
        if (rows > 0) {
            log.info("取消任务成功 - ID: {}", id);
            return true;
        }
        return false;
    }
    
    /**
     * 重试任务
     * 创建一个新任务，使用相同的参数
     */
    @Transactional
    public AlgorithmTask retryTask(Long id) {
        log.info("重试任务 - 原任务ID: {}", id);
        AlgorithmTask oldTask = algorithmTaskMapper.selectById(id);
        
        if (oldTask == null) {
            log.warn("任务不存在 - ID: {}", id);
            throw new RuntimeException("任务不存在");
        }
        
        // 创建新任务
        AlgorithmTask newTask = new AlgorithmTask();
        newTask.setScenarioId(oldTask.getScenarioId());
        newTask.setAlgorithm(oldTask.getAlgorithm());
        newTask.setStatus("PENDING");
        newTask.setParams(oldTask.getParams());
        newTask.setProgress(0);
        newTask.setCreateTime(LocalDateTime.now());
        
        algorithmTaskMapper.insert(newTask);
        log.info("重试任务成功 - 原任务ID: {}, 新任务ID: {}", id, newTask.getId());
        
        // 发布任务创建事件，在事务提交后执行异步任务
        eventPublisher.publishEvent(new TaskCreatedEvent(newTask.getId()));
        
        return newTask;
    }
    
    /**
     * 按场景删除所有任务
     */
    @Transactional
    public Map<String, Object> deleteByScenarioId(Long scenarioId) {
        log.info("删除场景所有任务 - 场景ID: {}", scenarioId);
        
        List<AlgorithmTask> tasks = listByScenarioId(scenarioId);
        int successCount = 0;
        int failCount = 0;
        
        for (AlgorithmTask task : tasks) {
            // 只跳过正在运行的任务
            if ("RUNNING".equals(task.getStatus())) {
                failCount++;
                continue;
            }
            
            try {
                int rows = algorithmTaskMapper.deleteById(task.getId());
                if (rows > 0) {
                    successCount++;
                } else {
                    failCount++;
                }
            } catch (Exception e) {
                failCount++;
                log.error("删除任务失败 - ID: {}", task.getId(), e);
            }
        }
        
        Map<String, Object> result = new HashMap<>();
        result.put("total", tasks.size());
        result.put("success", successCount);
        result.put("fail", failCount);
        
        log.info("删除场景任务完成 - 场景ID: {}, 成功: {}, 失败: {}", scenarioId, successCount, failCount);
        return result;
    }
    
    /**
     * 获取任务统计信息
     */
    public Map<String, Object> getStatistics() {
        log.info("获取任务统计信息");
        
        List<AlgorithmTask> allTasks = listAll();
        
        long totalCount = allTasks.size();
        long pendingCount = allTasks.stream().filter(t -> "PENDING".equals(t.getStatus())).count();
        long runningCount = allTasks.stream().filter(t -> "RUNNING".equals(t.getStatus())).count();
        long completedCount = allTasks.stream().filter(t -> "COMPLETED".equals(t.getStatus())).count();
        long failedCount = allTasks.stream().filter(t -> "FAILED".equals(t.getStatus())).count();
        
        Map<String, Object> statistics = new HashMap<>();
        statistics.put("total", totalCount);
        statistics.put("pending", pendingCount);
        statistics.put("running", runningCount);
        statistics.put("completed", completedCount);
        statistics.put("failed", failedCount);
        
        log.info("任务统计 - 总数: {}, 待处理: {}, 运行中: {}, 已完成: {}, 失败: {}", 
            totalCount, pendingCount, runningCount, completedCount, failedCount);
        
        return statistics;
    }
    
    /**
     * 按场景获取统计信息
     */
    public Map<String, Object> getStatisticsByScenario(Long scenarioId) {
        log.info("获取场景任务统计信息 - 场景ID: {}", scenarioId);
        
        List<AlgorithmTask> tasks = listByScenarioId(scenarioId);
        
        long totalCount = tasks.size();
        long pendingCount = tasks.stream().filter(t -> "PENDING".equals(t.getStatus())).count();
        long runningCount = tasks.stream().filter(t -> "RUNNING".equals(t.getStatus())).count();
        long completedCount = tasks.stream().filter(t -> "COMPLETED".equals(t.getStatus())).count();
        long failedCount = tasks.stream().filter(t -> "FAILED".equals(t.getStatus())).count();
        
        Map<String, Object> statistics = new HashMap<>();
        statistics.put("scenarioId", scenarioId);
        statistics.put("total", totalCount);
        statistics.put("pending", pendingCount);
        statistics.put("running", runningCount);
        statistics.put("completed", completedCount);
        statistics.put("failed", failedCount);
        
        return statistics;
    }
    
    /**
     * 统计任务数量
     */
    public Long countByScenarioId(Long scenarioId) {
        QueryWrapper<AlgorithmTask> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("scenario_id", scenarioId);
        return algorithmTaskMapper.selectCount(queryWrapper);
    }
    
    /**
     * 统计指定状态的任务数量
     */
    public Long countByStatus(String status) {
        QueryWrapper<AlgorithmTask> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("status", status);
        return algorithmTaskMapper.selectCount(queryWrapper);
    }
}
