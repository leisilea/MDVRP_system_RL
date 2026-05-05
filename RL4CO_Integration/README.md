# RL4CO Integration - RouteFinder

使用RouteFinder预训练模型求解VRP问题（CVRP、MDVRP等）

## 快速开始

### 环境安装
```bash
conda create -n GD python=3.9
conda activate GD
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install tensordict torchrl rl4co lightning scikit-learn
```

### 测试CVRP
```bash
cd routefinder
python test.py --checkpoint checkpoints/100/rf-transformer.ckpt \
               --datasets data/cvrp/test/100.npz \
               --device cuda
```

### 求解P21 MDVRP
```bash
python solve_p21_simple.py
```

## 文档导航

### 📖 主要文档
- **[RouteFinder成功使用指南.md](RouteFinder成功使用指南.md)** - 完整使用文档（推荐阅读）
- **[README_简明指南.md](README_简明指南.md)** - 快速参考

### 📚 参考文档
- [RL4CO_CVRP_使用指南.md](RL4CO_CVRP_使用指南.md) - CVRP基础使用
- [RL4CO_MDVRP_调研报告.md](RL4CO_MDVRP_调研报告.md) - MDVRP调研
- [VRP深度学习项目对比.md](VRP深度学习项目对比.md) - 项目对比

## 核心文件

### ✅ 成功的实现
- `solve_p21_simple.py` - P21 MDVRP求解器（K-Means + 采样）
- `routefinder/test.py` - 官方测试脚本（已修复兼容性）
- `quick_test.py` - 快速测试脚本

### 🔧 其他工具
- `generate_p01_sampling.py` - P01数据集采样
- `solve_p01_with_routefinder.py` - P01求解
- `test_p01_sampling.py` - P01测试
- `train_rl4co_cvrp.py` - CVRP训练（实验性）
- `use_pretrained_model.py` - 预训练模型使用示例

## 性能指标

### CVRP-100
- 平均Gap: 4.2%
- 推理速度: 0.14秒/实例 (RTX 3060)

### P21 MDVRP
- 360客户，9 depot
- K-Means分割: 每depot 40客户
- 总耗时: 27.53秒 (GPU)
- **归一化总成本**: 88.11
- **真实距离总成本**: 12460.20
- **P21 BKS (最优解)**: 5474.84
- **Gap**: 127.6% (相比BKS)

**注意**: Gap较大的原因：
1. K-Means简单分割未优化（未考虑容量和距离约束）
2. 各depot独立求解，未全局优化
3. 模型在CVRP上训练，非MDVRP专用
4. 这是一个快速原型，主要验证技术可行性

## 关键技术点

### 1. TorchRL兼容性修复
新版TorchRL改变了API，需要添加名称映射：
```python
import torchrl.data.tensor_specs as specs
if not hasattr(specs, 'CompositeSpec'):
    specs.CompositeSpec = specs.Composite
# ... 其他映射
```

### 2. 避免TensorDict副作用
`env.reset(td)`会修改传入的TensorDict，循环采样时需要克隆：
```python
td_original = env.load_data(npz_path).to(device)
for i in range(num_samples):
    td = td_original.clone()  # 关键
    td_reset = env.reset(td)
```

## 项目结构

```
RL4CO_Integration/
├── routefinder/              # RouteFinder官方代码
│   ├── checkpoints/          # 预训练模型
│   ├── data/                 # 测试数据
│   └── test.py              # 测试脚本（已修复）
├── solve_p21_simple.py      # P21 MDVRP求解器
├── quick_test.py            # 快速测试
├── p21_solutions/           # P21求解结果
└── 文档/                    # 各种使用指南
```

## 常见问题

### Q: 出现"CompositeSpec not found"错误？
A: 添加TorchRL兼容性修复代码

### Q: 出现维度不匹配错误？
A: 在循环中使用`td.clone()`

### Q: Windows下Unicode编码错误？
A: 避免使用emoji，使用ASCII字符

## 参考资料

- RouteFinder论文: https://arxiv.org/abs/2402.16891
- RL4CO: https://github.com/ai4co/rl4co
- TorchRL: https://pytorch.org/rl/

## License

本项目基于RouteFinder官方代码，遵循其原始License。
