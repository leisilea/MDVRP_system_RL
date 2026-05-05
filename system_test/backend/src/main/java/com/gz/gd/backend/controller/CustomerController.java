package com.gz.gd.backend.controller;

import com.gz.gd.backend.common.Result;
import com.gz.gd.backend.entity.Customer;
import com.gz.gd.backend.service.CustomerService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/customer")
@CrossOrigin(origins = "*")  // 允许跨域
public class CustomerController {
    
    @Autowired
    private CustomerService customerService;

    /**
     * 创建客户
     * POST /api/customer
     */
    @PostMapping
    public Result<Customer> createCustomer(@RequestBody Customer customer) {
        log.info("创建客户: {}", customer.getName());
        try {
            boolean result = customerService.createCustomer(customer);
            if (result) {
                // 重新查询以获取完整数据
                Customer createdCustomer = customerService.getById(customer.getId());
                return Result.success(createdCustomer);
            } else {
                return Result.error("创建客户失败");
            }
        } catch (Exception e) {
            log.error("创建客户异常", e);
            return Result.error("创建客户异常: " + e.getMessage());
        }
    }

    /**
     * 获取客户详情
     * GET /api/customer/{id}
     */
    @GetMapping("/{id}")
    public Result<Customer> getById(@PathVariable Long id) {
        log.info("查询客户 ID: {}", id);
        try {
            Customer customer = customerService.getById(id);
            if (customer != null) {
                return Result.success(customer);
            } else {
                return Result.error(404, "客户不存在");
            }
        } catch (Exception e) {
            log.error("查询客户异常", e);
            return Result.error("查询客户异常: " + e.getMessage());
        }
    }

    /**
     * 获取场景的所有客户
     * GET /api/customer/list/{scenarioId}
     */
    @GetMapping("/list/{scenarioId}")
    public Result<List<Customer>> listByScenarioId(@PathVariable Long scenarioId) {
        log.info("查询场景 {} 的所有客户", scenarioId);
        try {
            List<Customer> customers = customerService.listByScenarioId(scenarioId);
            return Result.success(customers);
        } catch (Exception e) {
            log.error("查询客户列表异常", e);
            return Result.error("查询客户列表异常: " + e.getMessage());
        }
    }

    /**
     * 更新客户
     * PUT /api/customer/{id}
     */
    @PutMapping("/{id}")
    public Result<Void> updateCustomer(@PathVariable Long id, @RequestBody Customer customer) {
        log.info("更新客户 ID: {}", id);
        try {
            customer.setId(id);
            boolean result = customerService.updateCustomer(customer);
            if (result) {
                return Result.success();
            } else {
                return Result.error("更新客户失败");
            }
        } catch (Exception e) {
            log.error("更新客户异常", e);
            return Result.error("更新客户异常: " + e.getMessage());
        }
    }
    
    /**
     * 删除客户
     * DELETE /api/customer/{id}
     */
    @DeleteMapping("/{id}")
    public Result<Void> deleteById(@PathVariable Long id) {
        log.info("删除客户 ID: {}", id);
        try {
            boolean result = customerService.deleteById(id);
            if (result) {
                return Result.success();
            } else {
                return Result.error("删除客户失败");
            }
        } catch (Exception e) {
            log.error("删除客户异常", e);
            return Result.error("删除客户异常: " + e.getMessage());
        }
    }

    /**
     * 批量创建客户
     * POST /api/customer/batch
     */
    @PostMapping("/batch")
    public Result<List<Customer>> batchCreateCustomer(@RequestBody List<Customer> customers) {
        log.info("批量创建 {} 个客户", customers.size());
        try {
            customerService.batchCreate(customers);
            return Result.success(customers);
        } catch (Exception e) {
            log.error("批量创建客户异常", e);
            return Result.error("批量创建客户异常: " + e.getMessage());
        }
    }
}
