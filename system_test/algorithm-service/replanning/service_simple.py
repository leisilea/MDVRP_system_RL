"""
简化版重规划服务

只对受堵塞影响的单个车辆进行局部重规划
"""

import time
import numpy as np
from typing import List, Dict, Optional, Set, Tuple

try:
    from .models import (
        DepotInput,
        CustomerInput,
        RouteInput,
        BlockedEdgeInput,
        RouteOutput,
        ReplanResponse
    )
    from .exceptions import NoFeasibleSolution
except ImportError:
    # 用于直接运行测试
    from models import (
        DepotInput,
        CustomerInput,
        RouteInput,
        BlockedEdgeInput,
        RouteOutput,
        ReplanResponse
    )
    from exceptions import NoFeasibleSolution


class SimpleReplanningService:
    """
    简化版重规划服务
    
    只对受堵塞路段影响的车辆进行局部重规划
    """
    
    def replan(
        self,
        depots: List[DepotInput],
        customers: List[CustomerInput],
        routes: List[RouteInput],
        blocked_edges: List[BlockedEdgeInput],
        vehicle_positions: Optional[Dict[int, int]] = None,
        algorithm: str = 'GREEDY',
        params: Optional[Dict] = None
    ) -> ReplanResponse:
        """
        执行简化版重规划
        
        Args:
            depots: 仓库列表
            customers: 客户列表
            routes: 当前路径列表
            blocked_edges: 阻塞路段列表
            vehicle_positions: 车辆位置映射 {vehicle_id: customer_id}
            algorithm: 算法名称（GREEDY=贪心, 2OPT=贪心+2-opt优化）
            params: 算法参数（可选）
                - max_iterations: 2-opt最大迭代次数（默认100）
        
        Returns:
            重规划响应
        """
        start_time = time.time()
        
        # 解析参数
        if params is None:
            params = {}
        max_iterations = params.get('max_iterations', 100)
        
        # 标准化算法名称
        algorithm = algorithm.upper() if algorithm else 'GREEDY'
        if algorithm not in ['GREEDY', '2OPT']:
            print(f"  警告: 不支持的算法 '{algorithm}'，使用默认算法 'GREEDY'")
            algorithm = 'GREEDY'
        
        print(f"\n{'='*60}")
        print(f"简化版重规划 - 单车辆局部重规划")
        print(f"{'='*60}")
        print(f"仓库数: {len(depots)}")
        print(f"客户数: {len(customers)}")
        print(f"路径数: {len(routes)}")
        print(f"阻塞路段数: {len(blocked_edges)}")
        print(f"算法: {algorithm}")
        if algorithm == '2OPT':
            print(f"2-opt最大迭代次数: {max_iterations}")
        
        # 创建客户映射
        customer_map = {c.id: c for c in customers}
        depot_map = {d.id: d for d in depots}
        
        # 步骤1: 识别受影响的车辆
        print(f"\n[步骤1] 识别受堵塞影响的车辆...")
        affected_routes = self._identify_affected_routes(
            routes, blocked_edges, vehicle_positions
        )
        print(f"  受影响的车辆数: {len(affected_routes)}")
        
        if not affected_routes:
            print(f"  没有车辆受影响，无需重规划")
            return self._create_empty_response(algorithm, time.time() - start_time)
        
        # 步骤2: 对每个受影响的车辆进行局部重规划
        print(f"\n[步骤2] 对受影响车辆进行局部重规划...")
        new_routes = []
        
        for route in routes:
            if route.vehicleId in affected_routes:
                # 重新规划这条路径
                print(f"  重规划车辆 {route.vehicleId}...")
                
                # 获取车辆当前位置
                current_pos = vehicle_positions.get(route.vehicleId) if vehicle_positions else None
                
                # 确定未服务客户
                if current_pos and current_pos in route.path:
                    # 车辆在路径中某个客户位置
                    current_idx = route.path.index(current_pos)
                    unserved = route.path[current_idx + 1:]  # 当前位置之后的客户
                else:
                    # 车辆在仓库或路径起点
                    unserved = route.path
                
                if not unserved:
                    print(f"    车辆 {route.vehicleId} 没有未服务客户")
                    continue
                
                # 使用TSP求解器重新排序未服务客户
                new_path = self._solve_tsp(
                    depot_id=route.depotId,
                    current_position=current_pos,
                    unserved_customers=unserved,
                    blocked_edges=blocked_edges,
                    customer_map=customer_map,
                    depot_map=depot_map,
                    algorithm=algorithm,
                    max_iterations=max_iterations
                )
                
                # 创建新路径
                new_route = RouteOutput(
                    vehicleId=route.vehicleId,
                    depotId=route.depotId,
                    path=new_path,
                    cost=0.0  # 暂不计算成本
                )
                new_routes.append(new_route)
                
                print(f"    原路径: {route.path}")
                print(f"    新路径: {new_path}")
            else:
                # 不受影响的路径保持不变
                new_route = RouteOutput(
                    vehicleId=route.vehicleId,
                    depotId=route.depotId,
                    path=route.path,
                    cost=route.cost
                )
                new_routes.append(new_route)
        
        # 构建响应
        solve_time = time.time() - start_time
        response = ReplanResponse(
            new_routes=new_routes,
            replanned_route_ids=list(affected_routes),
            cost_before=0.0,
            cost_after=0.0,
            cost_difference=0.0,
            cost_change_percent=0.0,
            algorithm=algorithm,
            solve_time=solve_time,
            num_routes=len(new_routes),
            temporary_depots=[],
            vehicle_positions=vehicle_positions
        )
        
        print(f"\n{'='*60}")
        print(f"重规划完成")
        print(f"  重规划车辆数: {len(affected_routes)}")
        print(f"  总耗时: {solve_time:.2f}秒")
        print(f"{'='*60}\n")
        
        return response
    
    def _identify_affected_routes(
        self,
        routes: List[RouteInput],
        blocked_edges: List[BlockedEdgeInput],
        vehicle_positions: Optional[Dict[int, int]]
    ) -> Set[int]:
        """
        识别受堵塞路段影响的车辆
        
        Args:
            routes: 路径列表
            blocked_edges: 阻塞路段列表
            vehicle_positions: 车辆位置
        
        Returns:
            受影响的车辆ID集合
        """
        affected = set()
        
        # 创建阻塞路段集合（双向）
        blocked_set = set()
        for edge in blocked_edges:
            blocked_set.add((edge.from_node, edge.to_node))
            blocked_set.add((edge.to_node, edge.from_node))
        
        for route in routes:
            # 确定车辆当前位置在路径中的索引
            current_pos = vehicle_positions.get(route.vehicleId) if vehicle_positions else None
            
            if current_pos and current_pos in route.path:
                start_idx = route.path.index(current_pos)
            else:
                start_idx = -1  # 从仓库开始
            
            # 构建完整路径（包括仓库）
            if start_idx == -1:
                # 从仓库出发
                full_path = [route.depotId] + route.path + [route.depotId]
                check_from = 0
            else:
                # 从当前位置出发
                remaining_path = route.path[start_idx:]
                full_path = remaining_path + [route.depotId]
                check_from = 0
            
            # 检查路径中是否包含阻塞路段
            for i in range(check_from, len(full_path) - 1):
                edge = (full_path[i], full_path[i + 1])
                if edge in blocked_set:
                    affected.add(route.vehicleId)
                    print(f"  车辆 {route.vehicleId} 受影响: 路段 {edge[0]} -> {edge[1]} 被堵塞")
                    break
        
        return affected
    
    def _greedy_reorder(
        self,
        depot_id: int,
        current_position: Optional[int],
        unserved_customers: List[int],
        blocked_edges: List[BlockedEdgeInput],
        customer_map: Dict[int, CustomerInput],
        depot_map: Dict[int, DepotInput]
    ) -> List[int]:
        """
        使用贪心最近邻算法重新排序未服务客户
        
        Args:
            depot_id: 仓库ID
            current_position: 当前位置（客户ID或None表示在仓库）
            unserved_customers: 未服务客户ID列表
            blocked_edges: 阻塞路段列表
            customer_map: 客户映射
            depot_map: 仓库映射
        
        Returns:
            重新排序后的客户ID列表
        """
        if not unserved_customers:
            return []
        
        # 创建阻塞路段集合
        blocked_set = set()
        for edge in blocked_edges:
            blocked_set.add((edge.from_node, edge.to_node))
            blocked_set.add((edge.to_node, edge.from_node))
        
        # 贪心最近邻算法
        new_path = []
        remaining = set(unserved_customers)
        
        # 起点位置
        if current_position:
            current = current_position
            current_x = customer_map[current].x
            current_y = customer_map[current].y
        else:
            current = depot_id
            current_x = depot_map[depot_id].x
            current_y = depot_map[depot_id].y
        
        while remaining:
            # 找到最近的未服务客户（且不经过阻塞路段）
            best_customer = None
            best_distance = float('inf')
            
            for cust_id in remaining:
                # 检查是否有阻塞路段
                if (current, cust_id) in blocked_set:
                    continue
                
                # 计算距离
                cust = customer_map[cust_id]
                distance = np.sqrt((cust.x - current_x)**2 + (cust.y - current_y)**2)
                
                if distance < best_distance:
                    best_distance = distance
                    best_customer = cust_id
            
            if best_customer is None:
                # 所有剩余客户都被阻塞，选择距离最近的（忽略阻塞）
                for cust_id in remaining:
                    cust = customer_map[cust_id]
                    distance = np.sqrt((cust.x - current_x)**2 + (cust.y - current_y)**2)
                    if distance < best_distance:
                        best_distance = distance
                        best_customer = cust_id
            
            # 添加到路径
            new_path.append(best_customer)
            remaining.remove(best_customer)
            
            # 更新当前位置
            current = best_customer
            current_x = customer_map[current].x
            current_y = customer_map[current].y
        
        return new_path
    
    def _solve_tsp(
        self,
        depot_id: int,
        current_position: Optional[int],
        unserved_customers: List[int],
        blocked_edges: List[BlockedEdgeInput],
        customer_map: Dict[int, CustomerInput],
        depot_map: Dict[int, DepotInput],
        algorithm: str = 'GREEDY',
        max_iterations: int = 100
    ) -> List[int]:
        """
        求解TSP问题：对未服务客户进行最优排序
        
        Args:
            depot_id: 仓库ID
            current_position: 当前位置（客户ID或None表示在仓库）
            unserved_customers: 未服务客户ID列表
            blocked_edges: 阻塞路段列表
            customer_map: 客户映射
            depot_map: 仓库映射
            algorithm: 算法选择（GREEDY或2OPT）
        
        Returns:
            优化后的客户访问顺序
        """
        if not unserved_customers:
            return []
        
        # 如果只有1个客户，直接返回
        if len(unserved_customers) == 1:
            return unserved_customers
        
        # 步骤1: 使用贪心算法生成初始解
        initial_path = self._greedy_reorder(
            depot_id=depot_id,
            current_position=current_position,
            unserved_customers=unserved_customers,
            blocked_edges=blocked_edges,
            customer_map=customer_map,
            depot_map=depot_map
        )
        
        # 如果算法选择是GREEDY或客户数太少，直接返回贪心解
        if algorithm == 'GREEDY' or len(unserved_customers) <= 3:
            return initial_path
        
        # 步骤2: 使用2-opt改进解
        print(f"    使用2-opt优化（客户数: {len(unserved_customers)}）...")
        optimized_path = self._two_opt(
            path=initial_path,
            depot_id=depot_id,
            current_position=current_position,
            blocked_edges=blocked_edges,
            customer_map=customer_map,
            depot_map=depot_map,
            max_iterations=max_iterations
        )
        
        return optimized_path
    
    def _two_opt(
        self,
        path: List[int],
        depot_id: int,
        current_position: Optional[int],
        blocked_edges: List[BlockedEdgeInput],
        customer_map: Dict[int, CustomerInput],
        depot_map: Dict[int, DepotInput],
        max_iterations: int = 100
    ) -> List[int]:
        """
        2-opt局部搜索优化TSP路径
        
        Args:
            path: 初始路径
            depot_id: 仓库ID
            current_position: 当前位置
            blocked_edges: 阻塞路段列表
            customer_map: 客户映射
            depot_map: 仓库映射
            max_iterations: 最大迭代次数
        
        Returns:
            优化后的路径
        """
        if len(path) <= 2:
            return path
        
        # 创建阻塞路段集合
        blocked_set = set()
        for edge in blocked_edges:
            blocked_set.add((edge.from_node, edge.to_node))
            blocked_set.add((edge.to_node, edge.from_node))
        
        # 计算路径总距离
        def calculate_path_cost(p: List[int]) -> float:
            cost = 0.0
            
            # 起点到第一个客户
            if current_position:
                start_x = customer_map[current_position].x
                start_y = customer_map[current_position].y
            else:
                start_x = depot_map[depot_id].x
                start_y = depot_map[depot_id].y
            
            first_cust = customer_map[p[0]]
            cost += np.sqrt((first_cust.x - start_x)**2 + (first_cust.y - start_y)**2)
            
            # 客户之间
            for i in range(len(p) - 1):
                c1 = customer_map[p[i]]
                c2 = customer_map[p[i + 1]]
                cost += np.sqrt((c2.x - c1.x)**2 + (c2.y - c1.y)**2)
            
            # 最后一个客户到仓库
            last_cust = customer_map[p[-1]]
            depot = depot_map[depot_id]
            cost += np.sqrt((depot.x - last_cust.x)**2 + (depot.y - last_cust.y)**2)
            
            return cost
        
        # 检查路径是否包含阻塞路段
        def has_blocked_edge(p: List[int]) -> bool:
            # 检查起点到第一个客户
            start_node = current_position if current_position else depot_id
            if (start_node, p[0]) in blocked_set:
                return True
            
            # 检查客户之间
            for i in range(len(p) - 1):
                if (p[i], p[i + 1]) in blocked_set:
                    return True
            
            # 检查最后一个客户到仓库
            if (p[-1], depot_id) in blocked_set:
                return True
            
            return False
        
        best_path = path[:]
        best_cost = calculate_path_cost(best_path)
        improved = True
        iteration = 0
        
        while improved and iteration < max_iterations:
            improved = False
            iteration += 1
            
            # 尝试所有可能的2-opt交换
            for i in range(len(best_path) - 1):
                for j in range(i + 2, len(best_path)):
                    # 创建新路径：反转i+1到j之间的部分
                    new_path = best_path[:i+1] + best_path[i+1:j+1][::-1] + best_path[j+1:]
                    
                    # 检查新路径是否包含阻塞路段
                    if has_blocked_edge(new_path):
                        continue
                    
                    # 计算新路径成本
                    new_cost = calculate_path_cost(new_path)
                    
                    # 如果更好，更新
                    if new_cost < best_cost:
                        best_path = new_path
                        best_cost = new_cost
                        improved = True
                        break
                
                if improved:
                    break
        
        if iteration > 1:
            print(f"      2-opt完成: {iteration}次迭代, 成本改善: {calculate_path_cost(path):.2f} -> {best_cost:.2f}")
        
        return best_path
    
    def _create_empty_response(
        self,
        algorithm: str,
        solve_time: float
    ) -> ReplanResponse:
        """创建空响应"""
        return ReplanResponse(
            new_routes=[],
            replanned_route_ids=[],
            cost_before=0.0,
            cost_after=0.0,
            cost_difference=0.0,
            cost_change_percent=0.0,
            algorithm=algorithm,
            solve_time=solve_time,
            num_routes=0,
            temporary_depots=[],
            vehicle_positions=None
        )
