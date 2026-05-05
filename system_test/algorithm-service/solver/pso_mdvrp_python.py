"""
PSO-MDVRP Python实现
支持自定义距离矩阵，专门用于重规划场景
"""

import numpy as np
import time
from typing import Dict, List, Tuple
import random


class PSOSolver:
    """
    粒子群优化算法求解MDVRP
    支持自定义距离矩阵
    """
    
    def __init__(
        self,
        particle_count=30,
        iterations=100,
        inertia_weight=0.7,
        cognitive_weight=2.0,
        social_weight=2.0
    ):
        """
        初始化PSO求解器
        
        Args:
            particle_count: 粒子数量
            iterations: 迭代次数
            inertia_weight: 惯性权重
            cognitive_weight: 认知权重
            social_weight: 社会权重
        """
        self.particle_count = particle_count
        self.iterations = iterations
        self.w = inertia_weight
        self.c1 = cognitive_weight
        self.c2 = social_weight
    
    def solve(
        self,
        instance_data: Dict,
        distance_matrix: np.ndarray = None
    ) -> Dict:
        """
        求解MDVRP实例
        
        Args:
            instance_data: 包含depots和customers的字典
            distance_matrix: 自定义距离矩阵 (可选)
        
        Returns:
            求解结果字典
        """
        start_time = time.time()
        
        print(f"\n{'='*60}")
        print(f"PSO-MDVRP Python求解器")
        print(f"{'='*60}")
        print(f"粒子数: {self.particle_count}")
        print(f"迭代次数: {self.iterations}")
        
        # 解析输入数据
        depots = instance_data['depots']
        customers = instance_data['customers']
        
        num_depots = len(depots)
        num_customers = len(customers)
        
        print(f"仓库数: {num_depots}")
        print(f"客户数: {num_customers}")
        
        # 打印仓库信息
        print(f"\n仓库详情:")
        for i, depot in enumerate(depots):
            print(f"  仓库{i}: 车辆数={depot['vehicle_count']}, 容量={depot['capacity']}")
        
        # 打印客户需求
        total_demand = sum(c['demand'] for c in customers)
        total_capacity = sum(d['vehicle_count'] * d['capacity'] for d in depots)
        print(f"\n需求统计:")
        print(f"  总需求: {total_demand}")
        print(f"  总容量: {total_capacity}")
        print(f"  容量利用率: {total_demand / total_capacity * 100:.1f}%")
        
        if total_demand > total_capacity:
            print(f"  ⚠️ 警告: 总需求超过总容量！")
        
        # 构建或使用距离矩阵
        if distance_matrix is None:
            print("使用欧几里得距离")
            distance_matrix = self._build_distance_matrix(depots, customers)
        else:
            print(f"使用自定义距离矩阵: {distance_matrix.shape}")
        
        # 初始化粒子群
        particles = self._initialize_particles(depots, customers)
        
        # PSO主循环
        global_best_solution = None
        global_best_cost = float('inf')
        
        # 跟踪所有可行解（成功分配所有客户的解）
        feasible_solutions = []  # [(solution, cost, routes), ...]
        
        # 创建客户ID集合用于验证
        all_customer_ids = set(c['id'] for c in customers)
        
        for iteration in range(self.iterations):
            for particle in particles:
                # 评估粒子并获取路径
                routes = self._solution_to_routes(
                    particle['position'], depots, customers, distance_matrix
                )
                
                # 检查是否所有客户都被分配（使用客户ID）
                assigned_customer_ids = set()
                for route in routes:
                    assigned_customer_ids.update(route['customers'])
                
                is_feasible = assigned_customer_ids == all_customer_ids
                
                # 计算成本
                cost = sum(route['cost'] for route in routes)
                
                # 如果是可行解，记录下来
                if is_feasible:
                    feasible_solutions.append({
                        'solution': particle['position'].copy(),
                        'cost': cost,
                        'routes': routes
                    })
                
                # 更新个体最优（只考虑可行解）
                if is_feasible and cost < particle['best_cost']:
                    particle['best_cost'] = cost
                    particle['best_position'] = particle['position'].copy()
                
                # 更新全局最优（只考虑可行解）
                if is_feasible and cost < global_best_cost:
                    global_best_cost = cost
                    global_best_solution = particle['position'].copy()
            
            # 更新粒子速度和位置
            for particle in particles:
                if global_best_solution is not None:
                    self._update_particle(particle, global_best_solution)
            
            if (iteration + 1) % 20 == 0:
                feasible_count = len([s for s in feasible_solutions if s['cost'] < float('inf')])
                if global_best_cost < float('inf'):
                    print(f"迭代 {iteration + 1}/{self.iterations}, 最优成本: {global_best_cost:.2f}, 可行解数: {feasible_count}")
                else:
                    print(f"迭代 {iteration + 1}/{self.iterations}, 尚未找到可行解")
        
        # 从所有可行解中选择成本最优的
        if feasible_solutions:
            best_feasible = min(feasible_solutions, key=lambda s: s['cost'])
            routes = best_feasible['routes']
            global_best_cost = best_feasible['cost']
            print(f"\n从 {len(feasible_solutions)} 个可行解中选择了成本最优的解")
        else:
            # 如果没有可行解，使用最后一次评估的结果（可能不完整）
            print(f"\n警告: 未找到可行解，使用最后一次评估结果")
            if global_best_solution is not None:
                routes = self._solution_to_routes(
                    global_best_solution, depots, customers, distance_matrix
                )
            else:
                # 使用第一个粒子的位置
                routes = self._solution_to_routes(
                    particles[0]['position'], depots, customers, distance_matrix
                )
        
        compute_time = time.time() - start_time
        
        print(f"\n求解完成")
        print(f"  最优成本: {global_best_cost:.2f}")
        print(f"  路径数: {len(routes)}")
        print(f"  计算时间: {compute_time:.2f}秒")
        print(f"{'='*60}\n")
        
        return {
            'algorithm': 'PSO-MDVRP (Python)',
            'total_cost': global_best_cost,
            'compute_time': compute_time,
            'routes': routes,
            'num_vehicles': len(routes),
            'convergence_data': []
        }
    
    def _build_distance_matrix(
        self,
        depots: List[Dict],
        customers: List[Dict]
    ) -> np.ndarray:
        """构建欧几里得距离矩阵"""
        num_depots = len(depots)
        num_customers = len(customers)
        total_nodes = num_depots + num_customers
        
        matrix = np.zeros((total_nodes, total_nodes))
        
        # 收集坐标
        coords = []
        for depot in depots:
            coords.append((depot['x'], depot['y']))
        for customer in customers:
            coords.append((customer['x'], customer['y']))
        
        # 计算距离
        for i in range(total_nodes):
            for j in range(total_nodes):
                if i != j:
                    x1, y1 = coords[i]
                    x2, y2 = coords[j]
                    matrix[i, j] = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        
        return matrix
    
    def _initialize_particles(
        self,
        depots: List[Dict],
        customers: List[Dict]
    ) -> List[Dict]:
        """初始化粒子群"""
        particles = []
        num_customers = len(customers)
        
        for _ in range(self.particle_count):
            # 随机排列客户
            position = list(range(num_customers))
            random.shuffle(position)
            
            particle = {
                'position': position,
                'velocity': [0] * num_customers,
                'best_position': position.copy(),
                'best_cost': float('inf')
            }
            particles.append(particle)
        
        return particles
    
    def _solution_to_routes(
        self,
        solution: List[int],
        depots: List[Dict],
        customers: List[Dict],
        distance_matrix: np.ndarray
    ) -> List[Dict]:
        """将解转换为路径"""
        routes = []
        num_depots = len(depots)
        
        # 为每个仓库分配车辆
        depot_vehicles = []
        for depot_idx, depot in enumerate(depots):
            for vehicle_idx in range(depot['vehicle_count']):
                depot_vehicles.append({
                    'depot_id': depot_idx,
                    'depot_idx': depot_idx,
                    'vehicle_id': len(depot_vehicles) + 1,
                    'capacity': depot['capacity'],
                    'remaining_capacity': depot['capacity'],
                    'customers': []
                })
        
        print(f"\n[路径构建] 总车辆数: {len(depot_vehicles)}, 总客户数: {len(solution)}")
        
        # 贪心分配客户到车辆
        assigned_count = 0
        for customer_idx in solution:
            customer = customers[customer_idx]
            demand = customer['demand']
            
            # 找到最近的有容量的车辆
            best_vehicle = None
            best_cost = float('inf')
            
            for vehicle in depot_vehicles:
                if vehicle['remaining_capacity'] >= demand:
                    # 计算插入成本
                    depot_idx = vehicle['depot_idx']
                    
                    if not vehicle['customers']:
                        # 空路径：仓库 -> 客户 -> 仓库
                        cost = (
                            distance_matrix[depot_idx, num_depots + customer_idx] +
                            distance_matrix[num_depots + customer_idx, depot_idx]
                        )
                    else:
                        # 插入到路径末尾
                        last_customer_idx = vehicle['customers'][-1]
                        cost = (
                            distance_matrix[num_depots + last_customer_idx, num_depots + customer_idx] +
                            distance_matrix[num_depots + customer_idx, depot_idx] -
                            distance_matrix[num_depots + last_customer_idx, depot_idx]
                        )
                    
                    if cost < best_cost:
                        best_cost = cost
                        best_vehicle = vehicle
            
            # 分配客户到最佳车辆
            if best_vehicle:
                best_vehicle['customers'].append(customer_idx)
                best_vehicle['remaining_capacity'] -= demand
                assigned_count += 1
        
        print(f"[路径构建] 成功分配 {assigned_count}/{len(solution)} 个客户")
        
        # 转换为输出格式
        for vehicle in depot_vehicles:
            if vehicle['customers']:
                # 计算路径成本
                cost = self._calculate_route_cost(
                    vehicle['depot_idx'],
                    vehicle['customers'],
                    distance_matrix,
                    num_depots
                )
                
                # 将客户索引转换为客户ID
                customer_ids = [customers[idx]['id'] for idx in vehicle['customers']]
                
                routes.append({
                    'depot_id': vehicle['depot_id'],
                    'vehicle_id': vehicle['vehicle_id'],
                    'customers': customer_ids,  # 使用客户ID而不是索引
                    'cost': cost
                })
        
        print(f"[路径构建] 生成 {len(routes)} 条非空路径")
        
        return routes
    
    def _calculate_route_cost(
        self,
        depot_idx: int,
        customer_indices: List[int],
        distance_matrix: np.ndarray,
        num_depots: int
    ) -> float:
        """计算路径成本"""
        if not customer_indices:
            return 0.0
        
        cost = 0.0
        
        # 仓库到第一个客户
        cost += distance_matrix[depot_idx, num_depots + customer_indices[0]]
        
        # 客户之间
        for i in range(len(customer_indices) - 1):
            from_idx = num_depots + customer_indices[i]
            to_idx = num_depots + customer_indices[i + 1]
            cost += distance_matrix[from_idx, to_idx]
        
        # 最后一个客户回仓库
        cost += distance_matrix[num_depots + customer_indices[-1], depot_idx]
        
        return cost
    
    def _update_particle(
        self,
        particle: Dict,
        global_best: List[int]
    ):
        """更新粒子速度和位置"""
        # 简化的PSO更新：随机交换操作
        r1 = random.random()
        r2 = random.random()
        
        # 以一定概率向个体最优移动
        if r1 < self.c1 / (self.c1 + self.c2):
            self._move_towards(particle['position'], particle['best_position'])
        
        # 以一定概率向全局最优移动
        if r2 < self.c2 / (self.c1 + self.c2):
            self._move_towards(particle['position'], global_best)
        
        # 随机扰动（惯性）
        if random.random() < self.w:
            self._random_swap(particle['position'])
    
    def _move_towards(self, current: List[int], target: List[int]):
        """将当前位置向目标位置移动"""
        # 找到不同的位置并交换
        for i in range(len(current)):
            if current[i] != target[i]:
                # 找到target[i]在current中的位置
                j = current.index(target[i])
                # 交换
                current[i], current[j] = current[j], current[i]
                break
    
    def _random_swap(self, position: List[int]):
        """随机交换两个位置"""
        i = random.randint(0, len(position) - 1)
        j = random.randint(0, len(position) - 1)
        position[i], position[j] = position[j], position[i]


# 测试代码
if __name__ == '__main__':
    print("测试 PSO-MDVRP Python求解器\n")
    
    # 创建测试实例
    instance_data = {
        'depots': [
            {'x': 20, 'y': 20, 'vehicle_count': 2, 'capacity': 80},
            {'x': 30, 'y': 40, 'vehicle_count': 2, 'capacity': 80},
        ],
        'customers': [
            {'x': 10, 'y': 10, 'demand': 10},
            {'x': 15, 'y': 15, 'demand': 15},
            {'x': 25, 'y': 25, 'demand': 20},
            {'x': 35, 'y': 35, 'demand': 12},
            {'x': 40, 'y': 40, 'demand': 18},
        ]
    }
    
    try:
        # 创建求解器
        solver = PSOSolver(particle_count=20, iterations=50)
        
        # 求解
        result = solver.solve(instance_data)
        
        print("\n最终结果:")
        print(f"  算法: {result['algorithm']}")
        print(f"  总成本: {result['total_cost']:.2f}")
        print(f"  路径数: {result['num_vehicles']}")
        print(f"  计算时间: {result['compute_time']:.2f}秒")
        
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
