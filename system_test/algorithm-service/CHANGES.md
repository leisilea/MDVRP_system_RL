# 算法服务更新记录

## 2026-04-11 - 算法整合与接口完善

### 完成的工作

#### 1. PSO算法整合
- ✅ 将旧版PSO文件移动到PSO_V03文件夹
  - `pso_v02.py` → `PSO_V03/`
  - `pso_v03.py` → `PSO_V03/`
  - `pso_v04.py` → `PSO_V03/`
  - `pso_v05.py` → `PSO_V03/`
  - `pso_with_constraints.py` → `PSO_V03/`
  - `pso_original.py` → `PSO_V03/`
- ✅ 将`pso_v03.py`复制为`pso.py`作为PSO的唯一实现
- ✅ 更新`mdvrp_solver.py`中的PSO导入路径

#### 2. GA混合强化学习求解器集成
- ✅ 在`mdvrp_solver.py`中添加`GAMDVRPRLHybridSolver`类
- ✅ 添加算法ID: `GA_RL_HYBRID`, `ga_rl_hybrid`, `hybrid`
- ✅ 支持参数配置:
  - `rl_seed_ratio`: RL种子占比 (默认0.2)
  - `num_rl_samples`: 采样数量 (默认20)
  - `use_gpu`: 是否使用GPU (默认True)
  - `model_type`: 模型类型 (默认'auto')

#### 3. API接口更新
- ✅ 更新`app.py`中的算法验证列表
- ✅ 更新`/api/algorithms`接口，添加GA_RL_HYBRID信息
- ✅ 确保所有5种算法都可以通过API调用

#### 4. 文档和测试
- ✅ 创建`ALGORITHM_API.md` - 完整的API文档
- ✅ 创建`test_all_algorithms.py` - 自动化测试脚本
- ✅ 创建`CHANGES.md` - 更新记录

### 当前可用的5种算法

| # | 算法名称 | 算法ID | 文件 | 状态 |
|---|---------|--------|------|------|
| 1 | PSO - 粒子群算法 | `PSO` | `solver/pso.py` | ✅ 可用 |
| 2 | ACO - 蚁群算法 | `ACO`, `ant_colony` | `solver/aco.py` | ✅ 可用 |
| 3 | GA - 遗传算法(正常初始化) | `genetic`, `GA` | `solver/ga_multiprogramming.py` | ✅ 可用 |
| 4 | GA Hybrid - 遗传算法(混合RL) | `GA_RL_HYBRID`, `ga_rl_hybrid`, `hybrid` | `solver/ga_mdvrp_rl_hybrid.py` | ✅ 可用 |
| 5 | GA Multiprocessing - 遗传算法(多进程) | `ga_multiprogramming` | `solver/ga_multiprogramming.py` | ✅ 可用 |

### 文件结构

```
system_test/algorithm-service/
├── app.py                          # Flask API服务
├── config.py                       # 配置文件
├── solver/
│   ├── mdvrp_solver.py            # 求解器工厂和基类
│   ├── pso.py                     # PSO算法 (唯一实现)
│   ├── aco.py                     # ACO算法
│   ├── ga_multiprogramming.py     # GA算法 (正常/多进程)
│   ├── ga_mdvrp_rl_hybrid.py      # GA混合RL算法
│   ├── ga_mdvrp_java.py           # GA Java版本
│   └── ...
├── ALGORITHM_API.md               # API文档
├── test_all_algorithms.py         # 测试脚本
└── CHANGES.md                     # 本文件
```

### 测试方法

#### 1. 启动服务
```bash
cd system_test/algorithm-service
python app.py
```

#### 2. 运行自动化测试
```bash
python test_all_algorithms.py
```

测试脚本会依次测试所有5种算法，并输出详细结果。

#### 3. 手动测试单个算法
```bash
curl -X POST http://localhost:5000/api/solve \
  -H "Content-Type: application/json" \
  -d '{
    "depots": [{"id": 1, "x": 0, "y": 0, "vehicles": 3, "capacity": 100}],
    "customers": [
      {"id": 1, "x": 10, "y": 20, "demand": 15},
      {"id": 2, "x": 30, "y": 40, "demand": 20}
    ],
    "params": {
      "algorithm": "PSO",
      "max_iterations": 100
    }
  }'
```

### 前端调用示例

```javascript
// 调用PSO算法
const response = await fetch('http://localhost:5000/api/solve', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    depots: [{ id: 1, x: 0, y: 0, vehicles: 5, capacity: 100 }],
    customers: [
      { id: 1, x: 10, y: 20, demand: 15 },
      { id: 2, x: 30, y: 40, demand: 20 }
    ],
    params: {
      algorithm: 'PSO',  // 可选: 'PSO', 'ACO', 'genetic', 'GA_RL_HYBRID', 'ga_multiprogramming'
      max_iterations: 1000
    }
  })
});

const result = await response.json();
console.log('总成本:', result.data.totalCost);
console.log('路径数:', result.data.numRoutes);
```

### 注意事项

1. **GA_RL_HYBRID算法依赖**:
   - 需要PyTorch和TorchRL
   - 需要RouteFinder模型文件
   - 可选GPU加速 (设置`use_gpu: false`使用CPU)

2. **算法参数**:
   - 不同算法支持不同的参数
   - 详见`ALGORITHM_API.md`文档

3. **性能考虑**:
   - GA_RL_HYBRID初次运行会加载模型，需要额外时间
   - ga_multiprogramming会使用多进程，注意CPU资源
   - 大规模问题建议增加`max_iterations`

### 下一步工作

- [ ] 添加算法性能对比测试
- [ ] 优化GA_RL_HYBRID的模型加载速度
- [ ] 添加更多算法参数的文档说明
- [ ] 前端界面集成测试

