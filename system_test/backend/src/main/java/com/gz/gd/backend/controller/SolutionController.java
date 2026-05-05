package com.gz.gd.backend.controller;

import com.gz.gd.backend.common.Result;
import com.gz.gd.backend.entity.Solution;
import com.gz.gd.backend.service.SolutionService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/solution")
@CrossOrigin(origins = "*")  // 允许跨域
public class SolutionController {
    
    @Autowired
    private SolutionService solutionService;
    
    /**
     * 获取解决方案详情
     * GET /api/solution/{id}
     */
    @GetMapping("/{id}")
    public Result<Solution> getById(@PathVariable Long id) {
        log.info("查询解决方案 ID: {}", id);
        try {
            Solution solution = solutionService.getById(id);
            if (solution != null) {
                return Result.success(solution);
            } else {
                return Result.error(404, "解决方案不存在");
            }
        } catch (Exception e) {
            log.error("查询解决方案异常", e);
            return Result.error("查询解决方案异常: " + e.getMessage());
        }
    }
    
    /**
     * 获取所有解决方案
     * GET /api/solution/all
     */
    @GetMapping("/all")
    public Result<List<Solution>> listAll() {
        log.info("查询所有解决方案");
        try {
            List<Solution> solutions = solutionService.listAll();
            return Result.success(solutions);
        } catch (Exception e) {
            log.error("查询所有解决方案异常", e);
            return Result.error("查询所有解决方案异常: " + e.getMessage());
        }
    }
    
    /**
     * 按算法查询解决方案（不限场景）
     * GET /api/solution/algorithm/{algorithm}
     */
    @GetMapping("/algorithm/{algorithm}")
    public Result<List<Solution>> listByAlgorithm(@PathVariable String algorithm) {
        log.info("查询算法 {} 的所有解决方案", algorithm);
        try {
            List<Solution> solutions = solutionService.listByAlgorithm(algorithm);
            return Result.success(solutions);
        } catch (Exception e) {
            log.error("查询算法解决方案异常", e);
            return Result.error("查询算法解决方案异常: " + e.getMessage());
        }
    }
    
    /**
     * 按场景和算法组合查询解决方案
     * GET /api/solution/scenario/{scenarioId}/algorithm/{algorithm}
     */
    @GetMapping("/scenario/{scenarioId}/algorithm/{algorithm}")
    public Result<List<Solution>> listByScenarioAndAlgorithm(
            @PathVariable Long scenarioId, 
            @PathVariable String algorithm) {
        log.info("查询场景 {} 算法 {} 的解决方案", scenarioId, algorithm);
        try {
            List<Solution> solutions = solutionService.listByScenarioAndAlgorithm(scenarioId, algorithm);
            return Result.success(solutions);
        } catch (Exception e) {
            log.error("查询场景算法解决方案异常", e);
            return Result.error("查询场景算法解决方案异常: " + e.getMessage());
        }
    }
    
    /**
     * 获取场景的所有解决方案
     * GET /api/solution/list/{scenarioId}
     */
    @GetMapping("/list/{scenarioId}")
    public Result<List<Solution>> listByScenarioId(@PathVariable Long scenarioId) {
        log.info("查询场景 {} 的所有解决方案", scenarioId);
        try {
            List<Solution> solutions = solutionService.listByScenarioId(scenarioId);
            return Result.success(solutions);
        } catch (Exception e) {
            log.error("查询解决方案列表异常", e);
            return Result.error("查询解决方案列表异常: " + e.getMessage());
        }
    }
    
    /**
     * 获取最优解决方案
     * GET /api/solution/best/{scenarioId}
     */
    @GetMapping("/best/{scenarioId}")
    public Result<Solution> getBestSolution(@PathVariable Long scenarioId) {
        log.info("查询场景 {} 的最优解决方案", scenarioId);
        try {
            Solution solution = solutionService.getBestSolution(scenarioId);
            if (solution != null) {
                return Result.success(solution);
            } else {
                return Result.error(404, "该场景暂无解决方案");
            }
        } catch (Exception e) {
            log.error("查询最优解决方案异常", e);
            return Result.error("查询最优解决方案异常: " + e.getMessage());
        }
    }
    
    /**
     * 删除解决方案
     * DELETE /api/solution/{id}
     */
    @DeleteMapping("/{id}")
    public Result<Void> deleteById(@PathVariable Long id) {
        log.info("删除解决方案 ID: {}", id);
        try {
            boolean result = solutionService.deleteById(id);
            if (result) {
                return Result.success();
            } else {
                return Result.error("删除解决方案失败");
            }
        } catch (Exception e) {
            log.error("删除解决方案异常", e);
            return Result.error("删除解决方案异常: " + e.getMessage());
        }
    }
    
    /**
     * 对比多个解决方案
     * POST /api/solution/compare
     * 请求体示例: [1, 2, 3]
     */
    @PostMapping("/compare")
    public Result<Map<String, Object>> compareSolutions(@RequestBody List<Long> solutionIds) {
        log.info("对比解决方案: {}", solutionIds);
        try {
            Map<String, Object> comparison = solutionService.compareSolutions(solutionIds);
            return Result.success(comparison);
        } catch (Exception e) {
            log.error("对比解决方案异常", e);
            return Result.error("对比解决方案异常: " + e.getMessage());
        }
    }
}       