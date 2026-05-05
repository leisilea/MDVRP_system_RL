package com.gz.gd.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.gz.gd.backend.entity.Depot;
import com.gz.gd.backend.mapper.DepotMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Slf4j
@Service
public class DepotService {
    
    @Autowired
    private DepotMapper depotMapper;
    
    // ==================== CRUD 方法 ====================

    private void fillDefaultConstraints(Depot depot) {
        if (depot.getVehicleMaxDistance() == null) {
            depot.setVehicleMaxDistance(0.0);
        }
    }
    
    // TODO: 在这里添加核心功能方法
    // 1. 创建仓库
    @Transactional
    public boolean createDepot(Depot depot) {
        log.info("创建仓库: {}", depot.getName());
        fillDefaultConstraints(depot);
        int result = depotMapper.insert(depot);
        return result > 0;
    }
    // 2. 按照ID获取
    public Depot getById(Long id) {
        log.info("根据ID获取仓库: {}", id);
        return depotMapper.selectById(id);
    }
    // 3. 查询该场景的所有仓库
    public List<Depot> listByScenarioId(Long scenarioId){
        log.info("查询该场景 {} 所有仓库", scenarioId);
        QueryWrapper<Depot> wrapper = new QueryWrapper<Depot>().eq("scenario_id", scenarioId);
        return depotMapper.selectList(wrapper);
    }
    // 4. 更新仓库
    @Transactional
    public int updateDepot(Depot depot){
        log.info("更新仓库: {}", depot.getId());
        fillDefaultConstraints(depot);
        int result = depotMapper.updateById(depot);
        return result;
    }
    // 5. 删除仓库
    @Transactional
    public boolean deleteById(Long id) {
        log.info("删除仓库: {}", id);
        int result = depotMapper.deleteById(id);
        return result > 0;
    }
    // 6. 批量创建新的仓库
    @Transactional
    public void batchCreate(List<Depot> depots) {
        log.info("批量创建仓库");
        for (Depot depot : depots) {
            fillDefaultConstraints(depot);
            depotMapper.insert(depot);
        }
    }
    // 7. 依据场景id删除仓库
    @Transactional
    public void deleteByScenarioId(Long scenarioId){
        log.info("依据场景id删除仓库: {}", scenarioId);
        QueryWrapper<Depot> wrapper = new QueryWrapper<Depot>().eq("scenario_id", scenarioId);
        depotMapper.delete(wrapper);
    }
    // 8. 输出该场景下仓库数量
    public int countByScenarioId(Long scenarioId){
        log.info("输出该场景下仓库数量: {}", scenarioId);
        QueryWrapper<Depot> wrapper = new QueryWrapper<Depot>().eq("scenario_id", scenarioId);
        Long count = depotMapper.selectCount(wrapper);
        return count != null ? count.intValue() : 0;
    }
    // 9. 统计总车辆数
    public int getTotalVehicles(Long scenarioId){
        log.info("统计总车辆数: {}", scenarioId);
        QueryWrapper<Depot> wrapper = new QueryWrapper<Depot>().eq("scenario_id", scenarioId);
        List<Depot> depots = depotMapper.selectList(wrapper);
        int totalVehicles = 0;
        for (Depot depot : depots) {
            totalVehicles += depot.getVehicleCount();
        }
        return totalVehicles;
    }
    
}
