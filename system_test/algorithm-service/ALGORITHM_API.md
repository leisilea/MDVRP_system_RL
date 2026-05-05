# MDVRP 算法服务 API 文档

## 概述

本服务提供5种MDVRP求解算法的REST API接口。

## 可用算法

### 1. PSO - 粒子群算法
- **算法ID**: `PSO`
- **描述**: 基于群体智能的优化算法
- **文件**: `solver/pso.py`
- **状态**: ✅ 可用

### 2. ACO - 蚁群算法
- **算法ID**: `ACO` 或 `ant_colony`
- **描述**: 模拟蚂蚁觅食行为的优化算法
- **文件**: `solver/aco.py`
- **状态**: ✅ 可用

### 3. GA - 遗传算法(正常初始化)
- **算法ID**: `genetic` 或 `GA`
- **描述**: 基于自然选择的启发式算法
- **文件**: `solver/ga_multiprogramming.py`
- **状态**: ✅ 可用

### 4. GA Hybrid - 遗传算法(混合强化学习初始化)
- **算法ID**: `GA_RL_HYBRID`, `ga_rl_hybrid`, 或 `hybrid`
- **描述**: 结合遗传算法和强化学习(RouteFinder)的混合求解器
- **文件**: `solver/ga_mdvrp_rl_hybrid.py`
- **状态**: ✅ 可用
- **依赖**: PyTorch, TorchRL, CUDA (可选)

### 5. GA Multiprocessing - 遗传算法(多进程)
- **算法ID**: `ga_multiprogramming`
- **描述**: 使用多进程加速的遗传算法
- **文件**: `solver/ga_multiprogramming.py`
- **状态**: ✅ 可用

## API 接口

### 1. 健康检查
```
GET /health
```

**响应示例**:
```json
{
  "success": true,
  "status": "ok",
  "service": "MDVRP Algorithm Service",
  "version": "1.0.0"
}
```

### 2. 获取算法列表
```
GET /api/algorithms
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "algorithms": [
      {
        "id": "PSO",
        "name": "粒子群算法 (PSO)",
        "description": "基于群体智能的优化算法",
        "status": "available"
      },
      ...
    ]
  }
}
```

### 3. 求解MDVRP问题
```
POST /api/solve
```

**请求格式**:
```json
{
  "depots": [
    {
      "id": 1,
      "x": 0,
      "y": 0,
      "vehicles": 5,
      "capacity": 100,
      "maxDistance": 200
    }
  ],
  "customers": [
    {
      "id": 1,
      "x": 10,
      "y": 20,
      "demand": 15
    }
  ],
  "params": {
    "algorithm": "PSO",
    "max_iterations": 1000,
    "population_size": 50
  }
}
```

**算法特定参数**:

#### PSO
```json
{
  "algorithm": "PSO",
  "max_iterations": 1000,
  "num_particles": 50
}
```

#### ACO
```json
{
  "algorithm": "ACO",
  "max_iterations": 1000,
  "num_ants": 50
}
```

#### GA (正常初始化)
```json
{
  "algorithm": "genetic",
  "max_iterations": 1000,
  "population_size": 50
}
```

#### GA Hybrid (混合强化学习)
```json
{
  "algorithm": "GA_RL_HYBRID",
  "max_iterations": 1000,
  "population_size": 50,
  "rl_seed_ratio": 0.2,
  "num_rl_samples": 20,
  "use_gpu": true,
  "model_type": "auto"
}
```

#### GA Multiprocessing (多进程)
```json
{
  "algorithm": "ga_multiprogramming",
  "max_iterations": 1000,
  "population_size": 50,
  "num_processes": 4
}
```

**响应格式**:
```json
{
  "success": true,
  "data": {
    "routes": [
      {
        "vehicleId": 1,
        "depotId": 1,
        "path": [1, 3, 5, 7],
        "cost": 150.5
      }
    ],
    "totalCost": 270.8,
    "computeTime": 2.34,
    "numRoutes": 1,
    "algorithm": "PSO",
    "convergence": [[0, 500], [10, 450], [20, 400]]
  }
}
```

## 测试

### 启动服务
```bash
cd system_test/algorithm-service
python app.py
```

### 运行测试
```bash
python test_all_algorithms.py
```

测试脚本会自动测试所有5种算法，并输出详细的测试结果。

## 前端调用示例

### JavaScript/Vue
```javascript
async function solveWithAlgorithm(algorithm) {
  const response = await fetch('http://localhost:5000/api/solve', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      depots: [
        { id: 1, x: 0, y: 0, vehicles: 5, capacity: 100 }
      ],
      customers: [
        { id: 1, x: 10, y: 20, demand: 15 },
        { id: 2, x: 30, y: 40, demand: 20 }
      ],
      params: {
        algorithm: algorithm,  // 'PSO', 'ACO', 'genetic', 'GA_RL_HYBRID', 'ga_multiprogramming'
        max_iterations: 1000
      }
    })
  });
  
  const result = await response.json();
  if (result.success) {
    console.log('总成本:', result.data.totalCost);
    console.log('路径数:', result.data.numRoutes);
    console.log('计算时间:', result.data.computeTime);
  }
}
```

### Python
```python
import requests

response = requests.post('http://localhost:5000/api/solve', json={
    'depots': [
        {'id': 1, 'x': 0, 'y': 0, 'vehicles': 5, 'capacity': 100}
    ],
    'customers': [
        {'id': 1, 'x': 10, 'y': 20, 'demand': 15},
        {'id': 2, 'x': 30, 'y': 40, 'demand': 20}
    ],
    'params': {
        'algorithm': 'PSO',  # 或 'ACO', 'genetic', 'GA_RL_HYBRID', 'ga_multiprogramming'
        'max_iterations': 1000
    }
})

result = response.json()
if result['success']:
    print(f"总成本: {result['data']['totalCost']}")
    print(f"路径数: {result['data']['numRoutes']}")
```

## 故障排除

### 问题1: 服务无法启动
- 检查端口5000是否被占用
- 检查Python依赖是否安装完整

### 问题2: GA_RL_HYBRID算法失败
- 检查PyTorch和TorchRL是否安装
- 检查RouteFinder模型文件是否存在
- 尝试设置 `use_gpu: false` 使用CPU模式

### 问题3: 算法返回错误
- 检查输入数据格式是否正确
- 查看服务器日志获取详细错误信息
- 确认算法ID拼写正确

## 更新日志

### 2026-04-11
- ✅ 整合PSO算法，使用pso.py作为唯一实现
- ✅ 添加GA_RL_HYBRID混合求解器支持
- ✅ 更新API文档和测试脚本
- ✅ 确认5种算法全部可用

