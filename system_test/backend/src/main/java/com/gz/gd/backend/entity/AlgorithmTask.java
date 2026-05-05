package com.gz.gd.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("algorithm_task")
public class AlgorithmTask {
    @TableId(type = IdType.AUTO)
    private Long id;
    
    private Long scenarioId;
    
    private String algorithm;
    
    private String status;  // PENDING, RUNNING, COMPLETED, FAILED
    
    private String params;  // JSON格式的参数
    
    private String result;  // JSON格式的结果
    
    private String error;  // 错误信息
    
    private BigDecimal totalCost;
    
    private BigDecimal computeTime;
    
    private Integer progress;  // 进度百分比 0-100
    
    private LocalDateTime createTime;
    
    private LocalDateTime startTime;
    
    private LocalDateTime endTime;
}
