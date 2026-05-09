package com.gz.gd.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;

/**
 * 单个算法执行结果实体
 * Individual Algorithm Execution Result Entity
 */
// 预留,目前并未使用
@Data
@TableName("algorithm_result")
public class AlgorithmResult {
    
    @TableId(type = IdType.AUTO)
    private Long id;
    
    /**
     * 比较结果ID
     */
    private Long comparisonId;
    
    /**
     * 算法名称
     */
    private String algorithm;
    
    /**
     * 是否执行成功
     */
    private Boolean success;
    
    /**
     * 总成本
     */
    private BigDecimal totalCost;
    
    /**
     * 计算时间(秒)
     */
    private BigDecimal computeTime;
    
    /**
     * 路径数量
     */
    private Integer numRoutes;
    
    /**
     * 路径详情(JSON格式)
     */
    private String routes;
    
    /**
     * 收敛数据(JSON格式)
     */
    private String convergence;
    
    /**
     * 错误信息
     */
    private String errorMessage;
}
