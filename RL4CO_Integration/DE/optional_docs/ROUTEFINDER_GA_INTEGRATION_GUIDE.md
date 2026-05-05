# RouteFinder + GA-MDVRP 集成使用指南

本文档介绍如何使用RouteFinder生成的解来初始化GA-MDVRP遗传算法，以加快收敛速度并提高解的质量。

## 目录

1. [概述](#概述)
2. [环境准备](#环境准备)
3. [完整工作流程](#完整工作流程)
4. [关键文件说明](#关键文件说明)
5. [参数配置](#参数配置)
6. [结果分析](#结果分析)
7. [常见问题](#常见问题)

---

## 概述

### 集成方案

使用RouteFinder（基于强化学习的MDVRP求解器）生成高质量的初始解，然后将这些解转换为GA-MDVRP Java程序能接受的格式，用于初始化遗传算法的种群。

### 优势

- **更好的初始解质量**：RouteFinder生成的解比随机初始化质量高9-10%
- **更快的收敛速度**：减少达到相同质量所需的迭代次数
- **更好的最终解**：在相同代数下，最终解质量提升约5-10%

### 技术栈

- **RouteFinder**: PyTorch + TorchRL (强化学习求解器)
- **GA-MDVRP**: Java (遗传算法)
- **数据转换**: Python + JSON
- **可视化**: Matplotlib

---

## 环境准备

### Python环境

```bash
# 激活虚拟环境
conda activate GD  # 或你的环境名

# 确保安装了必要的包
pip install torch torchrl numpy matplotlib
```

### Java环境

```bash
# 确保Java已安装
java -version  # 应该显示Java 8或更高版本

# 确保Gson库已配置
# 位置: system_test/ga_mdvrp_reproduction/GA-MDVRP/lib/gson-2.11.0.jar
```

### 目录结构

```
GraduationDesign/
├── RL4CO_Integration/
│   ├── routefinder/              # RouteFinder源码
│   ├── solve_p21_fixed.py        # P21求解脚本
│   ├── convert_to_ga_format.py   # 格式转换脚本
│   └── p21_ga_initial_population.json  # 生成的初始种群
├── system_test/ga_mdvrp_reproduction/GA-MDVRP/
│   ├── src/                      # Java源码
│   ├── bin/                      # 编译后的class文件
│   ├── lib/                      # 依赖库（Gson）
│   ├── data/
│   │   ├── problems/p21          # 问题数据
│   │   └── solutions/            # 解输出目录
│   └── plot_convergence.py       # 收敛曲线绘制脚本
└── MDVRP-Instances/
    └── dat/p21                   # P21原始数据
```

---

## 完整工作流程

### 步骤1: 使用RouteFinder生成解

```bash
cd RL4CO_Integration

# 运行RouteFinder求解P21问题
python solve_p21_fixed.py
```

**输出**:
- `p21_solutions_fixed/results.json` - 包含所有depot的采样解
- 每个depot生成20个样本解
- 总耗时约2-3分钟（GPU）

**关键参数**:
```python
num_samples = 20  # 每个depot的采样数量
```

### 步骤2: 转换为GA格式

```bash
# 在RL4CO_Integration目录下
python convert_to_ga_format.py
```

**输出**:
- `p21_ga_initial_population.json` - GA-MDVRP可用的初始种群
- 包含20个Individual（占种群的20%）

**JSON格式**:
```json
{
  "population": [
    {
      "chromosome": {
        "1": [  // Depot ID (1-indexed)
          {
            "route": [24, 32, ...],  // Customer IDs (1-indexed)
            "demand": 56,
            "distance": 0.0
          },
          ...
        ],
        ...
      },
      "fitness": 8810.69,
      "isFeasible": true
    },
    ...
  ]
}
```

### 步骤3: 编译Java代码

```bash
cd system_test/ga_mdvrp_reproduction/GA-MDVRP

# 编译（排除Visualizer.java，它需要JavaFX）
javac -encoding UTF-8 -d bin -cp "lib/*" ^
  src/Utils/Formatter.java ^
  src/Utils/Euclidian.java ^
  src/GA/Components/*.java ^
  src/GA/Operations/*.java ^
  src/MDVRP/*.java ^
  src/GA/*.java ^
  src/MainCLI.java
```

### 步骤4: 运行GA-MDVRP

#### 4.1 使用RouteFinder初始化

```bash
java -cp "bin;lib/*" MainCLI ^
  data/problems/p21 ^
  data/solutions/p21_routefinder.res ^
  ../../../RL4CO_Integration/p21_ga_initial_population.json
```

#### 4.2 纯随机初始化（对比）

```bash
java -cp "bin;lib/*" MainCLI ^
  data/problems/p21 ^
  data/solutions/p21_random.res
```

**运行时间**: 约1.5-2分钟/次（1200代）

### 步骤5: 绘制收敛曲线对比

```bash
# 在GA-MDVRP目录下
python plot_convergence.py
```

**输出**:
- `convergence_comparison_1200gen_20seeds.png` - 收敛曲线对比图
- 显示随机初始化 vs RouteFinder初始化的性能对比

---

## 关键文件说明

### Python脚本

#### `solve_p21_fixed.py`
- **功能**: 使用RouteFinder求解P21 MDVRP问题
- **关键修复**:
  - `vehicle_capacity = 60` (单车容量，不是depot总容量)
  - `scale_factor = max(x_range, y_range)` (归一化因子)
- **输出**: `p21_solutions_fixed/results.json`

#### `convert_to_ga_format.py`
- **功能**: 将RouteFinder解转换为GA-MDVRP格式
- **关键逻辑**:
  - 贪心分配客户到最近的depot
  - 转换actions数组为route列表
  - 生成GA Individual结构
- **输出**: `p21_ga_initial_population.json`

#### `plot_convergence.py`
- **功能**: 运行两次GA并绘制收敛曲线对比
- **特点**:
  - 自动运行随机初始化和RouteFinder初始化
  - 解析输出日志提取收敛数据
  - 生成高质量对比图

### Java代码修改

#### `MainCLI.java`
```java
// 支持第3个参数：seed population JSON路径
String seedPopulationPath = args.length > 2 ? args[2] : null;
Algorithm ga = new Algorithm(manager, seedPopulationPath);
```

#### `Algorithm.java`
```java
// 构造函数支持seed population
public Algorithm(Manager manager, String seedPopulationPath) {
    this.seedPopulationPath = seedPopulationPath;
    // ...
}

// 初始化时传递seed path
List<Individual> population = Initializer.init(
    this.populationSize, 
    crowdedDepots, 
    this.metrics, 
    this.seedPopulationPath
);
```

#### `Initializer.java`
```java
// 加载JSON并创建seed individuals
private static List<Individual> loadFromJson(String jsonPath, Metrics metrics) {
    // 使用Gson解析JSON
    // 创建Individual对象
    // 调用metrics.evaluateRoute()计算distance
    return individuals;
}
```

**关键修复**: 必须调用`metrics.evaluateRoute(depotId, route)`来计算Route的distance，否则fitness会是0。

#### `Individual.java`
```java
// getClone()方法不复制fitness和isFeasible
// 这样crossover/mutation后的offspring会被重新评估
public Individual getClone() {
    // 只复制chromosome
    return new Individual(chromosomeCopy);
}
```

#### `Manager.java`
```java
// 支持3值和4值的Cordeau格式第一行
String[] parts = firstLine.split("\\s+");
if (parts.length == 3) {
    // 3值格式: vehicles customers depots
} else if (parts.length == 4) {
    // 4值格式: type vehicles customers depots
}
```

---

## 参数配置

### RouteFinder参数

```python
# solve_p21_fixed.py
num_samples = 20          # 每个depot的采样数量
vehicle_capacity = 60     # 单车容量
scale_factor = max(x_range, y_range)  # 归一化因子
```

### GA参数

```java
// Algorithm.java
int populationSize = 100;           // 种群大小
int numberOfGenerations = 1200;     // 迭代代数
int refinementAfter = 700;          // 精细化模式切换代数
int eliteReplacement = 20;          // 精英保留数量
double crossoverRate = 0.8;         // 交叉率
double mutationRate = 0.05;         // 变异率
```

### 初始种群配置

```python
# convert_to_ga_format.py
num_solutions = 20  # 导出20个解（占种群的20%）
```

**推荐配置**:
- 种群大小100，使用20个RouteFinder解（20%）
- 剩余80个随机生成
- 这样既保证了多样性，又有高质量的起点

---

## 结果分析

### 性能对比（P21, 1200代）

| 指标 | 随机初始化 | RouteFinder初始化 | 改进 |
|------|-----------|------------------|------|
| 初始平均距离 | ~19400 | ~17500 | 9.8% ↓ |
| 最终最优解 | ~6500 | ~6200 | 4.6% ↓ |
| 收敛速度 | 基准 | 更快 | - |
| BKS (5474.84) | Gap 18.7% | Gap 13.2% | 5.5% ↓ |

### 收敛曲线特征

**随机初始化**:
- 初始解质量差
- 前期改进快，后期缓慢
- 需要更多代数才能收敛

**RouteFinder初始化**:
- 初始解质量高
- 全程保持优势
- 更快达到相同质量水平

### 可视化

收敛曲线图包含：
- 蓝色线：随机初始化
- 红色线：RouteFinder初始化
- 绿色虚线：BKS参考值
- X轴：代数（每10代一个数据点）
- Y轴：最优解距离

---

## 常见问题

### Q1: 编译时出现"找不到符号 Formatter"错误

**原因**: 没有编译Formatter.java

**解决**:
```bash
javac -encoding UTF-8 -d bin -cp "lib/*" src/Utils/Formatter.java src/Utils/Euclidian.java ...
```

### Q2: 运行时出现"Best distance: 0.0"

**原因**: Route的distance字段没有被正确计算

**解决**: 确保在`Initializer.loadFromJson()`中调用了：
```java
metrics.evaluateRoute(depotId, route);
```

### Q3: JSON加载失败

**原因**: 
- Gson库未配置
- JSON路径错误
- JSON格式不正确

**解决**:
1. 确认`lib/gson-2.11.0.jar`存在
2. 使用相对路径：`../../../RL4CO_Integration/p21_ga_initial_population.json`
3. 检查JSON格式是否符合规范

### Q4: RouteFinder运行很慢

**原因**: 使用CPU而不是GPU

**解决**:
```python
# solve_p21_fixed.py
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
```

确保PyTorch能识别GPU：
```python
import torch
print(torch.cuda.is_available())  # 应该返回True
```

### Q5: 收敛曲线图生成失败

**原因**: 
- matplotlib未安装
- 中文字体问题

**解决**:
```bash
pip install matplotlib

# 如果中文显示有问题，脚本已配置SimHei字体
```

### Q6: 如何调整seed个数？

修改`convert_to_ga_format.py`:
```python
num_solutions = 20  # 改为你想要的数量（建议10-30）
```

然后重新运行转换脚本。

### Q7: 如何修改GA代数？

修改`Algorithm.java`:
```java
int numberOfGenerations = 1200;  // 改为你想要的代数
```

然后重新编译。

---

## 最佳实践

### 1. 参数选择

- **种群大小**: 100（标准配置）
- **Seed比例**: 10-20%（10-20个）
- **迭代代数**: 800-1200（取决于问题规模）
- **采样数量**: 20（每个depot）

### 2. 性能优化

- 使用GPU运行RouteFinder（速度提升10-20倍）
- 编译Java时使用`-O`优化选项
- 对于大规模问题，考虑增加采样数量

### 3. 结果验证

- 对比随机初始化和RouteFinder初始化
- 检查解的可行性（所有约束都满足）
- 计算与BKS的gap

### 4. 调试技巧

- 使用`System.out.println()`添加调试输出
- 检查JSON文件的格式和内容
- 验证Route的distance是否正确计算

---

## 引用

如果使用本集成方案，请引用：

```bibtex
@misc{routefinder_ga_integration,
  title={RouteFinder-GA Integration for MDVRP},
  author={Your Name},
  year={2026},
  note={Integration of RouteFinder (RL-based) with GA-MDVRP}
}
```

---

## 更新日志

### 2026-04-10
- 初始版本
- 支持P21问题
- 实现RouteFinder到GA的完整工作流
- 添加收敛曲线对比功能

---

## 联系方式

如有问题或建议，请联系：[your-email@example.com]
