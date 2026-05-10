# 简化版重规划服务

## 概述

简化版重规划服务专注于处理道路阻塞情况下的车辆绕路重规划，**不涉及任务重新分配**。当道路被阻塞时，只对受影响的车辆进行局部路径调整，使用贪心最近邻算法快速生成绕路方案。

## 核心特性

1. **局部重规划**：只对受堵塞影响的车辆进行重规划，未受影响的车辆保持原路径
2. **快速响应**：使用贪心最近邻算法，通常在 0.1 秒内完成重规划
3. **避开阻塞路段**：自动将阻塞路段距离设置为极大值（1000000），确保不经过
4. **保证返回仓库**：重规划后的路径确保车辆最终返回出发仓库
5. **无任务转移**：不在车辆之间重新分配任务，保持原有任务分配

## 算法说明

### 贪心最近邻算法

**原理**：
- 从车辆当前位置开始，依次访问最近的未访问客户
- 使用修改后的距离矩阵（阻塞路段距离 = 1000000）
- 自动避开阻塞路段
- 时间复杂度：O(n²)，n 为剩余未服务客户数

**流程**：
1. 识别受阻塞影响的车辆（检查剩余路径是否经过阻塞路段）
2. 对每辆受影响车辆：
   - 确定当前位置和剩余客户
   - 使用贪心算法重新排序剩余客户
   - 计算新路径成本（包括返回仓库）
3. 未受影响车辆保持原路径

## API 使用

### 请求格式

```json
{
  "depots": [
    {"id": 12000, "x": 0, "y": 0, "vehicles": 2, "capacity": 100}
  ],
  "customers": [
    {"id": 12050, "x": 10, "y": 10, "demand": 10},
    {"id": 12051, "x": 20, "y": 10, "demand": 15}
  ],
  "routes": [
    {
      "vehicleId": 1,
      "depotId": 12000,
      "path": [12050, 12051, 12052],
      "cost": 100.0
    }
  ],
  "blocked_edges": [
    {"from_node": 35, "to_node": 4}
  ],
  "vehicle_positions": {
    "1": 12050
  },
  "algorithm": "greedy"
}
```

**注意**：
- `blocked_edges` 使用**算法索引**（0-53），不是数据库 ID
- 前端负责将数据库 ID 转换为算法索引
- 算法索引规则：仓库索引 0, 1, 2...，客户索引从仓库数量开始

### 响应格式

```json
{
  "new_routes": [
    {
      "vehicleId": 1,
      "depotId": 12000,
      "path": [12050, 12052, 12051],
      "cost": 120.5
    }
  ],
  "replanned_route_ids": [1],
  "cost_before": 100.0,
  "cost_after": 120.5,
  "cost_difference": 20.5,
  "cost_change_percent": 20.5,
  "algorithm": "greedy",
  "solve_time": 0.05,
  "num_routes": 1,
  "affected_vehicles": [1]
}
```

## 文件结构

```
replanning/
├── __init__.py              # 模块初始化
├── simple_replanner.py      # 核心重规划逻辑
├── api_simple.py            # API 处理函数
├── exceptions.py            # 异常定义
└── README.md               # 本文档
```

## 核心方法

### SimpleReplanner 类

**`__init__(depots, customers)`**
- 初始化重规划器
- 构建 ID 映射（数据库 ID ↔ 算法索引）
- 构建原始距离矩阵

**`replan(routes, blocked_edges, vehicle_positions, algorithm)`**
- 主入口方法
- 识别受影响车辆
- 修改距离矩阵（设置阻塞路段为不可通行）
- 对每辆受影响车辆进行重规划
- 计算成本对比

**`_identify_affected_vehicles(routes, blocked_edges, vehicle_positions)`**
- 识别哪些车辆的剩余路径经过阻塞路段
- 返回受影响车辆的详细信息

**`_replan_single_vehicle(route, current_position, modified_matrix, algorithm)`**
- 为单个车辆重规划剩余路径
- 使用贪心最近邻算法
- 确保车辆返回仓库

**`_greedy_nearest_neighbor(start_pos, customers, depot_id, distance_matrix)`**
- 贪心最近邻算法实现
- 从当前位置开始，依次访问最近的未访问客户

**`_calculate_route_cost(depot_id, path, distance_matrix)`**
- 计算路径成本
- **包括返回仓库的距离**
- 路径成本 = 仓库→第一个客户 + 客户间距离 + 最后客户→仓库

## 关键实现细节

### ID 映射机制

```python
# 数据库 ID -> 算法索引
id_to_index = {
    12000: 0,  # 仓库0
    12001: 1,  # 仓库1
    12050: 2,  # 客户0
    12051: 3,  # 客户1
    ...
}

# 算法索引 -> 数据库 ID
index_to_id = {
    0: 12000,
    1: 12001,
    2: 12050,
    ...
}
```

### 阻塞路段处理

```python
# 修改距离矩阵
modified_matrix = original_matrix.copy()
for edge in blocked_edges:
    from_idx = edge['from_node']  # 算法索引
    to_idx = edge['to_node']      # 算法索引
    modified_matrix[from_idx][to_idx] = 1000000.0
    modified_matrix[to_idx][from_idx] = 1000000.0  # 双向阻塞
```

### 返回仓库逻辑

```python
def _calculate_route_cost(depot_id, path, distance_matrix):
    cost = 0.0
    current_idx = id_to_index[depot_id]
    
    # 访问所有客户
    for customer_id in path:
        customer_idx = id_to_index[customer_id]
        cost += distance_matrix[current_idx][customer_idx]
        current_idx = customer_idx
    
    # 返回仓库（关键）
    depot_idx = id_to_index[depot_id]
    cost += distance_matrix[current_idx][depot_idx]
    
    return cost
```

## 性能指标

| 客户数 | 计算时间 | 内存占用 |
|--------|---------|---------|
| 10     | < 0.01s | < 1MB   |
| 50     | < 0.05s | < 5MB   |
| 100    | < 0.2s  | < 10MB  |
| 200    | < 0.5s  | < 20MB  |

## 测试

### 通过前端测试（推荐）

1. 启动所有服务（后端、算法服务、前端）
2. 在前端界面：
   - 求解一个 MDVRP 问题
   - 点击"重规划"按钮
   - 进入选择模式，点击两个节点选择阻塞路段
   - 点击"开始重规划"
   - 查看重规划结果和成本变化

### 通过 API 测试

```bash
cd system_test/algorithm-service
python app.py

# 在另一个终端
curl -X POST http://localhost:5000/api/replan \
  -H "Content-Type: application/json" \
  -d @test_data.json
```

## 与旧版本对比

| 特性 | 旧版本（临时仓库） | 新版本（简化版） |
|------|-------------------|-----------------|
| 复杂度 | 高（需要 MDVRP 求解器） | 低（贪心算法） |
| 计算时间 | 5-10 秒 | < 0.5 秒 |
| 任务分配 | 重新分配 | 不重新分配 |
| 容量约束 | 需要考虑 | 不需要考虑 |
| 影响范围 | 全局（所有车辆） | 局部（受影响车辆） |
| 实用性 | 低 | 高 |

## 常见问题

**Q: 为什么不重新分配任务？**
A: 简化版专注于快速绕路，不涉及复杂的任务重分配。任务重分配需要考虑容量约束、时间窗等，会大幅增加计算时间。

**Q: 如果所有路径都被阻塞怎么办？**
A: 算法会选择距离最短的路径（即使经过阻塞路段）。实际应用中，应该提示用户无可行解。

**Q: 车辆位置如何确定？**
A: 前端在打开重规划对话框时随机选择每辆车在其路径上的一个客户作为当前位置。也可以手动指定。

**Q: 为什么成本会增加？**
A: 绕路通常会增加行驶距离，因此成本增加是正常的。重规划的目标是找到避开阻塞路段的最短路径。

## 参考资料

- [贪心算法](https://en.wikipedia.org/wiki/Greedy_algorithm)
- [最近邻算法](https://en.wikipedia.org/wiki/Nearest_neighbour_algorithm)
- [旅行商问题](https://en.wikipedia.org/wiki/Travelling_salesman_problem)
