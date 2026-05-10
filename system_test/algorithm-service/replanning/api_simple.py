"""
简化版重规划API处理函数
"""

import time
import logging
from typing import Dict
from .simple_replanner import SimpleReplanner

logger = logging.getLogger(__name__)


def handle_simple_replan(data: Dict) -> Dict:
    """
    处理简化版重规划请求
    
    Args:
        data: 请求数据
            - depots: 仓库列表
            - customers: 客户列表
            - routes: 当前路径列表
            - blocked_edges: 阻塞路段列表
            - vehicle_positions: 可选的车辆位置
            - algorithm: 算法名称(目前只用于记录)
    
    Returns:
        重规划结果字典
    """
    start_time = time.time()
    
    # 提取参数
    depots = data['depots']
    customers = data['customers']
    routes = data['routes']
    blocked_edges = data['blocked_edges']
    vehicle_positions = data.get('vehicle_positions')
    algorithm = data.get('algorithm', 'greedy')
    
    logger.info(f"[简化重规划] 仓库: {len(depots)}, 客户: {len(customers)}, "
               f"路径: {len(routes)}, 阻塞路段: {len(blocked_edges)}")
    
    # 创建简化重规划器
    replanner = SimpleReplanner(depots, customers)
    
    # 执行重规划
    result = replanner.replan(
        routes=routes,
        blocked_edges=blocked_edges,
        vehicle_positions=vehicle_positions,
        algorithm=algorithm
    )
    
    total_time = time.time() - start_time
    logger.info(f"[简化重规划] 完成 - 耗时: {total_time:.2f}s, "
               f"受影响车辆: {len(result['replanned_route_ids'])}, "
               f"成本变化: {result['cost_change_percent']:.2f}%")
    
    return result


def validate_replan_request(data: Dict) -> None:
    """
    验证重规划请求数据
    
    Raises:
        ValueError: 如果数据格式不正确
    """
    required_fields = ['depots', 'customers', 'routes', 'blocked_edges']
    
    for field in required_fields:
        if field not in data:
            raise ValueError(f"缺少必需字段: {field}")
    
    # 验证depots
    if not isinstance(data['depots'], list):
        raise ValueError("depots必须是列表")
    
    for depot in data['depots']:
        required_depot_fields = ['id', 'x', 'y', 'vehicles', 'capacity']
        for field in required_depot_fields:
            if field not in depot:
                raise ValueError(f"仓库缺少必需字段: {field}")
    
    # 验证customers
    if not isinstance(data['customers'], list):
        raise ValueError("customers必须是列表")
    
    for customer in data['customers']:
        required_customer_fields = ['id', 'x', 'y', 'demand']
        for field in required_customer_fields:
            if field not in customer:
                raise ValueError(f"客户缺少必需字段: {field}")
    
    # 验证routes
    if not isinstance(data['routes'], list):
        raise ValueError("routes必须是列表")
    
    for route in data['routes']:
        required_route_fields = ['vehicleId', 'depotId', 'path']
        for field in required_route_fields:
            if field not in route:
                raise ValueError(f"路径缺少必需字段: {field}")
    
    # 验证blocked_edges
    if not isinstance(data['blocked_edges'], list):
        raise ValueError("blocked_edges必须是列表")
    
    for edge in data['blocked_edges']:
        # 支持 from/to 或 from_node/to_node
        has_from = 'from' in edge or 'from_node' in edge
        has_to = 'to' in edge or 'to_node' in edge
        
        if not (has_from and has_to):
            raise ValueError("阻塞路段必须包含 from/to 或 from_node/to_node 字段")
    
    logger.info("[简化重规划] 请求验证通过")
