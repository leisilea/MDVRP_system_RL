# Test脚本文件位置和用途说明

## 文件位置汇总

| 脚本名称 | 完整路径 | 用途 | 状态 |
|---------|---------|------|------|
| `test_p01_p23_complete.py` | `system_test/algorithm-service/solver/test_p01_p23_complete.py` | GA完整测试 | ✅ 最终版本 |
| `test_pso_p01_p23.py` | `system_test/algorithm-service/solver/test_pso_p01_p23.py` | PSO完整测试 | ✅ 最终版本 |
| `test_aco_pso_p01_p23_complete.py` | `system_test/algorithm-service/solver/test_aco_pso_p01_p23_complete.py` | ACO+PSO对比 | ✅ 最终版本 |
| `test_aco_pso_quick.py` | `DE/test_aco_pso_quick.py` | 快速测试 | ⚠️ 调试用 |
| `run_aco_pso_experiments.py` | `system_test/algorithm-service/solver/run_aco_pso_experiments.py` | 依赖模块 | 📦 支持模块 |

---

## 详细说明

### 1. test_p01_p23_complete.py
**路径**: `system_test/algorithm-service/solver/test_p01_p23_complete.py`

**用途**: P01-P23标准测试集的GA算法完整测试
- 测试内容: 纯GA vs 混合求解器(GA+RL)
- 运行次数: 每个问题 6次(3次纯GA + 3次混合)
- 总运行次数: 23个问题 × 6次 = 138次
- 输出目录: `system_test/algorithm-service/solver/p01_p23_complete_results/`

**运行命令**:
```bash
cd system_test/algorithm-service/solver
python test_p01_p23_complete.py

# 指定问题测试
python test_p01_p23_complete.py --problems p01 p08 p21

# 从某个问题开始
python test_p01_p23_complete.py --start-from p08
```

**输出文件**:
- `p01_results.json`, `p02_results.json`, ... (每个问题的详细结果)
- `summary.json` (汇总结果)

---

### 2. test_pso_p01_p23.py
**路径**: `system_test/algorithm-service/solver/test_pso_p01_p23.py`

**用途**: P01-P23标准测试集的PSO算法完整测试
- 测试内容: PSO三档参数配置(small/medium/large)
- 运行次数: 每个问题 9次(3档 × 3次)
- 总运行次数: 23个问题 × 9次 = 207次
- 输出目录: `system_test/algorithm-service/solver/pso_p01_p23_results/`

**参数配置**:
- Small: particles=100, iterations=350
- Medium: particles=150, iterations=525
- Large: particles=175, iterations=700

**运行命令**:
```bash
cd system_test/algorithm-service/solver
python test_pso_p01_p23.py

# 指定配置测试
python test_pso_p01_p23.py --configs small medium

# 指定问题测试
python test_pso_p01_p23.py --problems p01 p08
```

**输出文件**:
- `p01_pso_results.json`, `p02_pso_results.json`, ... (每个问题的详细结果)
- `pso_summary.json` (汇总结果)

**重要提示**: PSO数据需要先运行合并脚本修复分仓库数据异常:
```bash
python merge_pso_convergence.py
```

---

### 3. test_aco_pso_p01_p23_complete.py
**路径**: `system_test/algorithm-service/solver/test_aco_pso_p01_p23_complete.py`

**用途**: P01-P23标准测试集的ACO和PSO完整对比测试
- 测试内容: ACO(自适应参数) + PSO(三档参数)
- 运行次数: 每个问题 12次(ACO 3次 + PSO 9次)
- 总运行次数: 23个问题 × 12次 = 276次
- 输出目录: `system_test/algorithm-service/solver/aco_pso_p01_p23_results/`

**特点**:
- ACO自适应参数(根据客户数自动调整)
- PSO三档参数配置
- 自动生成收敛曲线图像(PNG格式)
- 详细的统计分析(平均值、标准差、方差、Gap)

**运行命令**:
```bash
cd system_test/algorithm-service/solver
python test_aco_pso_p01_p23_complete.py
```

**输出文件**:
- `aco_pso_p01_p23_results/p01/p01_results.json` (每个问题单独目录)
- `aco_pso_p01_p23_results/p01/p01_aco_convergence.png` (ACO收敛曲线)
- `aco_pso_p01_p23_results/p01/p01_pso_small_convergence.png` (PSO收敛曲线)
- `aco_pso_p01_p23_results/summary_results.json` (汇总结果)

---

### 4. test_aco_pso_quick.py
**路径**: `DE/test_aco_pso_quick.py`

**用途**: 快速测试ACO和PSO(仅在p01上运行,用于调试验证)
- 测试内容: ACO + PSO(small配置)
- 运行次数: 6次(ACO 3次 + PSO 3次)
- 仅测试p01问题

**依赖**: `system_test/algorithm-service/solver/run_aco_pso_experiments.py`

**运行命令**:
```bash
cd DE
python test_aco_pso_quick.py
```

**用途场景**:
- 快速验证算法是否正常工作
- 开发调试阶段使用
- 不保存详细JSON结果(仅控制台输出)

---

### 5. run_aco_pso_experiments.py (依赖模块)
**路径**: `system_test/algorithm-service/solver/run_aco_pso_experiments.py`

**用途**: 提供ACO和PSO实验的通用函数
- 被`test_aco_pso_quick.py`调用
- 提供`run_aco_single()`, `run_pso_single()`, `plot_average_convergence()`等函数

---

## 使用建议

### 场景1: GA算法测试
使用 `test_p01_p23_complete.py`
```bash
cd system_test/algorithm-service/solver
python test_p01_p23_complete.py
```

### 场景2: PSO算法测试
**步骤1**: 先运行合并脚本(修复数据异常)
```bash
cd system_test/algorithm-service/solver
python merge_pso_convergence.py
```

**步骤2**: 运行PSO测试
```bash
python test_pso_p01_p23.py
```

### 场景3: ACO+PSO完整对比
使用 `test_aco_pso_p01_p23_complete.py`
```bash
cd system_test/algorithm-service/solver
python test_aco_pso_p01_p23_complete.py
```

### 场景4: 快速验证/调试
使用 `test_aco_pso_quick.py`
```bash
cd DE
python test_aco_pso_quick.py
```

---

## 输出目录结构

```
system_test/algorithm-service/solver/
├── p01_p23_complete_results/          # GA测试结果
│   ├── p01_results.json
│   ├── p02_results.json
│   ├── ...
│   └── summary.json
│
├── pso_p01_p23_results/               # PSO测试结果
│   ├── p01_pso_results.json
│   ├── p01_pso_results_merged.json    # 合并后的数据
│   ├── p02_pso_results.json
│   ├── ...
│   └── pso_summary.json
│
└── aco_pso_p01_p23_results/           # ACO+PSO对比结果
    ├── p01/
    │   ├── p01_results.json
    │   ├── p01_aco_convergence.png
    │   ├── p01_pso_small_convergence.png
    │   ├── p01_pso_medium_convergence.png
    │   └── p01_pso_large_convergence.png
    ├── p02/
    │   └── ...
    └── summary_results.json
```

---

## 注意事项

1. **PSO数据异常问题**: PSO算法由于分仓库数据拼接导致收敛曲线异常,必须先运行`merge_pso_convergence.py`进行数据合并修复

2. **运行时间**: 
   - 小问题(p01-p07): 几分钟到十几分钟
   - 中等问题(p08-p14): 几十分钟到1小时
   - 大问题(p15-p23): 1小时到几小时

3. **断点续传**: 所有测试脚本都支持`--skip-completed`参数(默认启用),可以从中断处继续运行

4. **内存占用**: 大规模问题(p21-p23)可能需要较大内存(建议8GB以上)

5. **GPU支持**: 混合求解器(GA+RL)需要GPU支持,如果没有GPU会自动降级到CPU模式

---

## 最终使用版本总结

| 算法类型 | 使用脚本 | 位置 |
|---------|---------|------|
| GA算法 | `test_p01_p23_complete.py` | `system_test/algorithm-service/solver/` |
| PSO算法 | `test_pso_p01_p23.py` | `system_test/algorithm-service/solver/` |
| ACO+PSO对比 | `test_aco_pso_p01_p23_complete.py` | `system_test/algorithm-service/solver/` |
| 快速调试 | `test_aco_pso_quick.py` | `DE/` |

**结论**: 前三个是你的最终使用版本,第四个是调试辅助工具。
