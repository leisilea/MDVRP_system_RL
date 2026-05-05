"""
遗传算法求解器 - 基于原始 ga.py 优化版本
核心改进：
1. 混合初始化（随机 + 最近邻启发式）
2. 遗憾值法分配仓库
3. 动态参数调整
4. 灾变机制
"""
import numpy as np
import time
from multiprocessing import Pool, cpu_count
from typing import Tuple, List, Dict, Any
import warnings

warnings.filterwarnings('ignore')

# 全局变量
instance = None


# ========================= 多进程初始化 =========================

def init_worker(shared_instance):
    """多进程工作进程初始化"""
    global instance
    instance = shared_instance


# ========================= 局部搜索 =========================

def local_search_2opt(individual: np.ndarray, max_iterations: int = 50) -> np.ndarray:
    """
    2-opt 局部搜索优化 - 根据规模自适应
    """
    global instance
    n_customers = instance.num_customers if instance else len(individual)

    best_individual = individual.copy()
    best_cost = evaluate_individual(best_individual)

    improved = True
    iterations = 0

    # 根据规模调整搜索强度
    if n_customers <= 100:
        max_iterations = min(max_iterations, 10)
        search_range = 12
    elif n_customers <= 200:
        max_iterations = min(max_iterations, 15)
        search_range = 18
    else:
        max_iterations = min(max_iterations, 20)
        search_range = 20

    while improved and iterations < max_iterations:
        improved = False
        iterations += 1

        n = len(individual)

        for i in range(0, n - 1, 2):
            max_j = min(i + search_range, n)
            for j in range(i + 2, max_j):
                new_individual = best_individual.copy()
                new_individual[i:j] = new_individual[i:j][::-1]

                new_cost = evaluate_individual(new_individual)

                if new_cost < best_cost:
                    best_individual = new_individual
                    best_cost = new_cost
                    improved = True
                    break

            if improved:
                break

    return best_individual


# ========================= 单个个体评估函数 =========================

def evaluate_individual(individual):
    """评估单个个体的适应度（总成本）"""
    routes, routes_meta = task_individual(individual)
    assignment, cost_matrix = assign_depots(routes_meta)
    total_cost = 0
    for r_idx, depot_idx in enumerate(assignment):
        total_cost += cost_matrix[r_idx, depot_idx]
    return total_cost


# ========================= 种群初始化 =========================

def initialize_population_mixed(pop_size: int) -> np.ndarray:
    """
    混合初始化策略 - 统一优化方法
    30%随机 + 50%最近邻 + 20%需求优先
    """
    global instance
    n_customers = instance.num_customers if instance else 50

    pop_list = []

    # 预计算客户间距离排序
    c_start = instance.num_depots
    c_end = c_start + instance.num_customers
    cust_dist_matrix = instance.distance_matrix[c_start:c_end, c_start:c_end]

    # 30%随机 + 50%最近邻 + 20%需求优先
    n_random = int(pop_size * 0.3)
    n_heuristic = int(pop_size * 0.5)
    n_demand = pop_size - n_random - n_heuristic

    # 1. 随机初始化 30%
    random_matrix = np.random.rand(n_random, instance.num_customers)
    random_individuals = instance.num_depots + np.argsort(random_matrix, axis=1)
    pop_list.extend(random_individuals)

    # 2. 最近邻启发式 50%
    # 根据规模调整邻居数量
    if n_customers <= 100:
        neighbor_count = 8
    elif n_customers <= 200:
        neighbor_count = 12
    else:
        neighbor_count = 15
    
    # 确保邻居数量不超过客户数量-1
    neighbor_count = min(neighbor_count, n_customers - 1)
    
    # 如果客户数量太少，直接跳过最近邻初始化
    if neighbor_count <= 0 or n_customers < 3:
        # 客户数量太少，全部使用随机初始化
        n_random += n_heuristic
        n_heuristic = 0
    
    # 只有当 n_heuristic > 0 时才执行最近邻初始化
    if n_heuristic > 0:
        closest_neighbors = np.argsort(cust_dist_matrix, axis=1)[:, 1:neighbor_count+1]
        
        for _ in range(n_heuristic):
            individual = []
            visited = np.zeros(instance.num_customers, dtype=bool)
            current_node = np.random.randint(0, instance.num_customers)
            individual.append(current_node + instance.num_depots)
            visited[current_node] = True

            for _ in range(instance.num_customers - 1):
                candidates = [n for n in closest_neighbors[current_node] if not visited[n]]
                if candidates:
                    # 60%选最近的，40%随机选前3个
                    if np.random.rand() < 0.6:
                        next_node = candidates[0]
                    else:
                        next_node = np.random.choice(candidates[:min(3, len(candidates))])
                else:
                    unvisited = np.where(~visited)[0]
                    next_node = np.random.choice(unvisited)
                individual.append(next_node + instance.num_depots)
                visited[next_node] = True
                current_node = next_node

            pop_list.append(np.array(individual))

    # 3. 需求优先初始化 20%
    for _ in range(n_demand):
        if np.random.rand() < 0.5:
            sorted_indices = np.argsort(instance.demands)[::-1]  # 大需求优先
        else:
            sorted_indices = np.argsort(instance.demands)  # 小需求优先

        individual = instance.num_depots + sorted_indices
        # 添加随机性
        n_swaps = max(1, int(0.15 * len(individual)))
        for _ in range(n_swaps):
            i1, i2 = np.random.randint(0, len(individual), 2)
            individual[i1], individual[i2] = individual[i2], individual[i1]

        pop_list.append(individual)

    return np.array(pop_list)


# ========================= 路径分割 =========================

def task_individual(individual: np.ndarray) -> Tuple[List[np.ndarray], np.ndarray]:
    """
    按容量约束贪心分割路径
    返回：(routes, routes_meta)
    routes_meta: [[start_node, end_node, inner_distance, load], ...]
    """
    routes = []
    routes_deal = []
    
    i = 0
    while i < len(individual):
        load = 0
        left = i
        j = i
        
        # 贪心装载
        while j < len(individual):
            demand = instance.demands[individual[j] - instance.num_depots]
            
            if demand > instance.vehicle_capacity:
                raise Exception(f"Customer demand {demand} exceeds vehicle capacity {instance.vehicle_capacity}")
            
            if load + demand <= instance.vehicle_capacity:
                load += demand
                j += 1
            else:
                break
        
        right = j
        route = individual[left:right]
        
        # 计算路径内部距离
        if len(route) > 1:
            from_depot = route[:-1]
            to_depot = route[1:]
            route_distance = np.sum(instance.distance_matrix[from_depot, to_depot])
        else:
            route_distance = 0
        
        routes.append(route)
        routes_deal.append((route[0], route[-1], route_distance, load))
        i = j
    
    return routes, np.array(routes_deal)


# ========================= 仓库分配（遗憾值法）=========================

def assign_depots(routes_meta: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    使用遗憾值法为每条路径分配仓库
    考虑每个仓库的车辆数量限制
    """
    num_routes = len(routes_meta)
    num_depots = instance.num_depots
    
    # 获取每个仓库的车辆数
    if hasattr(instance, 'depot_vehicles'):
        vehicle_limits = instance.depot_vehicles.copy()
    else:
        # 兼容旧版本：假设每个仓库有相同数量的车辆
        vehicle_limits = np.full(num_depots, instance.num_vehicles)
    
    start_nodes = routes_meta[:, 0].astype(int)
    end_nodes = routes_meta[:, 1].astype(int)
    inner_dists = routes_meta[:, 2]
    
    # 计算每条路径到每个仓库的总成本（环线距离）
    d2s = instance.distance_matrix[start_nodes][:, :num_depots]
    e2d = instance.distance_matrix[end_nodes][:, :num_depots]
    cost_matrix = d2s + inner_dists[:, np.newaxis] + e2d
    
    assignment = np.full(num_routes, -1, dtype=int)
    unassigned_mask = np.ones(num_routes, dtype=bool)
    
    while np.any(unassigned_mask):
        # 找出还有车的仓库
        valid_depots = np.where(vehicle_limits > 0)[0]
        
        # 如果所有仓库都满了，强制分配给最近的
        if len(valid_depots) == 0:
            remaining_indices = np.where(unassigned_mask)[0]
            best_deps = np.argmin(cost_matrix[remaining_indices], axis=1)
            assignment[remaining_indices] = best_deps
            break
        
        # 计算遗憾值（只针对未分配的）
        candidates = []
        for r_idx in np.where(unassigned_mask)[0]:
            valid_costs = cost_matrix[r_idx, valid_depots]
            
            # 排序找最优和次优
            sorted_idx = np.argsort(valid_costs)
            best_cost = valid_costs[sorted_idx[0]]
            best_depot_idx = valid_depots[sorted_idx[0]]
            
            if len(valid_costs) > 1:
                second_cost = valid_costs[sorted_idx[1]]
                regret = second_cost - best_cost
            else:
                regret = float('inf')
            
            candidates.append((regret, r_idx, best_depot_idx))
        
        # 按遗憾值降序排序（先解决遗憾最大的）
        candidates.sort(key=lambda x: x[0], reverse=True)
        _, chosen_r_idx, chosen_depot = candidates[0]
        
        # 执行分配
        assignment[chosen_r_idx] = chosen_depot
        unassigned_mask[chosen_r_idx] = False
        vehicle_limits[chosen_depot] -= 1
    
    return assignment, cost_matrix


# ========================= 适应度评估 =========================

def fitness(population: np.ndarray, pool=None) -> np.ndarray:
    """计算种群的适应度"""
    if pool:
        costs = pool.map(evaluate_individual, population)
    else:
        costs = [evaluate_individual(ind) for ind in population]
    return np.array(costs)


# ========================= 选择操作 =========================

def select(population: np.ndarray, fitness_values: np.ndarray, n_select: int = None) -> np.ndarray:
    """锦标赛选择"""
    n_pop = len(population)
    if n_select is None:
        n_select = n_pop
    
    k = 3  # 锦标赛规模
    selection = []
    
    for _ in range(n_select):
        # randint更快的选择
        participants_idx = np.random.randint(0, n_pop, k)
        best_idx1 = np.argmin(fitness_values[participants_idx])
        best_idx = participants_idx[best_idx1]
        selection.append(population[best_idx])
    
    return np.array(selection)


# ========================= 交叉操作 =========================

def crossover(selection: np.ndarray, cross_rate: float = 0.9) -> np.ndarray:
    """
    单点交叉（Order Crossover）
    """
    new_population = []
    n_needed = len(selection)
    
    for i in range(0, n_needed, 2):
        parent1 = selection[i]
        # 如果是奇数个，最后一个就绕回去和第一个配对，保证生出足够的后代
        parent2 = selection[i + 1] if i + 1 < n_needed else selection[0]
        
        if np.random.rand() < cross_rate:
            point = np.random.randint(1, len(parent1) - 1)
            # 点之前保留，点之后按父2顺序加入没有点之前的点
            child1_part1 = parent1[:point]
            child1_part2 = []
            for gene in parent2:
                if gene not in child1_part1:
                    child1_part2.append(gene)
            child1 = np.concatenate((child1_part1, child1_part2))
            
            child2_part1 = parent2[:point]
            child2_part2 = []
            for gene in parent1:
                if gene not in child2_part1:
                    child2_part2.append(gene)
            child2 = np.concatenate((child2_part1, child2_part2))
            
            new_population.extend([child1, child2])
        else:
            new_population.extend([parent1, parent2])
    
    # 如果实际上只需要 n_needed 个（即输入是奇数个时，我们生成了偶数个，截断）
    return np.array(new_population[:n_needed])


# ========================= 变异操作 =========================

def mutate(population: np.ndarray, mutate_rate: float = 0.25) -> np.ndarray:
    """
    多种变异策略 - 统一优化方法
    """
    n_pop = len(population)
    n_genes = population.shape[1]

    for i in range(n_pop):
        if np.random.rand() < mutate_rate:
            p1, p2 = np.random.randint(0, n_genes, 2)
            while p1 == p2:
                p1, p2 = np.random.randint(0, n_genes, 2)

            mutation_type = np.random.rand()

            if mutation_type < 0.35:
                # Reverse (2-opt) - 35%
                start, end = min(p1, p2), max(p1, p2)
                population[i][start:end+1] = population[i][start:end+1][::-1]
            elif mutation_type < 0.60:
                # Swap - 25%
                population[i][p1], population[i][p2] = population[i][p2], population[i][p1]
            elif mutation_type < 0.85:
                # Insertion - 25%
                val = population[i][p1]
                temp = np.delete(population[i], p1)
                population[i] = np.insert(temp, p2, val)
            else:
                # Scramble - 15%
                start, end = min(p1, p2), max(p1, p2)
                if end - start > 1:
                    segment = population[i][start:end+1].copy()
                    np.random.shuffle(segment)
                    population[i][start:end+1] = segment

    return population


# ========================= 主求解器类 =========================

class GeneticAlgorithmOptimized:
    """
    优化的遗传算法求解器 - 基于原始ga.py
    """

    def __init__(self, inst, params: Dict[str, Any], depot_id_map=None, customer_id_map=None):
        self.instance = inst
        self.params = params
        self.depot_id_map = depot_id_map or {i: i + 1 for i in range(inst.num_depots)}
        self.customer_id_map = customer_id_map or {i: i + 1 for i in range(inst.num_customers)}

        n_customers = inst.num_customers

        # ==================== 统一优化策略 ====================
        # 固定参数
        self.cross_rate = 0.9
        self.mutate_rate = 0.25
        self.elite_ratio = 0.05  # 固定精英系数
        
        # ==================== 阶梯线性参数计算 ====================
        
        # 小规模 (≤100客户)
        if n_customers <= 100:
            # 种群大小：150 + 每10个客户增加10
            # 例如：50客户 -> 150 + 5*10 = 200
            self.population_size = 150 + (n_customers // 10) * 10
            self.population_size = min(200, self.population_size)  # 上限200
            
            # 迭代次数：300 + 每10个客户增加50
            # 例如：50客户 -> 300 + 5*50 = 550
            self.max_generations = 400 + (n_customers // 20) * 50
            self.max_generations = min(900, self.max_generations)  # 上限800
        
        # 中规模 (101-200客户)
        elif n_customers <= 200:
            # 种群大小：200 + 每10个客户增加5
            # 例如：150客户 -> 200 + 15*5 = 275 -> 向上取整到280
            base_pop = 200 + ((n_customers - 100) // 10) * 5
            self.population_size = ((base_pop + 9) // 10) * 10  # 向上取整到10的倍数
            self.population_size = min(300, self.population_size)  # 上限300
            
            # 迭代次数：1000 + 每10个客户增加30
            # 例如：150客户 -> 1000 + 15*30 = 1450
            self.max_generations = 600 + ((n_customers - 100) // 20) * 50
            self.max_generations = min(1500, self.max_generations)  # 上限1500
        
        # 大规模 (>200客户)
        else:
            # 种群大小：300 + 每20个客户增加10
            # 例如：240客户 -> 300 + 2*10 = 320
            base_pop = 300 + ((n_customers - 200) // 20) * 10
            self.population_size = ((base_pop + 9) // 10) * 10  # 向上取整到10的倍数
            self.population_size = min(400, self.population_size)  # 上限400
            
            # 迭代次数：1500 + 每20个客户增加50
            # 例如：240客户 -> 1500 + 2*50 = 1600
            self.max_generations = 800 + ((n_customers - 200) // 30) * 50
            self.max_generations = min(2500, self.max_generations)  # 上限2500

        # 确保种群大小为偶数
        if self.population_size % 2 != 0:
            self.population_size += 1

        self.elite_size = max(2, int(self.population_size * self.elite_ratio))
        
        # 灾变阈值：随代数增加而增加，且更大以避免频繁灾变
        # 公式：min(300, max(60, 迭代次数 // 8))  确保是整数，最大值300
        self.max_no_improve = min(300, self.max_generations // 10)

        # 更新用户指定的参数
        if 'population_size' in params:
            self.population_size = max(50, params['population_size'])
        if 'max_iterations' in params:
            self.max_generations = max(100, params['max_iterations'])
        if 'cross_rate' in params:
            self.cross_rate = params['cross_rate']
        if 'mutate_rate' in params:
            self.mutate_rate = params['mutate_rate']

    def solve(self) -> Dict[str, Any]:
        """
        主求解函数 - 针对不同规模优化
        """
        global instance
        instance = self.instance

        start_time = time.time()
        n_customers = self.instance.num_customers

        # 打印配置信息
        print(f"\n{'='*60}")
        print(f"GA统一优化策略")
        print(f"{'='*60}")
        print(f"  客户数: {n_customers}")
        print(f"  种群大小: {self.population_size}")
        print(f"  最大迭代: {self.max_generations}")
        print(f"  交叉率: {self.cross_rate:.2f}")
        print(f"  变异率: {self.mutate_rate:.2f}")
        print(f"  精英比例: {self.elite_ratio:.2f} ({self.elite_size}个)")
        print(f"  灾变阈值: {self.max_no_improve}代")
        print(f"  多进程: 是")
        print(f"{'='*60}\n")

        # 初始化种群（混合初始化）
        population = initialize_population_mixed(self.population_size)

        # 精英保留参数
        n_elites = self.elite_size
        n_offspring = self.population_size - n_elites
        if n_offspring % 2 != 0:
            n_elites += 1
            n_offspring -= 1

        best_solution = None
        best_cost = float('inf')
        convergence_data = []
        no_improve_count = 0

        # 所有实例都使用多进程
        use_multiprocessing = True


        if use_multiprocessing:
            n_processes = min(cpu_count(), 6)  # 限制进程数
            with Pool(processes=n_processes, initializer=init_worker,
                     initargs=(self.instance,)) as pool:
                best_solution, best_cost, convergence_data = self._evolution_loop(
                    population, n_elites, n_offspring, pool)

        compute_time = time.time() - start_time
        print(f"GA求解完成 - 耗时: {compute_time:.2f}秒, 最优成本: {best_cost:.2f}")

        # 格式化输出
        return self._format_solution(best_solution, best_cost, compute_time, convergence_data)

    def _evolution_loop(self, population, n_elites, n_offspring, pool):
        """进化循环主逻辑"""
        best_solution = None
        best_cost = float('inf')
        convergence_data = []
        no_improve_count = 0
        n_customers = self.instance.num_customers

        for gen in range(self.max_generations):
            # 计算适应度（根据是否有pool决定并行）
            costs = fitness(population, pool)

            # 排序寻找精英和当前最优
            sorted_indices = np.argsort(costs)
            min_cost = costs[sorted_indices[0]]

            # 记录收敛数据（小规模问题降低记录频率）
            if n_customers <= 50:
                record_interval = 25  # 小规模更少记录
            elif n_customers <= 100:
                record_interval = 15
            else:
                record_interval = 10

            if gen % record_interval == 0:
                convergence_data.append({
                    'generation': gen,
                    'bestCost': float(min_cost),
                    'avgCost': float(np.mean(costs))
                })

            if min_cost < best_cost:
                best_cost = min_cost
                best_solution = population[sorted_indices[0]].copy()
                no_improve_count = 0

                # 局部搜索策略：根据规模调整频率
                if n_customers <= 100:
                    # 小规模：适度局部搜索
                    ls_interval = 30
                    if gen % ls_interval == 0 and gen > 50:
                        ls_max_iter = 10
                        improved_solution = local_search_2opt(best_solution, max_iterations=ls_max_iter)
                        improved_cost = evaluate_individual(improved_solution)
                        if improved_cost < best_cost:
                            best_cost = improved_cost
                            best_solution = improved_solution
                elif n_customers <= 200:
                    # 中规模：标准局部搜索
                    ls_interval = 50
                    if gen % ls_interval == 0 and gen > 40:
                        ls_max_iter = 15
                        improved_solution = local_search_2opt(best_solution, max_iterations=ls_max_iter)
                        improved_cost = evaluate_individual(improved_solution)
                        if improved_cost < best_cost:
                            best_cost = improved_cost
                            best_solution = improved_solution
                else:
                    # 大规模：增强局部搜索
                    ls_interval = 25
                    if gen % ls_interval == 0 and gen > 30:
                        ls_max_iter = 20
                        improved_solution = local_search_2opt(best_solution, max_iterations=ls_max_iter)
                        improved_cost = evaluate_individual(improved_solution)
                        if improved_cost < best_cost:
                            best_cost = improved_cost
                            best_solution = improved_solution
            else:
                no_improve_count += 1

            # 灾变/重启机制
            if no_improve_count >= self.max_no_improve:
                print(f"触发灾变机制 (第{gen}代)")
                
                # 保留10%精英，其余重新初始化
                n_keep = max(2, int(self.population_size * 0.10))
                top_part = population[sorted_indices[:n_keep]]
                n_new = self.population_size - n_keep
                random_matrix_new = np.random.rand(n_new, self.instance.num_customers)
                new_part = self.instance.num_depots + np.argsort(random_matrix_new, axis=1)
                population = np.vstack((top_part, new_part))

                no_improve_count = 0
                continue

            # 精英保留
            elites = population[sorted_indices[:n_elites]]

            # 进化操作
            selected = select(population, costs, n_offspring)
            offspring = crossover(selected, self.cross_rate)
            offspring = mutate(offspring, self.mutate_rate)

            # 合并精英和后代
            population = np.vstack((elites, offspring))

        return best_solution, best_cost, convergence_data

    def _format_solution(self, solution: np.ndarray, total_cost: float,
                        compute_time: float, convergence_data: List[Dict]) -> Dict[str, Any]:
        """
        格式化解为API返回格式
        """
        if solution is None:
            return {
                'routes': [],
                'totalCost': float('inf'),
                'computeTime': compute_time,
                'convergence': convergence_data,
                'algorithm': 'genetic_optimized',
                'numRoutes': 0,
                'error': '未找到可行解'
            }

        # 解析路径
        routes, routes_meta = task_individual(solution)
        assignment, cost_matrix = assign_depots(routes_meta)

        # 构建路径列表
        formatted_routes = []
        for idx, (route, depot_idx) in enumerate(zip(routes, assignment)):
            # 将内部索引转换为实际客户ID（使用ID映射）
            customer_ids = [self.customer_id_map[node - self.instance.num_depots] for node in route]

            route_cost = cost_matrix[idx, depot_idx]

            formatted_routes.append({
                'vehicleId': idx + 1,
                'depotId': self.depot_id_map[depot_idx],
                'path': customer_ids,
                'cost': float(route_cost)
            })

        return {
            'routes': formatted_routes,
            'totalCost': float(total_cost),
            'computeTime': float(compute_time),
            'convergence': convergence_data,
            'algorithm': 'genetic_optimized',
            'numRoutes': len(formatted_routes)
        }


# ========================= 兼容性函数（用于旧代码调用）=========================

def initialize_population():
    """兼容性函数"""
    global instance
    return initialize_population_mixed(300)



# ==================== API Solver 包装类 ====================

class GeneticAlgorithmMultiprocessingSolver:
    """多进程遗传算法求解器 - API包装类"""
    
    def __init__(self, depots, customers, params):
        """
        初始化求解器
        
        Args:
            depots: 仓库列表
            customers: 客户列表
            params: 算法参数
        """
        from .mdvrp_solver import MDVRPInstance
        
        self.depots = depots
        self.customers = customers
        self.params = params
        
        # 创建ID映射
        self.depot_id_map = {i: d['id'] for i, d in enumerate(depots)}
        self.customer_id_map = {i: c['id'] for i, c in enumerate(customers)}
        
        # 转换为MDVRPInstance
        self.instance = self._convert_to_instance()
    
    def _convert_to_instance(self):
        """将JSON格式转换为MDVRPInstance对象"""
        from .mdvrp_solver import MDVRPInstance
        
        num_depots = len(self.depots)
        num_customers = len(self.customers)
        
        # 构建坐标数组
        depots_coords = np.array([[d['x'], d['y']] for d in self.depots], dtype=np.float32)
        customers_coords = np.array([[c['x'], c['y']] for c in self.customers], dtype=np.float32)
        
        # 构建需求数组
        demands = np.array([c.get('demand', 10) for c in self.customers], dtype=np.int32)
        
        # 每个仓库的车辆数和容量
        depot_vehicles = np.array([d.get('vehicles', 5) for d in self.depots], dtype=np.int32)
        depot_capacities = np.array([d.get('capacity', 100) for d in self.depots], dtype=np.int32)
        
        # 计算距离矩阵
        all_coords = np.vstack((depots_coords, customers_coords))
        diff = all_coords[:, np.newaxis, :] - all_coords[np.newaxis, :, :]
        distance_matrix = np.sqrt(np.sum(diff**2, axis=-1))
        
        return MDVRPInstance(
            name="api_instance_ga_multiprocessing",
            num_customers=num_customers,
            num_depots=num_depots,
            depot_vehicles=depot_vehicles,
            depot_capacities=depot_capacities,
            depots_coords=depots_coords,
            customers_coords=customers_coords,
            demands=demands,
            distance_matrix=distance_matrix
        )
    
    def solve(self):
        """求解MDVRP问题"""
        # 创建多进程GA求解器
        optimizer = GeneticAlgorithmOptimized(
            self.instance, 
            self.params,
            depot_id_map=self.depot_id_map,
            customer_id_map=self.customer_id_map
        )
        
        # 求解
        return optimizer.solve()
