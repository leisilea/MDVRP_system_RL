# P01-P23 完整测试指南

## 概述

这是一个完整的P01-P23测试套件，用于对比纯GA和混合求解器(GA+RouteFinder)的性能。

## 文件说明

### 测试脚本
- `test_p01_p23_complete.py` - 主测试脚本，运行所有P01-P23问题
- `analyze_p01_p23_complete.py` - 结果分析脚本，生成报告和图表

### 结果目录
- `p01_p23_complete_results/` - 测试结果保存目录
  - `p01_results.json` - P01的详细结果
  - `p02_results.json` - P02的详细结果
  - ... (每个问题一个文件)
  - `summary.json` - 汇总结果
  - `SUMMARY_REPORT.md` - 汇总报告
  - `p01_convergence.png` - P01收敛曲线
  - ... (每个问题一个图)

## 使用方法

### 1. 运行完整测试

```bash
# 测试所有P01-P23问题（推荐晚上运行）
python test_p01_p23_complete.py
```

**预计时间**:
- 小问题(P01-P07): 每个约10-30分钟
- 中等问题(P08-P14): 每个约30-60分钟
- 大问题(P15-P23): 每个约1-3小时
- **总计**: 约10-20小时

### 2. 测试特定问题

```bash
# 只测试P01, P08, P21
python test_p01_p23_complete.py --problems p01 p08 p21
```

### 3. 从某个问题继续

```bash
# 从P08开始测试（如果前面的已完成）
python test_p01_p23_complete.py --start-from p08
```

### 4. 分析结果

```bash
# 分析所有结果并生成报告
python analyze_p01_p23_complete.py

# 只分析特定问题
python analyze_p01_p23_complete.py --problems p01 p08 p21

# 不生成收敛曲线图（只生成报告）
python analyze_p01_p23_complete.py --no-plots
```

## 测试配置

### 每个问题的测试内容
- 纯GA: 3次独立运行
- 混合求解器: 3次独立运行
- 总计: 6次运行/问题

### 混合求解器配置
- RL种子比例: 20%
- RL采样数: 20次/depot
- GPU加速: 启用
- 模型选择: 自动（根据问题规模）

### 超时设置
- 单次运行超时: 2小时
- 如果超时，会记录错误并继续下一个测试

## 结果文件格式

### 单个问题结果 (例如 p01_results.json)

```json
{
  "problem": "p01",
  "num_customers": 50,
  "num_depots": 4,
  "max_distance": 0,
  "test_date": "2026-04-11 20:00:00",
  "pure_ga_runs": [
    {
      "run_id": 1,
      "total_cost": 600.17,
      "compute_time": 5.48,
      "convergence": [[10, 657.5], [20, 620.3], ...],
      "start_time": "2026-04-11 20:00:00",
      "end_time": "2026-04-11 20:00:05"
    },
    ...
  ],
  "hybrid_runs": [
    {
      "run_id": 1,
      "total_cost": 598.02,
      "compute_time": 15.94,
      "convergence": [[10, 599.7], [20, 598.5], ...],
      "start_time": "2026-04-11 20:00:10",
      "end_time": "2026-04-11 20:00:26"
    },
    ...
  ],
  "statistics": {
    "pure_ga": {
      "avg_time": 5.48,
      "avg_cost": 600.17,
      "std_time": 0.0,
      "std_cost": 0.0
    },
    "hybrid": {
      "avg_time": 15.94,
      "avg_cost": 598.02,
      "std_time": 0.0,
      "std_cost": 0.0
    }
  }
}
```

## 断点续传功能

测试脚本支持断点续传：
- 每完成一次运行就保存结果
- 默认跳过已完成的问题
- 可以随时中断并重新运行

```bash
# 如果测试中断，直接重新运行即可
python test_p01_p23_complete.py

# 会自动检测已完成的问题并跳过
```

## 注意事项

### 1. 磁盘空间
- 每个问题的结果文件约1-5MB
- 收敛曲线图约500KB/个
- 总计需要约100-200MB空间

### 2. 内存使用
- 纯GA: 约1-2GB
- 混合求解器: 约3-4GB (GPU模型加载)
- 建议至少8GB可用内存

### 3. GPU要求
- 混合求解器需要GPU
- 如果没有GPU，会自动降级到CPU（但会很慢）
- 推荐: NVIDIA GPU with 4GB+ VRAM

### 4. 运行建议
- 建议在晚上或周末运行完整测试
- 可以使用 `nohup` 或 `screen` 在后台运行
- 定期检查日志确保正常运行

```bash
# 后台运行示例
nohup python test_p01_p23_complete.py > test.log 2>&1 &

# 查看进度
tail -f test.log
```

## 结果分析

### 汇总报告内容
- 每个问题的对比表格
- 质量提升百分比
- 时间开销百分比
- 推荐评级（⭐⭐⭐⭐⭐）
- 总体统计

### 收敛曲线图
- 左图: 完整收敛过程
- 右图: 前100代放大（显示RL初始化效果）
- 蓝色: 纯GA
- 红色: 混合求解器

## 常见问题

### Q: 测试太慢怎么办？
A: 可以先测试几个代表性问题：
```bash
python test_p01_p23_complete.py --problems p01 p08 p15 p21
```

### Q: 如何只重新测试某个问题？
A: 删除对应的结果文件，然后重新运行：
```bash
rm p01_p23_complete_results/p08_results.json
python test_p01_p23_complete.py --problems p08
```

### Q: 测试中断了怎么办？
A: 直接重新运行，会自动跳过已完成的：
```bash
python test_p01_p23_complete.py
```

### Q: 如何查看实时进度？
A: 查看输出日志，每完成一次运行都会打印进度

### Q: GPU内存不足怎么办？
A: 可以修改 `ga_mdvrp_rl_hybrid.py` 中的 `num_rl_samples` 参数，从20减少到10

## 预期结果

根据之前的测试，预期结果：

### 小规模问题 (P01-P07)
- 质量提升: 0-1%
- 时间开销: +100-200%
- 推荐: ⭐⭐ (不推荐使用混合方法)

### 中等规模问题 (P08-P14)
- 质量提升: 1-3%
- 时间开销: +10-50%
- 推荐: ⭐⭐⭐⭐⭐ (强烈推荐使用混合方法)

### 大规模问题 (P15-P23)
- 质量提升: 0-1%
- 时间开销: +50-100%
- 推荐: ⭐⭐⭐ (视情况而定)

## 技术支持

如果遇到问题：
1. 检查 `test.log` 日志文件
2. 确认GPU可用性: `nvidia-smi`
3. 确认Java环境: `java -version`
4. 确认Python环境: `python --version`

## 更新日志

### 2026-04-11
- 创建完整测试套件
- 支持断点续传
- 自动生成报告和图表
