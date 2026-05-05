package com.gz.gd.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("solution")
public class Solution {
    @TableId(type = IdType.AUTO)
    private Long id;
    
    private Long scenarioId;
    
    private String algorithm;
    
    private String routes;  // JSON格式
    
    private BigDecimal totalCost;
    
    private BigDecimal computeTime;
    
    private LocalDateTime createTime;
}
