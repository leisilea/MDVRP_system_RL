package com.gz.gd.backend.controller;

import com.gz.gd.backend.common.Result;
import com.gz.gd.backend.entity.Depot;
import com.gz.gd.backend.service.DepotService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/depot")
@CrossOrigin(origins = "*")  // 允许跨域
public class DepotController {
    
    @Autowired
    private DepotService depotService;
    
    /**
     * 创建仓库
     * POST /api/depot
     */
    @PostMapping
    public Result<Depot> createDepot(@RequestBody Depot depot) {
        log.info("接收到创建仓库请求: {}", depot.getName());
        try {
            boolean result = depotService.createDepot(depot);
            if (result) {
                // 重新查询以获取完整数据
                Depot createdDepot = depotService.getById(depot.getId());
                return Result.success(createdDepot);
            } else {
                return Result.error("创建仓库失败");
            }
        } catch (Exception e) {
            log.error("创建仓库异常", e);
            return Result.error("创建仓库异常: " + e.getMessage());
        }
    }

    /**
     * 获取仓库详情
     * GET /api/depot/{id}
     */
    @GetMapping("/{id}")
    public Result<Depot> getById(@PathVariable Long id) {
        log.info("查询仓库 ID: {}", id);
        try {
            Depot depot = depotService.getById(id);
            if (depot != null) {
                return Result.success(depot);
            } else {
                return Result.error(404, "仓库不存在");
            }
        } catch (Exception e) {
            log.error("查询仓库异常", e);
            return Result.error("查询仓库异常: " + e.getMessage());
        }
    }

    /**
     * 获取场景的所有仓库
     * GET /api/depot/list/{scenarioId}
     */
    @GetMapping("/list/{scenarioId}")
    public Result<List<Depot>> listByScenarioId(@PathVariable Long scenarioId) {
        log.info("查询场景 {} 的所有仓库", scenarioId);
        try {
            List<Depot> depots = depotService.listByScenarioId(scenarioId);
            return Result.success(depots);
        } catch (Exception e) {
            log.error("查询仓库列表异常", e);
            return Result.error("查询仓库列表异常: " + e.getMessage());
        }
    }

    /**
     * 更新仓库
     * PUT /api/depot/{id}
     */
    @PutMapping("/{id}")
    public Result<Void> updateDepot(@PathVariable Long id, @RequestBody Depot depot) {
        log.info("更新仓库 ID: {}", id);
        try {
            depot.setId(id);
            int result = depotService.updateDepot(depot);
            if (result > 0) {
                return Result.success();
            } else {
                return Result.error("更新仓库失败");
            }
        } catch (Exception e) {
            log.error("更新仓库异常", e);
            return Result.error("更新仓库异常: " + e.getMessage());
        }
    }

    /**
     * 删除仓库
     * DELETE /api/depot/{id}
     */
    @DeleteMapping("/{id}")
    public Result<Void> deleteById(@PathVariable Long id) {
        log.info("删除仓库 ID: {}", id);
        try {
            boolean result = depotService.deleteById(id);
            if (result) {
                return Result.success();
            } else {
                return Result.error("删除仓库失败");
            }
        } catch (Exception e) {
            log.error("删除仓库异常", e);
            return Result.error("删除仓库异常: " + e.getMessage());
        }
    }

    /**
     * 批量创建仓库
     * POST /api/depot/batch
     */
    @PostMapping("/batch")
    public Result<List<Depot>> batchCreateDepot(@RequestBody List<Depot> depots) {
        log.info("批量创建 {} 个仓库", depots.size());
        try {
            depotService.batchCreate(depots);
            return Result.success(depots);
        } catch (Exception e) {
            log.error("批量创建仓库异常", e);
            return Result.error("批量创建仓库异常: " + e.getMessage());
        }
    }
}
