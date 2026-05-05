package com.gz.gd.backend.controller;

import com.gz.gd.backend.common.Result;
import com.gz.gd.backend.entity.Scenario;
import com.gz.gd.backend.service.ScenarioService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/scenario")
@CrossOrigin(origins = "*")  // 允许跨域
public class ScenarioController {
    
    @Autowired
    private ScenarioService scenarioService;
    
    /**
     * 创建场景
     * POST /api/scenario
     */
    @PostMapping
    public Result<Scenario> createScenario(@RequestBody Scenario scenario) {
        log.info("接收到创建场景请求: {}", scenario.getName());
        try {
            int result = scenarioService.createScenario(scenario);
            if (result > 0) {
                // 插入成功后，scenario 对象的 id 已经被 MyBatis-Plus 自动填充
                // 重新查询以获取完整数据（包括数据库自动生成的字段）
                Scenario createdScenario = scenarioService.getById(scenario.getId());
                return Result.success(createdScenario);
            } else {
                return Result.error("创建场景失败");
            }
        } catch (Exception e) {
            log.error("创建场景异常", e);
            return Result.error("创建场景异常: " + e.getMessage());
        }
    }
    
    /**
     * 获取场景详情
     * GET /api/scenario/{id}
     */
    @GetMapping("/{id}")
    public Result<Scenario> getById(@PathVariable Long id) {
        log.info("查询场景 ID: {}", id);
        try {
            Scenario scenario = scenarioService.getById(id);
            if (scenario != null) {
                return Result.success(scenario);
            } else {
                return Result.error(404, "场景不存在");
            }
        } catch (Exception e) {
            log.error("查询场景异常", e);
            return Result.error("查询场景异常: " + e.getMessage());
        }
    }

    /**
     * 获取所有场景
     * GET /api/scenario/list
     */
    @GetMapping("/list")
    public Result<List<Scenario>> listAll() {
        log.info("查询所有场景");
        try {
            List<Scenario> scenarios = scenarioService.listAll();
            return Result.success(scenarios);
        } catch (Exception e) {
            log.error("查询场景列表异常", e);
            return Result.error("查询场景列表异常: " + e.getMessage());
        }
    }
    
    /**
     * 更新场景
     * PUT /api/scenario/{id}
     */
    @PutMapping("/{id}")
    public Result<Void> updateScenario(@PathVariable Long id, @RequestBody Scenario scenario) {
        log.info("更新场景 ID: {}", id);
        try {
            scenario.setId(id);
            int result = scenarioService.updateById(scenario);
            if (result > 0) {
                return Result.success();
            } else {
                return Result.error("更新场景失败");
            }
        } catch (Exception e) {
            log.error("更新场景异常", e);
            return Result.error("更新场景异常: " + e.getMessage());
        }
    }
    
    /**
     * 删除场景（级联删除）
     * DELETE /api/scenario/{id}
     */
    @DeleteMapping("/{id}")
    public Result<Void> deleteById(@PathVariable Long id) {
        log.info("删除场景 ID: {}", id);
        try {
            boolean result = scenarioService.deleteById(id);
            if (result) {
                return Result.success();
            } else {
                return Result.error("删除场景失败");
            }
        } catch (Exception e) {
            log.error("删除场景异常", e);
            return Result.error("删除场景异常: " + e.getMessage());
        }
    }

    /**
     * 获取场景统计信息
     * GET /api/scenario/{id}/statistics
     */
    @GetMapping("/{id}/statistics")
    public Result<Map<String, Object>> getStatistics(@PathVariable Long id) {
        log.info("获取场景 {} 的统计信息", id);
        try {
            Map<String, Object> statistics = scenarioService.getScenarioStatistics(id);
            if (statistics != null) {
                return Result.success(statistics);
            } else {
                return Result.error(404, "场景不存在");
            }
        } catch (Exception e) {
            log.error("获取统计信息异常", e);
            return Result.error("获取统计信息异常: " + e.getMessage());
        }
    }
    
    /**
     * 验证场景数据完整性
     * GET /api/scenario/{id}/validate
     */
    @GetMapping("/{id}/validate")
    public Result<Boolean> validateScenario(@PathVariable Long id) {
        log.info("验证场景 {} 的数据完整性", id);
        try {
            boolean isValid = scenarioService.validateScenarioData(id);
            return Result.success(isValid);
        } catch (Exception e) {
            log.error("验证场景数据异常", e);
            return Result.error("验证场景数据异常: " + e.getMessage());
        }
    }
}
