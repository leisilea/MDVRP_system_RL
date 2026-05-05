# RouteFinder 成功使用指南

## 概述

本文档记录了成功使用RouteFinder预训练模型求解CVRP和MDVRP问题的完整流程。

## 环境配置

### 系统要求
- Python 3.9+
- CUDA 11.8+ (GPU加速)
- Windows/Linux

### 依赖安装
```bash
conda create -n GD python=3.9
conda activate GD
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install tensordict torchrl
pip install rl4co lightning scikit-learn
```

## 关键问题与解决方案

### 1. TorchRL API兼容性问题

**问题**: RouteFinder使用旧版TorchRL API，新版本中类名已更改
- `CompositeSpec` → `Composite`
- `BoundedTensorSpec` → `Bounded`
- `UnboundedContinuousTensorSpec` → `UnboundedContinuous`
- `UnboundedDiscreteTensorSpec` → `UnboundedDiscrete`

**解决方案**: 在加载checkpoint前添加名称映射
```python
import torchrl.data.tensor_specs as specs
if not hasattr(specs, 'CompositeSpec'):
    specs.CompositeSpec = specs.Composite
if not hasattr(specs, 'BoundedTensorSpec'):
    specs.BoundedTensorSpec = specs.Bounded
if not hasattr(specs, 'UnboundedContinuousTensorSpec'):
    specs.UnboundedContinuousTensorSpec = specs.UnboundedContinuous
if not hasattr(specs, 'UnboundedDiscreteTensorSpec'):
    specs.UnboundedDiscreteTensorSpec = specs.UnboundedDiscrete
```

### 2. MTVRPEnv reset方法的副作用

**问题**: `env.reset(td)` 会修改传入的TensorDict对象，在循环采样时导致维度错误
- 第1次reset: `demand_linehaul` 从 `[1, 40]` 变为 `[1, 41]` ✓
- 第2次reset: 从 `[1, 41]` 变为 `[1, 42]` ✗ (错误!)

**解决方案**: 每次采样前克隆原始TensorDict
```python
td_original = env.load_data(npz_path).to(device)

for i in range(num_samples):
    td = td_original.clone()  # 关键：每次都从原始数据克隆
    td_reset = env.reset(td)
    out = policy(td_reset, env, phase="test", decode_type="sampling")
```

### 3. Windows GBK编码问题

**问题**: Windows默认GBK编码无法显示emoji表情符号

**解决方案**: 使用纯ASCII字符替代emoji
```python
# 错误: print(f"📊 处理中...")
# 正确: print(f"Processing...")
```

## CVRP求解示例

### 测试官方模型
```bash
cd RL4CO_Integration/routefinder
python test.py --checkpoint checkpoints/100/rf-transformer.ckpt \
               --datasets data/cvrp/test/100.npz \
               --batch_size 10 \
               --device cuda
```

### 性能指标
- 数据集: CVRP-100 (100个客户)
- 测试实例: 10个
- 平均成本: 16.287
- 与BKS的Gap: 4.2%
- 推理时间: 1.39秒 (0.14秒/实例)
- 设备: RTX 3060 GPU

## MDVRP求解示例 (P21数据集)

### 问题描述
- P21数据集: 360个客户，9个depot
- 每个depot容量: 60
- 目标: 使用K-Means分割 + RouteFinder采样求解

### 完整代码: `solve_p21_simple.py`

```python
"""
P21 MDVRP求解器
使用K-Means分割 + RouteFinder采样
"""
import os
import sys
import json
import time
import torch
import numpy as np
from pathlib import Path
from sklearn.cluster import KMeans
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent / "routefinder"))

from routefinder.envs import MTVRPEnv
from routefinder.models import RouteFinderBase

# TorchRL兼容性修复
import torchrl.data.tensor_specs as specs
if not hasattr(specs, 'CompositeSpec'):
    specs.CompositeSpec = specs.Composite
if not hasattr(specs, 'BoundedTensorSpec'):
    specs.BoundedTensorSpec = specs.Bounded
if not hasattr(specs, 'UnboundedContinuousTensorSpec'):
    specs.UnboundedContinuousTensorSpec = specs.UnboundedContinuous
if not hasattr(specs, 'UnboundedDiscreteTensorSpec'):
    specs.UnboundedDiscreteTensorSpec = specs.UnboundedDiscrete


def read_p21(file_path):
    """读取P21数据"""
    with open(file_path, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]
    
    parts = lines[0].split()
    n_vehicles, n_customers, n_depots = int(parts[1]), int(parts[2]), int(parts[3])
    
    # 读取depot信息、客户信息、depot坐标
    # ... (完整代码见solve_p21_simple.py)
    
    return {'customers': customers, 'depots': depots}


def kmeans_split(data, n_clusters=9):
    """K-Means分割客户到各个depot"""
    customers = data['customers']
    depots = data['depots']
    
    customer_coords = np.array([[c['x'], c['y']] for c in customers])
    depot_coords = np.array([[d['x'], d['y']] for d in depots])
    
    # 使用depot坐标作为初始中心
    kmeans = KMeans(n_clusters=n_clusters, init=depot_coords, n_init=1, random_state=42)
    labels = kmeans.fit_predict(customer_coords)
    
    depot_customers = defaultdict(list)
    for idx, label in enumerate(labels):
        depot_customers[label].append(customers[idx])
    
    return depot_customers


def create_npz_for_depot(depot, customers, depot_idx, output_dir):
    """创建单个depot的npz文件（MTVRPEnv格式）"""
    n = len(customers)
    if n == 0:
        return None
    
    # 归一化坐标到[0, 1]
    all_x = [c['x'] for c in customers] + [depot['x']]
    all_y = [c['y'] for c in customers] + [depot['y']]
    x_min, x_max = min(all_x), max(all_x)
    y_min, y_max = min(all_y), max(all_y)
    x_range = max(x_max - x_min, 1)
    y_range = max(y_max - y_min, 1)
    
    # locs: [1, n+1, 2] - depot在第一个位置
    locs = np.zeros((1, n + 1, 2), dtype=np.float32)
    locs[0, 0, 0] = (depot['x'] - x_min) / x_range
    locs[0, 0, 1] = (depot['y'] - y_min) / y_range
    
    for i, c in enumerate(customers):
        locs[0, i + 1, 0] = (c['x'] - x_min) / x_range
        locs[0, i + 1, 1] = (c['y'] - y_min) / y_range
    
    # demand_linehaul: [1, n] - 只有客户的需求（不包含depot）
    demands = np.array([c['demand'] for c in customers], dtype=np.float32).reshape(1, n)
    
    # 归一化需求
    max_demand = demands.max()
    if max_demand > 0:
        demands = demands / max_demand
        capacity = depot['capacity'] / max_demand
    else:
        capacity = depot['capacity']
    
    # 保存npz
    npz_path = os.path.join(output_dir, f"depot_{depot_idx}.npz")
    np.savez(
        npz_path,
        locs=locs,
        demand_linehaul=demands,
        vehicle_capacity=np.array([[capacity]], dtype=np.float32),
        speed=np.ones((1, 1), dtype=np.float32),
        num_depots=np.ones((1, 1), dtype=np.int32)
    )
    
    return npz_path


def sample_depot_solutions(env, policy, npz_path, device, num_samples=20):
    """对单个depot采样多个解"""
    td_original = env.load_data(npz_path)
    td_original = td_original.to(device)
    
    solutions = []
    with torch.inference_mode():
        for i in range(num_samples):
            # 关键：每次都从原始td创建新副本
            td = td_original.clone()
            td_reset = env.reset(td)
            out = policy(td_reset, env, phase="test", num_starts=1, 
                        return_actions=True, decode_type="sampling")
            
            cost = -out['reward'].item()
            solutions.append({'sample_idx': i, 'cost': cost})
    
    solutions.sort(key=lambda x: x['cost'])
    return solutions


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # 1. 读取P21数据
    data = read_p21("../MDVRP-Instances/dat/p21")
    
    # 2. K-Means分割
    depot_customers = kmeans_split(data, n_clusters=len(data['depots']))
    
    # 3. 创建npz文件
    output_dir = "p21_npz_temp"
    os.makedirs(output_dir, exist_ok=True)
    
    npz_files = []
    for depot_idx in range(len(data['depots'])):
        customers = depot_customers[depot_idx]
        if len(customers) == 0:
            continue
        depot = data['depots'][depot_idx]
        npz_path = create_npz_for_depot(depot, customers, depot_idx, output_dir)
        if npz_path:
            npz_files.append((depot_idx, npz_path, len(customers)))
    
    # 4. 加载模型
    model = RouteFinderBase.load_from_checkpoint(
        "routefinder/checkpoints/100/rf-transformer.ckpt",
        map_location="cpu",
        strict=False
    )
    policy = model.policy.to(device).eval()
    env = MTVRPEnv()
    
    # 5. 采样求解
    all_results = []
    for depot_idx, npz_path, n_customers in npz_files:
        solutions = sample_depot_solutions(env, policy, npz_path, device, num_samples=20)
        
        result = {
            'depot_idx': depot_idx,
            'n_customers': n_customers,
            'best_cost': solutions[0]['cost'],
            'avg_cost': np.mean([s['cost'] for s in solutions]),
            'solutions': solutions
        }
        all_results.append(result)
    
    # 6. 保存结果
    with open("p21_solutions/results.json", 'w') as f:
        json.dump({'results': all_results}, f, indent=2)


if __name__ == "__main__":
    main()
```

### 运行结果
```bash
python solve_p21_simple.py
```

**输出**:
```
P21: 360 customers, 9 depots

K-Means分割:
  Depot 0: 40 customers
  Depot 1: 40 customers
  ...
  Depot 8: 40 customers

Processing Depot 0 (40 customers)...
  [OK] Best (normalized): 9.9722, Best (real): 1410.28
       Avg (normalized): 11.1396, Avg (real): 1575.42, Time: 3.37s
...
Processing Depot 8 (40 customers)...
  [OK] Best (normalized): 9.9536, Best (real): 1407.65
       Avg (normalized): 11.1008, Avg (real): 1569.65, Time: 2.99s

总耗时: 27.53s
总成本 (归一化): 88.11
总成本 (真实距离): 12460.20
```

### 性能分析
- 每个depot: 40个客户
- 每个depot采样: 20个解
- 平均求解时间: ~3秒/depot
- 总耗时: 27.53秒
- 设备: CUDA (RTX 3060)
- **归一化总成本**: 88.11
- **真实距离总成本**: 12460.20
- **P21 BKS (最优解)**: 5474.84
- **Gap**: 127.6% (相比BKS)

### Gap分析

**为什么Gap这么大？**

1. **简单分割策略**: K-Means只考虑地理位置，未考虑：
   - 容量约束（每个depot容量60，但分配了40个客户）
   - 距离约束
   - 需求分布

2. **独立求解**: 每个depot独立优化，缺少：
   - 全局协调
   - Depot间客户重新分配
   - 跨depot路径优化

3. **模型限制**: 
   - RouteFinder在CVRP上训练，非MDVRP专用
   - 未针对多depot场景优化

4. **归一化影响**: 
   - 每个depot独立归一化坐标
   - 可能导致距离计算偏差

### 改进方向

要获得更好的结果，可以：

1. **优化分割策略**:
   - 使用考虑容量的聚类算法
   - 迭代优化客户分配
   - 使用启发式方法（如Sweep算法）

2. **全局优化**:
   - 实现客户重新分配机制
   - 使用局部搜索改进
   - 考虑depot间协调

3. **使用专用模型**:
   - 训练MDVRP专用模型
   - 或使用传统优化算法（GA、PSO等）

4. **混合方法**:
   - RouteFinder生成初始解
   - 传统算法进一步优化

## NPZ数据格式规范

MTVRPEnv期望的npz文件格式：

```python
{
    'locs': np.ndarray,              # [batch, n_customers+1, 2]
                                     # 第0个位置是depot，后面是客户坐标
    
    'demand_linehaul': np.ndarray,   # [batch, n_customers]
                                     # 只包含客户需求，不包含depot
    
    'vehicle_capacity': np.ndarray,  # [batch, 1]
                                     # 车辆容量
    
    'speed': np.ndarray,             # [batch, 1]
                                     # 车辆速度（通常为1）
    
    'num_depots': np.ndarray         # [batch, 1]
                                     # depot数量（CVRP为1）
}
```

**重要提示**:
- `locs`包含depot（第0个位置）+ 所有客户
- `demand_linehaul`只包含客户需求，不包含depot
- 坐标和需求都应归一化到合理范围（如[0, 1]）

## 最佳实践

### 1. 使用GPU加速
```python
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
policy = policy.to(device)
td = td.to(device)
```

### 2. 批量推理
```python
# 如果有多个实例，使用batch推理更高效
batch_size = 10
td = env.load_data(npz_path)  # 自动处理batch
```

### 3. 采样策略
```python
# sampling: 随机采样，多样性高
out = policy(td, env, decode_type="sampling")

# greedy: 贪心解码，确定性强
out = policy(td, env, decode_type="greedy")
```

### 4. 内存管理
```python
with torch.inference_mode():  # 比torch.no_grad()更高效
    for i in range(num_samples):
        td = td_original.clone()  # 避免副作用
        # ... 推理代码
```

## 常见错误排查

### 错误1: "size of tensor a (X) must match size of tensor b (Y)"
**原因**: 没有在循环中克隆TensorDict
**解决**: 使用`td = td_original.clone()`

### 错误2: "CompositeSpec not found"
**原因**: TorchRL版本不兼容
**解决**: 添加名称映射代码

### 错误3: "UnicodeEncodeError: 'gbk' codec"
**原因**: Windows GBK编码问题
**解决**: 避免使用emoji，使用ASCII字符

## 参考资料

- RouteFinder论文: [Multi-Task Learning for Routing Problem](https://arxiv.org/abs/2402.16891)
- RL4CO文档: https://github.com/ai4co/rl4co
- TorchRL文档: https://pytorch.org/rl/

## 总结

成功使用RouteFinder的关键点：
1. ✅ 正确处理TorchRL API兼容性
2. ✅ 在循环采样时克隆TensorDict避免副作用
3. ✅ 使用正确的NPZ数据格式
4. ✅ 利用GPU加速推理
5. ✅ 避免Windows编码问题

完整代码见: `RL4CO_Integration/solve_p21_simple.py`
