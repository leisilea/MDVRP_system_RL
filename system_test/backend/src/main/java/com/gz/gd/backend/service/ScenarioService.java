package com.gz.gd.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.gz.gd.backend.entity.Customer;
import com.gz.gd.backend.entity.Depot;
import com.gz.gd.backend.entity.Scenario;
import com.gz.gd.backend.entity.Solution;
import com.gz.gd.backend.mapper.CustomerMapper;
import com.gz.gd.backend.mapper.DepotMapper;
import com.gz.gd.backend.mapper.ScenarioMapper;
import com.gz.gd.backend.mapper.SolutionMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
public class ScenarioService {
    
    @Autowired
    private ScenarioMapper scenarioMapper;
    
    @Autowired
    private DepotMapper depotMapper;
    
    @Autowired
    private CustomerMapper customerMapper;
    
    @Autowired
    private SolutionMapper solutionMapper;
    
    // ==================== CRUD 方法 ====================
    
    // TODO: 在这里添加核心功能方法
    // 1. 创建场景
    public int createScenario(Scenario scenario){
        log.info("创建新的场景: {}", scenario.getName());
        int result = scenarioMapper.insert(scenario);
        if (result > 0) {
            log.info("场景创建成功, id为: {}", scenario.getId());
        } else {
            log.error("场景创建失败: 场景名为{}", scenario.getName());
        }
        return result; 
    }
    // 2. 根据id查场景
    public Scenario getById(Long id){
        log.info("查询场景{}",id);
        return scenarioMapper.selectById(id);
    }
    // 3. 查询所有场景 listAll()
    public List<Scenario> listAll(){
        log.info("查询所有场景");
        return scenarioMapper.selectList(null);
    }
    // 4. 更新场景
    public int updateById(Scenario scenario){
        log.info("更新场景: {}", scenario.getName());
        return scenarioMapper.updateById(scenario);
    }
    // 5. 删除场景（级联删除）
    @Transactional
    public boolean deleteById(Long id){
        log.info("删除场景 ID: {}", id);
        
        // 1. 删除所有解决方案
        QueryWrapper<Solution> solutionWrapper = new QueryWrapper<>();
        solutionWrapper.eq("scenario_id", id);
        int solutionRows = solutionMapper.delete(solutionWrapper);
        log.info("删除了 {} 个解决方案", solutionRows);
        
        // 2. 删除所有客户
        QueryWrapper<Customer> customerWrapper = new QueryWrapper<>();
        customerWrapper.eq("scenario_id", id);
        int customerRows = customerMapper.delete(customerWrapper);
        log.info("删除了 {} 个客户", customerRows);
        
        // 3. 删除所有仓库
        QueryWrapper<Depot> depotWrapper = new QueryWrapper<>();
        depotWrapper.eq("scenario_id", id);
        int depotRows = depotMapper.delete(depotWrapper);
        log.info("删除了 {} 个仓库", depotRows);
        
        // 4. 删除场景本身
        int rows = scenarioMapper.deleteById(id);
        log.info("场景删除完成");
        
        return rows > 0;
    }
    // 6. 基于id获取场景统计信息
    public Map<String, Object> getScenarioStatistics(Long scenarioId) {
        log.info("获取场景 {} 的统计信息", scenarioId);
        Map<String, Object> statistics = new HashMap<>();

        // 查询场景信息
        Scenario scenario = scenarioMapper.selectById(scenarioId);
        if (scenario == null) {
            log.warn("场景不存在，ID: {}", scenarioId);
            return null;
        }

        // 查询仓库数量
        QueryWrapper<Depot> depotQueryWrapper = new QueryWrapper<>();
        depotQueryWrapper.eq("scenario_id", scenarioId);
        Long depotCount = depotMapper.selectCount(depotQueryWrapper);

        // 查询客户数量
        QueryWrapper<Customer> customerQueryWrapper = new QueryWrapper<>();
        customerQueryWrapper.eq("scenario_id", scenarioId);
        Long customerCount = customerMapper.selectCount(customerQueryWrapper);

        // 查询解决方案数量
        QueryWrapper<Solution> solutionQueryWrapper = new QueryWrapper<>();
        solutionQueryWrapper.eq("scenario_id", scenarioId);
        Long solutionCount = solutionMapper.selectCount(solutionQueryWrapper);
        
        // 查询最优成本和平均成本
        QueryWrapper<Solution> costQueryWrapper = new QueryWrapper<>();
        costQueryWrapper.eq("scenario_id", scenarioId);
        costQueryWrapper.select("total_cost");
        List<Solution> solutions = solutionMapper.selectList(costQueryWrapper);
        
        Double minCost = null;
        Double avgCost = null;
        
        if (!solutions.isEmpty()) {
            double totalCost = 0;
            double min = Double.MAX_VALUE;
            
            for (Solution solution : solutions) {
                if (solution.getTotalCost() != null) {
                    double cost = solution.getTotalCost().doubleValue();
                    totalCost += cost;
                    if (cost < min) {
                        min = cost;
                    }
                }
            }
            
            minCost = min == Double.MAX_VALUE ? null : min;
            avgCost = solutions.size() > 0 ? totalCost / solutions.size() : null;
        }

        // 将统计信息放入map
        statistics.put("scenarioName", scenario.getName());
        statistics.put("depotCount", depotCount);
        statistics.put("customerCount", customerCount);
        statistics.put("solutionCount", solutionCount);
        statistics.put("minCost", minCost);
        statistics.put("avgCost", avgCost);

        log.info("统计信息: {}", statistics);
        return statistics;
    
    }
    // 7. 验证场景数据完整性
    public boolean validateScenarioData(Long scenarioId) {
        // 查询场景
        Scenario scenario = scenarioMapper.selectById(scenarioId);
        if (scenario == null) {
            log.warn("场景不存在: {}", scenarioId);
            return false;
        }

        // 检查仓库数据
        QueryWrapper<Depot> depotQueryWrapper = new QueryWrapper<>();
        depotQueryWrapper.eq("scenario_id", scenarioId);
        List<Depot> depots = depotMapper.selectList(depotQueryWrapper);
        for (Depot depot : depots) {
            if (depot.getName() == null || depot.getName().isEmpty()) {
                log.warn("仓库名称为空: {}", depot.getId());
                return false;
            }
            if (depot.getLatitude() == null || depot.getLongitude() == null) {
                log.warn("仓库坐标为空: {}", depot.getId());
                return false;
            }
        }

        // 检查客户数据
        QueryWrapper<Customer> customerQueryWrapper = new QueryWrapper<>();
        customerQueryWrapper.eq("scenario_id", scenarioId);
        List<Customer> customers = customerMapper.selectList(customerQueryWrapper);
        for (Customer customer : customers) {
            if (customer.getName() == null || customer.getName().isEmpty()) {
                log.warn("客户名称为空: {}", customer.getId());
                return false;
            }
            if (customer.getLatitude() == null || customer.getLongitude() == null) {
                log.warn("客户坐标为空: {}", customer.getId());
                return false;
            }
            if (customer.getDemand() == null) {
                log.warn("客户需求量为空: {}", customer.getId());
                return false;
            }
        }

        log.info("场景数据验证通过: {}", scenarioId);
        return true;
    }
    
}
