# VPRL: RL4CO VRPL Integration for GA-MDVRP

使用强化学习(RL4CO)的VRPL模型为GA_Java算法提供高质量初始解，提升求解速度和质量。

## 核心特性

- **1.2倍过采样策略**: 生成24个样本，保留最优20个，带来5-10%质量提升
- **自动模型选择**: 根据客户数量自动选择20/50/100/200客户规模模型
- **收敛曲线监控**: 每10代报告一次最优成本，用于分析优化效果
- **文件通信机制**: 通过.init文件与GA_Java通信，不修改源代码
- **优雅降级**: 任何错误都不会导致崩溃，自动回退到纯GA_Java

## 快速开始

### 1. 安装依赖

```bash
pip install torch rl4co tensordict numpy scikit-learn
```

### 2. 基本使用

```python
from VPRL import VPRLSampler

# 创建求解器
sampler = VPRLSampler()

# 求解MDVRP实例
result = sampler.solve(
    instance_data="MDVRP-Instances/dat/p01",
    enable_vrpl=True,
    num_solutions_needed=20,
    vrpl_ratio=0.5
)

# 查看结果
print(f"Total cost: {result['total_cost']:.2f}")
print(f"Compute time: {result['compute_time']:.2f}s")
print(f"Oversampling improvement: {result['performance_metrics'].oversampling_improvement:.1f}%")
```

### 3. 自定义配置

```python
from VPRL import VPRLSampler, VPRLConfig

# 创建自定义配置
config = VPRLConfig(
    model_path="models/vrpl_cvrp100.ckpt",
    model_selection_strategy="auto",  # 自动选择模型
    num_solutions_needed=20,
    oversampling_ratio=1.2,  # 1.2倍过采样
    sampling_temperature=1.0,
    vrpl_ratio=0.5,
    convergence_report_interval=10,  # 每10代报告
    assignment_strategy="nearest",
    device="cuda"
)

# 使用自定义配置
sampler = VPRLSampler(config=config)
result = sampler.solve(instance_data="MDVRP-Instances/dat/p01")
```

## 配置参数

### 模型设置

- `model_path`: 模型检查点路径 (默认: `models/vrpl_cvrp100.ckpt`)
- `model_selection_strategy`: 模型选择策略 (`"auto"`, `"fixed"`, `"custom"`)
- `model_size_thresholds`: 自动选择的规模阈值

### 采样设置

- `num_solutions_needed`: 需要的解数量 (默认: 20)
- `oversampling_ratio`: 过采样倍数 (默认: 1.2)
- `sampling_temperature`: 采样温度 (默认: 1.0)
- `decode_type`: 解码类型 (默认: `"sampling"`)

### GA集成设置

- `vrpl_ratio`: VRPL解在初始种群中的占比 (默认: 0.5)
- `enable_vrpl`: 是否启用VRPL初始化 (默认: True)
- `convergence_report_interval`: 收敛报告间隔 (默认: 10代)
- `enable_convergence_tracking`: 是否启用收敛跟踪 (默认: True)

### 客户分配策略

- `assignment_strategy`: 客户分配策略 (`"nearest"`, `"balanced"`, `"kmeans"`)

### 性能设置

- `device`: 计算设备 (`"cuda"` 或 `"cpu"`)
- `batch_size`: 批处理大小 (默认: 1)

### 错误处理

- `fallback_on_error`: 错误时回退到纯GA_Java (默认: True)
- `skip_invalid_solutions`: 跳过无效解 (默认: True)

## 性能估算

### 采样时间 (50客户, GPU)

| 需要解数 | 采样数 | 时间 |
|---------|--------|------|
| 20 | 24 | 1.2-2.4s |
| 50 | 60 | 3-6s |
| 100 | 120 | 6-12s |

### 完整求解时间 (p01实例)

| 阶段 | 时间 | 占比 |
|------|------|------|
| VRPL生成 | ~1-2s | ~4% |
| 格式转换 | <0.1s | <1% |
| GA求解 | ~25s | ~95% |
| **总计** | **~26s** | **100%** |

## 收敛曲线

访问收敛数据：

```python
result = sampler.solve(instance_data="MDVRP-Instances/dat/p01")

# 获取收敛曲线
convergence_curve = result['performance_metrics'].convergence_curve

# 打印收敛点
for point in convergence_curve:
    print(f"Generation {point.generation}: {point.best_cost:.2f} "
          f"(at {point.timestamp:.1f}s)")

# 可视化收敛曲线
import matplotlib.pyplot as plt

generations = [p.generation for p in convergence_curve]
costs = [p.best_cost for p in convergence_curve]

plt.plot(generations, costs)
plt.xlabel('Generation')
plt.ylabel('Best Cost')
plt.title('GA Convergence Curve')
plt.show()
```

## 文件结构

```
VPRL/
├── __init__.py                 # 包初始化
├── config.py                   # 配置管理
├── config.json                 # 默认配置
├── instance_decomposer.py      # MDVRP分解
├── solution_converter.py       # 格式转换
├── vprl_sampler.py            # 主协调器
├── ga_java_wrapper.py         # GA_Java包装器
├── examples/
│   └── basic_usage.py         # 基本使用示例
└── README.md                   # 本文档
```

## 故障排除

### 1. 模型文件未找到

```
Error: Model file not found: models/vrpl_cvrp100.ckpt
```

**解决方案**: 
- 确保模型文件存在于指定路径
- 或修改配置文件中的`model_path`
- 或训练新模型

### 2. Java环境问题

```
Error: Java not found!
```

**解决方案**:
- 安装JDK 11或更高版本
- 设置JAVA_HOME环境变量

### 3. VRPL生成失败

系统会自动回退到纯GA_Java求解，不会崩溃。检查日志了解详细错误信息。

### 4. GPU内存不足

```
Error: CUDA out of memory
```

**解决方案**:
- 在配置中设置`device="cpu"`
- 或减少`num_solutions_needed`

## 示例

查看`examples/`目录获取更多示例：

- `basic_usage.py`: 基本使用示例
- 更多示例即将添加...

## 许可证

本项目遵循MIT许可证。

## 贡献

欢迎提交Issue和Pull Request！

## 联系方式

如有问题，请联系项目维护者。
