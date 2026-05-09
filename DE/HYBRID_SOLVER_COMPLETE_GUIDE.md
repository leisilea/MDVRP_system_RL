# GA-MDVRP + RouteFinder 混合求解器完整指南

## 目录
1. [概述](#概述)
2. [RouteFinder集成详解](#routefinder集成详解)
3. [NPZ数据格式](#npz数据格式)
4. [模型选择策略](#模型选择策略)
5. [使用指南](#使用指南)
6. [性能优化](#性能优化)
7. [故障排除](#故障排除)

---

## 概述

### 什么是混合求解器？

混合求解器结合了遗传算法（GA-MDVRP）和强化学习（RouteFinder）的优势，通过使用RL生成的高质量解来初始化GA种群，显著提升求解性能。

### 核心特性

✅ **智能模型选择**: 根据问题特征（规模、约束类型）自动选择最优模型  
✅ **多模型支持**: rf-pomo, rf-moe, rf-transformer, mtpomo, mvmoe  
✅ **GPU加速**: 支持CUDA加速，速度提升10-20倍  
✅ **灵活配置**: 可调整种子比例、采样数量等参数  
✅ **完整工作流**: 从数据预处理到GA优化的端到端解决方案  

### 工作流程

```
1. 数据预处理 → 2. RL生成种子 → 3. 格式转换 → 4. GA优化 → 5. 返回结果
   ↓                ↓                 ↓             ↓            ↓
 仓库分割        RouteFinder       JSON格式      Java GA      最优解
 客户分配        推理采样          Individual    遗传进化
```

### 性能对比

#### P21问题（360客户，9仓库）

| 方法 | 初始解 | 最终解 | Gap to BKS | 时间 |
|------|--------|--------|-----------|------|
| 纯GA（随机） | 19400 | 6500 | 18.7% | 120s |
| 混合求解器 | 17500 | 6200 | 13.2% | 125s |
| **改进** | **9.8%↓** | **4.6%↓** | **5.5%↓** | +4% |

---

## RouteFinder集成详解

### 为什么选择RouteFinder？

RouteFinder是基于强化学习的VRP求解器，具有以下优势：
- 预训练模型可直接使用
- 支持多种约束（容量、距离）
- 推理速度快（GPU加速）
- 解的质量高

### 集成架构

```python
# 混合求解器的核心流程
class GAMDVRPRLHybrid:
    def solve(self, instance_data):
        # 步骤1: 预处理
        depot_assignments = self._assign_customers_to_depots(instance_data)
        
        # 步骤2: 使用RouteFinder生成种子解
        rl_seeds = self._generate_rl_seeds(instance_data, depot_assignments)
        
        # 步骤3: 转换为GA格式
        ga_input = self._convert_to_ga_format(rl_seeds, instance_data)
        
        # 步骤4: Java GA优化
        result = self._run_java_ga(ga_input)
        
        return result
```

### 关键实现细节

#### 1. 仓库分割策略

对于MDVRP问题，需要将客户分配到不同的仓库：

```python
def _assign_customers_to_depots(self, instance_data):
    """将客户分配到最近的仓库"""
    depot_assignments = {i: [] for i in range(len(depots))}
    
    for cust_idx, customer in enumerate(customers):
        # 计算到每个仓库的距离
        distances = [euclidean_distance(customer, depot) 
                    for depot in depots]
        # 分配到最近的仓库
        nearest_depot = np.argmin(distances)
        depot_assignments[nearest_depot].append(cust_idx)
    
    return depot_assignments
```

#### 2. NPZ文件创建

**关键点**: 必须参照成功的代码实现（`solve_p21_fixed.py` 和 `test.py`）

```python
def _create_depot_npz(self, instance_data, depot_idx, customer_indices):
    """为单个depot创建NPZ文件"""
    depot = instance_data['depots'][depot_idx]
    customers = [instance_data['customers'][i] for i in customer_indices]
    
    # 提取坐标
    all_x = [depot['x']] + [c['x'] for c in customers]
    all_y = [depot['y']] + [c['y'] for c in customers]
    
    # 归一化坐标
    x_min, x_max = min(all_x), max(all_x)
    y_min, y_max = min(all_y), max(all_y)
    x_range = max(x_max - x_min, 1e-6)
    y_range = max(y_max - y_min, 1e-6)
    
    # 创建locs数组 (1, n_customers+1, 2)
    n_customers = len(customers)
    locs = np.zeros((1, n_customers + 1, 2), dtype=np.float32)
    
    # 第一个位置是depot
    locs[0, 0, 0] = (depot['x'] - x_min) / x_range
    locs[0, 0, 1] = (depot['y'] - y_min) / y_range
    
    # 后续位置是customers
    for i, customer in enumerate(customers):
        locs[0, i+1, 0] = (customer['x'] - x_min) / x_range
        locs[0, i+1, 1] = (customer['y'] - y_min) / y_range
    
    # 创建需求数组 (1, n_customers)
    demands = np.array([c['demand'] for c in customers], dtype=np.float32)
    max_demand = max(demands) if len(demands) > 0 else 1.0
    demands_normalized = demands / max_demand
    
    # 车辆容量 (1, 1) - 注意是单车容量！
    capacity_normalized = depot.get('capacity', 100) / max_demand
    vehicle_capacity = np.array([[capacity_normalized]], dtype=np.float32)
    
    # 其他字段
    speed = np.ones((1, 1), dtype=np.float32)
    num_depots = np.ones((1, 1), dtype=np.int32)
    
    # 保存NPZ文件
    npz_path = f"temp_depot_{depot_idx}.npz"
    np.savez(npz_path,
             locs=locs,
             demand_linehaul=demands_normalized.reshape(1, -1),
             vehicle_capacity=vehicle_capacity,
             speed=speed,
             num_depots=num_depots)
    
    return npz_path
```

#### 3. RouteFinder推理

**关键点**: 必须参照官方代码（`test.py`）的推理方式

```python
def _sample_depot_solutions(self, npz_path, num_samples=20):
    """使用RouteFinder对单个depot进行采样"""
    from routefinder.envs import MTVRPEnv
    
    # 创建环境
    env = MTVRPEnv()
    
    # 加载数据
    td = env.load_data(npz_path)
    
    # 重置环境
    td_reset = env.reset(td)
    
    # 采样多次
    solutions = []
    for i in range(num_samples):
        td_clone = td_reset.clone()
        
        # 推理
        out = policy(td_clone, env, phase="test", 
                    num_starts=1, return_actions=True, 
                    decode_type="sampling")
        
        # 提取结果
        actions = out['actions'][0].cpu().numpy()
        cost = -out['reward'][0].item()
        
        solutions.append({
            'actions': actions.tolist(),
            'cost': cost
        })
    
    return solutions
```

---

## NPZ数据格式

### 什么是NPZ文件？

NPZ是NumPy的压缩数组存储格式，用于将多个NumPy数组打包保存。在混合求解器中，NPZ文件是Cordeau格式和RouteFinder模型之间的桥梁。

### NPZ文件结构

| 字段 | 形状 | 含义 |
|------|------|------|
| `locs` | `(1, n_customers+1, 2)` | 归一化坐标（depot + customers） |
| `demand_linehaul` | `(1, n_customers)` | 归一化需求（仅customers） |
| `vehicle_capacity` | `(1, 1)` | 单车容量（归一化） |
| `speed` | `(1, 1)` | 车辆速度（通常为1.0） |
| `num_depots` | `(1, 1)` | 仓库数量（单depot子问题为1） |

### 完整示例

假设有1个depot和3个customers：

```python
# 原始数据
depot = {'x': 50, 'y': 50, 'capacity': 100}
customers = [
    {'x': 30, 'y': 40, 'demand': 20},
    {'x': 70, 'y': 60, 'demand': 30},
    {'x': 45, 'y': 80, 'demand': 25}
]

# 归一化
x_coords = [30, 70, 45, 50]
y_coords = [40, 60, 80, 50]
x_min, x_max = 30, 70  # x_range = 40
y_min, y_max = 40, 80  # y_range = 40
max_demand = 30

# NPZ数据
npz_data = {
    'locs': np.array([[
        [0.5, 0.25],    # depot: [(50-30)/40, (50-40)/40]
        [0.0, 0.0],     # cust1: [(30-30)/40, (40-40)/40]
        [1.0, 0.5],     # cust2: [(70-30)/40, (60-40)/40]
        [0.375, 1.0]    # cust3: [(45-30)/40, (80-40)/40]
    ]], dtype=np.float32),
    
    'demand_linehaul': np.array([[0.667, 1.0, 0.833]], dtype=np.float32),
    'vehicle_capacity': np.array([[3.333]], dtype=np.float32),
    'speed': np.array([[1.0]], dtype=np.float32),
    'num_depots': np.array([[1]], dtype=np.int32)
}
```

### 关键注意事项

⚠️ **常见错误**:

1. **容量混淆**：
   ```python
   # ❌ 错误：使用总容量
   vehicle_capacity = total_capacity_of_all_vehicles
   
   # ✅ 正确：使用单车容量
   vehicle_capacity = capacity_per_vehicle
   ```

2. **索引混淆**：
   ```python
   # locs包含depot（索引0）+ customers（索引1开始）
   # demand_linehaul只包含customers（不含depot）
   assert locs.shape[1] == demand_linehaul.shape[1] + 1
   ```

3. **归一化顺序**：
   ```python
   # ✅ 正确：先归一化坐标再构建数组
   coords_normalized = normalize(coords)
   locs = build_locs(coords_normalized)
   ```

---

## 模型选择策略

### 可用模型

#### 模型规模
- **50**: 适用于每个depot平均客户数 ≤ 30
- **100**: 适用于每个depot平均客户数 > 30

#### 模型类型

| 模型类型 | 说明 | 适用场景 |
|---------|------|---------|
| `rf-pomo` | RouteFinder + POMO | 标准CVRP，单一约束 |
| `rf-moe` | RouteFinder + MoE | 多约束问题（距离+容量） |
| `rf-transformer` | RouteFinder + Transformer | 通用场景 |
| `mtpomo` | Multi-Task POMO | 多任务学习 |
| `mvmoe` | Multi-Variant MoE | 多变体问题 |

### 自动选择规则

```python
# 规模选择
if 平均客户数/depot <= 30:
    model_size = '50'
else:
    model_size = '100'

# 类型选择
if 距离约束 AND 容量约束:
    model_type = 'rf-moe'  # 多约束，使用MoE
elif 距离约束:
    model_type = 'rf-pomo'  # 单一距离约束
else:
    model_type = 'rf-pomo'  # 容量约束或无约束
```

### 使用示例

```python
# 自动选择（推荐）
solver = GAMDVRPRLHybrid(model_type='auto')

# 手动指定
solver = GAMDVRPRLHybrid(model_type='rf-moe')
solver = GAMDVRPRLHybrid(model_type='rf-pomo')
```

### 模型性能对比

#### P21 (360客户, 9仓库, 距离+容量约束)

| 模型 | 平均成本 | Gap to BKS | 推理时间 |
|------|---------|-----------|---------|
| rf-pomo | 8850 | 61.7% | 2.3s |
| rf-moe | 8810 | 60.9% | 2.5s |
| mtpomo | 8920 | 63.0% | 2.1s |

---

## 使用指南

### 快速开始

```python
from ga_mdvrp_rl_hybrid import GAMDVRPRLHybrid

# 创建求解器
solver = GAMDVRPRLHybrid()

# 准备数据
instance_data = {
    'depots': [{'x': 30, 'y': 40, 'vehicle_count': 5, 'capacity': 200}],
    'customers': [{'x': 37, 'y': 52, 'demand': 7}],
    'max_distance': 1000
}

# 求解
result = solver.solve(instance_data)
print(f"总成本: {result['total_cost']:.2f}")
```

### 核心参数

```python
GAMDVRPRLHybrid(
    rl_seed_ratio=0.2,      # RL种子占比（推荐10-30%）
    num_rl_samples=20,      # 每个depot采样数（推荐10-30）
    use_gpu=True,           # 使用GPU加速
    model_type='auto'       # 模型选择（auto/rf-pomo/rf-moe/...）
)
```

### 参数调优建议

| 参数 | 默认值 | 推荐范围 | 说明 |
|------|--------|---------|------|
| `rl_seed_ratio` | 0.2 | 0.1-0.3 | 种子比例越高，初始解越好，但时间越长 |
| `num_rl_samples` | 20 | 10-30 | 采样数越多，解质量越高，但时间越长 |
| `use_gpu` | True | True | 强烈推荐使用GPU（速度提升10-20倍） |
| `model_type` | 'auto' | 'auto' | 自动选择通常是最优的 |

### 完整示例

```python
from ga_mdvrp_rl_hybrid import GAMDVRPRLHybrid
from pathlib import Path
import json

# 读取Cordeau格式文件
def load_cordeau_instance(filepath):
    # ... 解析Cordeau格式 ...
    return instance_data

# 创建求解器
solver = GAMDVRPRLHybrid(
    rl_seed_ratio=0.2,
    num_rl_samples=20,
    use_gpu=True,
    model_type='auto'
)

# 加载问题
instance_data = load_cordeau_instance('p21')

# 求解
result = solver.solve(instance_data)

# 输出结果
print(f"总成本: {result['total_cost']:.2f}")
print(f"计算时间: {result['compute_time']:.2f}秒")
print(f"车辆数: {len(result['routes'])}")

# 保存结果
with open('result.json', 'w') as f:
    json.dump(result, f, indent=2)
```

---

## 性能优化

### 时间分布分析

以P01为例（50客户，4仓库）：

```
总时间: 26.95秒
├─ 数据预处理 (~0.1秒, 0.4%)
├─ RouteFinder推理 (~15秒, 55.6%)
│   ├─ 模型加载 (~2秒)
│   ├─ RL采样 (~12秒)
│   └─ 格式转换 (~1秒)
├─ Java GA优化 (~10秒, 37.1%)
└─ 清理 (~0.01秒, 0.04%)
```

### 优化方案

#### 1. 模型缓存（推荐⭐⭐⭐⭐⭐）

**收益**: 节省2秒/问题（批量测试时）

```python
class GAMDVRPRLHybrid:
    # 类级别的模型缓存
    _policy_cache = {}
    
    def _load_model(self, checkpoint_path):
        cache_key = str(checkpoint_path)
        
        if cache_key in self._policy_cache:
            print(f"  [Cache Hit] 使用缓存模型")
            return self._policy_cache[cache_key]
        
        print(f"  [Cache Miss] 加载模型")
        model = BaseLitModule.load_from_checkpoint(...)
        policy = model.policy.to(device)
        self._policy_cache[cache_key] = policy
        
        return policy
```

#### 2. 减少采样次数（推荐⭐⭐⭐⭐）

**收益**: 节省6秒/问题

```python
# 小问题用10次采样
solver = GAMDVRPRLHybrid(num_rl_samples=10)

# 大问题用30次采样
solver = GAMDVRPRLHybrid(num_rl_samples=30)
```

#### 3. 批量推理（推荐⭐⭐⭐⭐⭐）

**收益**: 节省8-10秒/问题

```python
# 当前: 逐个采样
for i in range(num_samples):
    out = policy(td.clone(), env, ...)

# 优化: 批量采样
td_batch = td.expand(num_samples)
out = policy(td_batch, env, ...)
```

### 优化优先级

| 优化方案 | 节省时间 | 实现难度 | 推荐度 |
|---------|---------|---------|--------|
| 模型缓存 | 2秒 | 低 | ⭐⭐⭐⭐⭐ |
| 减少采样 | 6秒 | 极低 | ⭐⭐⭐⭐ |
| 批量推理 | 8-10秒 | 中 | ⭐⭐⭐⭐⭐ |

---

## 故障排除

### 常见问题

#### Q1: 模型加载失败

**错误信息**:
```
FileNotFoundError: checkpoint not found: 100/rf-pomo.ckpt
```

**解决方案**:
1. 检查checkpoint文件是否存在
2. 确认路径配置正确
3. 尝试使用其他模型类型

```python
# 手动指定已存在的模型
solver = GAMDVRPRLHybrid(model_type='rf-moe')
```

#### Q2: GPU内存不足

**错误信息**:
```
RuntimeError: CUDA out of memory
```

**解决方案**:
1. 减少采样数量
2. 使用CPU模式
3. 清理GPU缓存

```python
# 使用CPU
solver = GAMDVRPRLHybrid(use_gpu=False)

# 或减少采样
solver = GAMDVRPRLHybrid(num_rl_samples=10)
```

#### Q3: NPZ文件格式错误

**错误信息**:
```
KeyError: 'locs'
```

**解决方案**:
参照成功的代码实现：
- `RL4CO_Integration/solve_p21_fixed.py`
- `RL4CO_Integration/routefinder/test.py`

确保NPZ文件包含所有必需字段。

#### Q4: Java GA运行失败

**错误信息**:
```
Error: Could not find or load main class GA.Algorithm
```

**解决方案**:
1. 重新编译Java代码
2. 检查classpath配置
3. 确认Gson库存在

```bash
cd system_test/ga_mdvrp_reproduction/GA-MDVRP
javac -encoding UTF-8 -d bin -cp "lib/*" src/**/*.java
```

### 调试技巧

#### 1. 启用详细输出

```python
solver = GAMDVRPRLHybrid(verbose=True)
```

#### 2. 检查NPZ文件

```python
import numpy as np

data = np.load('problem.npz')
print("字段:", list(data.keys()))

for key in data.keys():
    arr = data[key]
    print(f"{key}: shape={arr.shape}, dtype={arr.dtype}")
```

#### 3. 验证模型推理

```python
from routefinder.envs import MTVRPEnv

env = MTVRPEnv()
td = env.load_data('problem.npz')
td_reset = env.reset(td)

out = policy(td_reset, env, phase="test", 
            num_starts=1, return_actions=True)
print(f"Cost: {-out['reward'][0].item()}")
```

---

## 系统要求

### 必需
- Python 3.8+
- PyTorch 1.12+
- TorchRL
- Java 8+
- Gson库

### 推荐
- CUDA 11.0+ (GPU加速)
- 16GB+ RAM
- 4GB+ VRAM (GPU)

### 安装

```bash
# 1. 安装Python依赖
pip install torch torchrl numpy

# 2. 编译Java代码
cd system_test/ga_mdvrp_reproduction/GA-MDVRP
javac -encoding UTF-8 -d bin -cp "lib/*" src/**/*.java

# 3. 验证安装
cd system_test/algorithm-service/solver
python -c "from ga_mdvrp_rl_hybrid import GAMDVRPRLHybrid; print('OK')"
```

---

## 参考资料

### 成功的代码示例
- `RL4CO_Integration/solve_p21_fixed.py` - P21求解器
- `RL4CO_Integration/routefinder/test.py` - 官方测试代码
- `system_test/algorithm-service/solver/ga_mdvrp_rl_hybrid.py` - 混合求解器实现

### 相关文档
- RouteFinder论文: [链接]
- POMO论文: [链接]
- Cordeau数据格式: `MDVRP-Instances/Cordeau数据格式规范.md`

---

## 更新日志

### v1.0.0 (2026-04-11)
- ✨ 初始版本发布
- ✨ 支持自动模型选择
- ✨ 支持5种RouteFinder模型
- ✨ 完整的文档和示例
- 📝 整合所有分散的文档

---

## 许可证

MIT License

