package com.gz.gd.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;

@Data
@TableName("customer")
public class Customer {
    @TableId(type = IdType.AUTO)
    private Long id;
    
    private Long scenarioId;
    
    private String name;
    
    private String address;
    
    private BigDecimal longitude;
    
    private BigDecimal latitude;
    
    private Integer demand;
    
    private String timeWindow;
}
