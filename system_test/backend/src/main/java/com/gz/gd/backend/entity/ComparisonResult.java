package com.gz.gd.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 算法比较结果实体
 * Algorithm Comparison Result Entity
 */
@Data
@TableName("comparison_result")
public class ComparisonResult {
    
    @TableId(type = IdType.AUTO)
    private Long id;
    
    /**
     * 场景ID
     */
    private Long scenarioId;
    
    /**
     * 执行时间
     */
    private LocalDateTime executionTime;
    
    /**
     * 比较的算法列表(逗号分隔)
     */
    private String algorithmsCompared;
    
    /**
     * 最优算法(最低成本)
     */
    private String bestAlgorithm;
    
    /**
     * 最优成本
     */
    private BigDecimal bestCost;
    
    /**
     * 最快算法
     */
    private String fastestAlgorithm;
    
    /**
     * 最快时间(秒)
     */
    private BigDecimal fastestTime;
    
    /**
     * 创建时间
     */
    private LocalDateTime createTime;
}
