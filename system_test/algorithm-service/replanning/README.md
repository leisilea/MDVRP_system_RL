# 简化版重规划服务

## 概述

简化版重规划服务专注于单车辆局部重规划，将受堵塞影响的车辆路径重规划问题转化为TSP问题求解。

## 核心特性

1. **单车辆局部重规划**：只对受堵塞影响的车辆进行重规划
2. **TSP求解**：将重规划问题转化为旅行商问题
3. **两种算法**：
   - **GREEDY**：贪心最近邻算法（快速）
   - **2OPT**：贪心 + 2-opt局部搜索（质量更好）
4. **避开阻塞路段**：自动避开被堵塞的道路
5. **快速响应**：通常在1秒内完成重规划

## 算法说明

### GREEDY算法（贪心最近邻）

**原理**：
- 从当前位置开始，每次选择最近的未访问客户
- 优先选择不经过阻塞路段的客户
- 时间复杂度：O(n²)，n为未服务客户数

**适用场景**：
- 客户数 < 10
- 需要快速响应（< 0.1秒）
- 对解质量要求不高

### 2OPT算法（贪心 + 2-opt优化）

**原理**：
1. 使用贪心算法生成初始解
2. 使用2-opt局部搜索改进解
3. 每次尝试反转路径中的一段，如果成本降低则接受
4. 重复直到无法改进或达到最大迭代次数

**适用场景**：
- 客户数 ≥ 4
- 有一定计算时间（0.1-1秒）
- 追求更好的解质量

**参数**：
- `max_iterations`: 最大迭代次数（默认100）

## API使用

### 请求格式

```json
{
  "depots": [
    {"id": 1, "x": 0, "y": 0, "vehicles": 2, "capacity": 100}
  ],
  "customers": [
    {"id": 101, "x": 10, "y": 10, "demand": 10},
    {"id": 102, "x": 20, "y": 10, "demand": 15}
  ],
  "routes": [
    {
      "vehicleId": 1,
      "depotId": 1,
      "path": [101, 102, 103, 104],
      "cost": 100.0
    }
  ],
  "blocked_edges": [
    {"from": 102, "to": 103}
  ],
  "vehicle_positions": {
    "1": 101
  },
  "algorithm": "2OPT",
  "params": {
    "max_iterations": 100
  }
}
```

### 响应格式

```json
{
  "success": true,
  "data": {
    "new_routes": [
      {
        "vehicleId": 1,
        "depotId": 1,
        "path": [101, 104, 103, 102],
        "cost": 0.0
      }
    ],
    "replanned_route_ids": [1],
    "cost_before": 0.0,
    "cost_after": 0.0,
    "cost_difference": 0.0,
    "cost_change_percent": 0.0,
    "algorithm": "2OPT",
    "solve_time": 0.123,
    "num_routes": 1,
    "temporary_depots": [],
    "vehicle_positions": {"1": 101}
  }
}
```

## 测试

### 方法1：通过API测试（推荐）

1. 启动Flask服务：
```bash
cd system_test/algorithm-service
python app.py
```

2. 运行测试脚本：
```bash
python test_replanning_direct.py
```

### 方法2：前端测试

1. 启动所有服务（后端、算法服务、前端）
2. 在前端界面：
   - 求解一个MDVRP问题
   - 点击"重规划"按钮
   - 选择要阻塞的路段
   - 查看重规划结果

## 性能指标

| 客户数 | GREEDY时间 | 2OPT时间 | 质量提升 |
|--------|-----------|----------|----------|
| 5      | < 0.01s   | < 0.05s  | 5-10%    |
| 10     | < 0.02s   | < 0.1s   | 10-15%   |
| 20     | < 0.05s   | < 0.3s   | 15-20%   |
| 50     | < 0.2s    | < 1.0s   | 20-25%   |

## 实现细节

### 文件结构

```
replanning/
├── service_simple.py       # 简化版重规划服务
├── models.py               # 数据模型
├── exceptions.py           # 异常定义
└── README.md              # 本文档
```

### 核心方法

1. **`replan()`**: 主入口，协调整个重规划流程
2. **`_identify_affected_routes()`**: 识别受堵塞影响的车辆
3. **`_solve_tsp()`**: TSP求解器（选择GREEDY或2OPT）
4. **`_greedy_reorder()`**: 贪心最近邻算法
5. **`_two_opt()`**: 2-opt局部搜索优化

### 关键逻辑

**识别受影响车辆**：
```python
# 检查路径中是否包含阻塞路段
for i in range(len(path) - 1):
    edge = (path[i], path[i + 1])
    if edge in blocked_set:
        affected.add(vehicle_id)
        break
```

**贪心重排序**：
```python
while remaining_customers:
    # 找到最近的未服务客户（且不经过阻塞路段）
    best_customer = find_nearest(current, remaining, blocked_edges)
    path.append(best_customer)
    current = best_customer
```

**2-opt优化**：
```python
for i in range(len(path) - 1):
    for j in range(i + 2, len(path)):
        # 反转i+1到j之间的部分
        new_path = path[:i+1] + path[i+1:j+1][::-1] + path[j+1:]
        if cost(new_path) < cost(best_path):
            best_path = new_path
```

## 与旧版本对比

| 特性 | 旧版本（临时仓库） | 新版本（简化版） |
|------|-------------------|-----------------|
| 复杂度 | 高（需要PSO求解器） | 低（贪心+2-opt） |
| 计算时间 | 5-10秒 | < 1秒 |
| 容量约束 | 难以满足 | 不需要考虑 |
| 影响范围 | 全局（所有车辆） | 局部（受影响车辆） |
| 结果质量 | 不稳定 | 稳定 |
| 实用性 | 低 | 高 |

## 未来改进

1. **算法增强**：
   - 添加3-opt优化
   - 实现Or-opt算法
   - 支持时间窗约束

2. **性能优化**：
   - 并行处理多个受影响车辆
   - 缓存距离计算结果
   - 使用更高效的数据结构

3. **功能扩展**：
   - 支持多个阻塞路段的组合优化
   - 车辆之间的任务转移
   - 动态调整路径（实时重规划）

## 常见问题

**Q: 为什么不使用更复杂的算法（如遗传算法）？**
A: 重规划需要快速响应（< 1秒），简单算法更适合。对于单车辆TSP问题，2-opt已经能提供很好的解质量。

**Q: 如果所有路径都被阻塞怎么办？**
A: 算法会忽略阻塞约束，选择距离最近的客户。实际应用中，应该提示用户无可行解。

**Q: 能否支持多车辆协同重规划？**
A: 当前版本专注于单车辆局部重规划。多车辆协同需要考虑容量约束和任务分配，复杂度会大幅增加。

**Q: 2-opt的迭代次数如何选择？**
A: 默认100次对大多数情况足够。如果客户数很多（> 50），可以增加到200-500次。

## 参考资料

- [2-opt算法](https://en.wikipedia.org/wiki/2-opt)
- [旅行商问题](https://en.wikipedia.org/wiki/Travelling_salesman_problem)
- [贪心算法](https://en.wikipedia.org/wiki/Greedy_algorithm)
