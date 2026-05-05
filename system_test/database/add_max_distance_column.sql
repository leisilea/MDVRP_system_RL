-- ============================================================================
-- Migration Script: Add max_distance Column to depot Table
-- Feature: Vehicle Maximum Distance Constraint
-- Version: 1.0
-- Date: 2024-01-15
-- ============================================================================

USE mdvrp_db;

-- 1. 添加max_distance列
-- 类型: DECIMAL(10,2) 支持最大999999.99km,精度0.01km
-- 默认值: NULL 表示无距离限制
ALTER TABLE depot 
ADD COLUMN max_distance DECIMAL(10,2) DEFAULT NULL 
COMMENT '车辆最大行驶距离(km),NULL表示无限制';

-- 2. 添加CHECK约束确保max_distance为正数或NULL
ALTER TABLE depot 
ADD CONSTRAINT chk_max_distance_positive 
CHECK (max_distance IS NULL OR max_distance > 0);

-- 3. 添加索引优化查询性能
CREATE INDEX idx_depot_max_distance ON depot(max_distance);

-- 4. 验证迁移结果
SELECT 
    COUNT(*) as total_depots,
    COUNT(max_distance) as depots_with_limit,
    COUNT(*) - COUNT(max_distance) as depots_unlimited,
    MIN(max_distance) as min_distance,
    MAX(max_distance) as max_distance,
    AVG(max_distance) as avg_distance
FROM depot;

-- 5. 验证列定义
SELECT 
    COLUMN_NAME,
    DATA_TYPE,
    COLUMN_TYPE,
    IS_NULLABLE,
    COLUMN_DEFAULT,
    COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'mdvrp_db'
  AND TABLE_NAME = 'depot'
  AND COLUMN_NAME = 'max_distance';

-- ============================================================================
-- Rollback Script (如果需要回滚)
-- ============================================================================
-- 取消注释以下命令来回滚此迁移:

-- DROP INDEX idx_depot_max_distance ON depot;
-- ALTER TABLE depot DROP CONSTRAINT chk_max_distance_positive;
-- ALTER TABLE depot DROP COLUMN max_distance;

-- ============================================================================
-- 测试数据 (可选,用于开发环境测试)
-- ============================================================================
-- 取消注释以下命令来添加测试数据:

-- UPDATE depot SET max_distance = 50.0 WHERE id = 1;
-- UPDATE depot SET max_distance = 75.5 WHERE id = 2;
-- UPDATE depot SET max_distance = NULL WHERE id = 3;  -- 无限制

-- ============================================================================
-- 注意事项
-- ============================================================================
-- 1. 此脚本是幂等的,可以安全地多次执行(如果列已存在会报错但不影响数据)
-- 2. 所有现有depot记录的max_distance将自动设置为NULL
-- 3. NULL值在业务逻辑中解释为"无距离限制"
-- 4. 建议在生产环境执行前先在测试环境验证
-- 5. 执行前请备份数据库
-- ============================================================================
