"""
MDVRP求解器 - 封装遗传算法为REST服务
"""
import numpy as np
import time
from dataclasses import dataclass, field
from typing import Any
from multiprocessing import Pool, cpu_count

# 导入本地算法模块
# 算法模块延迟导入，避免依赖问题

# 全局变量
instance = None


@dataclass
class MDVRPInstance:
    """
    MDVRP 实例数据容器 - API 专用版本
    支持每个仓库有不同的车辆数和容量
    """
    name: str
    num_customers: int
    num_depots: int
    
    # 每个仓库的车辆数和容量 (shape: num_depots)
    depot_vehicles: np.ndarray      # 每个仓库的车辆数
    depot_capacities: np.ndarray    # 每个仓库的车辆容量
    
    # 坐标数据: shape (N, 2)
    depots_coords: np.ndarray
    customers_coords: np.ndarray
    
    # 客户需求: shape (num_customers,)
    demands: np.ndarray
    
    # 距离矩阵: shape (total_nodes, total_nodes)
    distance_matrix: np.ndarray = field(repr=False)
    
    # 最大路径长度约束 (shape: num_depots) - 可选
    max_route_distances: np.ndarray = field(default=None)
    
    # 兼容属性（用于旧代码）
    @property
    def num_vehicles(self) -> int:
        """总车辆数（所有仓库的车辆数之和）"""
        return int(np.sum(self.depot_vehicles))
    
    @property
    def vehicle_capacity(self) -> int:
        """平均车辆容量（用于兼容）"""
        return int(np.mean(self.depot_capacities))
    
    def __getitem__(self, key: str) -> Any:
        """兼容字典访问方式"""
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(f"MDVRPInstance has no key '{key}'")
    
    def get_distance(self, i: int, j: int) -> float:
        """获取两点间距离 (标量访问)"""
        return float(self.distance_matrix[i, j])

class MDVRPSolver:
    
    def __init__(self, depots, customers, params):
        """
        初始化求解器
        
        Args:
            depots: 仓库列表 [{"id": 1, "x": 0, "y": 0, "vehicles": 5, "capacity": 100}, ...]
            customers: 客户列表 [{"id": 1, "x": 10, "y": 20, "demand": 15}, ...]
            params: 算法参数 {"algorithm": "genetic", "max_iterations": 1000, ...}
        """
        self.depots = depots
        self.customers = customers
        self.params = params
        
        # 提取每个仓库的车辆数和容量（支持不同仓库有不同配置）
        self.depot_vehicles = np.array([d.get('vehicles', 5) for d in depots] if depots else [5], dtype=np.int32)
        self.depot_capacities = np.array([d.get('capacity', 100) for d in depots] if depots else [100], dtype=np.int32)
        # 每个仓库的最大行驶距离，<=0 表示不限制
        self.depot_max_distances = np.array(
            [float(d.get('maxDistance', d.get('max_distance', 0))) for d in depots] if depots else [0.0],
            dtype=np.float64
        )
        
        # 创建 ID 映射（索引 -> 实际 ID）
        self.depot_id_map = {i: d['id'] for i, d in enumerate(depots)}
        self.customer_id_map = {i: c['id'] for i, c in enumerate(customers)}
        
        # 转换为MDVRPInstance格式
        self.instance = self._convert_to_instance()
        
    def _convert_to_instance(self):
        """将JSON格式转换为MDVRPInstance对象"""
        num_depots = len(self.depots)
        num_customers = len(self.customers)
        
        # 构建坐标数组
        depots_coords = np.array([[d['x'], d['y']] for d in self.depots], dtype=np.float32)
        customers_coords = np.array([[c['x'], c['y']] for c in self.customers], dtype=np.float32)
        
        # 构建需求数组
        demands = np.array([c.get('demand', 10) for c in self.customers], dtype=np.int32)
        
        # 计算距离矩阵
        all_coords = np.vstack((depots_coords, customers_coords))
        diff = all_coords[:, np.newaxis, :] - all_coords[np.newaxis, :, :]
        distance_matrix = np.sqrt(np.sum(diff**2, axis=-1))
        
        return MDVRPInstance(
            name="api_instance",
            num_customers=num_customers,
            num_depots=num_depots,
            depot_vehicles=self.depot_vehicles,      # 每个仓库的车辆数
            depot_capacities=self.depot_capacities,  # 每个仓库的容量
            depots_coords=depots_coords,
            customers_coords=customers_coords,
            demands=demands,
            distance_matrix=distance_matrix,
            max_route_distances=self.depot_max_distances
        )
    
    def solve(self):
        """求解方法（由子类实现）"""
        raise NotImplementedError


class GeneticAlgorithmSolver(MDVRPSolver):
    """遗传算法求解器 - 使用Java版本的GA-MDVRP"""

    def solve(self):
        """
        使用Java版GA-MDVRP求解MDVRP (Ombuki-Berman 2009)

        Returns:
            dict: {
                'routes': [...],
                'totalCost': float,
                'computeTime': float,
                'convergence': [...]  # 收敛曲线数据
            }
        """
        try:
            from .ga_mdvrp_java import GAMDVRPJava
        except ImportError:
            from ga_mdvrp_java import GAMDVRPJava
        
        # 创建 Java 求解器实例
        java_solver = GAMDVRPJava()
        
        # 调用求解（传入 MDVRPInstance 对象）
        result = java_solver.solve(self.instance)
        
        # 格式转换：将 Java 返回的结果转换为统一格式
        routes = []
        for route in result.get('routes', []):
            # 将索引转换为实际 ID
            depot_id = self.depot_id_map.get(route['depot_id'], route['depot_id'])
            customers = [self.customer_id_map.get(c, c) for c in route['customers']]
            
            routes.append({
                'vehicleId': route['vehicle_id'],
                'depotId': depot_id,
                'path': customers,
                'cost': route.get('cost', 0)
            })
        
        return {
            'routes': routes,
            'totalCost': result['total_cost'],
            'computeTime': result['compute_time'],
            'numRoutes': result['num_vehicles'],
            'algorithm': 'GA-MDVRP (Ombuki-Berman 2009)',
            'convergence': result.get('convergence_data', [])
        }
    
    def _format_solution(self, solution, total_cost, compute_time, convergence_data):
        """将算法结果转换为API返回格式（已废弃，算法内部自行格式化）"""
        # 注意：现代算法实现已经在内部完成格式化，此方法保留用于兼容
        return {
            'routes': solution.get('routes', []),
            'totalCost': float(total_cost),
            'computeTime': float(compute_time),
            'convergence': convergence_data,
            'algorithm': 'genetic',
            'numRoutes': len(solution.get('routes', []))
        }


class GAMultiprogrammingSolver(MDVRPSolver):
    """遗传算法多进程求解器 - 使用Python版本"""

    def solve(self):
        """
        使用Python多进程版遗传算法求解MDVRP

        Returns:
            dict: {
                'routes': [...],
                'totalCost': float,
                'computeTime': float,
                'convergence': [...]  # 收敛曲线数据
            }
        """
        # 使用多进程版GA
        from .ga_multiprogramming import GeneticAlgorithmOptimized
        optimizer = GeneticAlgorithmOptimized(
            self.instance, 
            self.params,
            depot_id_map=self.depot_id_map,
            customer_id_map=self.customer_id_map
        )

        # 求解
        return optimizer.solve()


class GAMDVRPRLHybridSolver(MDVRPSolver):
    """GA-MDVRP + RouteFinder 混合求解器"""

    def solve(self):
        """
        使用 GA + RouteFinder 混合算法求解 MDVRP

        Returns:
            dict: {
                'routes': [...],
                'totalCost': float,
                'computeTime': float,
                'numRoutes': int,
                'algorithm': str,
                'convergence': []
            }
        """
        try:
            from .ga_mdvrp_rl_hybrid import GAMDVRPRLHybrid
        except ImportError:
            from ga_mdvrp_rl_hybrid import GAMDVRPRLHybrid
        
        # 准备instance_data格式
        instance_data = {
            'depots': [
                {
                    'x': float(self.instance.depots_coords[i][0]),
                    'y': float(self.instance.depots_coords[i][1]),
                    'vehicle_count': int(self.instance.depot_vehicles[i]),
                    'capacity': int(self.instance.depot_capacities[i])
                }
                for i in range(self.instance.num_depots)
            ],
            'customers': [
                {
                    'x': float(self.instance.customers_coords[i][0]),
                    'y': float(self.instance.customers_coords[i][1]),
                    'demand': int(self.instance.demands[i])
                }
                for i in range(self.instance.num_customers)
            ],
            'max_distance': float(self.instance.max_route_distances[0]) if self.instance.max_route_distances is not None and len(self.instance.max_route_distances) > 0 else 0
        }
        
        # 创建混合求解器
        hybrid_solver = GAMDVRPRLHybrid(
            rl_seed_ratio=self.params.get('rl_seed_ratio', 0.2),
            num_rl_samples=self.params.get('num_rl_samples', 20),
            use_gpu=self.params.get('use_gpu', True),
            model_type=self.params.get('model_type', 'auto')
        )
        
        # 求解
        result = hybrid_solver.solve(instance_data)
        
        # 格式转换
        routes = []
        for route in result.get('routes', []):
            depot_id = self.depot_id_map.get(route.get('depot_id', 0), route.get('depot_id', 0))
            customers = [self.customer_id_map.get(c, c) for c in route.get('customers', [])]
            
            routes.append({
                'vehicleId': route.get('vehicle_id', 0),
                'depotId': depot_id,
                'path': customers,
                'cost': route.get('cost', 0)
            })
        
        return {
            'routes': routes,
            'totalCost': result.get('total_cost', 0),
            'computeTime': result.get('compute_time', 0),
            'numRoutes': len(routes),
            'algorithm': 'GA-MDVRP + RouteFinder Hybrid',
            'convergence': result.get('convergence', [])
        }


class GAMDVRPJavaSolver(GeneticAlgorithmSolver):
    """GA-MDVRP Java 版本求解器（Ombuki-Berman 2009）- 与GeneticAlgorithmSolver相同"""
    pass


def create_solver(depots, customers, params):
    """
    工厂方法：根据参数创建对应的求解器
    
    Args:
        depots: 仓库列表
        customers: 客户列表
        params: 算法参数，包含 'algorithm' 字段
    
    Returns:
        MDVRPSolver: 求解器实例
    """
    algorithm = params.get('algorithm', 'genetic')
    
    if algorithm == 'genetic' or algorithm == 'GA':
        # GA算法 - 使用Java版本 (Ombuki-Berman 2009)
        return GeneticAlgorithmSolver(depots, customers, params)
    elif algorithm == 'ga_multiprogramming':
        # 多进程遗传算法 - 使用Python版本
        return GAMultiprogrammingSolver(depots, customers, params)
    elif algorithm == 'ACO':
        # 蚁群算法 (Ant Colony Optimization)
        from . import aco
        return aco.AntColonySolver(depots, customers, params)
    elif algorithm == 'PSO':
        # 粒子群算法 (Particle Swarm Optimization)
        from . import pso
        return pso.ParticleSwarmSolver(depots, customers, params)
    elif algorithm == 'SA':
        # 模拟退火算法尚未实现
        raise NotImplementedError("模拟退火算法 (SA) 尚未实现，请选择 GA, ACO 或 PSO 算法")
    elif algorithm == 'ant_colony':
        # 兼容旧的命名
        from . import aco
        return aco.AntColonySolver(depots, customers, params)
    elif algorithm == 'GA_MDVRP_JAVA' or algorithm == 'ga_mdvrp_java':
        # GA-MDVRP Java 版本（Ombuki-Berman 2009） - 与genetic相同
        return GAMDVRPJavaSolver(depots, customers, params)
    elif algorithm == 'GA_RL_HYBRID' or algorithm == 'ga_rl_hybrid' or algorithm == 'hybrid':
        # GA-MDVRP + RouteFinder 混合求解器
        return GAMDVRPRLHybridSolver(depots, customers, params)
    elif algorithm == 'tabu_search':
        # TODO: 实现禁忌搜索
        raise NotImplementedError("禁忌搜索尚未实现")
    else:
        raise ValueError(f"不支持的算法类型: {algorithm}，支持的算法: GA, ga_multiprogramming, ACO, PSO, GA_MDVRP_JAVA, GA_RL_HYBRID")
