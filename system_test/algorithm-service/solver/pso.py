"""
粒子群算法求解器 (PSO) - 带完整约束版本
包含：
1. 车辆容量约束
2. 路径长度约束（最大行驶距离）
"""

import numpy as np
import time
import random
from concurrent.futures import ThreadPoolExecutor
import warnings

# 忽略一些不重要的警告
warnings.filterwarnings('ignore', category=RuntimeWarning)


# 计算路径成本
def calculate_route_cost(route, distance_matrix, depot_idx):
    """
    计算路径总成本（包含往返仓库）
    
    Args:
        route: List[int] - 客户访问序列
        distance_matrix: np.ndarray - 距离矩阵
        depot_idx: int - 仓库索引
    
    Returns:
        float - 路径总成本
    """
    if len(route) == 0:
        return 0.0

    cost = distance_matrix[depot_idx, route[0]]  # 仓库到起点

    for i in range(len(route) - 1):
        cost += distance_matrix[route[i], route[i + 1]]  # 路径内部

    cost += distance_matrix[route[-1], depot_idx]  # 终点回仓库

    return cost

# 检查路径可行性
def check_route_feasibility(route, depot_idx, demands, distance_matrix, 
                           capacity, max_distance, num_depots):
    if not route:
        return True
    
    # 检查容量约束
    total_demand = sum(demands[customer - num_depots] for customer in route)
    if total_demand > capacity:
        return False
    
    # 检查路径长度约束
    if max_distance > 0:  # 只有当max_distance > 0时才检查
        route_distance = calculate_route_cost(route, distance_matrix, depot_idx)
        if route_distance > max_distance:
            return False
    
    return True

# 这种贪婪是随机选择起点,然后最近邻搜索 检查容量及距离约束
def greedy_construct_route(customers, distance_matrix, depot_idx, demands, 
                          capacity, max_distance, num_depots):
    if not customers:
        return []
    
    route = []
    remaining = set(customers)
    current_load = 0
    
    current_node = random.choice(list(remaining))
    route.append(current_node)
    remaining.remove(current_node)
    current_load += demands[current_node - num_depots]
    
    while remaining:
        best_customer = None
        best_distance = float('inf')
        
        for customer in remaining:
            demand = demands[customer - num_depots]
            if current_load + demand > capacity:
                continue
            if max_distance > 0:
                temp_route = route + [customer]
                temp_distance = calculate_route_cost(temp_route, distance_matrix, depot_idx)
                if temp_distance > max_distance:
                    continue

            distance = distance_matrix[current_node, customer]
            if distance < best_distance:
                best_distance = distance
                best_customer = customer
        
        if best_customer is None:
            break
        
        route.append(best_customer)
        remaining.remove(best_customer)
        current_load += demands[best_customer - num_depots]
        current_node = best_customer
    
    return route

# ========================= V03 新增：多样化初始化策略 =========================

def farthest_insertion(customers, distance_matrix, depot_idx, demands, 
                      capacity, max_distance, num_depots):
    """
    最远插入启发式：每次选择距离当前路径最远的客户插入
    """
    if not customers:
        return []
    
    route = []
    remaining = set(customers)
    current_load = 0
    
    # 选择距离仓库最远的客户作为起点
    farthest_customer = max(remaining, key=lambda c: distance_matrix[depot_idx, c])
    route.append(farthest_customer)
    remaining.remove(farthest_customer)
    current_load += demands[farthest_customer - num_depots]
    
    while remaining:
        # 找到距离当前路径最远的可行客户
        best_customer = None
        best_distance = -1
        
        for customer in remaining:
            demand = demands[customer - num_depots]
            if current_load + demand > capacity:
                continue
            
            # 计算到路径的最小距离
            min_dist_to_route = min(distance_matrix[customer, node] for node in route)
            
            if min_dist_to_route > best_distance:
                # 检查路径长度约束
                temp_route = route + [customer]
                if max_distance > 0:
                    temp_distance = calculate_route_cost(temp_route, distance_matrix, depot_idx)
                    if temp_distance > max_distance:
                        continue
                
                best_distance = min_dist_to_route
                best_customer = customer
        
        if best_customer is None:
            break
        
        route.append(best_customer)
        remaining.remove(best_customer)
        current_load += demands[best_customer - num_depots]
    
    return route


def savings_algorithm(customers, distance_matrix, depot_idx, demands, 
                     capacity, max_distance, num_depots):
    """
    节约算法启发式：计算合并两条路径的节约值，优先合并节约最大的
    """
    if not customers:
        return []
    
    # 计算所有客户对的节约值
    savings = []
    for i, ci in enumerate(customers):
        for j, cj in enumerate(customers):
            if i < j:
                # 节约值 = dist(depot, ci) + dist(depot, cj) - dist(ci, cj)
                save = (distance_matrix[depot_idx, ci] + 
                       distance_matrix[depot_idx, cj] - 
                       distance_matrix[ci, cj])
                savings.append((save, ci, cj))
    
    # 按节约值降序排序
    savings.sort(reverse=True, key=lambda x: x[0])
    
    # 初始化：每个客户一条路径
    routes = [[c] for c in customers]
    route_loads = [demands[c - num_depots] for c in customers]
    
    # 尝试合并路径
    for save_value, ci, cj in savings:
        # 找到包含 ci 和 cj 的路径
        route_i = None
        route_j = None
        idx_i = -1
        idx_j = -1
        
        for idx, route in enumerate(routes):
            if ci in route:
                route_i = route
                idx_i = idx
            if cj in route:
                route_j = route
                idx_j = idx
        
        # 如果在不同路径且可以合并
        if route_i != route_j and route_i and route_j:
            combined_load = route_loads[idx_i] + route_loads[idx_j]
            
            if combined_load <= capacity:
                # 合并路径
                combined_route = route_i + route_j
                
                # 检查路径长度约束
                if max_distance > 0:
                    route_distance = calculate_route_cost(combined_route, distance_matrix, depot_idx)
                    if route_distance > max_distance:
                        continue
                
                # 执行合并
                routes[idx_i] = combined_route
                route_loads[idx_i] = combined_load
                routes.pop(idx_j)
                route_loads.pop(idx_j)
    
    # 将所有路径合并为一个客户序列
    result = []
    for route in routes:
        result.extend(route)
    
    return result


def initialize_diverse_population(num_particles, customers, distance_matrix, 
                                 depot_idx, demands, capacity, max_distance, num_depots):
    """
    多样化初始化粒子群
    
    策略分配：
    - 30% 贪心构造（质量优先）
    - 30% 随机构造（多样性优先）
    - 20% 最远插入（分散性优先）
    - 20% 节约算法（成本优先）
    
    Returns:
        List[List[int]] - 初始化的粒子列表
    """
    particles = []
    
    # 计算每种策略的数量
    num_greedy = int(num_particles * 0.3)
    num_random = int(num_particles * 0.3)
    num_farthest = int(num_particles * 0.2)
    num_savings = num_particles - num_greedy - num_random - num_farthest
    
    # 1. 贪心构造（30%）
    for _ in range(num_greedy):
        particle = greedy_construct_route(customers, distance_matrix, depot_idx,
                                         demands, capacity, max_distance, num_depots)
        # 补充剩余客户
        remaining = [c for c in customers if c not in particle]
        random.shuffle(remaining)
        particle.extend(remaining)
        particles.append(particle)
    
    # 2. 随机构造（30%）
    for _ in range(num_random):
        particle = list(customers)
        random.shuffle(particle)
        particles.append(particle)
    
    # 3. 最远插入（20%）
    for _ in range(num_farthest):
        particle = farthest_insertion(customers, distance_matrix, depot_idx,
                                     demands, capacity, max_distance, num_depots)
        remaining = [c for c in customers if c not in particle]
        random.shuffle(remaining)
        particle.extend(remaining)
        particles.append(particle)
    
    # 4. 节约算法（20%）
    for _ in range(num_savings):
        particle = savings_algorithm(customers, distance_matrix, depot_idx,
                                    demands, capacity, max_distance, num_depots)
        remaining = [c for c in customers if c not in particle]
        random.shuffle(remaining)
        particle.extend(remaining)
        particles.append(particle)
    
    return particles


#解码粒子序列
def decode_and_split_routes(particle, depot_idx, demands, distance_matrix, 
                           capacity, max_distance, num_depots):
    routes = []
    current_route = []
    current_load = 0
    total_cost = 0.0
    
    for customer in particle:
        demand = demands[customer - num_depots]
        
        # 尝试将客户添加到当前路径
        temp_route = current_route + [customer]
        temp_load = current_load + demand
        
        # 检查容量约束
        capacity_ok = temp_load <= capacity
        
        # 检查路径长度约束
        distance_ok = True
        if max_distance > 0:
            temp_distance = calculate_route_cost(temp_route, distance_matrix, depot_idx)
            distance_ok = temp_distance <= max_distance
        
        if capacity_ok and distance_ok:
            # 可以继续装载
            current_route.append(customer)
            current_load += demand
        else:
            # 约束不满足，保存当前路径，开始新路径
            if current_route:
                route_cost = calculate_route_cost(current_route, distance_matrix, depot_idx)
                routes.append(current_route)
                total_cost += route_cost
            
            # 新路径
            current_route = [customer]
            current_load = demand
    
    # 最后一条路径
    if current_route:
        route_cost = calculate_route_cost(current_route, distance_matrix, depot_idx)
        routes.append(current_route)
        total_cost += route_cost
    
    return routes, total_cost


def crossover_ox(parent1, parent2):
    """
    顺序交叉 (Order Crossover, OX)
    从 parent1 选择一段，剩余位置按 parent2 的顺序填充
    
    Args:
        parent1: List[int] - 父代1
        parent2: List[int] - 父代2
    
    Returns:
        List[int] - 子代
    """
    size = len(parent1)
    if size <= 1:
        return parent1.copy()
    
    # 随机选择交叉区间
    start = random.randint(0, size - 1)
    end = random.randint(0, size - 1)
    if start > end:
        start, end = end, start
    
    # 从 parent1 复制区间
    child = [None] * size
    child[start:end+1] = parent1[start:end+1]
    
    # 从 parent2 填充剩余位置
    parent2_filtered = [item for item in parent2 if item not in child]
    
    idx = 0
    for i in range(size):
        if child[i] is None:
            child[i] = parent2_filtered[idx]
            idx += 1
    
    return child


def best_insertion(customer, routes, depot_idx, demands, distance_matrix, 
                   capacity, max_distance, num_depots):
    """
    找到客户的最佳插入位置（借鉴GA-MDVRP的Inserter）
    
    Args:
        customer: 要插入的客户ID
        routes: 当前路径列表
        depot_idx: 仓库索引
        demands: 客户需求数组
        distance_matrix: 距离矩阵
        capacity: 车辆容量
        max_distance: 最大路径长度
        num_depots: 仓库数量
    
    Returns:
        (best_route_idx, best_position, best_cost): 最佳路径索引、位置和插入成本
    """
    best_cost = float('inf')
    best_route_idx = -1
    best_position = -1
    
    customer_demand = demands[customer - num_depots]
    
    # 尝试插入到每条现有路径的每个位置
    for route_idx, route in enumerate(routes):
        # 检查容量约束
        route_demand = sum(demands[c - num_depots] for c in route)
        if route_demand + customer_demand > capacity:
            continue
        
        # 尝试每个插入位置
        for pos in range(len(route) + 1):
            # 计算插入成本
            if len(route) == 0:
                # 空路径：成本是往返仓库的距离
                cost = 2 * distance_matrix[depot_idx, customer]
            elif pos == 0:
                # 插入到开头
                cost = (distance_matrix[depot_idx, customer] + 
                       distance_matrix[customer, route[0]] - 
                       distance_matrix[depot_idx, route[0]])
            elif pos == len(route):
                # 插入到末尾
                cost = (distance_matrix[route[-1], customer] + 
                       distance_matrix[customer, depot_idx] - 
                       distance_matrix[route[-1], depot_idx])
            else:
                # 插入到中间
                cost = (distance_matrix[route[pos-1], customer] + 
                       distance_matrix[customer, route[pos]] - 
                       distance_matrix[route[pos-1], route[pos]])
            
            # 检查路径长度约束
            temp_route = route[:pos] + [customer] + route[pos:]
            if max_distance > 0:
                route_distance = calculate_route_cost(temp_route, distance_matrix, depot_idx)
                if route_distance > max_distance:
                    continue
            
            # 更新最佳插入
            if cost < best_cost:
                best_cost = cost
                best_route_idx = route_idx
                best_position = pos
    
    # 如果没有找到可行插入，创建新路径
    if best_route_idx == -1:
        best_route_idx = len(routes)
        best_position = 0
        best_cost = 2 * distance_matrix[depot_idx, customer]
    
    return best_route_idx, best_position, best_cost

# ========================= V03 新增：跨仓库边界客户交换 =========================

def identify_boundary_customers_global(depot_assignments, distance_matrix, num_depots, threshold=0.8):
    """
    全局识别所有仓库的边界客户
    
    Args:
        depot_assignments: Dict[int, List[int]] - 每个仓库分配的客户
        distance_matrix: 距离矩阵
        num_depots: 仓库数量
        threshold: 边界客户判定阈值
    
    Returns:
        Dict[int, List[Tuple]] - 每个仓库的边界客户列表 (customer, target_depot, distance_ratio)
    """
    boundary_info = {depot_idx: [] for depot_idx in range(num_depots)}
    
    for depot_idx, customers in depot_assignments.items():
        for customer in customers:
            dist_to_current = distance_matrix[depot_idx, customer]
            
            # 找到最近的其他仓库
            min_dist_to_other = float('inf')
            best_other_depot = -1
            
            for other_depot_idx in range(num_depots):
                if other_depot_idx != depot_idx:
                    dist = distance_matrix[other_depot_idx, customer]
                    if dist < min_dist_to_other:
                        min_dist_to_other = dist
                        best_other_depot = other_depot_idx
            
            # 如果其他仓库更近
            if min_dist_to_other < dist_to_current * threshold:
                distance_ratio = min_dist_to_other / dist_to_current
                boundary_info[depot_idx].append((customer, best_other_depot, distance_ratio))
    
    return boundary_info


def inter_depot_customer_swap(depot_assignments, boundary_info, demands, 
                              distance_matrix, capacity, max_distance, num_depots):
    """
    执行跨仓库客户交换
    
    Args:
        depot_assignments: Dict[int, List[int]] - 当前客户分配
        boundary_info: Dict[int, List[Tuple]] - 边界客户信息
        demands: 客户需求数组
        distance_matrix: 距离矩阵
        capacity: 车辆容量
        max_distance: 各仓库的最大路径长度
        num_depots: 仓库数量
    
    Returns:
        bool - 是否执行了交换
    """
    # 收集所有边界客户
    all_boundary_customers = []
    for depot_idx, customers_info in boundary_info.items():
        for customer, target_depot, ratio in customers_info:
            all_boundary_customers.append((depot_idx, customer, target_depot, ratio))
    
    if not all_boundary_customers:
        return False
    
    # 按距离比率排序，优先交换距离差异最大的
    all_boundary_customers.sort(key=lambda x: x[3])
    
    # 尝试交换前几个边界客户
    swapped = False
    for source_depot, customer, target_depot, ratio in all_boundary_customers[:3]:
        # 检查目标仓库是否有容量
        target_load = sum(demands[c - num_depots] for c in depot_assignments[target_depot])
        customer_demand = demands[customer - num_depots]
        
        # 简单检查：假设每个仓库最多10辆车
        if target_load + customer_demand <= capacity * 10:
            # 执行交换
            depot_assignments[source_depot].remove(customer)
            depot_assignments[target_depot].append(customer)
            swapped = True
            print(f"      跨仓库交换: 客户{customer} 从仓库{source_depot+1} 转移到仓库{target_depot+1} (距离比率: {ratio:.2f})")
            break  # 每次只交换一个客户
    
    return swapped


# ========================= PSO 主算法类 =========================

class ParticleSwarmOptimizerWithConstraints:
    """
    粒子群优化算法求解 MDVRP（带完整约束）
    
    主要特性：
    1. 车辆容量约束
    2. 路径长度约束
    3. 基于顺序交叉的粒子更新
    4. 个体最优和全局最优跟踪
    5. 自适应惯性权重
    """

    def __init__(self, instance, params, depot_id_map=None, customer_id_map=None):
        """
        初始化粒子群优化器
        
        Args:
            instance: MDVRPInstance - 问题实例
            params: Dict[str, Any] - 算法参数
            depot_id_map: dict - 仓库ID映射（可选）
            customer_id_map: dict - 客户ID映射（可选）
        """
        self.instance = instance
        self.params = params
        self.depot_id_map = depot_id_map or {i: i + 1 for i in range(instance.num_depots)}
        self.customer_id_map = customer_id_map or {i: i + 1 for i in range(instance.num_customers)}

        # PSO 基本参数
        self.num_particles = params.get('particleCount', min(50, max(20, instance.num_customers)))
        self.max_iterations = params.get('iterations', min(200, max(50, 3 * instance.num_customers)))
        
        # PSO 核心参数
        self.w = params.get('inertiaWeight', 0.7)          # 惯性权重
        self.c1 = params.get('cognitiveWeight', 2.0)       # 个体学习因子
        self.c2 = params.get('socialWeight', 2.0)          # 社会学习因子
        
        # 自适应参数
        self.w_max = 0.9
        self.w_min = 0.4
        
        # 获取最大路径长度约束
        if hasattr(instance, 'max_route_distances') and instance.max_route_distances is not None:
            self.max_route_distances = instance.max_route_distances
        else:
            # 如果没有指定，设为0（不限制）
            self.max_route_distances = np.zeros(instance.num_depots)

    def solve(self):
        """
        主求解函数
        
        Returns:
            Dict[str, Any] - 求解结果，包含routes, totalCost, computeTime等
        """
        start_time = time.time()

        print(f"开始粒子群优化 (PSO带完整约束) - 粒子数: {self.num_particles}, 迭代数: {self.max_iterations}")
        print(f"  约束: 容量={self.instance.vehicle_capacity}, 最大路径长度={self.max_route_distances}")

        # 为每个仓库分配客户
        depot_assignments = self._assign_customers_to_depots()
        
        # 为每个仓库创建独立的收敛数据列表
        depot_convergence_data = [[] for _ in range(self.instance.num_depots)]
        
        all_depot_solutions = []
        total_cost_all_depots = 0.0

        # 对每个仓库独立运行 PSO
        for depot_idx, assigned_customers in enumerate(depot_assignments):
            if not assigned_customers:
                continue
            
            max_distance = self.max_route_distances[depot_idx] if depot_idx < len(self.max_route_distances) else 0
            print(f"  处理仓库 {depot_idx + 1}, 客户数: {len(assigned_customers)}, 最大路径长度: {max_distance}")
            
            # 传入该仓库专属的收敛数据列表
            depot_solution, depot_cost = self._solve_for_depot(
                depot_idx, assigned_customers, max_distance, 
                depot_convergence_data[depot_idx]  # 独立列表
            )
            
            if depot_solution:
                all_depot_solutions.extend(depot_solution)
                total_cost_all_depots += depot_cost

        # ========== 跨仓库边界客户优化 ==========
        if self.instance.num_depots > 1:
            print("\n执行跨仓库边界客户优化...")
            initial_cost = total_cost_all_depots
            
            for swap_iteration in range(5):  # 最多5次迭代
                # 识别所有仓库的边界客户
                boundary_info = identify_boundary_customers_global(
                    {i: depot_assignments[i] for i in range(len(depot_assignments))},
                    self.instance.distance_matrix,
                    self.instance.num_depots,
                    threshold=0.8
                )
                
                # 尝试跨仓库交换
                swapped = inter_depot_customer_swap(
                    {i: depot_assignments[i] for i in range(len(depot_assignments))},
                    boundary_info,
                    self.instance.demands,
                    self.instance.distance_matrix,
                    self.instance.vehicle_capacity,
                    self.max_route_distances,
                    self.instance.num_depots
                )
                
                if not swapped:
                    print(f"  第{swap_iteration + 1}次迭代: 没有可交换的边界客户")
                    break
                
                # 重新计算受影响仓库的成本
                # (简化版: 只重新解码路径，不重新运行PSO)
                all_depot_solutions = []
                total_cost_all_depots = 0.0
                
                for depot_idx in range(self.instance.num_depots):
                    if not depot_assignments[depot_idx]:
                        continue
                    
                    # 使用贪心构造快速生成路径
                    max_distance = self.max_route_distances[depot_idx] if depot_idx < len(self.max_route_distances) else 0
                    particle = greedy_construct_route(
                        depot_assignments[depot_idx],
                        self.instance.distance_matrix,
                        depot_idx,
                        self.instance.demands,
                        self.instance.vehicle_capacity,
                        max_distance,
                        self.instance.num_depots
                    )
                    
                    # 补充剩余客户
                    remaining = [c for c in depot_assignments[depot_idx] if c not in particle]
                    particle.extend(remaining)
                    
                    # 解码为路径
                    routes, cost = decode_and_split_routes(
                        particle, depot_idx, self.instance.demands,
                        self.instance.distance_matrix, self.instance.vehicle_capacity,
                        max_distance, self.instance.num_depots
                    )
                    
                    # 格式化路径
                    for route in routes:
                        route_cost = calculate_route_cost(route, self.instance.distance_matrix, depot_idx)
                        all_depot_solutions.append({
                            'depotId': depot_idx + 1,
                            'route': route,
                            'cost': route_cost
                        })
                    
                    total_cost_all_depots += cost
            
            final_improvement = initial_cost - total_cost_all_depots
            if final_improvement > 0:
                print(f"  跨仓库优化完成: 成本从 {initial_cost:.2f} 降低到 {total_cost_all_depots:.2f}")
                print(f"  节省: {final_improvement:.2f} ({final_improvement/initial_cost*100:.2f}%)")
            else:
                print(f"  跨仓库优化完成: 成本保持在 {total_cost_all_depots:.2f}")
            
            # 将跨仓库优化后的最终成本追加到收敛数据
            # 找到最后一个generation编号
            last_gen = 0
            for depot_conv in depot_convergence_data:
                if depot_conv:
                    last_gen = max(last_gen, depot_conv[-1]['generation'])
            
            # 为每个仓库追加最终成本记录点
            for depot_idx, depot_conv in enumerate(depot_convergence_data):
                if depot_conv and depot_assignments[depot_idx]:
                    # 计算该仓库的最终成本
                    depot_final_cost = sum(
                        sol['cost'] for sol in all_depot_solutions 
                        if sol['depotId'] == depot_idx + 1
                    )
                    depot_conv.append({
                        'generation': last_gen + 10,  # 在最后一代后面追加
                        'best_cost': float(depot_final_cost),
                        'avg_cost': float(depot_final_cost)
                    })
        # ==========================================

        # 合并所有仓库的收敛数据
        convergence_data = self._merge_depot_convergence(depot_convergence_data)

        compute_time = time.time() - start_time
        print(f"粒子群优化 (PSO带完整约束) 完成 - 最优成本: {total_cost_all_depots:.2f}, 耗时: {compute_time:.2f}s")
        print(f"  收敛数据点数: {len(convergence_data)}")

        return self._format_solution(all_depot_solutions, total_cost_all_depots, compute_time, convergence_data)

    def _solve_for_depot(self, depot_idx, assigned_customers, max_distance, convergence_data):
        """
        为单个仓库运行 PSO（带完整约束）
        
        Args:
            depot_idx: int - 仓库索引
            assigned_customers: List[int] - 分配给该仓库的客户列表
            max_distance: float - 最大行驶距离
            convergence_data: List[Dict] - 收敛数据记录
        
        Returns:
            Tuple[List[Dict], float] - (格式化的路径列表, 总成本)
        """
        """为单个仓库运行 PSO（带完整约束）"""
        
        # 初始化粒子群 - V03: 使用多样化初始化策略
        particles = initialize_diverse_population(
            self.num_particles, assigned_customers,
            self.instance.distance_matrix, depot_idx,
            self.instance.demands, self.instance.vehicle_capacity,
            max_distance, self.instance.num_depots
        )
        
        pbest_positions = []
        pbest_costs = []
        
        for particle in particles:
            pbest_positions.append(particle.copy())
            
            # 计算初始成本
            _, cost = decode_and_split_routes(
                particle, depot_idx, self.instance.demands,
                self.instance.distance_matrix, self.instance.vehicle_capacity,
                max_distance, self.instance.num_depots
            )
            pbest_costs.append(cost)
        
        # 全局最优
        gbest_idx = np.argmin(pbest_costs)
        gbest_position = pbest_positions[gbest_idx].copy()
        gbest_cost = pbest_costs[gbest_idx]
        
        # 早停机制
        no_improvement_count = 0
        early_stop_threshold = 200  # 200代没有改进就停止
        
        # 迭代优化
        for iteration in range(self.max_iterations):
            # 线性递减惯性权重
            w = self.w_max - (self.w_max - self.w_min) * iteration / self.max_iterations
            
            # 记录本代开始前的最优成本
            prev_gbest_cost = gbest_cost
            
            for i in range(self.num_particles):
                # PSO 更新：使用顺序交叉模拟速度更新
                rand1 = random.random()
                rand2 = random.random()
                
                # 根据概率选择交叉对象
                total_weight = w + self.c1 * rand1 + self.c2 * rand2
                
                if total_weight == 0:
                    parent2 = particles[i][::-1]  # 逆序
                else:
                    prob_w = w / total_weight
                    prob_c1 = self.c1 * rand1 / total_weight
                    
                    rand_select = random.random()
                    
                    if rand_select < prob_w:
                        parent2 = particles[i][::-1]  # 惯性：逆序
                    elif rand_select < prob_w + prob_c1:
                        parent2 = pbest_positions[i]  # 认知：个体最优
                    else:
                        parent2 = gbest_position  # 社会：全局最优
                
                # 顺序交叉
                particles[i] = crossover_ox(particles[i], parent2)
                
                # 计算新位置的成本
                routes, cost = decode_and_split_routes(
                    particles[i], depot_idx, self.instance.demands,
                    self.instance.distance_matrix, self.instance.vehicle_capacity,
                    max_distance, self.instance.num_depots
                )
                
                # 更新个体最优
                if cost < pbest_costs[i]:
                    pbest_costs[i] = cost
                    pbest_positions[i] = particles[i].copy()
                    
                    # 更新全局最优
                    if cost < gbest_cost:
                        gbest_cost = cost
                        gbest_position = particles[i].copy()
            
            # 检查是否有改进
            if gbest_cost < prev_gbest_cost:
                no_improvement_count = 0  # 有改进，重置计数器
            else:
                no_improvement_count += 1  # 没有改进，计数器+1
            
            # 早停检查
            if no_improvement_count >= early_stop_threshold:
                print(f"    早停: {early_stop_threshold}代没有改进，在第{iteration+1}代停止")
                break
            
            # 记录收敛数据 (改为每10代记录，与ACO一致)
            if iteration % 10 == 0:
                avg_cost = np.mean(pbest_costs)
                convergence_data.append({
                    'generation': iteration,
                    'best_cost': float(gbest_cost),
                    'avg_cost': float(avg_cost)
                })
                print(f"    迭代 {iteration}: 最优成本 = {gbest_cost:.2f}, 平均成本 = {avg_cost:.2f}")
        
        # 解码最优解
        best_routes, best_cost = decode_and_split_routes(
            gbest_position, depot_idx, self.instance.demands,
            self.instance.distance_matrix, self.instance.vehicle_capacity,
            max_distance, self.instance.num_depots
        )
        
        # 验证所有路径的可行性
        print(f"    仓库 {depot_idx + 1} 最终解: {len(best_routes)}条路径")
        for idx, route in enumerate(best_routes):
            route_cost = calculate_route_cost(route, self.instance.distance_matrix, depot_idx)
            route_load = sum(self.instance.demands[c - self.instance.num_depots] for c in route)
            feasible = check_route_feasibility(
                route, depot_idx, self.instance.demands,
                self.instance.distance_matrix, self.instance.vehicle_capacity,
                max_distance, self.instance.num_depots
            )
            status = "✓" if feasible else "✗"
            print(f"      路径{idx+1}: 成本={route_cost:.2f}, 负载={route_load}/{self.instance.vehicle_capacity}, "
                  f"长度={route_cost:.2f}/{max_distance if max_distance > 0 else '无限制'} {status}")
        
        # 格式化为返回格式
        formatted_routes = []
        for route in best_routes:
            route_cost = calculate_route_cost(route, self.instance.distance_matrix, depot_idx)
            formatted_routes.append({
                'depotId': depot_idx + 1,
                'route': route,
                'cost': route_cost
            })
        
        return formatted_routes, best_cost

    def _assign_customers_to_depots(self):
        """
        将客户分配给仓库（基于距离和容量限制）
        
        Returns:
            List[List[int]] - 每个仓库分配到的客户列表
        """
        """将客户分配给仓库（基于距离和容量限制）"""
        depot_assignments = [[] for _ in range(self.instance.num_depots)]

        # 计算每个客户到各仓库的距离
        customer_depot_distances = []
        for customer_idx in range(self.instance.num_customers):
            actual_customer_idx = customer_idx + self.instance.num_depots
            distances = []

            for depot_idx in range(self.instance.num_depots):
                distance = self.instance.distance_matrix[depot_idx, actual_customer_idx]
                distances.append((distance, depot_idx))

            distances.sort()  # 按距离排序
            customer_depot_distances.append(distances)

        # 贪心分配，考虑仓库容量限制
        depot_loads = [0] * self.instance.num_depots
        # 正确计算：车辆容量 × 每个仓库的车辆数
        # 平均分配总车辆数给各个仓库
        vehicles_per_depot = self.instance.num_vehicles // self.instance.num_depots
        depot_max_loads = [self.instance.vehicle_capacity * vehicles_per_depot 
                          for _ in range(self.instance.num_depots)]

        for customer_idx in range(self.instance.num_customers):
            actual_customer_idx = customer_idx + self.instance.num_depots
            demand = self.instance.demands[customer_idx]

            assigned = False
            for distance, depot_idx in customer_depot_distances[customer_idx]:
                if depot_loads[depot_idx] + demand <= depot_max_loads[depot_idx]:
                    depot_assignments[depot_idx].append(actual_customer_idx)
                    depot_loads[depot_idx] += demand
                    assigned = True
                    break

            if not assigned:
                # 强制分配给最近的仓库
                _, closest_depot = customer_depot_distances[customer_idx][0]
                depot_assignments[closest_depot].append(actual_customer_idx)
                depot_loads[closest_depot] += demand

        return depot_assignments

    def _merge_depot_convergence(self, depot_data_list):
        """
        合并多个仓库的收敛数据
        
        核心逻辑: 在第t代，MDVRP总成本 = Σ(每个仓库在第t代的成本)
        
        Args:
            depot_data_list: List[List[Dict]] - 每个仓库的收敛数据
            
        Returns:
            List[Dict] - 合并后的收敛数据，按generation对齐并累加成本
        """
        if not depot_data_list:
            return []
        
        # 过滤掉空列表
        valid_depot_data = [data for data in depot_data_list if data]
        
        if not valid_depot_data:
            return []
        
        # 找到最长的收敛序列长度
        max_length = max(len(data) for data in valid_depot_data)
        
        merged = []
        
        for i in range(max_length):
            # 累加所有仓库在第i个记录点的成本
            total_best_cost = 0.0
            total_avg_cost = 0.0
            generation = 0
            count = 0
            
            for depot_data in valid_depot_data:
                if i < len(depot_data):
                    total_best_cost += depot_data[i]['best_cost']
                    total_avg_cost += depot_data[i]['avg_cost']
                    generation = depot_data[i]['generation']  # 所有仓库的generation应该相同
                    count += 1
            
            if count > 0:
                merged.append({
                    'generation': generation,
                    'best_cost': total_best_cost,  # 所有仓库的最优成本之和
                    'avg_cost': total_avg_cost     # 所有仓库的平均成本之和
                })
        
        return merged

    def _format_solution(self, all_routes, total_cost, compute_time, convergence_data):
        """
        格式化解为API返回格式
        
        Args:
            all_routes: List[Dict] - 所有路径信息
            total_cost: float - 总成本
            compute_time: float - 计算时间
            convergence_data: List[Dict] - 收敛数据
        
        Returns:
            Dict[str, Any] - 格式化的解决方案
        """
        """格式化解为API返回格式"""
        if not all_routes:
            return {
                'routes': [],
                'totalCost': float('inf'),
                'computeTime': compute_time,
                'convergence': convergence_data,
                'algorithm': 'pso_with_constraints',
                'numRoutes': 0,
                'error': '未找到可行解'
            }

        formatted_routes = []
        vehicle_id = 1

        for route_info in all_routes:
            route = route_info['route']
            depot_id = route_info['depotId']
            cost = route_info['cost']

            # 转换为实际客户ID（使用ID映射）
            customer_ids = [self.customer_id_map[node - self.instance.num_depots] for node in route]

            formatted_routes.append({
                'vehicleId': vehicle_id,
                'depotId': self.depot_id_map[depot_id - 1],
                'path': customer_ids,
                'cost': float(cost)
            })

            vehicle_id += 1

        return {
            'routes': formatted_routes,
            'totalCost': float(total_cost),
            'computeTime': float(compute_time),
            'convergence': convergence_data,
            'algorithm': 'pso_with_constraints',
            'numRoutes': len(formatted_routes)
        }


if __name__ == "__main__":
    print("粒子群算法 (PSO带完整约束) 模块加载成功")


# ========================= PSO 求解器包装类 =========================

class ParticleSwarmSolver:
    """
    粒子群算法求解器 - 适配 MDVRPSolver 接口
    """

    def __init__(self, depots, customers, params):
        """
        粒子群算法求解器 - 适配 MDVRPSolver 接口
        
        Args:
            depots: List[Dict] - 仓库列表
            customers: List[Dict] - 客户列表
            params: Dict[str, Any] - 算法参数
        """
        # 导入 MDVRPInstance
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from mdvrp_solver import MDVRPInstance

        # 创建 ID 映射（索引 -> 实际 ID）
        self.depot_id_map = {i: d['id'] for i, d in enumerate(depots)}
        self.customer_id_map = {i: c['id'] for i, c in enumerate(customers)}

        # 转换数据格式
        num_depots = len(depots)
        num_customers = len(customers)

        # 构建坐标数组
        depots_coords = np.array([[d['x'], d['y']] for d in depots], dtype=np.float32)
        customers_coords = np.array([[c['x'], c['y']] for c in customers], dtype=np.float32)

        # 构建需求数组
        demands = np.array([c.get('demand', 10) for c in customers], dtype=np.int32)

        # 每个仓库的车辆数和容量
        depot_vehicles = np.array([d.get('vehicles', 5) for d in depots], dtype=np.int32)
        depot_capacities = np.array([d.get('capacity', 100) for d in depots], dtype=np.int32)
        depot_max_distances = np.array(
            [float(d.get('maxDistance', d.get('max_distance', 0))) for d in depots],
            dtype=np.float64
        )

        # 计算距离矩阵
        all_coords = np.vstack((depots_coords, customers_coords))
        diff = all_coords[:, np.newaxis, :] - all_coords[np.newaxis, :, :]
        distance_matrix = np.sqrt(np.sum(diff**2, axis=-1))

        # 创建 MDVRPInstance
        self.instance = MDVRPInstance(
            name="pso_instance",
            num_customers=num_customers,
            num_depots=num_depots,
            depot_vehicles=depot_vehicles,
            depot_capacities=depot_capacities,
            depots_coords=depots_coords,
            customers_coords=customers_coords,
            demands=demands,
            distance_matrix=distance_matrix,
            max_route_distances=depot_max_distances
        )

        self.params = params

    def solve(self):
        """
        求解 MDVRP
        
        Returns:
            Dict[str, Any] - 求解结果
        """
        optimizer = ParticleSwarmOptimizerWithConstraints(
            self.instance, 
            self.params,
            depot_id_map=self.depot_id_map,
            customer_id_map=self.customer_id_map
        )
        return optimizer.solve()
