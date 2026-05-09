# 蚁群算法(ACO)

import numpy as np
import time
import json
from dataclasses import dataclass
from multiprocessing import Pool, cpu_count
import warnings

# 忽略一些不重要的警告
warnings.filterwarnings('ignore', category=RuntimeWarning)

# 全局变量用于多进程
_global_instance = None
_global_pheromone_matrix = None
_global_eta_matrix = None
_global_alpha = None
_global_beta = None


def get_depot_distance_limit(instance, depot_idx):
    """获取仓库最大里程约束，<=0 表示不限制。"""
    if hasattr(instance, 'max_route_distances') and instance.max_route_distances is not None:
        limits = np.asarray(instance.max_route_distances, dtype=float)
        if depot_idx < len(limits):
            return float(limits[depot_idx])
    return 0.0


def _init_worker(instance, pheromone_matrix, eta_matrix, alpha, beta):
    """多进程初始化函数"""
    # 问题实例 + 信息化矩阵 + 启发式信息矩阵 + alpha和beta级参数
    global _global_instance, _global_pheromone_matrix, _global_eta_matrix, _global_alpha, _global_beta
    _global_instance = instance
    _global_pheromone_matrix = pheromone_matrix
    _global_eta_matrix = eta_matrix
    _global_alpha = alpha
    _global_beta = beta


def calculate_distance(coord1, coord2):
    """计算两点间欧几里得距离"""
    return np.sqrt(np.sum((coord1 - coord2) ** 2))



'''
    计算 depot_idx 的一辆车的行驶距离 + 距离约束软惩罚
    input : 路线 - 距离矩阵 - 仓库索引 - 最大距离约束
    output: cost
    约束实现 : 把额外cost*1w
'''
def calculate_route_cost(route, distance_matrix,depot_idx, max_distance=0.0):
    if len(route) == 0:
        return 0.0

    cost = distance_matrix[depot_idx, route[0]]  
    for i in range(len(route) - 1):
        cost += distance_matrix[route[i], route[i + 1]]  
    cost += distance_matrix[route[-1], depot_idx]  
    if max_distance > 0 and cost > max_distance:
        cost += (cost - max_distance) * 10000.0

    return cost



'''
    input : 信息素矩阵 - 路线 - 仓库idx - 路径成本 - 信息素挥发率 - 信息素强度系数
    output: 无 -- 返回的是全局变量
    更新信息素矩阵
'''
def update_pheromone(pheromone_matrix, route, depot_idx, cost, rho, Q):
    # 信息素增量
    pheromone_increase = Q / cost
    # 更新信息素矩阵
    pheromone_matrix[depot_idx, route[0]] = (1 - rho) * pheromone_matrix[depot_idx, route[0]] + rho * pheromone_increase
    for i in range(len(route) - 1):
        pheromone_matrix[route[i], route[i + 1]] = (1 - rho) * pheromone_matrix[route[i], route[i + 1]] + rho * pheromone_increase
    pheromone_matrix[route[-1], depot_idx] = (1 - rho) * pheromone_matrix[route[-1], depot_idx] + rho * pheromone_increase



'''
    input : 全局 (实例 + 信息素矩阵 + 启发式信息素矩阵 + 两参)  ++  蚂蚁id
    多进程单个蚂蚁解
'''
def _construct_single_solution_worker(ant_id):
    global _global_instance, _global_pheromone_matrix, _global_eta_matrix, _global_alpha, _global_beta
    
    try:
        instance = _global_instance
        pheromone_matrix = _global_pheromone_matrix
        eta_matrix = _global_eta_matrix
        alpha = _global_alpha
        beta = _global_beta
        
        all_routes = []
        total_cost = 0.0
        visited_customers = set()

        # 为每个仓库分配蚂蚁构造路径
        depot_assignment = _assign_customers_to_depots_worker(instance)

        for depot_idx, assigned_customers in enumerate(depot_assignment):
            if not assigned_customers:
                continue

            # 贪心构造
            depot_routes = []
            remaining_customers = set(assigned_customers)

            while remaining_customers:
                route = _construct_route_for_depot_worker(
                    depot_idx, remaining_customers, instance, 
                    pheromone_matrix, eta_matrix, alpha, beta
                )

                if route:
                    depot_routes.append(route)
                    remaining_customers -= set(route)
                    visited_customers.update(route)
                else:
                    break

            # 计算该仓库所有路径的成本
            depot_max_distance = get_depot_distance_limit(instance, depot_idx)
            for route in depot_routes:
                route_cost = calculate_route_cost(
                    np.array(route), instance.distance_matrix, depot_idx, depot_max_distance
                )
                total_cost += route_cost

                all_routes.append({
                    'depot_id': depot_idx + 1,
                    'route': route,
                    'cost': route_cost
                })

        return {
            'routes': all_routes,
            'cost': total_cost,
            'visited_customers': visited_customers
        }

    except Exception as e:
        print(f"蚂蚁 {ant_id} 构造解失败: {e}")
        return None



'''
    input : 实例
    贪心仓库 - 客户分配
'''
def _assign_customers_to_depots_worker(instance):
    depot_assignments = [[] for _ in range(instance.num_depots)]

    # 计算每个客户到各仓库的距离
    customer_depot_distances = []
    for customer_idx in range(instance.num_customers):
        actual_customer_idx = customer_idx + instance.num_depots
        distances = []

        for depot_idx in range(instance.num_depots):
            distance = instance.distance_matrix[depot_idx, actual_customer_idx]
            distances.append((distance, depot_idx))

        distances.sort()  # 按距离排序
        customer_depot_distances.append(distances)

    # 贪心分配，考虑仓库容量限制
    depot_loads = [0] * instance.num_depots
    depot_max_loads = [instance.depot_vehicles[i] * instance.depot_capacities[i] for i in range(instance.num_depots)]

    for customer_idx in range(instance.num_customers):
        actual_customer_idx = customer_idx + instance.num_depots
        demand = instance.demands[customer_idx]

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


def _construct_route_for_depot_worker(depot_idx, available_customers,
                                      instance, pheromone_matrix, eta_matrix,
                                      alpha, beta):
    """为特定仓库构造一条路径 - Worker版本（优化版）"""
    route = []
    current_load = 0
    current_node = depot_idx
    current_distance = 0.0
    max_distance = get_depot_distance_limit(instance, depot_idx)
    remaining = available_customers.copy()
    
    # 预计算幂运算优化标志（常见参数值）
    use_fast_power = (alpha == 1.0 and beta == 2.0)

    while remaining:
        # 计算每个可行客户的选择概率（向量化）
        candidates = []
        pheromones = []
        heuristics = []

        for customer in remaining:
            demand = instance.demands[customer - instance.num_depots]

            if current_load + demand <= instance.vehicle_capacity:
                if max_distance > 0:
                    projected_distance = (
                        current_distance
                        + instance.distance_matrix[current_node, customer]
                        + instance.distance_matrix[customer, depot_idx]
                    )
                    if projected_distance > max_distance:
                        continue

                candidates.append(customer)
                pheromones.append(pheromone_matrix[current_node, customer])
                heuristics.append(eta_matrix[current_node, customer])

        if not candidates:
            break

        # 向量化概率计算（避免循环中的幂运算）
        pheromones = np.array(pheromones)
        heuristics = np.array(heuristics)
        
        if use_fast_power:
            # 快速路径：alpha=1.0, beta=2.0
            probabilities = pheromones * (heuristics * heuristics)
        else:
            # 通用路径：使用幂运算
            probabilities = np.power(pheromones, alpha) * np.power(heuristics, beta)

        # 轮盘赌选择（使用numpy优化）
        prob_sum = probabilities.sum()
        if prob_sum > 0:
            probabilities = probabilities / prob_sum
            # 使用numpy的choice（比手动循环快）
            best_customer = np.random.choice(candidates, p=probabilities)
        else:
            best_customer = candidates[0]

        # 添加客户到路径
        route.append(best_customer)
        current_distance += instance.distance_matrix[current_node, best_customer]
        current_load += instance.demands[best_customer - instance.num_depots]
        current_node = best_customer
        remaining.remove(best_customer)

    return route

class ImprovedAntColonyOptimizer:

    def __init__(self, instance, params, depot_id_map=None, customer_id_map=None):
        self.instance = instance
        self.params = params
        self.depot_id_map = depot_id_map or {i: i + 1 for i in range(instance.num_depots)}
        self.customer_id_map = customer_id_map or {i: i + 1 for i in range(instance.num_customers)}

        # 基本参数（优化后：减少计算量）
        self.num_ants = params.get('num_ants', min(50, max(15, instance.num_customers // 2)))
        self.max_iterations = params.get('max_iterations', min(200, max(50, 2 * instance.num_customers)))

        # ACO 核心参数（优化：使用快速幂运算的默认值）
        self.alpha = params.get('alpha', 1.0)      # 信息素重要度（保持1.0以使用快速路径）
        self.beta = params.get('beta', 2.0)        # 启发式信息重要度（保持2.0以使用快速路径）
        self.rho = params.get('rho', 0.15)         # 信息素挥发率（稍微增加）
        self.Q = params.get('Q', 100.0)            # 信息素强度

        # 精英策略参数（优化：减少精英比例）
        self.elite_ratio = 0.1
        self.num_elite_ants = max(1, int(self.num_ants * self.elite_ratio))

        # 局部搜索概率（优化：降低概率）
        self.local_search_prob = 0.1

        # 初始化信息素矩阵
        self._initialize_pheromone_matrix()

        # 距离启发式矩阵（预计算）
        self.eta_matrix = self._calculate_heuristic_matrix()

    def _initialize_pheromone_matrix(self):
        """初始化信息素矩阵"""
        total_nodes = self.instance.num_depots + self.instance.num_customers

        # 使用最近邻启发式估算初始信息素
        nn_cost = self._nearest_neighbor_estimate()
        tau_0 = 1.0 / (total_nodes * nn_cost) if nn_cost > 0 else 0.01

        self.pheromone_matrix = np.full((total_nodes, total_nodes), tau_0, dtype=np.float64)

    def _nearest_neighbor_estimate(self):
        """用最近邻启发式估算初始解的成本"""
        try:
            total_cost = 0.0
            visited = set()

            for depot_idx in range(self.instance.num_depots):
                if len(visited) >= self.instance.num_customers:
                    break

                current_load = 0
                current_cost = 0.0
                current_node = depot_idx

                while len(visited) < self.instance.num_customers:
                    best_customer = None
                    best_distance = float('inf')

                    # 寻找最近的未访问客户
                    for customer_idx in range(self.instance.num_customers):
                        actual_customer_idx = customer_idx + self.instance.num_depots

                        if actual_customer_idx not in visited:
                            demand = self.instance.demands[customer_idx]
                            if current_load + demand <= self.instance.vehicle_capacity:
                                distance = self.instance.distance_matrix[current_node, actual_customer_idx]
                                if distance < best_distance:
                                    best_distance = distance
                                    best_customer = actual_customer_idx

                    if best_customer is None:
                        # 当前车辆满载，返回仓库
                        current_cost += self.instance.distance_matrix[current_node, depot_idx]
                        break

                    # 移动到最近客户
                    visited.add(best_customer)
                    current_cost += best_distance
                    current_load += self.instance.demands[best_customer - self.instance.num_depots]
                    current_node = best_customer

                total_cost += current_cost

            return total_cost if total_cost > 0 else 1000.0

        except Exception:
            return 1000.0

    def _calculate_heuristic_matrix(self):
        """预计算启发式信息矩阵 (1/distance)"""
        total_nodes = self.instance.num_depots + self.instance.num_customers
        eta_matrix = np.zeros((total_nodes, total_nodes), dtype=np.float64)

        for i in range(total_nodes):
            for j in range(total_nodes):
                if i != j:
                    distance = self.instance.distance_matrix[i, j]
                    eta_matrix[i, j] = 1.0 / (distance + 1e-10)

        return eta_matrix

    def solve(self):
        """
        主求解函数
        """
        start_time = time.time()

        best_solution = None
        best_cost = float('inf')
        convergence_data = []
        iteration_costs = []

        no_improvement_count = 0
        patience = max(50, self.max_iterations // 10)

        print(f"开始蚁群优化 (ACO) - 蚂蚁数: {self.num_ants}, 迭代数: {self.max_iterations}, 多进程: 是")

        # 使用多进程并行
        n_processes = min(cpu_count(), 6)  # 限制进程数

        for iteration in range(self.max_iterations):
            # 构造解（使用多进程）
            solutions = self._construct_solutions_multiprocess(n_processes)

            if not solutions:
                continue

            # 评估解
            costs = [sol['cost'] for sol in solutions]

            # 找到当前迭代最优解
            best_idx = np.argmin(costs)
            iteration_best_cost = costs[best_idx]
            iteration_best_solution = solutions[best_idx]

            iteration_costs.append(iteration_best_cost)

            # 更新全局最优
            if iteration_best_cost < best_cost:
                best_cost = iteration_best_cost
                best_solution = iteration_best_solution.copy()
                no_improvement_count = 0
            else:
                no_improvement_count += 1

            # 记录收敛数据
            if iteration % 10 == 0:
                convergence_data.append({
                    'generation': iteration,
                    'best_cost': float(best_cost),
                    'avg_cost': float(np.mean(costs))
                })
                print(f"迭代 {iteration}: 最优成本 = {best_cost:.2f}, 平均成本 = {np.mean(costs):.2f}")

            # 局部搜索优化
            if np.random.rand() < self.local_search_prob:
                improved_solution = self._local_search_2opt(iteration_best_solution)
                if improved_solution['cost'] < iteration_best_cost:
                    solutions[best_idx] = improved_solution

            # 更新信息素
            self._update_pheromone(solutions, costs)

            # 早停机制
            if no_improvement_count >= patience:
                print(f"早停: {patience} 次迭代无改进")
                break

        compute_time = time.time() - start_time
        print(f"蚁群优化 (ACO) 完成 - 最优成本: {best_cost:.2f}, 耗时: {compute_time:.2f}s")

        return self._format_solution(best_solution, best_cost, compute_time, convergence_data)

    def _construct_solutions_multiprocess(self, n_processes):
        """使用多进程并行构造蚂蚁解"""
        solutions = []

        # 使用进程池并行构造解
        with Pool(processes=n_processes, initializer=_init_worker,
                 initargs=(self.instance, self.pheromone_matrix, self.eta_matrix, 
                          self.alpha, self.beta)) as pool:
            # 并行构造所有蚂蚁的解
            results = pool.map(_construct_single_solution_worker, range(self.num_ants))
            
            # 过滤掉失败的解
            solutions = [sol for sol in results if sol is not None]

        return solutions

    def _local_search_2opt(self, solution):
        """2-opt局部搜索优化（优化版：早停+限制搜索范围）"""
        improved_solution = solution.copy()
        improved_routes = []
        total_improvement = 0.0

        for route_info in solution['routes']:
            route = route_info['route'].copy()
            depot_idx = route_info['depot_id'] - 1
            depot_max_distance = get_depot_distance_limit(self.instance, depot_idx)

            if len(route) < 4:  # 路径太短，无法进行2-opt
                improved_routes.append(route_info)
                continue

            best_route = route.copy()
            best_cost = route_info['cost']
            improved = True
            
            # 限制2-opt迭代次数，避免过度优化
            max_iterations = 3
            iteration = 0

            # 多次迭代直到无改进或达到最大次数
            while improved and iteration < max_iterations:
                improved = False
                iteration += 1
                
                # 限制搜索窗口大小，避免检查所有组合
                max_window = min(20, len(route))  # 最多检查20个节点的窗口
                
                for i in range(len(route) - 1):
                    # 限制j的范围，只检查附近的节点
                    j_max = min(i + max_window, len(route))
                    
                    for j in range(i + 2, j_max):
                        # 2-opt交换
                        new_route = route[:i] + route[i:j+1][::-1] + route[j+1:]

                        # 计算新路径成本
                        new_cost = calculate_route_cost(
                            np.array(new_route), self.instance.distance_matrix, depot_idx, depot_max_distance
                        )

                        if new_cost < best_cost:
                            best_route = new_route
                            best_cost = new_cost
                            route = new_route  # 更新当前路径，继续优化
                            improved = True
                            break  # 找到改进就立即应用，不继续搜索
                    
                    if improved:
                        break  # 找到改进就跳出外层循环，开始新一轮

            improvement = route_info['cost'] - best_cost
            total_improvement += improvement

            improved_routes.append({
                'depot_id': route_info['depot_id'],
                'route': best_route,
                'cost': best_cost
            })

        improved_solution['routes'] = improved_routes
        improved_solution['cost'] = solution['cost'] - total_improvement

        return improved_solution

    def _update_pheromone(self, solutions, costs):
        """更新信息素矩阵"""
        # 信息素挥发
        self.pheromone_matrix *= (1.0 - self.rho)

        # 精英蚂蚁策略：最优的几个解加强信息素
        sorted_indices = np.argsort(costs)
        elite_solutions = [solutions[i] for i in sorted_indices[:self.num_elite_ants]]

        for solution in elite_solutions:
            for route_info in solution['routes']:
                route = route_info['route']
                depot_idx = route_info['depot_id'] - 1
                cost = route_info['cost']

                if cost > 0:
                    # 更新路径上的信息素
                    update_pheromone(
                        self.pheromone_matrix,
                        np.array(route),
                        depot_idx,
                        cost,
                        self.rho,
                        self.Q
                    )

        # 确保信息素在合理范围内
        tau_min = 0.01
        tau_max = 1.0
        self.pheromone_matrix = np.clip(self.pheromone_matrix, tau_min, tau_max)

    def _format_solution(self, solution, total_cost,
                        compute_time, convergence_data):
        """格式化解为API返回格式"""
        if solution is None:
            return {
                'routes': [],
                'totalCost': float('inf'),
                'computeTime': compute_time,
                'convergence': convergence_data,
                'algorithm': 'aco_optimized',
                'numRoutes': 0,
                'error': '未找到可行解'
            }

        formatted_routes = []
        vehicle_id = 1

        for route_info in solution['routes']:
            route = route_info['route']
            depot_id = route_info['depot_id']  # 这是 depot_idx + 1
            cost = route_info['cost']

            # 转换为实际客户ID（使用ID映射）
            customer_ids = [self.customer_id_map[node - self.instance.num_depots] for node in route]

            formatted_routes.append({
                'vehicleId': vehicle_id,
                'depotId': self.depot_id_map[depot_id - 1],  # depot_id 已经加了 1，所以要减回来
                'path': customer_ids,
                'cost': float(cost)
            })

            vehicle_id += 1

        return {
            'routes': formatted_routes,
            'totalCost': float(total_cost),
            'computeTime': float(compute_time),
            'convergence': convergence_data,
            'algorithm': 'aco_optimized',
            'numRoutes': len(formatted_routes)
        }


# ========================= 粒子群算法求解器包装类 =========================

class AntColonySolver:
    """
    蚁群算法求解器 - 适配 MDVRPSolver 接口
    """

    def __init__(self, depots, customers, params):
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
            name="aco_instance",
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
        optimizer = ImprovedAntColonyOptimizer(
            self.instance, 
            self.params,
            depot_id_map=self.depot_id_map,
            customer_id_map=self.customer_id_map
        )
        return optimizer.solve()


