-- 为已存在的 depot 表增加车辆最大行驶距离约束字段
-- 0 表示不限制最大行驶距离

SET @col_exists := (
	SELECT COUNT(*)
	FROM information_schema.COLUMNS
	WHERE TABLE_SCHEMA = DATABASE()
	  AND TABLE_NAME = 'depot'
	  AND COLUMN_NAME = 'vehicle_max_distance'
);

SET @ddl := IF(
	@col_exists = 0,
	'ALTER TABLE depot ADD COLUMN vehicle_max_distance DECIMAL(12,2) NOT NULL DEFAULT 0 COMMENT "车辆最大行驶距离，0表示不限制"',
	'SELECT "column vehicle_max_distance already exists"'
);

PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
