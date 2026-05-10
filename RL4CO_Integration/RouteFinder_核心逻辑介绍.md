# RouteFinder 核心逻辑介绍

## 📚 概述

**RouteFinder** 是一个基于深度强化学习的**车辆路径问题（VRP）基础模型**，旨在成为 VRP 领域的"通用求解器"。

### 核心特点
- 🌍 **多变体支持**: 支持 48 种 VRP 变体（CVRP, VRPTW, MDVRP 等）
- 🧠 **基础模型**: 一个模型解决多种 VRP 问题
- ⚡ **高效推理**: 使用预训练模型快速生成解
- 🎯 **SOTA 性能**: 在多个基准测试上达到最先进水平

---

## 🏗️ 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    RouteFinder 架构                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  输入层                编码器              解码器    输出层  │
│  ┌──────┐           ┌────────┐          ┌──────┐  ┌──────┐ │
│  │ VRP  │  ────>    │ Trans- │  ────>   │ Auto-│  │ 路径 │ │
│  │ 实例 │           │ former │          │ regr.│  │ 解   │ │
│  └──────┘           └────────┘          └──────┘  └──────┘ │
│     ↓                   ↓                   ↓         ↓     │
│  坐标、需求         特征嵌入            注意力机制   动作序列│
│  容量、时间窗       位置编码            指针网络     车辆路径│
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔑 核心组件

### 1. 环境（Environment）

**位置**: `routefinder/envs/`

**作用**: 定义 VRP 问题的状态空间和动作空间

#### 主要环境类型：

| 环境 | 文件 | 支持的变体 |
|------|------|-----------|
| **MTVRP** | `mtvrp/env.py` | 单仓库 VRP（32种变体） |
| **MTDVRP** | `mtdvrp/env.py` | 多仓库 VRP（16种变体） |

#### 环境核心方法：

```python
class MTVRPEnv:
    def reset(self, td):
        """重置环境，初始化状态"""
        # 设置初始位置（depot）
        # 初始化容量、时间等约束
        return td_reset
    
    def step(self, td, action):
        """执行动作，更新状态"""
        # 移动到选择的客户
        # 更新容量、时间、距离
        # 检查约束是否满足
        return td_next
    
    def get_reward(self, td, actions):
        """计算奖励（通常是负的总距离）"""
        return -total_distance
    
    def load_data(self, fpath):
        """从 NPZ 文件加载问题实例"""
        return tensordict
```

#### 状态表示（TensorDict）：

```python
{
    'locs': [batch, n_nodes, 2],        # 节点坐标
    'demand': [batch, n_nodes],         # 客户需求
    'capacity': [batch, 1],             # 车辆容量
    'time_windows': [batch, n_nodes, 2], # 时间窗（如果有）
    'current_node': [batch],            # 当前位置
    'visited': [batch, n_nodes],        # 访问标记
    'used_capacity': [batch],           # 已用容量
    'current_time': [batch],            # 当前时间
    ...
}
```

---

### 2. 模型（Model）

**位置**: `routefinder/models/`

#### 2.1 编码器（Encoder）

**作用**: 将 VRP 实例编码为特征表示

```python
class RouteFinderEncoder:
    def __init__(self):
        self.init_embedding = InitEmbedding()  # 初始嵌入
        self.transformer_layers = nn.ModuleList([
            TransformerLayer() for _ in range(n_layers)
        ])
    
    def forward(self, td):
        # 1. 初始嵌入
        h = self.init_embedding(td)  # [batch, n_nodes, embed_dim]
        
        # 2. Transformer 层
        for layer in self.transformer_layers:
            h = layer(h)  # 自注意力 + FFN
        
        return h  # 编码后的节点特征
```

**关键技术**：
- **Transformer 架构**: 使用多头自注意力机制
- **位置编码**: 编码节点的空间位置
- **特征融合**: 融合坐标、需求、时间窗等多种特征

#### 2.2 解码器（Decoder）

**作用**: 自回归地生成访问序列

```python
class RouteFinderDecoder:
    def __init__(self):
        self.pointer_network = PointerAttention()
    
    def forward(self, h_encoded, td):
        actions = []
        
        while not all_done(td):
            # 1. 计算注意力分数
            logits = self.pointer_network(
                query=h_current,      # 当前状态
                key=h_encoded,        # 所有节点特征
                mask=get_mask(td)     # 不可行动作掩码
            )
            
            # 2. 采样动作
            action = sample_action(logits, temperature)
            actions.append(action)
            
            # 3. 更新环境
            td = env.step(td, action)
        
        return actions
```

**关键技术**：
- **指针网络（Pointer Network）**: 使用注意力机制选择下一个节点
- **掩码机制**: 屏蔽不可行的动作（已访问、容量不足等）
- **采样策略**: 
  - **Greedy**: 选择概率最高的动作
  - **Sampling**: 按概率分布采样（训练时）

---

### 3. 策略（Policy）

**位置**: `routefinder/models/policy.py`

**作用**: 整合编码器和解码器，定义完整的决策策略

```python
class RouteFinderPolicy:
    def __init__(self):
        self.encoder = RouteFinderEncoder()
        self.decoder = RouteFinderDecoder()
    
    def forward(self, td, env, phase="train"):
        # 1. 编码
        h = self.encoder(td)
        
        # 2. 解码
        if phase == "train":
            # 训练时：采样多个解
            actions, log_probs = self.decoder.sample(h, td, env)
        else:
            # 推理时：贪心或采样
            actions = self.decoder.greedy(h, td, env)
        
        # 3. 计算奖励
        reward = env.get_reward(td, actions)
        
        return actions, reward, log_probs
```

---

### 4. 训练算法

#### 4.1 POMO (Policy Optimization with Multiple Optima)

**核心思想**: 从多个起点同时优化，增加解的多样性

```python
def pomo_training(policy, env, batch):
    # 1. 从每个节点作为起点
    num_starts = batch['locs'].shape[1]
    
    rewards = []
    log_probs = []
    
    for start_node in range(num_starts):
        # 设置起点
        td = env.reset(batch, start_node=start_node)
        
        # 生成解
        actions, reward, log_prob = policy(td, env)
        
        rewards.append(reward)
        log_probs.append(log_prob)
    
    # 2. 选择最好的解作为 baseline
    baseline = rewards.max(dim=0)
    
    # 3. 计算 policy gradient loss
    advantage = rewards - baseline
    loss = -(advantage * log_probs).mean()
    
    return loss
```

#### 4.2 强化学习训练流程

```python
def train_routefinder():
    for epoch in range(num_epochs):
        for batch in dataloader:
            # 1. 前向传播
            actions, rewards, log_probs = policy(batch, env)
            
            # 2. 计算损失
            loss = compute_reinforce_loss(rewards, log_probs)
            
            # 3. 反向传播
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            # 4. 记录指标
            avg_reward = rewards.mean()
            log_metrics(avg_reward, loss)
```

---

## 🔄 推理流程（你的项目中使用的）

### 在 VPRL 中的使用

```python
# VPRL/vprl_sampler.py

class VPRLSampler:
    def _load_model(self, model_path):
        """加载 RouteFinder 模型"""
        from routefinder.models import RouteFinderBase
        
        # 加载 checkpoint
        checkpoint = torch.load(model_path)
        
        # 创建模型
        self.model = RouteFinderBase(**checkpoint['hyper_parameters'])
        self.model.load_state_dict(checkpoint['state_dict'])
        self.model.eval()
    
    def sample_solutions(self, problem_data, num_samples=20):
        """生成多个解"""
        # 1. 准备数据
        td = self.prepare_tensordict(problem_data)
        
        # 2. 采样多次
        solutions = []
        for i in range(num_samples):
            # 设置随机种子以获得不同的解
            td_clone = td.clone()
            
            # 生成解
            with torch.no_grad():
                actions = self.model.policy(
                    td_clone, 
                    self.env,
                    decode_type="sampling",  # 采样模式
                    temperature=1.0
                )
            
            # 转换为解格式
            solution = self.actions_to_routes(actions, problem_data)
            solutions.append(solution)
        
        # 3. 选择最好的解
        best_solutions = sorted(solutions, key=lambda x: x['cost'])[:num_needed]
        
        return best_solutions
```

---

## 📊 数据流

### 1. 输入数据格式（NPZ）

```python
# NPZ 文件结构
{
    'locs': np.array([[x1, y1], [x2, y2], ...]),  # 坐标
    'demand': np.array([d1, d2, ...]),            # 需求
    'capacity': np.array([C]),                     # 容量
    'time_windows': np.array([[e1, l1], ...]),    # 时间窗（可选）
    'duration_limit': np.array([L]),              # 距离限制（可选）
    ...
}
```

### 2. 中间表示（TensorDict）

```python
# PyTorch TensorDict
td = TensorDict({
    'locs': torch.tensor(...),
    'demand': torch.tensor(...),
    'current_node': torch.tensor([0]),  # 从 depot 开始
    'visited': torch.zeros(n_nodes),
    'used_capacity': torch.tensor([0.0]),
    ...
}, batch_size=[batch_size])
```

### 3. 输出格式（Actions）

```python
# 动作序列
actions = [0, 3, 5, 7, 0, 2, 4, 6, 0]
#          ↑  ↑  ↑  ↑  ↑  ↑  ↑  ↑  ↑
#       depot → 客户 → depot → 客户 → depot
#       (路径1)        (路径2)
```

---

## 🎯 关键技术点

### 1. 注意力机制（Attention）

```python
def attention(query, key, value, mask=None):
    """
    query: [batch, 1, dim]      # 当前状态
    key:   [batch, n_nodes, dim] # 所有节点
    value: [batch, n_nodes, dim] # 节点特征
    """
    # 计算相似度
    scores = torch.matmul(query, key.transpose(-2, -1)) / sqrt(dim)
    
    # 应用掩码（屏蔽不可行动作）
    if mask is not None:
        scores = scores.masked_fill(mask, -1e9)
    
    # Softmax 得到概率分布
    attn_weights = F.softmax(scores, dim=-1)
    
    # 加权求和
    output = torch.matmul(attn_weights, value)
    
    return output, attn_weights
```

### 2. 掩码机制（Masking）

```python
def get_action_mask(td):
    """生成不可行动作的掩码"""
    mask = torch.zeros(batch_size, n_nodes, dtype=torch.bool)
    
    # 1. 已访问的节点
    mask |= td['visited']
    
    # 2. 容量不足的节点
    remaining_capacity = td['capacity'] - td['used_capacity']
    mask |= (td['demand'] > remaining_capacity)
    
    # 3. 时间窗约束（如果有）
    if 'time_windows' in td:
        current_time = td['current_time']
        latest_time = td['time_windows'][:, :, 1]
        mask |= (current_time > latest_time)
    
    # 4. 距离限制（如果有）
    if 'duration_limit' in td:
        distance_to_node = get_distance(td['current_node'], nodes)
        distance_to_depot = get_distance(nodes, depot)
        total_distance = td['current_distance'] + distance_to_node + distance_to_depot
        mask |= (total_distance > td['duration_limit'])
    
    return mask
```

### 3. 多变体支持

```python
class UnifiedVRPEnv:
    """统一的 VRP 环境，支持多种变体"""
    
    def __init__(self, variant_config):
        self.has_capacity = variant_config.get('capacity', True)
        self.has_time_windows = variant_config.get('time_windows', False)
        self.has_backhaul = variant_config.get('backhaul', False)
        self.has_open_route = variant_config.get('open_route', False)
        self.has_duration_limit = variant_config.get('duration_limit', False)
        self.is_multi_depot = variant_config.get('multi_depot', False)
    
    def step(self, td, action):
        """根据变体配置执行不同的逻辑"""
        # 基础更新
        td = self._update_location(td, action)
        
        # 容量约束
        if self.has_capacity:
            td = self._update_capacity(td, action)
        
        # 时间窗约束
        if self.has_time_windows:
            td = self._update_time(td, action)
        
        # Backhaul 逻辑
        if self.has_backhaul:
            td = self._handle_backhaul(td, action)
        
        # ... 其他约束
        
        return td
```

---

## 🔧 在你的项目中的应用

### 工作流程

```
1. 问题输入（Cordeau 格式）
   ↓
2. 转换为 NPZ 格式
   ├─ 坐标归一化
   ├─ 客户分配到 depot
   └─ 创建 TensorDict
   ↓
3. RouteFinder 推理
   ├─ 加载预训练模型
   ├─ 采样多个解（20-50个）
   └─ 选择最优解
   ↓
4. 转换为 GA 格式
   ├─ 解码动作序列
   ├─ 构建路径
   └─ 生成初始种群 JSON
   ↓
5. GA 算法使用
   └─ 作为高质量初始解
```

### 关键代码位置

| 功能 | 文件 | 说明 |
|------|------|------|
| **模型加载** | `VPRL/vprl_sampler.py` | 加载 RouteFinder checkpoint |
| **环境定义** | `routefinder/envs/mtvrp/env.py` | CVRP/MDVRP 环境 |
| **策略网络** | `routefinder/models/policy.py` | 编码器+解码器 |
| **推理脚本** | `routefinder/test.py` | 官方测试脚本 |

---

## 📈 性能特点

### 优势
- ✅ **快速推理**: GPU 上 0.1-0.2 秒/实例
- ✅ **高质量解**: 通常在 BKS 的 5-10% 以内
- ✅ **多样性**: 采样可以生成多个不同的解
- ✅ **泛化能力**: 一个模型适用多种规模

### 局限
- ⚠️ **Gap 较大**: 相比精确算法，解质量有差距
- ⚠️ **需要 GPU**: CPU 推理较慢
- ⚠️ **模型较大**: Checkpoint 约 15-50 MB

---

## 🎓 总结

RouteFinder 的核心逻辑：

1. **编码器**: Transformer 编码 VRP 实例特征
2. **解码器**: 指针网络自回归生成访问序列
3. **强化学习**: POMO 算法训练策略网络
4. **多变体**: 统一框架支持 48 种 VRP 变体
5. **快速推理**: 预训练模型快速生成高质量解

**在你的项目中的作用**:
- 为 GA 算法提供高质量的初始种群
- 通过 VPRL 模块集成到混合算法中
- 显著提升算法的收敛速度和解质量

---

## 📚 参考资料

- **论文**: [RouteFinder: Towards Foundation Models for Vehicle Routing Problems](https://arxiv.org/abs/2406.15007)
- **代码**: [GitHub - ai4co/routefinder](https://github.com/ai4co/routefinder)
- **基础框架**: [RL4CO](https://github.com/ai4co/rl4co)
