# 需求文档：道路阻塞动态重规划

## 简介

在MDVRP（多仓库车辆路径问题）求解过程中，当某些道路因突发事件被阻塞时，需要对现有路径进行动态重规划。本功能通过将车辆当前位置转换为临时仓库，并使用修改后的距离矩阵重新求解未完成的配送任务，实现快速的路径调整。

## 术语表

- **MDVRP_Solver**: 多仓库车辆路径问题求解器，支持PSO、ACO、GA、GA-MP、GA-RL等算法
- **Distance_Matrix**: 距离矩阵，存储所有节点（仓库和客户）之间的距离
- **Route**: 路径，表示一辆车从仓库出发，依次访问客户，最后返回仓库的完整路线
- **Blocked_Edge**: 阻塞路段，由两个节点（起点和终点）定义的不可通行道路
- **Vehicle_Position**: 车辆位置，表示车辆当前停留的客户节点
- **Temporary_Depot**: 临时仓库，由车辆当前位置转换而来的虚拟仓库
- **Remaining_Capacity**: 剩余容量，车辆初始容量减去已服务客户需求的总和
- **Served_Customer**: 已服务客户，车辆当前位置之前已访问的客户
- **Unserved_Customer**: 未服务客户，车辆当前位置之后尚未访问的客户
- **Replanning_API**: 重规划API端点，接收阻塞信息并返回新路径的服务接口
- **Cost_Comparison**: 成本对比，重规划前后的总路径成本差异

## 需求

### 需求 1: 道路阻塞输入

**用户故事:** 作为调度员，我希望能够指定被阻塞的路段，以便系统在重规划时避开这些道路。

#### 验收标准

1. THE Replanning_API SHALL接受一个阻塞路段列表作为输入参数
2. WHEN一个阻塞路段被指定时，THE Distance_Matrix SHALL将该路段的距离设置为1000000（表示不可通行）
3. THE Replanning_API SHALL验证每个阻塞路段由两个有效的节点标识符组成
4. WHEN阻塞路段列表为空时，THE Replanning_API SHALL使用原始距离矩阵进行重规划

### 需求 2: 车辆状态快照

**用户故事:** 作为调度员，我希望系统能够识别每辆车的当前状态，以便从实际位置开始重规划。

#### 验收标准

1. THE Replanning_API SHALL接受当前解决方案（routes）作为输入参数
2. WHEN用户提供车辆位置时，THE Replanning_API SHALL使用指定的位置作为每辆车的当前位置
3. WHEN用户未提供车辆位置时，THE Replanning_API SHALL为每辆车随机选择其路径上的一个客户位置
4. THE Replanning_API SHALL计算每辆车的已服务客户列表（当前位置之前的所有客户）
5. THE Replanning_API SHALL计算每辆车的未服务客户列表（当前位置之后的所有客户）
6. THE Replanning_API SHALL计算每辆车的剩余容量为初始容量减去已服务客户需求总和
7. WHEN车辆剩余容量计算结果为负数时，THE Replanning_API SHALL返回错误信息

### 需求 3: 临时仓库转换

**用户故事:** 作为系统设计者，我希望将车辆当前位置转换为临时仓库，以便使用现有求解器进行重规划。

#### 验收标准

1. WHEN车辆当前位置不在原始仓库时，THE Replanning_API SHALL创建一个临时仓库
2. THE Temporary_Depot SHALL使用车辆当前所在客户的坐标作为其坐标
3. THE Temporary_Depot SHALL使用车辆的剩余容量作为其容量限制
4. THE Temporary_Depot SHALL配置为拥有1辆车辆
5. WHEN车辆当前位置在原始仓库时，THE Replanning_API SHALL保留该原始仓库配置
6. THE Replanning_API SHALL构建包含所有临时仓库和仍在使用的原始仓库的仓库列表

### 需求 4: 重新求解

**用户故事:** 作为调度员，我希望系统使用修改后的问题配置重新求解路径，以便获得避开阻塞路段的新方案。

#### 验收标准

1. THE Replanning_API SHALL使用修改后的距离矩阵调用MDVRP_Solver
2. THE Replanning_API SHALL使用临时仓库列表作为仓库配置
3. THE Replanning_API SHALL使用未服务客户列表作为客户集合
4. THE Replanning_API SHALL接受算法选择参数（PSO、ACO、GA、GA-MP、GA-RL）
5. THE Replanning_API SHALL将用户指定的算法传递给MDVRP_Solver
6. WHEN未服务客户列表为空时，THE Replanning_API SHALL返回空路径列表而不调用求解器

### 需求 5: 结果输出

**用户故事:** 作为调度员，我希望查看重规划结果和成本变化，以便评估新方案的质量。

#### 验收标准

1. THE Replanning_API SHALL返回新的路径规划结果
2. THE Replanning_API SHALL标识哪些路径是重规划生成的
3. THE Replanning_API SHALL计算重规划前的总成本（基于原始路径和修改后的距离矩阵）
4. THE Replanning_API SHALL计算重规划后的总成本
5. THE Replanning_API SHALL返回成本对比信息（包含重规划前成本、重规划后成本和差异）
6. THE Replanning_API SHALL在响应中包含使用的算法名称和求解时间

### 需求 6: 容量约束验证

**用户故事:** 作为系统设计者，我希望确保重规划结果满足容量约束，以便保证方案的可行性。

#### 验收标准

1. THE MDVRP_Solver SHALL确保每辆车分配的未服务客户需求总和不超过其剩余容量
2. WHEN求解器无法找到满足容量约束的解时，THE Replanning_API SHALL返回错误信息
3. THE Replanning_API SHALL在返回结果前验证每条路径的容量约束
4. WHEN验证发现容量约束违反时，THE Replanning_API SHALL返回错误信息并包含违反约束的路径标识

### 需求 7: 阻塞路段验证

**用户故事:** 作为调度员，我希望确保新路径不包含阻塞路段，以便车辆能够实际执行规划。

#### 验收标准

1. THE Replanning_API SHALL在返回结果前验证新路径不包含任何阻塞路段
2. WHEN验证发现路径包含阻塞路段时，THE Replanning_API SHALL返回错误信息
3. THE Replanning_API SHALL在错误信息中标识包含阻塞路段的具体路径和路段位置

### 需求 8: 多次重规划支持

**用户故事:** 作为调度员，我希望能够在重规划结果上再次进行重规划，以便应对连续发生的道路阻塞事件。

#### 验收标准

1. THE Replanning_API SHALL接受之前重规划的结果作为当前解决方案输入
2. THE Replanning_API SHALL累积所有历史阻塞路段到距离矩阵修改中
3. THE Replanning_API SHALL支持在同一会话中多次调用重规划功能
4. THE Replanning_API SHALL在每次重规划时保持距离矩阵修改的一致性

### 需求 9: API接口设计

**用户故事:** 作为前端开发者，我希望有清晰的API接口，以便集成重规划功能到用户界面。

#### 验收标准

1. THE Replanning_API SHALL提供POST端点 /api/replan
2. THE Replanning_API SHALL接受JSON格式的请求体，包含depots、customers、routes、blocked_edges、vehicle_positions（可选）和algorithm字段
3. THE Replanning_API SHALL返回JSON格式的响应，包含new_routes、replanned_route_ids、cost_before、cost_after、cost_difference、algorithm和solve_time字段
4. WHEN请求参数缺失或格式错误时，THE Replanning_API SHALL返回HTTP 400状态码和错误描述
5. WHEN求解过程发生错误时，THE Replanning_API SHALL返回HTTP 500状态码和错误描述
6. WHEN重规划成功时，THE Replanning_API SHALL返回HTTP 200状态码

### 需求 10: 前端集成

**用户故事:** 作为用户，我希望在界面上直观地选择阻塞路段并查看重规划结果，以便快速响应道路变化。

#### 验收标准

1. THE前端界面 SHALL在算法计算页面提供"重规划"功能入口按钮
2. WHEN用户点击重规划按钮时，THE前端界面 SHALL允许用户在地图上点击选择阻塞路段
3. THE前端界面 SHALL在地图上以不同颜色显示重规划前的路径和重规划后的路径
4. THE前端界面 SHALL显示成本变化信息（重规划前、重规划后、差异和百分比变化）
5. THE前端界面 SHALL显示重规划使用的算法和求解时间
6. THE前端界面 SHALL允许用户在重规划结果上继续进行新的重规划操作

### 需求 11: 距离矩阵高效修改

**用户故事:** 作为系统设计者，我希望距离矩阵修改操作高效执行，以便快速响应重规划请求。

#### 验收标准

1. THE Replanning_API SHALL仅修改阻塞路段对应的距离矩阵元素，而不重新计算整个矩阵
2. THE Replanning_API SHALL对每个阻塞路段执行O(1)时间复杂度的矩阵修改操作
3. WHEN阻塞路段数量为N时，THE Replanning_API SHALL在O(N)时间内完成距离矩阵修改
4. THE Replanning_API SHALL保持原始距离矩阵不变，使用副本进行修改

### 需求 12: 算法兼容性

**用户故事:** 作为系统维护者，我希望重规划功能兼容所有现有算法，以便用户可以选择最适合的求解方法。

#### 验收标准

1. THE Replanning_API SHALL支持PSO算法进行重规划
2. THE Replanning_API SHALL支持ACO算法进行重规划
3. THE Replanning_API SHALL支持GA算法进行重规划
4. THE Replanning_API SHALL支持GA-MP算法进行重规划
5. THE Replanning_API SHALL支持GA-RL算法进行重规划
6. WHEN用户指定不支持的算法时，THE Replanning_API SHALL返回错误信息并列出支持的算法列表
