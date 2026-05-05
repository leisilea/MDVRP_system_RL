# Cordeau MDVRP 数据格式规范

## ⚠️ 重要说明

本文档规范了Cordeau MDVRP实例的正确读取和使用方式，用于指导所有算法实现和基准测试代码。

---

## 📁 文件结构

```
MDVRP-Instances/
├── dat/          # 数据文件 (问题实例)
│   ├── p01       # 实例1-23: 标准MDVRP
│   ├── p02
│   ├── ...
│   ├── pr01      # 实例pr01-pr10: 带距离约束的MDVRP
│   └── ...
├── sol/          # 解文件 (最优解或最佳已知解)
│   ├── p01.res
│   ├── p02.res
│   └── ...
└── DESCRIPTION.md
```

---

## 📄 数据文件格式 (dat/)

### 第1行: 问题类型和规模

```
type m n t
```

- `type`: 问题类型
  - 0 = VRP
  - 1 = PVRP
  - **2 = MDVRP** (我们使用的类型)
  - 3 = SDVRP
  - 4 = VRPTW
  - 5 = PVRPTW
  - 6 = MDVRPTW
  - 7 = SDVRPTW
- `m`: 车辆数量
- `n`: 客户数量
- `t`: 仓库数量 (对于MDVRP)

**示例** (p01):
```
2 4 50 4
```
表示: MDVRP问题，4辆车，50个客户，4个仓库

### 第2行到第(t+1)行: 车辆约束

每个仓库/车辆类型一行:
```
D Q
```

- `D`: 最大路径距离 (maximum duration of a route)
  - **D = 0**: 无距离限制 (p系列)
  - **D > 0**: 有距离限制 (pr系列)
- `Q`: 车辆容量 (maximum load of a vehicle)

**示例** (p01):
```
0 80
0 80
0 80
0 80
```
表示: 4个仓库，每个仓库的车辆容量为80，无距离限制

### 第(t+2)行到第(n+t+1)行: 节点信息

**客户节点** (前n行):
```
i x y d q f a list e l
```

- `i`: 节点编号 (1到n)
- `x`, `y`: 坐标
- `d`: 服务时间 (service duration)
- `q`: 需求量 (demand)
- `f`: 访问频率 (对于PVRP，MDVRP中为1)
- `a`: 可能的访问组合数 (对于MDVRP通常为4)
- `list`: 访问组合列表 (对于MDVRP通常为"1 2 4 8")
- `e`: 时间窗开始 (对于VRPTW)
- `l`: 时间窗结束 (对于VRPTW)

**仓库节点** (最后t行):
```
i x y d q f a list e l
```

- `i`: 节点编号 (n+1到n+t)
- `x`, `y`: 坐标
- `d`: 0 (仓库无服务时间)
- `q`: 0 (仓库无需求)
- `f`, `a`, `list`, `e`, `l`: 0 (仓库无这些属性)

**示例** (p01的部分节点):
```
 1 37 52 0   7 1 4 1 2 4 8    # 客户1: 坐标(37,52), 需求7
 2 49 49 0  30 1 4 1 2 4 8    # 客户2: 坐标(49,49), 需求30
...
51 20 20 0   0 0 0            # 仓库1: 坐标(20,20)
52 30 40 0   0 0 0            # 仓库2: 坐标(30,40)
53 50 30 0   0 0 0            # 仓库3: 坐标(50,30)
54 60 50 0   0 0 0            # 仓库4: 坐标(60,50)
```

---

## 📄 解文件格式 (sol/)

### 第1行: 解的成本

```
cost
```

- `cost`: **总路径距离 (不包括服务时间)**
- 这是评估解质量的唯一标准
- **这就是Best Known Solution (BKS)**

**示例** (p01.res):
```
576.87
```
表示: 最优解的总距离为576.87

### 第2行及以后: 路径详情

每条路径一行:
```
l k d q list
```

- `l`: 仓库编号 (1到t)
- `k`: 车辆编号
- `d`: 路径距离 (duration of the route)
- `q`: 路径载重 (load of the vehicle)
- `list`: 客户访问序列 (0表示仓库)

**示例** (p01.res):
```
1   1   60.06   71   0 44 45 33 15 37 17 0 
1   2   66.55   79   0 42 19 40 41 13 0 
```
表示:
- 仓库1的车辆1: 距离60.06, 载重71, 路径: 仓库→44→45→33→15→37→17→仓库
- 仓库1的车辆2: 距离66.55, 载重79, 路径: 仓库→42→19→40→41→13→仓库

---

## 📊 Best Known Solutions (BKS)

### 如何获取BKS

**方法1: 从解文件读取** (推荐)
```python
def get_best_known_solution(instance_name):
    """从sol/目录读取最优解"""
    sol_path = f'MDVRP-Instances/sol/{instance_name}.res'
    with open(sol_path, 'r') as f:
        first_line = f.readline().strip()
        bks = float(first_line)
    return bks
```

**方法2: 硬编码** (仅当sol文件不可用时)
```python
BEST_KNOWN_SOLUTIONS = {
    'p01': 576.87,
    'p02': 473.53,
    'p03': 641.19,
    'p04': 1001.59,
    'p05': 750.03,
    'p06': 876.50,
    'p07': 885.80,
    'p08': 4420.95,  # 注意: 原文件为4420.9451
    # ... 其他实例
}
```

### BKS数据表 (p01-p08)

| Instance | Customers | Depots | Vehicles | Capacity | Max Distance | BKS |
|----------|-----------|--------|----------|----------|--------------|-----|
| p01 | 50 | 4 | 4 | 80 | 0 (无限制) | 576.87 |
| p02 | 50 | 4 | 2 | 160 | 0 (无限制) | 473.53 |
| p03 | 75 | 5 | 5 | 140 | 0 (无限制) | 641.19 |
| p04 | 100 | 2 | 8 | 100 | 0 (无限制) | 1001.59 |
| p05 | 100 | 2 | 4 | 200 | 0 (无限制) | 750.03 |
| p06 | 100 | 3 | 6 | 100 | 0 (无限制) | 876.50 |
| p07 | 100 | 4 | 4 | 100 | 0 (无限制) | 885.80 |
| **p08** | **249** | **2** | **14** | **500** | **310** ⚠️ | **4420.95** |

**⚠️ 重要**: p08是p系列中唯一有距离限制的实例！
- p01-p07: 无距离限制 (D=0)
- p08: 有距离限制 (D=310)
- pr系列 (pr01-pr10): 全部有距离限制

---

## ⚠️ 距离约束特别说明

### P系列实例的距离约束分布

Cordeau MDVRP实例在距离约束上有重要区别：

| 系列 | 实例 | 距离约束 | 说明 |
|------|------|----------|------|
| p系列 | p01-p07 | D=0 (无限制) | 只有容量约束 |
| p系列 | **p08** | **D=310** ⚠️ | **唯一有距离限制的p实例** |
| p系列 | p09-p23 | D=0 (无限制) | 只有容量约束 |
| pr系列 | pr01-pr10 | D>0 (有限制) | 同时有容量和距离约束 |

### 算法适用性

**只支持容量约束的算法**:
- ✅ 可以处理: p01-p07, p09-p23
- ❌ 不能处理: p08, pr01-pr10
- 需要明确说明算法不支持距离约束

**同时支持容量和距离约束的算法**:
- ✅ 可以处理: 所有p系列和pr系列
- 这是完整的MDVRP算法

### Benchmark建议

1. **基础测试**: 使用p01-p07 (无距离限制)
2. **完整测试**: 使用p01-p08 (包含距离约束)
3. **高级测试**: 使用pr系列 (全部有距离约束)

**注意**: 如果算法不支持距离约束，必须排除p08和pr系列，或明确说明结果可能不可行。

---

## 🔍 距离计算

### 欧几里得距离

所有Cordeau实例使用**欧几里得距离**:

```python
import math

def euclidean_distance(x1, y1, x2, y2):
    """计算两点之间的欧几里得距离"""
    return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)
```

### 路径成本计算

**总成本 = 所有路径的距离之和 (不包括服务时间)**

```python
def calculate_route_cost(route, nodes):
    """
    计算单条路径的成本
    
    Args:
        route: 路径 [depot_id, customer1, customer2, ..., depot_id]
        nodes: 所有节点的坐标字典
    
    Returns:
        cost: 路径距离
    """
    cost = 0.0
    for i in range(len(route) - 1):
        node1 = nodes[route[i]]
        node2 = nodes[route[i + 1]]
        cost += euclidean_distance(node1['x'], node1['y'], 
                                   node2['x'], node2['y'])
    return cost

def calculate_solution_cost(solution, nodes):
    """
    计算解的总成本
    
    Args:
        solution: 所有路径的列表
        nodes: 所有节点的坐标字典
    
    Returns:
        total_cost: 总距离
    """
    total_cost = 0.0
    for route in solution['routes']:
        total_cost += calculate_route_cost(route['path'], nodes)
    return total_cost
```

---

## ✅ 约束验证

### 必须满足的约束

1. **容量约束**: 每条路径的总需求 ≤ 车辆容量
   ```python
   route_demand = sum(nodes[customer]['demand'] for customer in route)
   assert route_demand <= vehicle_capacity
   ```

2. **距离约束** (仅pr系列): 每条路径的总距离 ≤ 最大距离
   ```python
   if max_distance > 0:  # pr系列
       route_distance = calculate_route_cost(route, nodes)
       assert route_distance <= max_distance
   ```

3. **客户访问**: 每个客户必须被访问恰好一次
   ```python
   visited_customers = set()
   for route in solution['routes']:
       for customer in route:
           assert customer not in visited_customers
           visited_customers.add(customer)
   assert len(visited_customers) == n_customers
   ```

4. **仓库约束**: 每条路径必须从某个仓库出发并返回同一仓库
   ```python
   for route in solution['routes']:
       assert route[0] == route[-1]  # 起点=终点
       assert route[0] in depot_ids   # 是仓库
   ```

---

## 📈 Gap计算

### 正确的Gap计算公式

```python
def calculate_gap(algorithm_cost, best_known_cost):
    """
    计算Gap百分比
    
    Args:
        algorithm_cost: 算法得到的解的成本
        best_known_cost: 最优解的成本 (从.res文件读取)
    
    Returns:
        gap_percent: Gap百分比
    """
    gap = ((algorithm_cost - best_known_cost) / best_known_cost) * 100
    return gap
```

**解释**:
- Gap > 0: 算法解比最优解差 (正常情况)
- Gap = 0: 算法找到了最优解
- Gap < 0: **错误!** 说明:
  - 算法计算的成本有误
  - BKS读取错误
  - 约束违反 (解不可行)

### Gap示例

```python
# 正确示例
bks = 576.87  # 从p01.res读取
algorithm_cost = 589.23
gap = (589.23 - 576.87) / 576.87 * 100 = 2.14%  # 正确

# 错误示例 (负Gap)
bks = 576.87
algorithm_cost = 550.00  # 比BKS还小!
gap = (550.00 - 576.87) / 576.87 * 100 = -4.66%  # 错误!
# 需要检查: 是否违反约束? 距离计算是否正确?
```

---

## 🚨 常见错误

### 错误1: 使用错误的BKS值

❌ **错误**: 硬编码错误的BKS值

✅ **正确**: 从sol/目录动态读取
```python
def load_best_known_solutions():
    """从sol/目录动态加载BKS"""
    bks = {}
    sol_dir = Path('MDVRP-Instances/sol')
    for sol_file in sol_dir.glob('*.res'):
        instance_name = sol_file.stem
        with open(sol_file, 'r') as f:
            cost = float(f.readline().strip())
            bks[instance_name] = cost
    return bks
```

**验证**: 运行 `verify_solution_calculation.py` 验证所有p01-p08实例的BKS计算

### 错误2: 包含服务时间

❌ **错误**:
```python
# 错误: 包含了服务时间
route_cost = 0
for i in range(len(route) - 1):
    route_cost += distance(route[i], route[i+1])
    route_cost += nodes[route[i]]['service_time']  # 错误!
```

✅ **正确**:
```python
# 正确: 只计算距离
route_cost = 0
for i in range(len(route) - 1):
    route_cost += distance(route[i], route[i+1])
# 不包括服务时间!
```

### 错误3: 节点编号混淆

❌ **错误**:
```python
# 错误: 客户编号从0开始
customers = list(range(0, n))  # [0, 1, 2, ..., n-1]
depots = list(range(n, n+t))   # [n, n+1, ..., n+t-1]
```

✅ **正确**:
```python
# 正确: 客户编号从1开始
customers = list(range(1, n+1))      # [1, 2, ..., n]
depots = list(range(n+1, n+t+1))     # [n+1, n+2, ..., n+t]
```

### 错误4: 距离计算精度

❌ **错误**:
```python
# 错误: 使用整数距离
distance = int(math.sqrt((x1-x2)**2 + (y1-y2)**2))
```

✅ **正确**:
```python
# 正确: 使用浮点数距离
distance = math.sqrt((x1-x2)**2 + (y1-y2)**2)
```

### 错误5: 仓库坐标错误

❌ **错误**:
```python
# 错误: 所有路径都使用同一个仓库坐标
depot_coord = depots[0]  # 总是使用第一个仓库
```

✅ **正确**:
```python
# 正确: 每条路径使用其所属仓库的坐标
depot_num = route['depot']  # 1, 2, 3, 或 4
depot_coord = depots[depot_num]  # 使用对应仓库的坐标
```

### ⚠️ 负Gap的真正原因

如果出现负Gap (算法成本 < BKS)，**只有以下可能**:

1. **约束违反**: 解不满足容量或距离约束
   - 检查: 运行约束验证函数
   
2. **距离计算错误**: 算法计算距离的方式与标准不同
   - 检查: 是否使用欧几里得距离
   - 检查: 是否包含了服务时间
   - 检查: 是否使用了错误的仓库坐标
   
3. **节点编号错误**: 客户/仓库编号混淆
   - 检查: 客户是否从1开始编号
   - 检查: 仓库是否从n+1开始编号
   
4. **BKS读取错误**: 读取了错误的BKS值
   - 检查: 运行 `test_bks_loading.py`
   - 检查: 运行 `verify_solution_calculation.py`

**重要**: 负Gap **不可能**是因为算法太好！BKS是经过多年研究得到的最优或接近最优解，新算法不太可能轻易超越。

---

## 📝 代码实现规范

### 1. 实例加载器

```python
class CordeauInstanceLoader:
    """Cordeau MDVRP实例加载器"""
    
    @staticmethod
    def load_instance(filepath: str) -> Dict:
        """加载实例"""
        with open(filepath, 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
        
        # 第1行: type m n t
        type_id, m, n, t = map(int, lines[0].split())
        
        # 第2到t+1行: D Q
        vehicles = []
        for i in range(1, t + 1):
            D, Q = map(float, lines[i].split())
            vehicles.append({
                'max_distance': D,
                'capacity': Q
            })
        
        # 第t+2到n+t+1行: 客户和仓库
        customers = []
        depots = []
        
        for i in range(t + 1, len(lines)):
            parts = lines[i].split()
            node_id = int(parts[0])
            x, y = float(parts[1]), float(parts[2])
            service_time = float(parts[3])
            demand = float(parts[4])
            
            node_info = {
                'id': node_id,
                'x': x,
                'y': y,
                'service_time': service_time,
                'demand': demand
            }
            
            # 最后t个节点是仓库
            if i >= len(lines) - t:
                depots.append(node_info)
            else:
                customers.append(node_info)
        
        return {
            'type': type_id,
            'n_vehicles': m,
            'n_customers': n,
            'n_depots': t,
            'vehicles': vehicles,
            'customers': customers,
            'depots': depots
        }
    
    @staticmethod
    def load_best_known_solution(instance_name: str) -> float:
        """从sol/目录加载BKS"""
        sol_path = f'MDVRP-Instances/sol/{instance_name}.res'
        with open(sol_path, 'r') as f:
            bks = float(f.readline().strip())
        return bks
```

### 2. 距离计算

```python
import math

def euclidean_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """计算欧几里得距离"""
    return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)

def calculate_route_distance(route: List[int], nodes: Dict) -> float:
    """计算路径距离 (不包括服务时间)"""
    distance = 0.0
    for i in range(len(route) - 1):
        node1 = nodes[route[i]]
        node2 = nodes[route[i + 1]]
        distance += euclidean_distance(
            node1['x'], node1['y'],
            node2['x'], node2['y']
        )
    return distance
```

### 3. 约束验证

```python
def validate_solution(solution: Dict, instance: Dict) -> Tuple[bool, str]:
    """验证解的可行性"""
    
    # 1. 检查客户访问
    visited = set()
    for route in solution['routes']:
        for customer in route['customers']:
            if customer in visited:
                return False, f"客户{customer}被访问多次"
            visited.add(customer)
    
    if len(visited) != instance['n_customers']:
        return False, f"未访问所有客户: {len(visited)}/{instance['n_customers']}"
    
    # 2. 检查容量约束
    for route in solution['routes']:
        demand = sum(instance['customers'][c-1]['demand'] 
                    for c in route['customers'])
        capacity = instance['vehicles'][route['depot']-1]['capacity']
        if demand > capacity:
            return False, f"路径{route['id']}超载: {demand} > {capacity}"
    
    # 3. 检查距离约束 (如果有)
    for route in solution['routes']:
        max_dist = instance['vehicles'][route['depot']-1]['max_distance']
        if max_dist > 0:  # 有距离限制
            if route['distance'] > max_dist:
                return False, f"路径{route['id']}超距: {route['distance']} > {max_dist}"
    
    return True, "解可行"
```

### 4. Gap计算

```python
def calculate_gap(algorithm_cost: float, best_known_cost: float) -> float:
    """计算Gap百分比"""
    if best_known_cost == 0:
        return float('inf')
    gap = ((algorithm_cost - best_known_cost) / best_known_cost) * 100
    return gap

def report_results(instance_name: str, algorithm_cost: float, bks: float):
    """报告结果"""
    gap = calculate_gap(algorithm_cost, bks)
    
    print(f"实例: {instance_name}")
    print(f"  BKS: {bks:.2f}")
    print(f"  算法成本: {algorithm_cost:.2f}")
    print(f"  Gap: {gap:.2f}%")
    
    if gap < 0:
        print(f"  ⚠️ 警告: 负Gap! 请检查:")
        print(f"     - 约束是否满足?")
        print(f"     - 距离计算是否正确?")
        print(f"     - BKS是否正确?")
```

---

## 📚 参考文献

1. Cordeau, J., Gendreau, M., Laporte, G. (1997). A tabu search heuristic for periodic and multi-depot vehicle routing problems. Networks 30(2), 105–119.

2. Vidal, T., Crainic, T., Gendreau, M., Lahrichi, N., Rei, W. (2012). A hybrid genetic algorithm for multi-depot and periodic vehicle routing problems. Operations Research 60(3), 611–624.

3. NEO Research Group: http://neo.lcc.uma.es/vrp/vrp-instances/

---

## ✅ 检查清单

在实现算法或运行基准测试前，请确认:

- [ ] BKS从sol/目录的.res文件读取
- [ ] 距离使用欧几里得距离计算
- [ ] 成本不包括服务时间
- [ ] 客户编号从1开始 (不是0)
- [ ] 仓库编号从n+1开始
- [ ] 容量约束已验证
- [ ] 距离约束已验证 (pr系列)
- [ ] 所有客户被访问恰好一次
- [ ] Gap计算公式正确
- [ ] 负Gap时会发出警告

---

**创建时间**: 2026-03-31  
**版本**: v1.0  
**维护**: MDVRP项目团队
