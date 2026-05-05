# PSO收敛数据处理说明

## 背景

PSO算法对MDVRP问题采用分仓库独立求解的策略。每个仓库独立运行PSO算法，因此原始的`convergence`数组包含了所有仓库的收敛数据按顺序拼接。

为了查看整体问题的收敛曲线，需要将相同generation的不同仓库的成本数据进行合并。

## 数据结构

### 原始数据（未合并）

```json
{
  "run_id": 1,
  "convergence": [
    // 仓库1的数据
    {"generation": 0, "best_cost": 193.73, "avg_cost": 241.03},
    {"generation": 50, "best_cost": 161.66, "avg_cost": 170.62},
    ...
    // 仓库2的数据
    {"generation": 0, "best_cost": 293.50, "avg_cost": 372.69},
    {"generation": 50, "best_cost": 237.03, "avg_cost": 248.51},
    ...
    // 仓库3和仓库4的数据...
  ]
}
```

### 合并后的数据

```json
{
  "run_id": 1,
  "convergence_merged": [
    // generation 0: 所有仓库的成本之和
    {"generation": 0, "best_cost": 746.60, "avg_cost": 930.55},
    // generation 50: 所有仓库的成本之和
    {"generation": 50, "best_cost": 630.21, "avg_cost": 657.57},
    ...
  ],
  "convergence_original": [
    // 保留原始数据用于参考
  ]
}
```

## 合并逻辑

1. **识别仓库边界**: 当generation值回退或重新开始时，说明是新仓库的数据
2. **按generation对齐**: 将相同generation的best_cost和avg_cost分别相加
3. **处理不同迭代次数**: 如果某仓库迭代次数较少（如只到generation 100），而其他仓库到了generation 300，则对于generation 300，使用该仓库在generation 100时的最后值

## 使用方法

### 1. 合并单个文件

```bash
python merge_pso_convergence.py pso_p01_p23_results/p01_pso_results.json
```

输出: `p01_pso_results_merged.json`

### 2. 绘制收敛曲线

```bash
python plot_pso_convergence.py pso_p01_p23_results/p01_pso_results_merged.json pso_p01_p23_results/
```

输出:
- `p01_pso_small_convergence.png` - small配置的收敛曲线
- `p01_pso_medium_convergence.png` - medium配置的收敛曲线
- `p01_pso_large_convergence.png` - large配置的收敛曲线
- `p01_pso_config_comparison.png` - 配置对比图

### 3. 批量处理所有文件

```bash
python process_all_pso_results.py pso_p01_p23_results/
```

自动处理目录下所有的`*_pso_results.json`文件。

## 生成的图表

### 单配置收敛曲线
- 左图: 最优成本（best_cost）随generation的变化
- 右图: 平均成本（avg_cost）随generation的变化
- 每条线代表一个run
- 红色虚线表示BKS（最佳已知解）

### 配置对比图
- 左图: 不同配置的平均最优成本对比
- 右图: 不同配置的平均成本对比
- 每条线代表一个配置（small/medium/large）的所有run的平均值

## 验证

合并后的最终成本应该与`total_cost`字段完全匹配，这验证了合并逻辑的正确性。

示例输出:
```
Run 1: 合并 22 条记录 -> 7 个generation
  最终成本: 618.80 (验证: 617.33)  ✓ 匹配
```

## 文件说明

- `*_pso_results.json` - 原始PSO结果文件
- `*_pso_results_merged.json` - 合并后的结果文件
- `*_pso_*_convergence.png` - 各配置的收敛曲线图
- `*_pso_config_comparison.png` - 配置对比图
