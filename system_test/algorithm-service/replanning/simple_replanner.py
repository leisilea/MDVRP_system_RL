"""
简化版重规划器

只处理被堵车辆的绕路重规划,不涉及任务重新分配
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
import time
import logging

logger = logging.getLogger(__name__)


class SimpleReplanner:
    """简化的重规划器 - 只处理绕路,不重新分配任务"""
    
    BLOCKED_DISTANCE = 1000000.0  # 阻塞路段的距离值
    
    def __init__(self, depots: List[Dict], customers: List[Dict]):
        """
        初始化重规划器
        
        Args:
            depots: 仓库列表 (使用数据库ID)
            customers: 客户列表 (使用数据库ID)
        """
        self.depots = depots
        self.customers = customers
        
        # 构建ID映射 (数据库ID -> 节点对象)
        self.depot_map = {d['id']: d for d in depots}
        self.customer_map = {c['id']: c for c in customers}
        
        # 构建ID到索引的映射 (数据库ID -> 矩阵索引)
        self.id_to_index = {}
        for i, depot in enumerate(depots):
            self.id_to_index[depot['id']] = i
        
        depot_count = len(depots)
        for i, customer in enumerate(customers):
            self.id_to_index[customer['id']] = depot_count + i
        
        # 构建索引到ID的映射 (矩阵索引 -> 数据库ID)
        self.index_to_id = {v: k for k, v in self.id_to_index.items()}
        
        # 构建原始距离矩阵 (使用索引访问)
        self.original_distance_matrix = self._build_distance_matrix()
    
    def replan(
        self,
        routes: List[Dict],
        blocked_edges: List[Dict],
        vehicle_positions: Optional[Dict[int, int]] = None,
        algorithm: str = "genetic"
    ) -> Dict:
        """
        执行简化重规划
        
        Args:
            routes: 当前路径列表
            blocked_edges: 阻塞路段列表 [{from: int, to: int}]
            vehicle_positions: 车辆当前位置 {vehicle_id: customer_id}
            algorithm: 使用的算法
        
        Returns:
            重规划结果
        """
        start_time = time.time()
        
        logger.info(f"[重规划] 开始 - 路径数: {len(routes)}, 阻塞路段数: {len(blocked_edges)}")
        logger.info(f"[重规划] 阻塞路段: {blocked_edges}")
        logger.info(f"[重规划] 车辆位置: {vehicle_positions}")
        
        # 1. 识别被堵车辆
        affected_vehicles = self._identify_affected_vehicles(routes, blocked_edges, vehicle_positions)
        
        logger.info(f"[重规划] 受影响车辆数: {len(affected_vehicles)}")
        logger.info(f"[重规划] 受影响车辆ID: {list(affected_vehicles.keys())}")
        
        if not affected_vehicles:
            # 没有车辆受影响,直接返回原路径
            logger.warning("[重规划] 没有车辆受影响!")
            return {
                'new_routes': routes,
                'replanned_route_ids': [],
                'cost_before': self._calculate_total_cost(routes, self.original_distance_matrix),
                'cost_after': self._calculate_total_cost(routes, self.original_distance_matrix),
                'cost_difference': 0.0,
                'cost_change_percent': 0.0,
                'algorithm': algorithm,
                'solve_time': time.time() - start_time,
                'num_routes': len(routes),
                'affected_vehicles': []
            }
        
        # 2. 修改距离矩阵(设置阻塞路段为不可通行)
        modified_matrix = self._modify_distance_matrix(blocked_edges)
        
        logger.info(f"[重规划] 距离矩阵已修改 - 阻塞路段设置为 {self.BLOCKED_DISTANCE}")
        
        # 3. 对每辆被堵车辆进行局部重规划
        new_routes = []
        replanned_ids = []
        
        for route in routes:
            vehicle_id = route['vehicleId']
            
            if vehicle_id in affected_vehicles:
                logger.info(f"[重规划] 车辆 {vehicle_id} - 原路径: {route['path']}")
                
                # 被堵车辆 - 重规划剩余路径
                new_route = self._replan_single_vehicle(
                    route,
                    vehicle_positions.get(vehicle_id) if vehicle_positions else None,
                    modified_matrix,
                    algorithm
                )
                
                logger.info(f"[重规划] 车辆 {vehicle_id} - 新路径: {new_route['path']}")
                logger.info(f"[重规划] 车辆 {vehicle_id} - 新成本: {new_route.get('cost', 0):.2f}")
                
                new_routes.append(new_route)
                replanned_ids.append(vehicle_id)
            else:
                # 未受影响车辆 - 保持原路径
                new_routes.append(route)
        
        # 4. 计算成本对比
        cost_before = self._calculate_total_cost(routes, modified_matrix)
        cost_after = self._calculate_total_cost(new_routes, modified_matrix)
        cost_diff = cost_after - cost_before
        cost_percent = (cost_diff / cost_before * 100) if cost_before > 0 else 0.0
        
        logger.info(f"[重规划] 成本对比 - 前: {cost_before:.2f}, 后: {cost_after:.2f}, 差异: {cost_diff:.2f} ({cost_percent:.2f}%)")
        
        return {
            'new_routes': new_routes,
            'replanned_route_ids': replanned_ids,
            'cost_before': cost_before,
            'cost_after': cost_after,
            'cost_difference': cost_diff,
            'cost_change_percent': cost_percent,
            'algorithm': algorithm,
            'solve_time': time.time() - start_time,
            'num_routes': len(new_routes),
            'affected_vehicles': list(affected_vehicles.keys())
        }
    
    def _identify_affected_vehicles(
        self,
        routes: List[Dict],
        blocked_edges: List[Dict],
        vehicle_positions: Optional[Dict[int, int]]
    ) -> Dict[int, Dict]:
        """
        识别受阻塞影响的车辆
        
        Args:
            routes: 路径列表 (使用数据库ID)
            blocked_edges: 阻塞路段列表 (使用算法索引 - 前端已转换)
            vehicle_positions: 车辆位置 (使用数据库ID)
        
        Returns:
            {vehicle_id: {
                'route': route_dict,
                'current_position_index': int,
                'remaining_path': List[int]
            }}
        """
        affected = {}
        
        # 构建阻塞路段集合(双向,使用算法索引)
        blocked_set = set()
        for edge in blocked_edges:
            # 前端已经将数据库ID转换为算法索引
            from_idx = edge.get('from') or edge.get('from_node')
            to_idx = edge.get('to') or edge.get('to_node')
            blocked_set.add((from_idx, to_idx))
            blocked_set.add((to_idx, from_idx))  # 双向阻塞
        
        logger.info(f"[识别受影响车辆] 阻塞路段集合(算法索引): {blocked_set}")
        
        for route in routes:
            vehicle_id = route['vehicleId']
            path = route['path']  # 数据库ID列表
            depot_id = route['depotId']  # 数据库ID
            
            if not path:
                continue
            
            # 确定车辆当前位置
            if vehicle_positions and vehicle_id in vehicle_positions:
                current_pos = vehicle_positions[vehicle_id]
                try:
                    current_idx = path.index(current_pos)
                except ValueError:
                    # 位置不在路径中,假设在起点
                    current_idx = -1
            else:
                # 随机选择一个位置(简化:选择中间位置)
                current_idx = len(path) // 2 if path else -1
            
            logger.info(f"[识别受影响车辆] 车辆 {vehicle_id} - 路径(数据库ID): {path}, 当前位置索引: {current_idx}")
            
            # 构建完整路径(包括仓库,使用数据库ID)
            full_path_db_ids = [depot_id] + path + [depot_id]
            
            # 将完整路径转换为算法索引
            full_path_indices = []
            for db_id in full_path_db_ids:
                idx = self.id_to_index.get(db_id)
                if idx is not None:
                    full_path_indices.append(idx)
                else:
                    logger.warning(f"[识别受影响车辆] 无法找到数据库ID {db_id} 的索引映射")
            
            logger.info(f"[识别受影响车辆] 车辆 {vehicle_id} - 路径(算法索引): {full_path_indices}")
            
            # 检查剩余路径是否经过阻塞路段
            # 注意：current_idx 是在 path 中的索引，需要映射到 full_path_indices
            # full_path_indices = [depot] + path + [depot]
            # 所以 path[current_idx] 对应 full_path_indices[current_idx + 1]
            start_idx_in_full_path = current_idx + 2  # 从当前位置的下一个节点开始（+1是depot，+1是current_idx）
            is_affected = False
            blocked_edge_found = None
            
            logger.info(f"[识别受影响车辆] 车辆 {vehicle_id} - 检查范围: 从索引 {start_idx_in_full_path} 到 {len(full_path_indices) - 1}")
            
            for i in range(start_idx_in_full_path, len(full_path_indices)):
                if i >= len(full_path_indices):
                    break
                edge = (full_path_indices[i - 1], full_path_indices[i])
                logger.info(f"[识别受影响车辆] 车辆 {vehicle_id} - 检查路段(算法索引): {edge}")
                if edge in blocked_set:
                    is_affected = True
                    blocked_edge_found = edge
                    logger.info(f"[识别受影响车辆] 车辆 {vehicle_id} - 发现阻塞路段(算法索引): {edge}")
                    break
            
            if is_affected:
                # 剩余路径(使用数据库ID)
                remaining_path = path[current_idx + 1:] if current_idx >= 0 else path
                
                logger.info(f"[识别受影响车辆] 车辆 {vehicle_id} - 受影响! 剩余路径(数据库ID): {remaining_path}")
                
                affected[vehicle_id] = {
                    'route': route,
                    'current_position_index': current_idx,
                    'current_position': path[current_idx] if current_idx >= 0 else depot_id,
                    'remaining_path': remaining_path,
                    'depot_id': depot_id
                }
            else:
                logger.info(f"[识别受影响车辆] 车辆 {vehicle_id} - 未受影响")
        
        return affected
    
    def _replan_single_vehicle(
        self,
        route: Dict,
        current_position: Optional[int],
        modified_matrix: np.ndarray,
        algorithm: str
    ) -> Dict:
        """
        为单个车辆重规划剩余路径
        
        使用贪心最近邻算法快速生成绕路方案
        注意：新路径必须确保车辆最终返回仓库
        """
        vehicle_id = route['vehicleId']
        depot_id = route['depotId']
        original_path = route['path']
        
        logger.info(f"[重规划单车] 车辆 {vehicle_id} - 原路径: {original_path}, 当前位置: {current_position}")
        
        if not original_path:
            return route
        
        # 确定当前位置和剩余客户
        if current_position and current_position in original_path:
            current_idx = original_path.index(current_position)
            current_pos = current_position
            remaining_customers = original_path[current_idx + 1:]
        else:
            # 假设在仓库或路径起点
            current_pos = depot_id
            remaining_customers = original_path
        
        logger.info(f"[重规划单车] 车辆 {vehicle_id} - 当前位置: {current_pos}, 剩余客户: {remaining_customers}")
        
        if not remaining_customers:
            # 没有剩余客户,直接返回仓库
            logger.info(f"[重规划单车] 车辆 {vehicle_id} - 无剩余客户，返回空路径")
            return {
                'vehicleId': vehicle_id,
                'depotId': depot_id,
                'path': [],
                'cost': 0.0
            }
        
        # 使用贪心最近邻算法重新排序剩余客户
        new_path = self._greedy_nearest_neighbor(
            current_pos,
            remaining_customers,
            depot_id,
            modified_matrix
        )
        
        logger.info(f"[重规划单车] 车辆 {vehicle_id} - 新路径: {new_path}")
        
        # 计算新路径成本（包括返回仓库）
        new_cost = self._calculate_route_cost(depot_id, new_path, modified_matrix)
        
        logger.info(f"[重规划单车] 车辆 {vehicle_id} - 新成本: {new_cost:.2f}")
        
        return {
            'vehicleId': vehicle_id,
            'depotId': depot_id,
            'path': new_path,  # 路径只包含客户ID，不包含仓库（仓库在计算成本时隐式包含）
            'cost': new_cost
        }
    
    def _greedy_nearest_neighbor(
        self,
        start_pos: int,
        customers: List[int],
        depot_id: int,
        distance_matrix: np.ndarray
    ) -> List[int]:
        """
        贪心最近邻算法 - 从当前位置开始,依次访问最近的未访问客户
        
        Args:
            start_pos: 起始位置的数据库ID
            customers: 客户ID列表 (数据库ID)
            depot_id: 仓库的数据库ID
            distance_matrix: 距离矩阵 (使用索引访问)
        
        Returns:
            重新排序的客户ID列表 (数据库ID)
        """
        if not customers:
            return []
        
        unvisited = set(customers)
        path = []
        current_id = start_pos
        current_idx = self.id_to_index.get(current_id)
        
        if current_idx is None:
            return list(customers)  # 无法找到起始位置,返回原顺序
        
        while unvisited:
            # 找到最近的未访问客户
            min_dist = float('inf')
            nearest_id = None
            
            for customer_id in unvisited:
                customer_idx = self.id_to_index.get(customer_id)
                if customer_idx is None:
                    continue
                
                dist = distance_matrix[current_idx][customer_idx]
                if dist < min_dist:
                    min_dist = dist
                    nearest_id = customer_id
            
            if nearest_id is None:
                # 无法找到有效的最近客户,添加剩余所有客户
                path.extend(list(unvisited))
                break
            
            path.append(nearest_id)
            unvisited.remove(nearest_id)
            current_id = nearest_id
            current_idx = self.id_to_index.get(current_id)
        
        return path
    
    def _modify_distance_matrix(self, blocked_edges: List[Dict]) -> np.ndarray:
        """
        修改距离矩阵,设置阻塞路段为不可通行
        
        注意：blocked_edges 使用算法索引，不是数据库ID
        """
        matrix = self.original_distance_matrix.copy()
        
        for edge in blocked_edges:
            # 这里的 from_node 和 to_node 已经是算法索引了（前端已转换）
            from_idx = edge.get('from') or edge.get('from_node')
            to_idx = edge.get('to') or edge.get('to_node')
            
            if from_idx is None or to_idx is None:
                continue
            
            # 双向阻塞
            matrix[from_idx][to_idx] = self.BLOCKED_DISTANCE
            matrix[to_idx][from_idx] = self.BLOCKED_DISTANCE
        
        return matrix
    
    def _build_distance_matrix(self) -> np.ndarray:
        """构建距离矩阵"""
        # 所有节点 = 仓库 + 客户
        all_nodes = self.depots + self.customers
        n = len(all_nodes)
        
        matrix = np.zeros((n, n))
        
        for i, node1 in enumerate(all_nodes):
            for j, node2 in enumerate(all_nodes):
                if i != j:
                    dist = np.sqrt(
                        (node1['x'] - node2['x']) ** 2 +
                        (node1['y'] - node2['y']) ** 2
                    )
                    matrix[i][j] = dist
        
        return matrix
    
    def _calculate_route_cost(
        self,
        depot_id: int,
        path: List[int],
        distance_matrix: np.ndarray
    ) -> float:
        """
        计算单条路径的成本
        
        路径成本 = 仓库→第一个客户 + 客户间距离 + 最后客户→仓库
        
        Args:
            depot_id: 仓库的数据库ID
            path: 客户ID列表 (数据库ID)
            distance_matrix: 距离矩阵 (使用索引访问)
        """
        if not path:
            return 0.0
        
        cost = 0.0
        
        # 从仓库出发
        current_idx = self.id_to_index.get(depot_id)
        if current_idx is None:
            logger.warning(f"[计算成本] 无法找到仓库ID {depot_id} 的索引")
            return 0.0
        
        # 访问所有客户
        for customer_id in path:
            customer_idx = self.id_to_index.get(customer_id)
            if customer_idx is None:
                logger.warning(f"[计算成本] 无法找到客户ID {customer_id} 的索引")
                continue
            
            cost += distance_matrix[current_idx][customer_idx]
            current_idx = customer_idx
        
        # 返回仓库（关键：确保车辆最终回到仓库）
        depot_idx = self.id_to_index.get(depot_id)
        if depot_idx is not None:
            return_cost = distance_matrix[current_idx][depot_idx]
            cost += return_cost
            logger.debug(f"[计算成本] 返回仓库成本: {return_cost:.2f}, 总成本: {cost:.2f}")
        
        return cost
    
    def _calculate_total_cost(
        self,
        routes: List[Dict],
        distance_matrix: np.ndarray
    ) -> float:
        """计算所有路径的总成本"""
        total = 0.0
        for route in routes:
            depot_id = route['depotId']
            path = route['path']
            total += self._calculate_route_cost(depot_id, path, distance_matrix)
        return total
