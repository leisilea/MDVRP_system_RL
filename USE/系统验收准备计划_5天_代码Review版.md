# 系统验收准备计划（5天）- 代码Review重点版

## 验收时间：2026年5月8日（周五）
## 准备周期：2026年5月3日-5月7日

---

## 📋 验收准备总览

### 核心目标
1. **深入理解代码**（50%）- 搞懂每个文件的作用，特别是RL部分
2. **系统功能演示**（30%）- 展示核心功能和用户操作流程
3. **技术问题准备**（20%）- 预测技术问题并准备答案

### 代码结构概览

```
项目根目录/
├── system_test/                    # 系统测试主目录
│   ├── frontend/                   # Vue.js前端
│   ├── backend/                    # Spring Boot后端
│   ├── algorithm-service/          # Flask算法服务
│   └── ga_mdvrp_reproduction/      # Java GA实现
├── RL4CO_Integration/              # RL4CO深度学习集成
│   └── routefinder/                # RouteF深度学习模型
├── VPRL/                           # VPRL包装器
└── MDVRP-Instances/                # 测试算例
```

---

## 📅 Day 1：核心算法代码Review（5月3日 周日）

### 🎯 目标
理解PSO、ACO、GA三个核心算法的实现

### ✅ 任务清单

#### 1.1 PSO算法代码Review（2小时）
**文件位置**：`system_test/algorithm-service/solver/pso.py`

**Review重点**：
- [ ] **类结构**：`PSO_MDVRP`类的初始化参数
- [ ] **粒子表示**：粒子如何编码路径（position, velocity）
- [ ] **适应度函数**：如何计算总成本
- [ ] **速度更新**：`update_velocity()`方法的实现
- [ ] **位置更新**：`update_position()`方法的实现
- [ ] **约束处理**：容量约束如何满足
- [ ] **主循环**：`solve()`方法的迭代逻辑

**关键问题**：
- PSO的粒子如何表示MDVRP的路径？
- 速度和位置更新公式是什么？
- 如何保证生成的路径是可行的？

#### 1.2 ACO算法代码Review（2小时）
**文件位置**：`system_test/algorithm-service/solver/aco.py`

**Review重点**：
- [ ] **类结构**：`ACO_MDVRP`类的初始化参数
- [ ] **信息素矩阵**：如何初始化和更新
- [ ] **启发式信息**：距离的倒数作为启发
- [ ] **路径构建**：蚂蚁如何选择下一个节点
- [ ] **信息素更新**：全局更新和局部更新
- [ ] **信息素挥发**：evaporation_rate的作用
- [ ] **多进程并行**：如何实现并行计算

**关键问题**：
- 信息素矩阵的维度是多少？
- 蚂蚁选择下一个节点的概率公式是什么？
- 多进程如何分配蚂蚁？

#### 1.3 GA算法代码Review（2小时）
**文件位置**：`system_test/ga_mdvrp_reproduction/GA-MDVRP/src/GA/Algorithm.java`

**Review重点**：
- [ ] **染色体表示**：`Individual`类如何编码路径
- [ ] **初始化**：`initializePopulation()`方法
- [ ] **选择算子**：锦标赛选择（Tournament Selection）
- [ ] **交叉算子**：`crossover()`方法的实现
- [ ] **变异算子**：`mutate()`方法的实现
- [ ] **适应度评估**：`evaluateFitness()`方法
- [ ] **精英保留**：Elitism策略

**关键问题**：
- 染色体如何表示多仓库多车辆的路径？
- 交叉和变异如何保证路径可行性？
- 精英保留保留多少个体？

---

## 📅 Day 2：深度学习集成代码Review（RL重点）（5月4日 周一）

### 🎯 目标
深入理解RL4CO和RouteF的集成方式

### ✅ 任务清单

#### 2.1 RL4CO集成架构Review（3小时）
**文件位置**：`RL4CO_Integration/`

**核心文件**：
1. `RL4CO_MDVRP_调研报告.md` - 先读这个了解背景
2. `README.md` - 了解使用方式
3. `generate_solutions.py` - RL4CO如何生成解
4. `train_rl4co_cvrp.py` - 如何训练模型（如果有）
5. `use_pretrained_model.py` - 如何使用预训练模型

**Review重点**：
- [ ] **RL4CO是什么**：强化学习框架，用于组合优化
- [ ] **模型架构**：Attention机制（Transformer）
- [ ] **输入格式**：如何将MDVRP实例转换为RL4CO输入
- [ ] **输出格式**：RL4CO输出的解如何转换回路径
- [ ] **采样策略**：Greedy vs Sampling
- [ ] **多仓库处理**：如何将MDVRP分解为多个CVRP子问题

**关键问题**：
- RL4CO原生支持MDVRP吗？（答案：不支持，需要分解）
- 如何将MDVRP分解为CVRP？（答案：按仓库分解）
- RL4CO生成的解质量如何？

#### 2.2 RouteF集成代码Review（3小时）
**文件位置**：`RL4CO_Integration/routefinder/`

**核心文件**：
1. `README.md` - 了解RouteF项目
2. `routefinder/models/` - 模型定义
3. `routefinder/rl/` - 强化学习训练代码
4. `test.py` - 测试脚本
5. `run.py` - 运行脚本

**Review重点**：
- [ ] **RouteF是什么**：基于RL4CO的VRP求解器
- [ ] **模型加载**：如何加载预训练checkpoint
- [ ] **推理过程**：如何使用模型生成解
- [ ] **采样机制**：如何生成多个解（sampling）
- [ ] **与GA集成**：如何将RouteF解作为GA初始种群

**关键问题**：
- RouteF和RL4CO的关系是什么？（答案：RouteF基于RL4CO）
- 如何加载checkpoint？（答案：使用`torch.load`）
- 采样生成多少个解？（答案：可配置，如100个）

#### 2.3 VPRL包装器代码Review（1小时）
**文件位置**：`VPRL/`

**核心文件**：
1. `__init__.py` - 包初始化
2. `vprl_sampler.py` - 采样器
3. `ga_java_wrapper.py` - Java GA包装器
4. `instance_decomposer.py` - 实例分解器
5. `solution_converter.py` - 解转换器

**Review重点**：
- [ ] **VPRL的作用**：统一接口，连接RL模型和GA
- [ ] **采样流程**：如何调用RouteF生成解
- [ ] **格式转换**：如何将RL解转换为GA格式
- [ ] **错误处理**：如何处理RL模型失败的情况

**关键问题**：
- VPRL是什么的缩写？（Vehicle Path Reinforcement Learning？）
- VPRL如何与Java GA通信？（答案：通过JSON文件）
- 如果RL模型失败怎么办？（答案：回退到随机初始化）

---

## 📅 Day 3：前后端代码Review + 系统集成（5月5日 周二）

### 🎯 目标
理解前后端如何协作，以及算法服务如何集成

### ✅ 任务清单

#### 3.1 后端代码Review（2小时）
**文件位置**：`system_test/backend/src/main/java/com/gz/gd/backend/`

**核心文件**：
1. `controller/AlgorithmController.java` - 算法API控制器
2. `service/AlgorithmService.java` - 算法服务
3. `service/TaskService.java` - 任务管理服务
4. `entity/Task.java` - 任务实体
5. `entity/Solution.java` - 解实体

**Review重点**：
- [ ] **API端点**：`/api/algorithm/solve`等
- [ ] **异步任务**：`@Async`注解的使用
- [ ] **线程池配置**：`ThreadPoolTaskExecutor`
- [ ] **任务状态管理**：PENDING → RUNNING → COMPLETED
- [ ] **与算法服务通信**：`RestTemplate`调用Flask API
- [ ] **数据持久化**：MyBatis-Plus的使用

**关键问题**：
- 后端如何调用算法服务？（答案：HTTP POST请求）
- 异步任务如何实现？（答案：@Async + 线程池）
- 任务状态如何持久化？（答案：数据库）

#### 3.2 前端代码Review（2小时）
**文件位置**：`system_test/frontend/src/`

**核心文件**：
1. `views/AlgorithmCompute.vue` - 算法计算页面
2. `components/MapView.vue` - 地图组件
3. `components/ReplanningDialog.vue` - 重规划对话框
4. `api/algorithm.js` - 算法API客户端
5. `api/replanning.js` - 重规划API客户端

**Review重点**：
- [ ] **页面结构**：Vue组件的组织方式
- [ ] **状态管理**：`ref`和`reactive`的使用
- [ ] **API调用**：`axios`的使用
- [ ] **轮询机制**：如何轮询任务状态
- [ ] **地图可视化**：如何绘制路径
- [ ] **重规划功能**：如何选择阻塞路段

**关键问题**：
- 前端如何轮询任务状态？（答案：`setInterval`每2秒）
- 地图使用什么库？（答案：可能是Leaflet或自定义Canvas）
- 重规划如何选择路段？（答案：点击两个节点）

#### 3.3 算法服务API Review（2小时）
**文件位置**：`system_test/algorithm-service/`

**核心文件**：
1. `app.py` - Flask应用主文件
2. `solver/ga_mdvrp_java.py` - GA算法包装器
3. `solver/pso.py` - PSO算法
4. `solver/aco.py` - ACO算法
5. `replanning/models.py` - 重规划模型

**Review重点**：
- [ ] **API端点**：`/solve/ga`, `/solve/pso`, `/solve/aco`, `/api/replan`
- [ ] **请求格式**：JSON格式的depots, customers, routes
- [ ] **响应格式**：JSON格式的routes, cost, time
- [ ] **算法调用**：如何调用Java GA（subprocess）
- [ ] **重规划逻辑**：如何修改距离矩阵，如何创建临时仓库

**关键问题**：
- Flask如何调用Java GA？（答案：subprocess运行jar）
- 重规划如何实现？（答案：修改距离矩阵 + 临时仓库）
- 如何处理算法失败？（答案：返回错误信息）

---

## 📅 Day 4：重规划功能深入 + 技术问题准备（5月6日 周三）

### 🎯 目标
深入理解重规划功能，准备技术问答

### ✅ 任务清单

#### 4.1 重规划算法代码Review（3小时）
**文件位置**：`system_test/algorithm-service/replanning/`

**核心文件**：
1. `models.py` - 重规划数据模型
2. `replan_service.py` - 重规划服务（如果有）
3. `test_replan_api.py` - 重规划测试

**Review重点**：
- [ ] **输入处理**：如何解析blocked_edges和vehicle_positions
- [ ] **距离矩阵修改**：如何将阻塞路段距离设为无穷大
- [ ] **车辆状态分析**：如何确定已服务和未服务客户
- [ ] **临时仓库创建**：如何将车辆位置转换为临时仓库
- [ ] **剩余容量计算**：如何计算车辆剩余容量
- [ ] **重新求解**：如何调用MDVRP求解器
- [ ] **结果验证**：如何验证容量约束和阻塞路段

**关键问题**：
- 如何修改距离矩阵？（答案：`dist_matrix[i][j] = 1000000`）
- 临时仓库的容量是多少？（答案：车辆剩余容量）
- 如何验证新路径不包含阻塞路段？（答案：遍历检查）

#### 4.2 技术问题准备（3小时）

**算法类问题**：
```
Q1: PSO、ACO、GA三种算法的优缺点是什么？
A: 
- PSO：收敛快，但容易陷入局部最优
- ACO：全局搜索能力强，但计算量大
- GA：平衡性好，可并行计算，但参数敏感

Q2: 深度学习如何提升GA性能？
A:
- 使用RL4CO/RouteF生成高质量初始种群
- 深度学习模型学习了大量VRP实例的模式
- 初始种群质量高，加速GA收敛
- 实验表明可提升5-15%的解质量

Q3: 重规划算法的核心思想是什么？
A:
- 将车辆当前位置转换为临时仓库
- 修改距离矩阵，阻塞路段距离设为无穷大
- 只对未服务客户重新求解
- 保持已服务客户的路径不变
```

**系统架构类问题**：
```
Q4: 为什么选择前后端分离架构？
A:
- 前后端独立开发和部署
- 前端可灵活切换技术栈
- 后端可提供多种客户端
- 便于团队协作和维护

Q5: 为什么算法服务使用Python而不是Java？
A:
- Python在科学计算方面有丰富的库
- 深度学习框架主要支持Python
- Python代码更简洁，算法实现更直观
- 通过RESTful API解耦，避免直接集成复杂性

Q6: 异步任务机制如何实现？
A:
- 使用Spring Boot的@Async注解
- 配置独立的线程池
- 前端提交任务后立即返回任务ID
- 前端轮询任务状态（每2秒）
- 任务状态持久化到数据库
```

**深度学习类问题**：
```
Q7: RL4CO是什么？
A:
- 强化学习框架，用于组合优化问题
- 基于Transformer的Attention机制
- 使用REINFORCE算法训练
- 支持TSP、CVRP等多种VRP变体

Q8: RouteF和RL4CO的关系？
A:
- RouteF是基于RL4CO的VRP求解器
- 提供了预训练的checkpoint
- 支持采样生成多个解
- 可以直接用于CVRP求解

Q9: 如何将MDVRP分解为CVRP？
A:
- 按仓库分解，每个仓库对应一个CVRP子问题
- 客户分配到最近的仓库
- 每个子问题独立求解
- 最后合并所有子问题的解
```

---

## 📅 Day 5：系统测试 + 演示彩排（5月7日 周四）

### 🎯 目标
完整测试系统，彩排演示流程

### ✅ 任务清单

#### 5.1 系统环境检查（2小时）
- [ ] **前端环境**
  - 启动前端：`cd system_test/frontend && npm run dev`
  - 验证所有页面可访问
  - 检查浏览器控制台无错误

- [ ] **后端环境**
  - 启动后端：`cd system_test/backend && mvn spring-boot:run`
  - 验证数据库连接正常
  - 检查所有API端点可访问

- [ ] **算法服务**
  - 启动算法服务：`cd system_test/algorithm-service && python app.py`
  - 测试GA、PSO、ACO端点
  - 测试重规划端点

#### 5.2 功能测试（2小时）
- [ ] **场景管理**
  - 创建新场景
  - 导入p01、p08、p21
  - 编辑场景参数

- [ ] **算法求解**
  - 测试GA算法（p01）
  - 测试PSO算法（p08）
  - 测试ACO算法（p01）
  - 测试GA-RL算法（p21）

- [ ] **重规划功能**
  - 选择阻塞路段
  - 执行重规划
  - 查看结果对比
  - 测试多次重规划

#### 5.3 演示脚本编写（2小时）
**演示流程（30分钟）**：

```
1. 开场介绍（2分钟）
   - 系统名称和目标
   - 核心功能概述

2. 系统架构讲解（5分钟）
   - 展示架构图
   - 说明四层架构
   - 强调技术亮点

3. 功能演示1：算法求解（8分钟）
   - 选择场景p01
   - 选择GA算法
   - 配置参数
   - 开始计算
   - 查看结果（成本、路径、地图）

4. 功能演示2：深度学习集成（7分钟）
   - 选择场景p21
   - 选择GA-RL算法
   - 说明RL4CO的作用
   - 展示结果对比（纯GA vs GA-RL）

5. 功能演示3：动态重规划（8分钟）
   - 基于p01的GA结果
   - 选择2个阻塞路段
   - 执行重规划
   - 展示结果对比
   - 演示多次重规划

6. 技术问答（10分钟）
   - 回答评审专家问题
   - 展示代码和图表

7. 总结（2分钟）
   - 总结系统特色
   - 说明创新点
```

#### 5.4 完整彩排（2小时）
- [ ] **第一次彩排**
  - 按照演示脚本完整走一遍
  - 记录每个环节的耗时
  - 标记出现的问题

- [ ] **问题修复**
  - 修复彩排中发现的问题
  - 优化演示流程

- [ ] **第二次彩排**
  - 再次完整走一遍
  - 确保所有问题已解决
  - 确认总时长在30分钟内

---

## 📊 代码Review进度跟踪表

| 日期 | 模块 | 文件数 | 预计时长 | 完成状态 | 备注 |
|------|------|--------|---------|---------|------|
| 5月3日 | PSO算法 | 1 | 2小时 | ⬜ |  |
| 5月3日 | ACO算法 | 1 | 2小时 | ⬜ |  |
| 5月3日 | GA算法 | 1 | 2小时 | ⬜ |  |
| 5月4日 | RL4CO集成 | 5 | 3小时 | ⬜ | **重点** |
| 5月4日 | RouteF集成 | 5 | 3小时 | ⬜ | **重点** |
| 5月4日 | VPRL包装器 | 5 | 1小时 | ⬜ |  |
| 5月5日 | 后端代码 | 5 | 2小时 | ⬜ |  |
| 5月5日 | 前端代码 | 5 | 2小时 | ⬜ |  |
| 5月5日 | 算法服务API | 5 | 2小时 | ⬜ |  |
| 5月6日 | 重规划功能 | 3 | 3小时 | ⬜ |  |
| 5月6日 | 技术问题准备 | - | 3小时 | ⬜ |  |
| 5月7日 | 系统测试 | - | 4小时 | ⬜ |  |
| 5月7日 | 演示彩排 | - | 4小时 | ⬜ |  |

---

## 🎯 核心技术亮点（验收时强调）

### 1. 多进程并行计算
- GA和ACO使用Python multiprocessing
- 在6核CPU上实现3-5倍加速
- 种群迁移机制保证解的多样性

### 2. 深度学习集成
- 集成RL4CO和RouteF两个深度学习模型
- 生成高质量初始种群
- 实验表明可提升5-15%的解质量

### 3. 动态重规划
- 应对实时道路阻塞
- 临时仓库转换机制
- 保持已服务客户路径不变

### 4. 前后端分离架构
- Vue.js + Spring Boot + Flask
- RESTful API通信
- 异步任务处理

### 5. 异步任务机制
- @Async + 线程池
- 前端轮询任务状态
- 避免HTTP超时

---

## 📝 代码Review笔记模板

为每个模块准备一个笔记文档，记录：

```markdown
# [模块名称] 代码Review笔记

## 文件位置
[文件路径]

## 核心功能
[简要描述这个文件/模块的作用]

## 关键类/函数
1. [类名/函数名]
   - 作用：[描述]
   - 输入：[参数]
   - 输出：[返回值]
   - 关键逻辑：[核心算法或流程]

## 技术细节
- [技术点1]
- [技术点2]
- [技术点3]

## 可能的问题
Q: [问题]
A: [答案]

## 与其他模块的关系
- 调用：[调用了哪些模块]
- 被调用：[被哪些模块调用]
```

---

## ✅ 验收日检查清单（5月8日早上）

- [ ] 所有服务可正常启动
- [ ] 演示数据已准备
- [ ] 演示脚本已熟悉
- [ ] 技术问题答案已准备
- [ ] 代码Review笔记已整理
- [ ] 笔记本电脑已充电
- [ ] 转接线已准备
- [ ] 心态已调整

---

**祝验收顺利！🎉**
