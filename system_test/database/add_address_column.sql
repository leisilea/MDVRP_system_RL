-- 添加地址字段到 depot 和 customer 表
-- 执行时间：请在修改前备份数据库

USE mdvrp_db;

-- 为 depot 表添加 address 字段
ALTER TABLE depot ADD COLUMN address VARCHAR(500) COMMENT '仓库地址' AFTER name;

-- 为 customer 表添加 address 字段  
ALTER TABLE customer ADD COLUMN address VARCHAR(500) COMMENT '客户地址' AFTER name;

-- 查看修改结果
DESC depot;
DESC customer;

-- 验证数据
SELECT COUNT(*) as depot_count FROM depot;
SELECT COUNT(*) as customer_count FROM customer;
