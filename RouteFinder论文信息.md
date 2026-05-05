# RouteFinder 论文信息

## 基本信息

**论文标题**: RouteFinder: Towards Foundation Models for Vehicle Routing Problems

**作者**: 
- Federico Berto
- Chuanbo Hua
- Nayeli Gast Zepeda
- André Hottung
- Niels Wouda
- Leon Lan
- Junyoung Park
- Kevin Tierney
- Jinkyoo Park

**发表信息**:
- **期刊**: Transactions on Machine Learning Research (TMLR)
- **年份**: 2025
- **接收状态**: 已接收 (Accepted at TMLR 2025)

**会议展示**:
- **ICML 2024 FM-Wild Workshop** - Oral Presentation (口头报告)
- Workshop主题: Foundation Models in the Wild

## 论文链接

- **arXiv**: https://arxiv.org/abs/2406.15007
- **OpenReview**: https://openreview.net/forum?id=QzGLoaOPiY
- **GitHub**: https://github.com/ai4co/routefinder
- **HuggingFace Models**: https://huggingface.co/ai4co/routefinder
- **HuggingFace Dataset**: https://huggingface.co/datasets/ai4co/routefinder

## 核心贡献

### 1. Foundation Model for VRP
RouteFinder是第一个针对车辆路径问题（VRP）的基础模型（Foundation Model），能够处理多种VRP变体。

### 2. 支持48种VRP变体
从最初的24种变体扩展到48种，包括：
- TSP (Traveling Salesman Problem)
- CVRP (Capacitated VRP)
- VRPTW (VRP with Time Windows)
- MDVRP (Multi-Depot VRP)
- 以及各种组合变体

### 3. 预训练模型
提供多个规模的预训练模型：
- 50客户
- 100客户
- 200客户

### 4. 多种模型架构
- **RouteFinder-POMO**: 基于POMO的模型
- **RouteFinder-MoE**: 混合专家模型（Mixture of Experts）
- **RouteFinder-Transformer**: 基于Transformer的模型

## 技术特点

### 多任务学习
通过多任务学习（Multi-Task Learning）训练单一模型处理多种VRP变体，而不是为每种变体训练单独的模型。

### 零样本泛化
模型能够在未见过的VRP变体上进行零样本推理（Zero-shot Inference），展现出良好的泛化能力。

### 高效推理
- 推理速度极快（0.05-0.14秒/实例）
- 支持GPU加速
- 支持批量处理

## 与RL4CO的关系

RouteFinder是基于RL4CO框架开发的：
- **RL4CO**: 一个用于组合优化的强化学习框架
- **RouteFinder**: 在RL4CO基础上构建的VRP专用基础模型
- 两者由同一团队（AI4CO）开发维护

## 版本历史

- **v0.4.0** (2025年9月): 
  - 改进安装说明
  - 在HuggingFace发布模型和数据集
  - TMLR 2025接收

- **v0.3.0** (2025年2月):
  - VRP变体从24种扩展到48种
  - 多项改进

- **v0.2.0** (2024年10月):
  - 添加预印本的最新贡献
  - 代码库大幅改进

- **v0.1.0** (2024年7月):
  - ICML 2024 FM-Wild Workshop口头报告

## 引用格式

### BibTeX
```bibtex
@article{berto2025routefinder,
  title={{RouteFinder: Towards Foundation Models for Vehicle Routing Problems}},
  author={Federico Berto and Chuanbo Hua and Nayeli Gast Zepeda and Andr{\'e} Hottung and Niels Wouda and Leon Lan and Junyoung Park and Kevin Tierney and Jinkyoo Park},
  journal={Transactions on Machine Learning Research},
  year={2025},
  url={https://openreview.net/forum?id=QzGLoaOPiY}
}
```

### 文本引用
Berto, F., Hua, C., Zepeda, N. G., Hottung, A., Wouda, N., Lan, L., Park, J., Tierney, K., & Park, J. (2025). RouteFinder: Towards Foundation Models for Vehicle Routing Problems. Transactions on Machine Learning Research.

## 在你的项目中的使用

在你的项目中，RouteFinder被用于：

1. **GA+RL混合初始化**: 使用RouteFinder生成高质量的初始解（种子解）
2. **MDVRP求解**: 通过将MDVRP分解为多个CVRP子问题，使用RouteFinder求解每个子问题
3. **快速推理**: 利用RouteFinder的快速推理能力生成初始种群

### 你的实现特点
- 使用RouteFinder的预训练模型（无需训练）
- 每个depot采样20个解，选择最优解
- RL种子占种群的20%（20个个体）
- 与纯GA相比，平均Gap降低0.46个百分点

## 相关资源

- **AI4CO社区**: https://ai4co.org/
- **Slack讨论组**: https://join.slack.com/t/ai4co-community/shared_invite/zt-3jsdjs3ec-3KHdV3HwanL884mq_9tyYw
- **RL4CO框架**: https://github.com/ai4co/rl4co
- **RL4CO文档**: https://rl4co.readthedocs.io/

## 总结

RouteFinder是一个创新的VRP基础模型，它：
- ✅ 提供预训练模型，无需长时间训练
- ✅ 支持多种VRP变体（包括MDVRP）
- ✅ 推理速度极快
- ✅ 在TMLR 2025发表，学术认可度高
- ✅ 活跃维护，持续更新

这使得它成为你的GA+RL混合算法的理想选择，能够快速生成高质量的初始解，提升整体求解性能。

---

**创建时间**: 2026-04-13  
**最后更新**: 2026-04-13  
**版本**: v1.0
