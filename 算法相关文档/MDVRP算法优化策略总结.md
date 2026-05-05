# MDVRP算法优化策略总结

本文档整理了当前实现的四个核心算法优化策略，用于多仓库车辆路径问题（MDVRP）的求解。

---

## 算法概览

| 算法编号 | 算法名称 | 优化层次 | 使用时机 | 时间复杂度 |
|---------|---------|---------|---------|-----------|
| 算法2-5 | 最佳位置插入算法 | 路径构造 | 初始解构造、客户插入 | O(\|R_d\| × n²) |
| 算法X | 边界客户跨仓库重分配 | 仓库分配优化 | 初始解后、变异操作中 | O(\|D\|² × \|BC\| × \|R_d\| × n²) |
| 算法Y | 2-opt局部搜索 | 路径内优化 | 路径细节优化 | O(n² × 迭代次数) |
| 算法Z | 路径间客户交换 | 路径间优化 | 全局优化阶段 | O(\|R\|² × n²) |

---

## 算法1：最佳位置插入算法（算法2-5）

### 核心思想
在所有现有路径中寻找使增量成本最小的插入位置，若无法插入则尝试创建新路径。

### 算法伪代码
```
输入: 待插入客户c, 目标仓库d, 路径集合R_d, 距离矩阵Dist, 容量约束Q, 里程约束L
输出: 更新后路径集合R_d', 插入标志flag, 增量成本Δ_best

1:  Δ_best ← +∞, best_route ← null, best_pos ← null
2:  for each r ∈ R_d do
3:      if ∑(demand[i] for i in r) + demand[c] > Q then continue  // 容量约束检查
4:      dist_r ← calculate_distance(r, d, Dist)
5:      for pos ← 1 to |r| + 1 do
6:          r' ← insert(r, c, pos)
7:          dist_r' ← calculate_distance(r', d, Dist)
8:          if dist_r' > L then continue  // 里程约束检查
9:          Δ ← dist_r' - dist_r
10:         if Δ < Δ_best then
11:             Δ_best ← Δ, best_route ← r, best_pos ← pos
12:         end if
13:     end for
14: end for
15: if best_route ≠ null then
16:     insert(best_route, c, best_pos), flag ← true  // 在最佳位置插入
17: else if demand[c] ≤ Q and 2 × Dist[d][c] ≤ L then
18:     R_d ← R_d ∪ {[c]}, Δ_best ← 2 × Dist[d][c], flag ← true  // 创建新路径
19: else
20:     flag ← false  // 插入失败
21: end if
22: return R_d, flag, Δ_best
```

### 使用场景
1. **初始解构造**：将客户逐个插入到路径中
2. **客户重分配**：跨仓库重分配时的插入操作
3. **修复操作**：变异或交叉后的解修复

### 优点
- 自动处理容量和里程约束
- 保证插入位置最优（在当前路径集合下）
- 支持创建新路径的灵活性

### 参数说明
- **Q**: 车辆容量上限
- **L**: 车辆最大行驶里程
- **Δ_best**: 最小增量成本（距离增加量）

---

## 算法2：边界客户跨仓库重分配

### 核心思想
识别位于仓库服务区域边界的客户，尝试将其重分配到距离更近的仓库，从而降低总配送成本。

### 算法伪代码
```
输入: 所有仓库集合D, 各仓库路径集合{R_d | d ∈ D}, 距离矩阵Dist, 容量约束Q, 里程约束L, 边界阈值θ
输出: 优化后的路径集合{R_d' | d ∈ D}, 总成本改善Δ_total

1:  Δ_total ← 0, improved ← true
2:  while improved do
3:      improved ← false
4:      for each 仓库对 (d_i, d_j) ∈ D × D, i ≠ j do
5:          BC ← identify_boundary_customers(d_i, d_j, R_{d_i}, Dist, θ)  // 识别边界客户
6:          for each 边界客户 c ∈ BC do
7:              cost_remove ← calculate_removal_cost(c, R_{d_i}, d_i, Dist)  // 移除成本
8:              R_{d_j}', flag, Δ_insert ← 算法2-5(c, d_j, R_{d_j}, Dist, Q, L)  // 使用最佳位置插入
9:              if flag = true and Δ_insert < cost_remove then  // 插入成功且有益
10:                 remove_customer(c, R_{d_i})  // 从原仓库移除
11:                 R_{d_j} ← R_{d_j}'  // 更新目标仓库路径
12:                 Δ_total ← Δ_total + (cost_remove - Δ_insert)
13:                 improved ← true
14:             end if
15:         end for
16:     end for
17: end while
18: return {R_d' | d ∈ D}, Δ_total
```

### 边界客户识别
```
函数 identify_boundary_customers(d_i, d_j, R_{d_i}, Dist, θ):
输入: 源仓库d_i, 目标仓库d_j, 源仓库路径集合R_{d_i}, 距离矩阵Dist, 边界阈值θ
输出: 边界客户集合BC

1:  BC ← ∅
2:  for each 路径 r ∈ R_{d_i} do
3:      for each 客户 c ∈ r do
4:          if Dist[d_j][c] < Dist[d_i][c] × (1 + θ) then  // 到目标仓库距离接近
5:              BC ← BC ∪ {c}
6:          end if
7:      end for
8:  end for
9:  return BC
```

### 使用场景
1. **初始解构造后**：修正简单分配规则（如最近仓库分配）的不合理性
2. **遗传算法变异操作**：作为跨仓库交换变异的核心逻辑
3. **局部搜索阶段**：系统性地优化仓库分配

### 优点
- 针对性强：只考虑边界客户，计算效率高
- 效果明显：通常能改善2-5%的总成本
- 模块化：调用算法2-5处理插入，逻辑清晰

### 参数说明
- **θ (theta)**: 边界阈值，通常取0.1-0.2
  - θ = 0.1 表示第二近仓库距离在最近仓库的1.1倍以内
  - θ 越大，边界范围越宽，候选客户越多

### 在项目中的实现
根据代码分析，你的项目采用了**预识别 + 按需使用**的策略：
- **初始化阶段**：`Manager.assignCustomersToDepots()` 识别所有边界客户
- **变异阶段**：`Mutation.interDepotSwapping()` 从边界客户中随机选择并重分配

---

## 算法3：2-opt局部搜索（路径内优化）

### 核心思想
通过反转路径中的一段来消除路径交叉，降低路径总长度。

### 算法伪代码
```
输入: 路径r, 仓库d, 距离矩阵Dist, 最大迭代次数max_iter
输出: 优化后的路径r'

1:  improved ← true, iter ← 0
2:  while improved and iter < max_iter do
3:      improved ← false
4:      for i ← 1 to |r| - 2 do
5:          for j ← i + 2 to |r| do
6:              r' ← reverse(r, i, j)  // 反转r[i+1:j]
7:              if cost(r') < cost(r) then
8:                  r ← r'
9:                  improved ← true
10:                 break
11:             end if
12:         end for
13:         if improved then break
14:     end for
15:     iter ← iter + 1
16: end while
17: return r
```

### 使用场景
1. **初始解优化**：对构造的初始路径进行细化
2. **局部搜索**：在遗传算法的局部搜索阶段使用
3. **解修复**：修复变异或交叉产生的低质量路径

### 优点
- 简单高效：实现简单，计算快速
- 效果稳定：通常能改善5-15%的路径成本
- 适用广泛：适用于各种VRP变体

### 参数说明
- **max_iter**: 最大迭代次数，通常取50-200

---

## 算法4：路径间客户交换（路径间优化）

### 核心思想
在同一仓库的不同路径之间交换客户，或在不同仓库的路径之间转移客户，以降低总成本。

### 算法伪代码（同仓库路径间交换）
```
输入: 路径集合R_d, 仓库d, 距离矩阵Dist, 容量约束Q, 里程约束L
输出: 优化后的路径集合R_d'

1:  improved ← true
2:  while improved do
3:      improved ← false
4:      for each 路径对 (r_i, r_j) ∈ R_d × R_d, i ≠ j do
5:          for each 客户 c_i ∈ r_i do
6:              for each 客户 c_j ∈ r_j do
7:                  cost_before ← cost(r_i) + cost(r_j)
8:                  r_i', r_j' ← swap(r_i, c_i, r_j, c_j)  // 交换客户
9:                  if feasible(r_i', Q, L) and feasible(r_j', Q, L) then
10:                     cost_after ← cost(r_i') + cost(r_j')
11:                     if cost_after < cost_before then
12:                         r_i ← r_i', r_j ← r_j'
13:                         improved ← true
14:                         break
15:                     end if
16:                 end if
17:             end for
18:             if improved then break
19:         end for
20:         if improved then break
21:     end for
22: end while
23: return R_d
```

### 使用场景
1. **局部搜索**：在遗传算法的局部搜索阶段
2. **解平衡**：平衡不同路径的负载
3. **成本优化**：进一步降低总配送成本

### 优点
- 全局视角：考虑路径间的协同优化
- 灵活性高：支持多种交换模式（1-1交换、2-1交换等）
- 效果显著：在路径负载不均时效果明显

---

## 算法组合策略

### 典型的MDVRP求解流程

```
阶段1: 初始解构造
  ├─ 客户-仓库分配（最近仓库分配）
  └─ 路径构造（算法2-5：最佳位置插入）

阶段2: 仓库分配优化 ⭐
  └─ 算法X：边界客户跨仓库重分配

阶段3: 路径优化
  ├─ 算法Y：2-opt局部搜索（路径内优化）
  └─ 算法Z：路径间客户交换（路径间优化）

阶段4: 全局优化（遗传算法）
  ├─ 选择、交叉、变异
  ├─ 变异中使用：边界客户跨仓库重分配
  └─ 局部搜索：2-opt + 路径间交换
```

### 算法调用关系

```
遗传算法主循环
  │
  ├─ 初始种群生成
  │   ├─ 最近仓库分配
  │   ├─ 算法2-5（最佳位置插入）
  │   └─ 边界客户跨仓库重分配
  │
  ├─ 选择操作
  │
  ├─ 交叉操作
  │   └─ 算法2-5（修复不可行解）
  │
  ├─ 变异操作
  │   ├─ 路径内变异（2-opt）
  │   └─ 跨仓库变异（边界客户重分配）
  │
  └─ 局部搜索（每N代执行）
      ├─ 2-opt优化
      ├─ 路径间交换
      └─ 边界客户重分配
```

---

## 算法性能对比

### 计算复杂度对比

| 算法 | 时间复杂度 | 空间复杂度 | 适用规模 |
|------|-----------|-----------|---------|
| 最佳位置插入 | O(\|R_d\| × n²) | O(n) | 所有规模 |
| 边界客户重分配 | O(\|D\|² × \|BC\| × \|R_d\| × n²) | O(\|BC\|) | 中大规模 |
| 2-opt | O(n² × iter) | O(n) | 所有规模 |
| 路径间交换 | O(\|R\|² × n²) | O(n) | 中小规模 |

### 改善效果对比（经验值）

| 算法 | 平均改善 | 最佳场景 | 计算时间 |
|------|---------|---------|---------|
| 最佳位置插入 | 基准 | 初始解构造 | 快 |
| 边界客户重分配 | 2-5% | 多仓库、边界客户多 | 中等 |
| 2-opt | 5-15% | 路径交叉多 | 快 |
| 路径间交换 | 3-8% | 路径负载不均 | 慢 |

---

## 参数调优建议

### 边界阈值 θ
- **小问题（< 100客户）**: θ = 0.05-0.1（严格边界）
- **中等问题（100-300客户）**: θ = 0.1-0.15
- **大问题（> 300客户）**: θ = 0.15-0.2（宽松边界）

### 2-opt迭代次数
- **快速模式**: 50次
- **标准模式**: 100次
- **精细模式**: 200-500次

### 算法执行频率（在遗传算法中）
- **边界客户重分配**: 每5-10代执行一次
- **2-opt优化**: 对精英个体每代执行
- **路径间交换**: 每10-20代执行一次

---

## 实现建议

### 代码模块化
```python
class MDVRPSolver:
    def __init__(self):
        self.insertion = BestInsertionAlgorithm()
        self.boundary = BoundaryCustomerReassignment()
        self.two_opt = TwoOptOptimizer()
        self.exchange = InterRouteExchange()
    
    def solve(self, problem):
        # 阶段1: 初始解构造
        solution = self.construct_initial_solution(problem)
        
        # 阶段2: 仓库分配优化
        solution = self.boundary.optimize(solution)
        
        # 阶段3: 路径优化
        solution = self.two_opt.optimize(solution)
        solution = self.exchange.optimize(solution)
        
        # 阶段4: 遗传算法全局优化
        solution = self.genetic_algorithm(solution)
        
        return solution
```

### 性能监控
建议记录每个算法的执行时间和改善效果：
```python
def log_optimization(algorithm_name, cost_before, cost_after, time_elapsed):
    improvement = (cost_before - cost_after) / cost_before * 100
    print(f"{algorithm_name}: {improvement:.2f}% improvement in {time_elapsed:.2f}s")
```

---

## 总结

本文档整理的四个算法构成了完整的MDVRP优化策略体系：

1. **算法2-5（最佳位置插入）**: 基础构造算法，被其他算法调用
2. **边界客户跨仓库重分配**: 仓库分配层面的优化
3. **2-opt局部搜索**: 路径内部的优化
4. **路径间客户交换**: 路径之间的协同优化

这些算法相互配合，从不同层次优化MDVRP解的质量，形成了一个层次化、模块化的优化框架。
