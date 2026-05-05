#!/bin/bash

# 重规划功能集成测试脚本

echo "=========================================="
echo "重规划功能集成测试"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 测试 1: 检查 Flask 服务
echo "测试 1: 检查 Flask 算法服务..."
FLASK_RESPONSE=$(curl -s http://localhost:5000/health)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Flask 服务运行正常${NC}"
    echo "  响应: $FLASK_RESPONSE"
else
    echo -e "${RED}✗ Flask 服务未运行${NC}"
    echo "  请运行: cd system_test/algorithm-service && python app.py"
    exit 1
fi
echo ""

# 测试 2: 检查 Spring Boot 服务
echo "测试 2: 检查 Spring Boot 后端服务..."
SPRING_RESPONSE=$(curl -s http://localhost:8080/api/algorithm/tasks/statistics)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Spring Boot 服务运行正常${NC}"
    echo "  响应: $SPRING_RESPONSE"
else
    echo -e "${RED}✗ Spring Boot 服务未运行${NC}"
    echo "  请运行: cd system_test/backend && mvn spring-boot:run"
    exit 1
fi
echo ""

# 测试 3: 测试 Flask /api/replan 端点
echo "测试 3: 测试 Flask /api/replan 端点..."
FLASK_REPLAN_REQUEST='{
  "depots": [
    {"id": 1, "x": 0, "y": 0, "vehicles": 2, "capacity": 100}
  ],
  "customers": [
    {"id": 1, "x": 10, "y": 10, "demand": 20},
    {"id": 2, "x": 20, "y": 20, "demand": 30}
  ],
  "routes": [
    {"vehicleId": 1, "depotId": 1, "path": [1, 2], "cost": 50.0}
  ],
  "blocked_edges": [
    {"from": 1, "to": 2}
  ],
  "algorithm": "GA",
  "params": {
    "algorithm": "GA",
    "population_size": 50,
    "max_iterations": 100
  }
}'

FLASK_REPLAN_RESPONSE=$(curl -s -X POST http://localhost:5000/api/replan \
  -H "Content-Type: application/json" \
  -d "$FLASK_REPLAN_REQUEST")

if echo "$FLASK_REPLAN_RESPONSE" | grep -q '"success": true'; then
    echo -e "${GREEN}✓ Flask /api/replan 端点工作正常${NC}"
    echo "  响应包含 success: true"
else
    echo -e "${RED}✗ Flask /api/replan 端点返回错误${NC}"
    echo "  响应: $FLASK_REPLAN_RESPONSE"
    exit 1
fi
echo ""

# 测试 4: 测试 Spring Boot /api/replan 端点（代理）
echo "测试 4: 测试 Spring Boot /api/replan 端点（代理到 Flask）..."
SPRING_REPLAN_REQUEST='{
  "depots": [
    {"id": 1, "x": 0, "y": 0, "vehicles": 2, "capacity": 100}
  ],
  "customers": [
    {"id": 1, "x": 10, "y": 10, "demand": 20},
    {"id": 2, "x": 20, "y": 20, "demand": 30}
  ],
  "routes": [
    {"vehicleId": 1, "depotId": 1, "path": [1, 2], "cost": 50.0}
  ],
  "blocked_edges": [
    {"from_node": 1, "to_node": 2}
  ],
  "algorithm": "GA",
  "params": {
    "algorithm": "GA",
    "population_size": 50,
    "max_iterations": 100
  }
}'

SPRING_REPLAN_RESPONSE=$(curl -s -X POST http://localhost:8080/api/replan \
  -H "Content-Type: application/json" \
  -d "$SPRING_REPLAN_REQUEST")

if echo "$SPRING_REPLAN_RESPONSE" | grep -q '"code":200'; then
    echo -e "${GREEN}✓ Spring Boot /api/replan 端点工作正常${NC}"
    echo "  响应包含 code: 200"
    
    # 检查是否包含重规划结果
    if echo "$SPRING_REPLAN_RESPONSE" | grep -q 'new_routes'; then
        echo -e "${GREEN}✓ 响应包含重规划结果 (new_routes)${NC}"
    else
        echo -e "${YELLOW}⚠ 响应不包含 new_routes，可能有问题${NC}"
    fi
else
    echo -e "${RED}✗ Spring Boot /api/replan 端点返回错误${NC}"
    echo "  响应: $SPRING_REPLAN_RESPONSE"
    exit 1
fi
echo ""

# 测试 5: 检查前端服务
echo "测试 5: 检查前端服务..."
FRONTEND_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8081)
if [ "$FRONTEND_RESPONSE" = "200" ]; then
    echo -e "${GREEN}✓ 前端服务运行正常${NC}"
    echo "  访问地址: http://localhost:8081"
else
    echo -e "${YELLOW}⚠ 前端服务可能未运行 (HTTP $FRONTEND_RESPONSE)${NC}"
    echo "  请运行: cd system_test/frontend && npm run dev"
fi
echo ""

# 总结
echo "=========================================="
echo "测试完成！"
echo "=========================================="
echo ""
echo -e "${GREEN}所有后端服务正常运行${NC}"
echo ""
echo "下一步："
echo "1. 访问前端: http://localhost:8081"
echo "2. 选择场景并计算路径"
echo "3. 点击'重规划'按钮测试功能"
echo ""
echo "如果遇到问题，请查看:"
echo "- system_test/REPLANNING_DEBUG_GUIDE.md"
echo "- system_test/REPLANNING_FIXES_SUMMARY.md"
echo ""
