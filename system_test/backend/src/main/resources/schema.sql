-- MDVRP 数据库表结构
-- 用于存储多仓库车辆路径问题的场景、仓库和客户数据
-- 注意：此脚本使用 CREATE TABLE IF NOT EXISTS，可以安全地重复执行

-- 创建数据库
CREATE DATABASE IF NOT EXISTS mdvrp_db DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE mdvrp_db;

-- 场景表
CREATE TABLE IF NOT EXISTS `scenario` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '场景ID',
    `name` VARCHAR(100) NOT NULL COMMENT '场景名称',
    `description` TEXT COMMENT '场景描述',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    INDEX `idx_name` (`name`),
    INDEX `idx_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='MDVRP场景表';

-- 仓库表
CREATE TABLE IF NOT EXISTS `depot` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '仓库ID',
    `scenario_id` BIGINT NOT NULL COMMENT '所属场景ID',
    `name` VARCHAR(100) NOT NULL COMMENT '仓库名称',
    `address` VARCHAR(255) COMMENT '仓库地址',
    `longitude` DECIMAL(10, 6) NOT NULL COMMENT '经度（X坐标）',
    `latitude` DECIMAL(10, 6) NOT NULL COMMENT '纬度（Y坐标）',
    `vehicle_count` INT NOT NULL DEFAULT 5 COMMENT '车辆数量',
    `vehicle_capacity` INT NOT NULL DEFAULT 100 COMMENT '车辆容量',
    `vehicle_max_distance` DECIMAL(12, 2) NOT NULL DEFAULT 0 COMMENT '车辆最大行驶距离，0表示不限制',
    PRIMARY KEY (`id`),
    INDEX `idx_scenario_id` (`scenario_id`),
    INDEX `idx_name` (`name`),
    CONSTRAINT `fk_depot_scenario` FOREIGN KEY (`scenario_id`) REFERENCES `scenario` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='仓库表';

-- 客户表
CREATE TABLE IF NOT EXISTS `customer` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '客户ID',
    `scenario_id` BIGINT NOT NULL COMMENT '所属场景ID',
    `name` VARCHAR(100) NOT NULL COMMENT '客户名称',
    `address` VARCHAR(255) COMMENT '客户地址',
    `longitude` DECIMAL(10, 6) NOT NULL COMMENT '经度（X坐标）',
    `latitude` DECIMAL(10, 6) NOT NULL COMMENT '纬度（Y坐标）',
    `demand` INT NOT NULL DEFAULT 10 COMMENT '需求量',
    `time_window` VARCHAR(50) COMMENT '时间窗口（可选）',
    PRIMARY KEY (`id`),
    INDEX `idx_scenario_id` (`scenario_id`),
    INDEX `idx_name` (`name`),
    CONSTRAINT `fk_customer_scenario` FOREIGN KEY (`scenario_id`) REFERENCES `scenario` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='客户表';

-- 用户表
CREATE TABLE IF NOT EXISTS `user` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '用户ID',
    `username` VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    `password` VARCHAR(255) NOT NULL COMMENT '密码（加密）',
    `email` VARCHAR(100) COMMENT '邮箱',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    UNIQUE INDEX `uk_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- 算法结果表
CREATE TABLE IF NOT EXISTS `algorithm_result` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '结果ID',
    `scenario_id` BIGINT NOT NULL COMMENT '场景ID',
    `algorithm_name` VARCHAR(50) NOT NULL COMMENT '算法名称（GA/ACO/PSO）',
    `total_cost` DECIMAL(12, 2) NOT NULL COMMENT '总成本',
    `compute_time` DECIMAL(10, 3) NOT NULL COMMENT '计算时间（秒）',
    `num_routes` INT NOT NULL COMMENT '路径数量',
    `convergence_data` TEXT COMMENT '收敛数据（JSON）',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    INDEX `idx_scenario_id` (`scenario_id`),
    INDEX `idx_algorithm_name` (`algorithm_name`),
    INDEX `idx_create_time` (`create_time`),
    CONSTRAINT `fk_result_scenario` FOREIGN KEY (`scenario_id`) REFERENCES `scenario` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='算法结果表';

-- 解决方案表
CREATE TABLE IF NOT EXISTS `solution` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '解决方案ID',
    `result_id` BIGINT NOT NULL COMMENT '算法结果ID',
    `vehicle_id` INT NOT NULL COMMENT '车辆ID',
    `depot_id` BIGINT NOT NULL COMMENT '仓库ID',
    `route_path` TEXT NOT NULL COMMENT '路径（客户ID列表，JSON）',
    `route_cost` DECIMAL(10, 2) NOT NULL COMMENT '路径成本',
    PRIMARY KEY (`id`),
    INDEX `idx_result_id` (`result_id`),
    INDEX `idx_depot_id` (`depot_id`),
    CONSTRAINT `fk_solution_result` FOREIGN KEY (`result_id`) REFERENCES `algorithm_result` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_solution_depot` FOREIGN KEY (`depot_id`) REFERENCES `depot` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='解决方案表';

-- 算法对比结果表
CREATE TABLE IF NOT EXISTS `comparison_result` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '对比结果ID',
    `scenario_id` BIGINT NOT NULL COMMENT '场景ID',
    `ga_cost` DECIMAL(12, 2) COMMENT '遗传算法成本',
    `ga_time` DECIMAL(10, 3) COMMENT '遗传算法时间',
    `aco_cost` DECIMAL(12, 2) COMMENT '蚁群算法成本',
    `aco_time` DECIMAL(10, 3) COMMENT '蚁群算法时间',
    `pso_cost` DECIMAL(12, 2) COMMENT '粒子群算法成本',
    `pso_time` DECIMAL(10, 3) COMMENT '粒子群算法时间',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    INDEX `idx_scenario_id` (`scenario_id`),
    INDEX `idx_create_time` (`create_time`),
    CONSTRAINT `fk_comparison_scenario` FOREIGN KEY (`scenario_id`) REFERENCES `scenario` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='算法对比结果表';

-- 算法任务表（用于异步任务管理）
CREATE TABLE IF NOT EXISTS `algorithm_task` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '任务ID',
    `scenario_id` BIGINT NOT NULL COMMENT '场景ID',
    `algorithm` VARCHAR(50) NOT NULL COMMENT '算法名称',
    `status` VARCHAR(20) NOT NULL COMMENT '任务状态：PENDING, RUNNING, COMPLETED, FAILED',
    `params` TEXT COMMENT '算法参数（JSON格式）',
    `result` TEXT COMMENT '算法结果（JSON格式）',
    `error` TEXT COMMENT '错误信息',
    `total_cost` DECIMAL(12, 2) COMMENT '总成本',
    `compute_time` DECIMAL(10, 3) COMMENT '计算时间（秒）',
    `progress` INT DEFAULT 0 COMMENT '进度百分比 0-100',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `start_time` DATETIME COMMENT '开始时间',
    `end_time` DATETIME COMMENT '结束时间',
    PRIMARY KEY (`id`),
    INDEX `idx_scenario_id` (`scenario_id`),
    INDEX `idx_status` (`status`),
    INDEX `idx_create_time` (`create_time`),
    CONSTRAINT `fk_task_scenario` FOREIGN KEY (`scenario_id`) REFERENCES `scenario` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='算法任务表';

-- 插入示例数据
-- 示例场景
INSERT INTO `scenario` (`name`, `description`) VALUES
('测试场景1', '包含2个仓库和10个客户的小规模测试场景'),
('测试场景2', '包含3个仓库和20个客户的中等规模测试场景')
ON DUPLICATE KEY UPDATE `name` = VALUES(`name`);

-- 获取场景ID
SET @scenario1_id = (SELECT id FROM scenario WHERE name = '测试场景1' LIMIT 1);
SET @scenario2_id = (SELECT id FROM scenario WHERE name = '测试场景2' LIMIT 1);

-- 场景1的仓库
INSERT INTO `depot` (`scenario_id`, `name`, `address`, `longitude`, `latitude`, `vehicle_count`, `vehicle_capacity`, `vehicle_max_distance`) VALUES
(@scenario1_id, '仓库A', '广州市天河区', 113.324520, 23.146760, 5, 100, 80.0),
(@scenario1_id, '仓库B', '广州市越秀区', 113.264530, 23.129110, 5, 100, 80.0)
ON DUPLICATE KEY UPDATE `name` = VALUES(`name`);

-- 场景1的客户
INSERT INTO `customer` (`scenario_id`, `name`, `address`, `longitude`, `latitude`, `demand`) VALUES
(@scenario1_id, '客户1', '广州市天河区客户1', 113.334520, 23.156760, 15),
(@scenario1_id, '客户2', '广州市天河区客户2', 113.344520, 23.166760, 20),
(@scenario1_id, '客户3', '广州市天河区客户3', 113.354520, 23.176760, 25),
(@scenario1_id, '客户4', '广州市越秀区客户4', 113.274530, 23.139110, 18),
(@scenario1_id, '客户5', '广州市越秀区客户5', 113.284530, 23.149110, 22),
(@scenario1_id, '客户6', '广州市海珠区客户6', 113.314520, 23.106760, 16),
(@scenario1_id, '客户7', '广州市海珠区客户7', 113.324520, 23.116760, 19),
(@scenario1_id, '客户8', '广州市白云区客户8', 113.294520, 23.186760, 21),
(@scenario1_id, '客户9', '广州市白云区客户9', 113.304520, 23.196760, 17),
(@scenario1_id, '客户10', '广州市番禺区客户10', 113.384520, 23.006760, 23)
ON DUPLICATE KEY UPDATE `name` = VALUES(`name`);

-- 默认用户（密码: admin123）
INSERT INTO `user` (`username`, `password`, `email`) VALUES
('admin', '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBOsl7iKTVKIUi', 'admin@example.com')
ON DUPLICATE KEY UPDATE `username` = VALUES(`username`);
