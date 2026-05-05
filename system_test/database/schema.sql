-- 创建数据库
CREATE DATABASE IF NOT EXISTS mdvrp_db DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE mdvrp_db;

-- 场景表
CREATE TABLE scenario (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL COMMENT '场景名称',
    description TEXT COMMENT '场景描述',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='场景配置表';

-- 仓库表
CREATE TABLE depot (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    scenario_id BIGINT NOT NULL,
    name VARCHAR(50) NOT NULL,
    longitude DECIMAL(10, 6) NOT NULL,
    latitude DECIMAL(10, 6) NOT NULL,
    vehicle_count INT DEFAULT 5 COMMENT '车辆数量',
    vehicle_capacity INT DEFAULT 100 COMMENT '车辆载重',
    FOREIGN KEY (scenario_id) REFERENCES scenario(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='仓库表';

-- 客户表
CREATE TABLE customer (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    scenario_id BIGINT NOT NULL,
    name VARCHAR(50) NOT NULL,
    longitude DECIMAL(10, 6) NOT NULL,
    latitude DECIMAL(10, 6) NOT NULL,
    demand INT NOT NULL COMMENT '需求量',
    time_window VARCHAR(50) COMMENT '时间窗 JSON格式',
    FOREIGN KEY (scenario_id) REFERENCES scenario(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客户表';

-- 解决方案表
CREATE TABLE solution (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    scenario_id BIGINT NOT NULL,
    algorithm VARCHAR(50) NOT NULL COMMENT '算法名称',
    routes TEXT NOT NULL COMMENT '路径结果 JSON格式',
    total_cost DECIMAL(10, 2) NOT NULL,
    compute_time DECIMAL(10, 3) NOT NULL COMMENT '计算时间(秒)',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (scenario_id) REFERENCES scenario(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='解决方案表';

-- 创建索引
CREATE INDEX idx_scenario_id ON depot(scenario_id);
CREATE INDEX idx_scenario_id ON customer(scenario_id);
CREATE INDEX idx_solution_scenario ON solution(scenario_id);
