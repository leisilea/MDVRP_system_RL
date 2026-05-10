"""
解转换器: 将 RL4CO 解转换为 Cordeau 格式
"""

import numpy as np
import torch
from typing import List, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Route:
    """Cordeau 格式的路径"""
    depot_id: int          # 仓库 ID(1-based)
    vehicle_id: int        # 车辆 ID
    customers: List[int]   # 客户 ID 列表(1-based)
    cost: float           # 路径距离
    load: float           # 总需求量


class SolutionConverter:
    """将 RL4CO 解转换为 Cordeau 格式"""
    
    @staticmethod
    def convert_rl4co_to_cordeau(
        actions: torch.Tensor,
        depot_id: int,
        customer_mapping: Dict[int, int],
        depot_coords: np.ndarray,
        customer_coords: np.ndarray,
        demands: np.ndarray,
        capacity: float) -> List[Route]:
        """
        将 RL4CO 动作序列转换为 Cordeau 路径格式
        
        参数:
            actions: RL4CO 动作张量 [seq_len]
            depot_id: 仓库 ID(0-based,将被转换为 1-based)
            customer_mapping: 局部客户索引到全局客户 ID 的映射(0-based)
            depot_coords: 仓库坐标 [2]
            customer_coords: 客户坐标 [N, 2]
            demands: 客户需求 [N]
            capacity: 车辆容量
            
        返回:
            Cordeau 格式的路径列表
        """
        # 将动作转换为 numpy
        if isinstance(actions, torch.Tensor):
            actions = actions.cpu().numpy()
        
        # 解析动作序列以提取客户访问顺序
        # RL4CO 动作: 0 = 仓库, 1+ = 客户
        customer_sequence = []
        for action in actions:
            action_int = int(action)
            if action_int > 0:  # 客户(非仓库)
                # 从 RL4CO 索引(动作中为 1-based)转换为局部索引(0-based)
                local_idx = action_int - 1
                if local_idx < len(customer_mapping):
                    customer_sequence.append(local_idx)
        
        # 根据容量约束分割为多条路径
        routes = []
        current_route = []
        current_load = 0.0
        vehicle_id = 1
        
        for local_idx in customer_sequence:
            demand = demands[local_idx]
            
            # 检查添加此客户是否超过容量
            if current_load + demand > capacity and len(current_route) > 0:
                # 完成当前路径
                route = SolutionConverter._create_route(
                    depot_id=depot_id + 1,  # 转换为 1-based
                    vehicle_id=vehicle_id,
                    local_customers=current_route,
                    customer_mapping=customer_mapping,
                    depot_coords=depot_coords,
                    customer_coords=customer_coords,
                    demands=demands
                )
                routes.append(route)
                
                # 开始新路径
                current_route = []
                current_load = 0.0
                vehicle_id += 1
            
            # 将客户添加到当前路径
            current_route.append(local_idx)
            current_load += demand
        
        # 如果不为空,添加最后一条路径
        if len(current_route) > 0:
            route = SolutionConverter._create_route(
                depot_id=depot_id + 1,  # 转换为 1-based
                vehicle_id=vehicle_id,
                local_customers=current_route,
                customer_mapping=customer_mapping,
                depot_coords=depot_coords,
                customer_coords=customer_coords,
                demands=demands
            )
            routes.append(route)
        
        return routes
    
    @staticmethod
    def _create_route(
        depot_id: int,
        vehicle_id: int,
        local_customers: List[int],
        customer_mapping: Dict[int, int],
        depot_coords: np.ndarray,
        customer_coords: np.ndarray,
        demands: np.ndarray) -> Route:
        """创建带有成本和载重计算的 Route 对象"""
        
        # 将局部索引转换为全局 1-based 客户 ID
        global_customers = [customer_mapping[local_idx] + 1 for local_idx in local_customers]
        
        # 计算路径成本(距离)
        cost = 0.0
        prev_coords = depot_coords
        
        for local_idx in local_customers:
            curr_coords = customer_coords[local_idx]
            cost += np.linalg.norm(curr_coords - prev_coords)
            prev_coords = curr_coords
        
        # 返回仓库
        cost += np.linalg.norm(depot_coords - prev_coords)
        
        # 计算总载重
        load = sum(demands[local_idx] for local_idx in local_customers)
        
        return Route(
            depot_id=depot_id,
            vehicle_id=vehicle_id,
            customers=global_customers,
            cost=float(cost),
            load=float(load)
        )
    
    @staticmethod
    def validate_route(
        route: Route,
        capacity: float,
        distance_limit: float) -> Tuple[bool, str]:
        """
        根据约束验证路径
        
        参数:
            route: 要验证的路径
            capacity: 车辆容量
            distance_limit: 最大路径距离
            
        返回:
            (is_valid, error_message)
        """
        # 检查容量约束
        if route.load > capacity:
            return False, f"Capacity exceeded: {route.load:.2f} > {capacity:.2f}"
        
        # 检查距离约束(如果指定)
        if distance_limit > 0 and route.cost > distance_limit:
            return False, f"Distance exceeded: {route.cost:.2f} > {distance_limit:.2f}"
        
        # 检查路径不为空
        if len(route.customers) == 0:
            return False, "Empty route"
        
        return True, ""
    
    @staticmethod
    def write_initial_solution_file(
        routes: List[Route],
        filepath: str,
        instance_name: str) -> None:
        """
        为 GA_Java 写入初始解文件
        
        参数:
            routes: 路径列表
            filepath: 输出文件路径
            instance_name: 实例名称(用于参考)
        """
        with open(filepath, 'w') as f:
            # 写入文件头
            f.write("# Initial solutions for GA-MDVRP\n")
            f.write(f"# Instance: {instance_name}\n")
            f.write("# Generated by: VPRL_Sampler\n")
            f.write(f"# Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Number of routes: {len(routes)}\n")
            f.write("\n")
            
            # 计算总成本
            total_cost = sum(route.cost for route in routes)
            
            # 写入解
            f.write("SOLUTION 1\n")
            f.write(f"COST {total_cost:.2f}\n")
            
            # 按仓库分组路径
            routes_by_depot = {}
            for route in routes:
                if route.depot_id not in routes_by_depot:
                    routes_by_depot[route.depot_id] = []
                routes_by_depot[route.depot_id].append(route)
            
            # 写入路径
            for depot_id in sorted(routes_by_depot.keys()):
                depot_routes = routes_by_depot[depot_id]
                for route in depot_routes:
                    # 格式: ROUTE depot_id vehicle_id: 0 customer1 customer2 ... 0
                    customers_str = " ".join(str(c) for c in route.customers)
                    f.write(f"ROUTE {route.depot_id} {route.vehicle_id}: 0 {customers_str} 0\n")
            
            f.write("\n")
