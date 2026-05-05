# RouteFinder 简明使用指南

## 快速开始

### 1. 环境安装
```bash
conda create -n GD python=3.9
conda activate GD
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install tensordict torchrl rl4co lightning scikit-learn
```

### 2. 测试CVRP
```bash
cd routefinder
python test.py --checkpoint checkpoints/100/rf-transformer.ckpt \
               --datasets data/cvrp/test/100.npz \
               --device cuda
```

### 3. 求解P21 MDVRP
```bash
python solve_p21_simple.py
```

## 核心文件

### 成功的实现
- ✅ `solve_p21_simple.py` - P21 MDVRP求解器（K-Means + 采样）
- ✅ `routefinder/test.py` - 官方测试脚本（已修复TorchRL兼容性）
- ✅ `quick_test.py` - 快速测试脚本

### 文档
- 📖 `RouteFinder成功使用指南.md` - **完整使用文档（推荐阅读）**
- 📖 `RL4CO_CVRP_使用指南.md` - CVRP基础使用
- 📖 `RL4CO_MDVRP_调研报告.md` - MDVRP调研
- 📖 `VRP深度学习项目对比.md` - 项目对比

### 其他有用的脚本
- `generate_p01_sampling.py` - P01数据集采样
- `solve_p01_with_routefinder.py` - P01求解
- `test_p01_sampling.py` - P01测试

## 关键技术点

### TorchRL兼容性修复
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

### 避免TensorDict副作用
```python
td_original = env.load_data(npz_path).to(device)

for i in range(num_samples):
    td = td_original.clone()  # 关键：每次克隆
    td_reset = env.reset(td)
    out = policy(td_reset, env, decode_type="sampling")
```

## 性能指标

### CVRP-100
- 平均Gap: 4.2%
- 推理速度: 0.14秒/实例 (GPU)

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

## 常见问题

### Q: 出现"CompositeSpec not found"错误？
A: 添加TorchRL兼容性修复代码（见上方）

### Q: 出现"size of tensor a (X) must match size of tensor b (Y)"错误？
A: 在循环中使用`td.clone()`避免副作用

### Q: Windows下出现Unicode编码错误？
A: 避免使用emoji，使用ASCII字符

## 更多信息

详细文档请参考：`RouteFinder成功使用指南.md`
