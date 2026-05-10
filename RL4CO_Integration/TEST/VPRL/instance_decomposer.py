"""
实例分解器: 将 MDVRP 转换为多个 CVRP 子问题
"""

import numpy as np
import torch
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from tensordict import TensorDict
from sklearn.cluster import KMeans


@dataclass
class CVRPSubProblem:
    """单个仓库的 CVRP 子问题"""
    depot_id: int
    depot_coords: np.ndarray       # [2]
    customer_indices: List[int]    # 全局客户 ID
    customer_coords: np.ndarray    # [N, 2]
    demands: np.ndarray            # [N]
    capacity: float
    distance_limit: float
    tensordict: Optional[TensorDict] = None


class InstanceDecomposer:
    """将 MDVRP 分解为 CVRP 子问题"""
    
    @staticmethod
    def decompose_mdvrp(instance, strategy: str = "nearest") -> List[CVRPSubProblem]:
        """
        将 MDVRP 分解为 CVRP 子问题(每个仓库一个)
        
        参数:
            instance: MDVRPInstance 对象
            strategy: 客户分配策略 ("nearest", "balanced", "kmeans")
            
        返回:
            CVRP 子问题列表
        """
        num_depots = instance.num_depots
        num_customers = instance.num_customers
        
        # 将客户分配给仓库
        assignments = InstanceDecomposer.assign_customers_to_depots(
            customers=instance.customers_coords,
            depots=instance.depots_coords,
            strategy=strategy
        )
        
        # 创建 CVRP 子问题
        sub_problems = []
        for depot_id in range(num_depots):
            customer_indices = assignments.get(depot_id, [])
            
            if len(customer_indices) == 0:
                # 跳过空仓库
                continue
            
            # 提取该仓库客户的数据
            customer_coords = instance.customers_coords[customer_indices]
            customer_demands = instance.demands[customer_indices]
            
            # 创建子问题
            sub_problem = CVRPSubProblem(
                depot_id=depot_id,
                depot_coords=instance.depots_coords[depot_id],
                customer_indices=customer_indices,
                customer_coords=customer_coords,
                demands=customer_demands,
                capacity=float(instance.depot_capacities[depot_id]),
                distance_limit=float(instance.max_route_distances[depot_id]) 
                    if instance.max_route_distances is not None else 0.0
            )
            
            # 转换为 TensorDict
            sub_problem.tensordict = InstanceDecomposer.convert_to_tensordict(
                depot_coords=sub_problem.depot_coords,
                customer_coords=sub_problem.customer_coords,
                demands=sub_problem.demands,
                capacity=sub_problem.capacity,
                distance_limit=sub_problem.distance_limit
            )
            
            sub_problems.append(sub_problem)
        
        return sub_problems
    
    @staticmethod
    def assign_customers_to_depots(
        customers: np.ndarray,
        depots: np.ndarray,
        strategy: str = "nearest") -> Dict[int, List[int]]:
        """
        将客户分配给仓库
        
        参数:
            customers: 客户坐标 [N, 2]
            depots: 仓库坐标 [M, 2]
            strategy: 分配策略 ("nearest", "balanced", "kmeans")
            
        返回:
            字典,映射 depot_id 到客户索引列表
        """
        num_customers = len(customers)
        num_depots = len(depots)
        
        if strategy == "nearest":
            # 将每个客户分配给最近的仓库
            assignments = {i: [] for i in range(num_depots)}
            
            for cust_idx in range(num_customers):
                cust_coord = customers[cust_idx]
                distances = np.linalg.norm(depots - cust_coord, axis=1)
                nearest_depot = np.argmin(distances)
                assignments[nearest_depot].append(cust_idx)
        
        elif strategy == "balanced":
            # 平衡各仓库的客户数量
            assignments = {i: [] for i in range(num_depots)}
            
            # 计算每个客户到每个仓库的距离
            distances = np.zeros((num_customers, num_depots))
            for i in range(num_customers):
                for j in range(num_depots):
                    distances[i, j] = np.linalg.norm(customers[i] - depots[j])
            
            # 按到任意仓库的最小距离排序客户
            min_distances = np.min(distances, axis=1)
            sorted_customers = np.argsort(min_distances)
            
            # 以轮询方式分配客户
            for idx, cust_idx in enumerate(sorted_customers):
                depot_id = idx % num_depots
                assignments[depot_id].append(int(cust_idx))
        
        elif strategy == "kmeans":
            # 使用 K-means 聚类
            if num_depots > 1:
                kmeans = KMeans(n_clusters=num_depots, init=depots, n_init=1, random_state=42)
                labels = kmeans.fit_predict(customers)
                
                assignments = {i: [] for i in range(num_depots)}
                for cust_idx, label in enumerate(labels):
                    assignments[int(label)].append(cust_idx)
            else:
                # 单仓库:分配所有客户
                assignments = {0: list(range(num_customers))}
        
        else:
            raise ValueError(f"未知的分配策略: {strategy}")
        
        return assignments
    
    @staticmethod
    def convert_to_tensordict(
        depot_coords: np.ndarray,
        customer_coords: np.ndarray,
        demands: np.ndarray,
        capacity: float,
        distance_limit: float) -> TensorDict:
        """
        将 CVRP 子问题转换为 RL4CO TensorDict 格式
        
        创建与 MTVRPGenerator 兼容的完整 TensorDict,
        包括 subsample=True 时所需的所有字段。
        
        参数:
            depot_coords: 仓库坐标 [2]
            customer_coords: 客户坐标 [N, 2]
            demands: 客户需求 [N]
            capacity: 车辆容量
            distance_limit: 最大路径距离
            
        返回:
            与 RL4CO MTVRP 环境兼容的 TensorDict
        """
        num_customers = len(customer_coords)
        
        # 合并仓库和客户坐标
        # RL4CO 期望格式: [仓库, 客户1, 客户2, ...]
        locs = np.vstack([depot_coords.reshape(1, 2), customer_coords])
        
        # 需求:仓库需求为 0
        demand_linehaul = np.concatenate([[0.0], demands])
        
        # 按容量缩放需求(MTVRPGenerator 在 scale_demand=True 时期望缩放后的需求)
        demand_linehaul_scaled = demand_linehaul / capacity
        
        # 转换为张量并添加批次维度
        td = TensorDict({
            'locs': torch.tensor(locs, dtype=torch.float32).unsqueeze(0),  # [1, N+1, 2]
            'demand_linehaul': torch.tensor(demand_linehaul_scaled, dtype=torch.float32).unsqueeze(0),  # [1, N+1] (已缩放)
            'demand_backhaul': torch.zeros(1, num_customers + 1, dtype=torch.float32),  # [1, N+1]
            'backhaul_class': torch.tensor([1.0], dtype=torch.float32).unsqueeze(0),  # [1, 1] - 经典回程
            'distance_limit': torch.tensor([distance_limit], dtype=torch.float32).unsqueeze(0),  # [1, 1]
            'time_windows': torch.tensor(
                [[0.0, float('inf')]] * (num_customers + 1), 
                dtype=torch.float32
            ).unsqueeze(0),  # [1, N+1, 2]
            'service_time': torch.zeros(1, num_customers + 1, dtype=torch.float32),  # [1, N+1]
            'vehicle_capacity': torch.tensor([1.0], dtype=torch.float32).unsqueeze(0),  # [1, 1] - 缩放后的容量
            'capacity_original': torch.tensor([capacity], dtype=torch.float32).unsqueeze(0),  # [1, 1] - 未缩放的容量
            'open_route': torch.tensor([False], dtype=torch.bool).unsqueeze(0),  # [1, 1]
            'speed': torch.tensor([1.0], dtype=torch.float32).unsqueeze(0),  # [1, 1]
        }, batch_size=[1])
        
        return td
