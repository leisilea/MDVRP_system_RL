package com.gz.gd.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.gz.gd.backend.entity.Customer;
import com.gz.gd.backend.mapper.CustomerMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Slf4j
@Service
public class CustomerService {
    
    @Autowired
    private CustomerMapper customerMapper;
    
    // ==================== CRUD 方法 ====================
    
    // 1. 创建客户
    @Transactional
    public boolean createCustomer(Customer customer) {
        log.info("创建客户信息: {}", customer);
        return customerMapper.insert(customer) > 0;
    }
    
    // 2. 按照id获取
    public Customer getById(Long id) {
        log.info("根据ID获取客户信息: {}", id);
        return customerMapper.selectById(id);
    }
    
    // 3. 按照场景id列出客户
    public List<Customer> listByScenarioId(Long scenarioId) {
        log.info("根据场景ID获取客户信息: {}", scenarioId);
        QueryWrapper<Customer> wrapper = new QueryWrapper<Customer>().eq("scenario_id", scenarioId);
        return customerMapper.selectList(wrapper);
    }
    
    // 4. 更新客户
    @Transactional
    public boolean updateCustomer(Customer customer) {
        log.info("更新客户信息: {}", customer);
        return customerMapper.updateById(customer) > 0;
    }
    
    // 5. 删除客户
    @Transactional
    public boolean deleteById(Long id) {
        log.info("删除客户信息，ID: {}", id);
        return customerMapper.deleteById(id) > 0;
    }
    
    // 6. 批量创建客户
    @Transactional
    public void batchCreate(List<Customer> customers) {
        log.info("批量创建 {} 个客户", customers.size());
        for (Customer customer : customers) {
            customerMapper.insert(customer);
        }
        log.info("成功创建 {} 个客户", customers.size());
    }
    
    // 7. 根据场景id删除客户
    @Transactional
    public void deleteByScenarioId(Long scenarioId) {
        log.info("根据场景ID删除客户信息: {}", scenarioId);
        QueryWrapper<Customer> wrapper = new QueryWrapper<Customer>().eq("scenario_id", scenarioId);
        customerMapper.delete(wrapper);
    }
    
    // 8. 统计客户数量
    public int countByScenarioId(Long scenarioId) {
        log.info("根据场景ID统计客户数量: {}", scenarioId);
        QueryWrapper<Customer> wrapper = new QueryWrapper<Customer>().eq("scenario_id", scenarioId);
        Long count = customerMapper.selectCount(wrapper);
        return count != null ? count.intValue() : 0;
    }
    
    // 9. 统计总需求量
    public int getTotalDemand(Long scenarioId) {
        log.info("根据场景ID获取总需求量: {}", scenarioId);
        QueryWrapper<Customer> wrapper = new QueryWrapper<Customer>().eq("scenario_id", scenarioId);
        List<Customer> customers = customerMapper.selectList(wrapper);
        return customers.stream().mapToInt(Customer::getDemand).sum();
    }
    
}
