package com.gz.gd.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;

@Data
@TableName("depot")
public class Depot {
    @TableId(type = IdType.AUTO)
    private Long id;
    
    private Long scenarioId;
    
    private String name;
    
    private String address;
    
    private BigDecimal longitude;
    
    private BigDecimal latitude;
    
    private Integer vehicleCount;
    
    private Integer vehicleCapacity;

    private Double vehicleMaxDistance;
}
