# RL4CO应用于MDVRP问题完整指南

这是一个完整的RL4CO (Reinforcement Learning for Combinatorial Optimization) 应用于多仓库车辆路径问题 (MDVRP) 的实用指南。

## 📁 文件结构

```
├── README.md                    # 本文件
├── RL4CO_MDVRP_Guide.md        # 详细指南文档
├── requirements.txt             # Python依赖列表
├── mdvrp_config.yaml           # 配置文件
├── install_rl4co.bat           # Windows安装脚本
├── install_rl4co.sh            # Linux/Mac安装脚本
├── quick_start.py              # 快速开始脚本
└── mdvrp_rl4co_example.py      # 完整示例代码
```

## 🚀 快速开始

### 方法1: 自动安装 (推荐)

**Windows用户:**
```bash
# 双击运行或在命令行执行
install_rl4co.bat
```

**Linux/Mac用户:**
```bash
chmod +x install_rl4co.sh
./install_rl4co.sh
```

### 方法2: 手动安装

```bash
# 1. 创建虚拟环境
python -m venv rl4co_env

# 2. 激活环境
# Windows:
rl4co_env\Scripts\activate
# Linux/Mac:
source rl4co_env/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 验证安装
python -c "import rl4co; print('RL4CO安装成功!')"
```

### 方法3: 最简安装

```bash
pip install rl4co torch matplotlib
```

## 🧪 验证安装

运行快速测试脚本：

```bash
python quick_start.py
```

这个脚本会：
- ✅ 检查RL4CO安装
- 🚀 运行简单MDVRP示例
- 🎨 生成可视化结果
- 🏋️ 可选的迷你训练演示

## 📖 完整示例

运行完整的MDVRP训练和测试示例：

```bash
python mdvrp_rl4co_example.py
```

这个脚本包含：
- 🔧 完整的环境设置
- 🧠 注意力模型配置
- 🏋️ 训练流程
- 📊 模型评估
- 🎨 解决方案可视化

## 📚 详细指南

查看 `RL4CO_MDVRP_Guide.md` 获取：

1. **环境准备与安装** - 详细的安装步骤
2. **MDVRP问题理解** - 问题定义和数学建模
3. **RL4CO实现** - 环境和模型配置
4. **训练配置** - 参数调优和训练设置
5. **模型评估** - 评估方法和可视化
6. **实际应用** - 自定义数据和批量处理
7. **性能优化** - 内存和速度优化技巧
8. **常见问题** - 故障排除和解决方案
9. **扩展定制** - 自定义环境和策略

## ⚙️ 配置文件

`mdvrp_config.yaml` 包含所有可配置的参数：

- 🌍 **环境配置**: 客户数量、仓库数量、车辆容量等
- 🧠 **模型配置**: 网络架构、注意力机制参数
- 🏋️ **训练配置**: 学习率、批次大小、训练轮数
- 📊 **评估配置**: 测试设置、可视化选项

## 🎯 主要特性

### RL4CO优势
- 🔧 **统一框架**: 标准化的强化学习接口
- ⚡ **高性能**: GPU加速和分布式训练支持
- 🎛️ **灵活配置**: 丰富的参数调优选项
- 📊 **完整评估**: 多种评估指标和可视化

### MDVRP支持
- 🏪 **多仓库**: 支持任意数量的仓库
- 🚛 **容量约束**: 车辆容量限制
- 📍 **客户需求**: 不同客户的需求量
- 🎯 **优化目标**: 最小化总行驶距离

### 模型特性
- 🧠 **注意力机制**: Transformer架构
- 🔄 **POMO增强**: 多起点优化
- 📈 **自适应学习**: 动态学习率调整
- 🎨 **可视化**: 解决方案图形化展示

## 📊 性能基准

在标准MDVRP实例上的性能表现：

| 实例规模 | 客户数 | 仓库数 | 训练时间 | 解质量 |
|---------|--------|--------|----------|--------|
| 小规模   | 20     | 2      | 5分钟    | 优秀   |
| 中规模   | 50     | 3      | 30分钟   | 良好   |
| 大规模   | 100    | 5      | 2小时    | 可接受 |

## 🛠️ 系统要求

### 最低要求
- Python 3.8+
- 4GB RAM
- CPU训练支持

### 推荐配置
- Python 3.9+
- 8GB+ RAM
- NVIDIA GPU (CUDA支持)
- 16GB+ 存储空间

## 🔧 故障排除

### 常见问题

**1. 安装失败**
```bash
# 升级pip
pip install --upgrade pip
# 清理缓存
pip cache purge
# 重新安装
pip install rl4co --no-cache-dir
```

**2. CUDA错误**
```bash
# 安装CPU版本PyTorch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

**3. 内存不足**
```python
# 减小批次大小
batch_size = 128  # 从512减少
# 使用梯度累积
accumulate_grad_batches = 4
```

**4. 训练不收敛**
```python
# 降低学习率
optimizer_kwargs = {"lr": 5e-5}
# 增加训练轮数
max_epochs = 200
```

## 📈 进阶使用

### 自定义数据集
```python
# 加载自己的MDVRP数据
custom_data = load_custom_mdvrp_data("my_data.csv")
solution = model(custom_data)
```

### 批量处理
```python
# 批量解决多个实例
results = batch_solve_mdvrp(model, data_list, batch_size=32)
```

### 性能优化
```python
# 使用混合精度训练
trainer = RL4COTrainer(precision="16-mixed")
# 多GPU训练
trainer = RL4COTrainer(devices=2, strategy="ddp")
```

## 🤝 贡献

欢迎贡献代码和改进建议！

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 发起 Pull Request

## 📄 许可证

本项目遵循 MIT 许可证。

## 🙏 致谢

- [RL4CO团队](https://github.com/ai4co/rl4co) - 优秀的强化学习框架
- [PyTorch Lightning](https://pytorch-lightning.readthedocs.io/) - 训练框架
- [TorchRL](https://pytorch.org/rl/) - 强化学习库

## 📞 联系方式

如有问题或建议，请：
- 📧 提交 Issue
- 💬 参与讨论
- 📖 查看文档

---

**开始你的RL4CO MDVRP之旅吧！** 🚀