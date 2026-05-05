package com.gz.gd.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.gz.gd.backend.entity.Solution;
import com.gz.gd.backend.mapper.SolutionMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
public class SolutionService {
    
    @Autowired
    private SolutionMapper solutionMapper;
    
    @Autowired
    private ObjectMapper objectMapper;
    
    // 根据ID查询单个解决方案
    public Solution getById(Long id) {
        log.info("查询解决方案 BY ID: {}", id);
        Solution solution = solutionMapper.selectById(id);
        if (solution == null) {
            log.warn("解决方案不存在，BY ID: {}", id);
        }
        return solution;
    }
    
    // 查询所有解决方案
    public List<Solution> listAll() {
        log.info("查询所有解决方案");
        QueryWrapper<Solution> queryWrapper = new QueryWrapper<>();
        queryWrapper.orderByDesc("create_time");
        return solutionMapper.selectList(queryWrapper);
    }
    
    // 按算法查询解决方案（不限场景）
    public List<Solution> listByAlgorithm(String algorithm) {
        log.info("查询算法 {} 的所有解决方案", algorithm);
        QueryWrapper<Solution> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("algorithm", algorithm)
                    .orderByDesc("create_time");
        return solutionMapper.selectList(queryWrapper);
    }
    
    // 按场景和算法组合查询解决方案
    public List<Solution> listByScenarioAndAlgorithm(Long scenarioId, String algorithm) {
        log.info("查询场景 {} 算法 {} 的解决方案", scenarioId, algorithm);
        QueryWrapper<Solution> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("scenario_id", scenarioId)
                    .eq("algorithm", algorithm)
                    .orderByDesc("create_time");
        return solutionMapper.selectList(queryWrapper);
    }
    
    // 查询某场景的所有解决方案
    public List<Solution> listByScenarioId(Long scenarioId) {
        log.info("查询场景 {} 的所有解决方案", scenarioId);
        QueryWrapper<Solution> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("scenario_id", scenarioId)
                    .orderByDesc("create_time");
        return solutionMapper.selectList(queryWrapper);
    }
    
    // 查询某场景的最优解
    public Solution getBestSolution(Long scenarioId) {
        log.info("查询场景 {} 的最优解决方案", scenarioId);
        QueryWrapper<Solution> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("scenario_id", scenarioId)
                    .orderByAsc("total_cost")
                    .last("LIMIT 1");
        return solutionMapper.selectOne(queryWrapper);
    }

    // 对比多个解决方案
    public Map<String, Object> compareSolutions(List<Long> solutionIds){
        if (solutionIds == null || solutionIds.isEmpty()){
            log.warn("未传入数据");
            return Collections.emptyMap();
        }
    
        log.info("开始对比 {} 个解决方案", solutionIds.size());
        List<Solution> solutions = solutionMapper.selectBatchIds(solutionIds);
        if (solutions.isEmpty()){
            log.warn("未找到解决方案");
            return Collections.emptyMap();
            // emptyMap是返回一个静态不可变的对象,防止后期不小心被引用修改的防御性编程措施
        }
        log.info("成功查询到{}个解决方案", solutions.size());

        //stream工作流简化工作对象方便选择性提交给前端,转Json也较为方便
        List<Map<String,Object>> solutionDetails = solutions.stream().map(solution ->{
            Map<String,Object> detail = new HashMap<>();
            detail.put("id", solution.getId());
            detail.put("algorithm", solution.getAlgorithm());
            detail.put("totalCost", solution.getTotalCost());
            detail.put("computeTime", solution.getComputeTime());

            int routeCount = parseRouteCount(solution.getRoutes());
            detail.put("routeCount",routeCount);
            detail.put("createTime", solution.getCreateTime());
            return detail;
        })
        .collect(Collectors.toList());

        //单独再做一部分用于代码可读性和下方调用
        List<BigDecimal> costs = solutions.stream().map(Solution::getTotalCost).collect(Collectors.toList());
        List<BigDecimal> times = solutions.stream().map(Solution::getComputeTime).collect(Collectors.toList());

        Map<String,Object> statistics = new HashMap<>();

        //输出最优成本 bestCost
        BigDecimal bestCost = costs.stream().min(BigDecimal::compareTo).orElse(BigDecimal.ZERO);
        statistics.put("bestCost", bestCost);
        //输出最差成本 worstCost
        BigDecimal worstCost = costs.stream().max(BigDecimal::compareTo).orElse(BigDecimal.ZERO);
        statistics.put("worstCost", worstCost);
        //输出2位进度四舍五入平均成本 avgCost
        BigDecimal avgCost = costs.stream().reduce(BigDecimal.ZERO, BigDecimal::add).divide(BigDecimal.valueOf(costs.size()), 2, BigDecimal.ROUND_HALF_UP);
        statistics.put("avgCost",avgCost);
        //最优算法 bestAlgorithm
        Solution bestSolution = solutions.stream().min(Comparator.comparing(Solution::getTotalCost)).orElse(null);
        statistics.put("bestAlgorithm",  bestSolution != null ? bestSolution.getAlgorithm() : "warning:null");
        //最快计算时间 fastestTime
        BigDecimal fastestTime = times.stream().min(BigDecimal::compareTo).orElse(BigDecimal.ZERO);
        statistics.put("fastestTime",fastestTime);
        //最慢计算时间 slowestTime
        BigDecimal slowestTime = times.stream().max(BigDecimal::compareTo).orElse(BigDecimal.ZERO);
        statistics.put("slowestTime",slowestTime);
        //输出2位进度四舍五入平均计算时间 avgTime
        BigDecimal avgTime = times.stream().reduce(BigDecimal.ZERO, BigDecimal::add).divide(BigDecimal.valueOf(times.size()), 2, BigDecimal.ROUND_HALF_UP);
        statistics.put("avgTime",avgTime);
        //solution数量 totalSolutions
        statistics.put("totalSolutions", solutions.size());

        //返回一个2容量的Map 统一输出 0:解具体细节 1:解分析
        Map<String,Object> result = new HashMap<>();
        result.put("solutions", solutionDetails);
        result.put("statistics", statistics);
        log.info("对比完成,最优成本:{},最优算法{}", statistics.get("bestCost"), statistics.get("bestAlgorithm"));

        return result;
    }

    //上个算法的附属private算法,用于解析路径数量
    private int parseRouteCount(String routeJson){
        if(routeJson == null || routeJson.isEmpty()){
            return 0;
        }
        try{
            List<?> routes = objectMapper.readValue(routeJson,List.class);
            return routes.size();
        }catch(Exception e){
            log.error("解析路径失败:{}", routeJson,e);
            return 0;
        }

    }

    //对比算法
    public Map<String, List<Solution>> compareAlgorithms(Long scenarioId){
        log.info("对比场景 {} 的不同算法", scenarioId);
        List<Solution> solutions = listByScenarioId(scenarioId);
        log.info("场景 {} 共有 {} 个解决方案", scenarioId, solutions.size());
        Map<String, List<Solution>> groupedByAlgorithm = solutions.stream().collect(Collectors.groupingBy(Solution::getAlgorithm));
        log.info("场景 {} 共采取过 {} 种算法", scenarioId, groupedByAlgorithm.size());
        return groupedByAlgorithm;
    }

    @Transactional
    //根据解决方案ID删除解决方案
    public boolean deleteById(Long id) {
        log.info("删除解决方案 BY ID: {}", id);
        int rows = solutionMapper.deleteById(id);
        return rows > 0;
    }

    @Transactional
    //根据场景ID删除解决方案
    public int deleteByScenarioId(Long scenarioId) {
        log.info("删除场景 {} 的所有解决方案", scenarioId);
        QueryWrapper<Solution> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("scenario_id", scenarioId);
        int rows = solutionMapper.delete(queryWrapper);
        log.info("成功删除 {} 条记录", rows);
        return rows;
    }
    
    //根据场景ID查询解决方案数量
    public Long countByScenarioId(Long scenarioId) {
        QueryWrapper<Solution> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("scenario_id", scenarioId);
        return solutionMapper.selectCount(queryWrapper);
    }

    @Transactional
    //保存算法求解结果到数据库
    public Solution saveSolution(Long scenarioId, String algorithm, String routesJson, BigDecimal totalCost, BigDecimal computeTime) {
        log.info("保存场景 {} 的解决方案，算法: {}", scenarioId, algorithm);
        
        Solution solution = new Solution();
        solution.setScenarioId(scenarioId);
        solution.setAlgorithm(algorithm);
        solution.setRoutes(routesJson);
        solution.setTotalCost(totalCost);
        solution.setComputeTime(computeTime);
        
        solutionMapper.insert(solution);
        log.info("解决方案保存成功，ID: {}", solution.getId());
        
        return solution;
    }
}
