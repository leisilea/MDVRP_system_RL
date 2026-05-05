package com.gz.gd.backend.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.gz.gd.backend.entity.AlgorithmResult;
import org.apache.ibatis.annotations.Mapper;

/**
 * 单个算法执行结果Mapper
 * Individual Algorithm Execution Result Mapper
 */
@Mapper
public interface AlgorithmResultMapper extends BaseMapper<AlgorithmResult> {
}
