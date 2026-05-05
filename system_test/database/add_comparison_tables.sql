-- 算法比较功能数据库迁移脚本
-- Algorithm Comparison Feature Database Migration

USE mdvrp_db;

-- 比较结果表
CREATE TABLE IF NOT EXISTS comparison_result (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    scenario_id BIGINT NOT NULL COMMENT '场景ID',
    execution_time DATETIME NOT NULL COMMENT '执行时间',
    algorithms_compared VARCHAR(200) NOT NULL COMMENT '比较的算法列表(逗号分隔)',
    best_algorithm VARCHAR(50) COMMENT '最优算法(最低成本)',
    best_cost DECIMAL(10, 2) COMMENT '最优成本',
    fastest_algorithm VARCHAR(50) COMMENT '最快算法',
    fastest_time DECIMAL(10, 3) COMMENT '最快时间(秒)',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (scenario_id) REFERENCES scenario(id) ON DELETE CASCADE,
    INDEX idx_scenario_execution (scenario_id, execution_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='算法比较结果表';

-- 单个算法结果表
CREATE TABLE IF NOT EXISTS algorithm_result (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    comparison_id BIGINT NOT NULL COMMENT '比较结果ID',
    algorithm VARCHAR(50) NOT NULL COMMENT '算法名称',
    success BOOLEAN NOT NULL COMMENT '是否执行成功',
    total_cost DECIMAL(10, 2) COMMENT '总成本',
    compute_time DECIMAL(10, 3) COMMENT '计算时间(秒)',
    num_routes INT COMMENT '路径数量',
    routes TEXT COMMENT '路径详情(JSON格式)',
    convergence TEXT COMMENT '收敛数据(JSON格式)',
    error_message TEXT COMMENT '错误信息',
    FOREIGN KEY (comparison_id) REFERENCES comparison_result(id) ON DELETE CASCADE,
    INDEX idx_comparison (comparison_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='单个算法执行结果表';
