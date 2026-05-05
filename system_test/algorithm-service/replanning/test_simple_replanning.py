"""
测试简化版重规划服务
"""

import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from replanning.service_simple import SimpleReplanningService
from replanning.models import (
    DepotInput,
    CustomerInput,
    RouteInput,
    BlockedEdgeInput
)


def test_basic_replanning():
    """测试基本重规划功能"""
    print("\n" + "="*60)
    print("测试1: 基本重规划（单车辆，单阻塞路段）")
    print("="*60)
    
    # 创建测试数据
    depots = [
        DepotInput(id=1, x=0, y=0, vehicles=2, capacity=100)
    ]
    
    customers = [
        CustomerInput(id=101, x=10, y=10, demand=10),
        CustomerInput(id=102, x=20, y=10, demand=15),
        CustomerInput(id=103, x=30, y=10, demand=20),
        CustomerInput(id=104, x=40, y=10, demand=10),
    ]
    
    routes = [
        RouteInput(
            vehicleId=1,
            depotId=1,
            path=[101, 102, 103, 104],
            cost=100.0
        )
    ]
    
    # 阻塞路段：102 -> 103
    blocked_edges = [
        BlockedEdgeInput(from_node=102, to_node=103)
    ]
    
    # 车辆位置：车辆1在客户101
    vehicle_positions = {1: 101}
    
    # 执行重规划
    service = SimpleReplanningService()
    
    # 测试GREEDY算法
    print("\n--- 使用GREEDY算法 ---")
    result = service.replan(
        depots=depots,
        customers=customers,
        routes=routes,
        blocked_edges=blocked_edges,
        vehicle_positions=vehicle_positions,
        algorithm='GREEDY'
    )
    
    print(f"\n结果:")
    print(f"  重规划车辆数: {len(result.replanned_route_ids)}")
    print(f"  新路径数: {len(result.new_routes)}")
    print(f"  求解时间: {result.solve_time:.3f}秒")
    for route in result.new_routes:
        print(f"  车辆{route.vehicleId}: {route.path}")
    
    # 测试2-OPT算法
    print("\n--- 使用2-OPT算法 ---")
    result = service.replan(
        depots=depots,
        customers=customers,
        routes=routes,
        blocked_edges=blocked_edges,
        vehicle_positions=vehicle_positions,
        algorithm='2OPT',
        params={'max_iterations': 50}
    )
    
    print(f"\n结果:")
    print(f"  重规划车辆数: {len(result.replanned_route_ids)}")
    print(f"  新路径数: {len(result.new_routes)}")
    print(f"  求解时间: {result.solve_time:.3f}秒")
    for route in result.new_routes:
        print(f"  车辆{route.vehicleId}: {route.path}")


def test_multiple_vehicles():
    """测试多车辆重规划"""
    print("\n" + "="*60)
    print("测试2: 多车辆重规划")
    print("="*60)
    
    depots = [
        DepotInput(id=1, x=0, y=0, vehicles=3, capacity=100)
    ]
    
    customers = [
        CustomerInput(id=101, x=10, y=10, demand=10),
        CustomerInput(id=102, x=20, y=10, demand=15),
        CustomerInput(id=103, x=30, y=10, demand=20),
        CustomerInput(id=104, x=10, y=20, demand=10),
        CustomerInput(id=105, x=20, y=20, demand=15),
        CustomerInput(id=106, x=30, y=20, demand=20),
    ]
    
    routes = [
        RouteInput(vehicleId=1, depotId=1, path=[101, 102, 103], cost=100.0),
        RouteInput(vehicleId=2, depotId=1, path=[104, 105, 106], cost=100.0),
        RouteInput(vehicleId=3, depotId=1, path=[], cost=0.0),  # 空路径
    ]
    
    # 阻塞两条路段
    blocked_edges = [
        BlockedEdgeInput(from_node=102, to_node=103),
        BlockedEdgeInput(from_node=105, to_node=106),
    ]
    
    vehicle_positions = {1: 101, 2: 104}
    
    service = SimpleReplanningService()
    result = service.replan(
        depots=depots,
        customers=customers,
        routes=routes,
        blocked_edges=blocked_edges,
        vehicle_positions=vehicle_positions,
        algorithm='2OPT'
    )
    
    print(f"\n结果:")
    print(f"  受影响车辆: {result.replanned_route_ids}")
    print(f"  求解时间: {result.solve_time:.3f}秒")
    for route in result.new_routes:
        if route.path:
            print(f"  车辆{route.vehicleId}: {route.path}")


def test_no_blockage():
    """测试无阻塞情况"""
    print("\n" + "="*60)
    print("测试3: 无阻塞路段（应该不重规划）")
    print("="*60)
    
    depots = [DepotInput(id=1, x=0, y=0, vehicles=1, capacity=100)]
    customers = [
        CustomerInput(id=101, x=10, y=10, demand=10),
        CustomerInput(id=102, x=20, y=10, demand=15),
    ]
    routes = [RouteInput(vehicleId=1, depotId=1, path=[101, 102], cost=50.0)]
    blocked_edges = []  # 无阻塞
    
    service = SimpleReplanningService()
    result = service.replan(
        depots=depots,
        customers=customers,
        routes=routes,
        blocked_edges=blocked_edges,
        vehicle_positions=None,
        algorithm='GREEDY'
    )
    
    print(f"\n结果:")
    print(f"  受影响车辆数: {len(result.replanned_route_ids)}")
    print(f"  应该为0（无阻塞）")


def test_large_scale():
    """测试大规模重规划"""
    print("\n" + "="*60)
    print("测试4: 大规模重规划（20个客户）")
    print("="*60)
    
    depots = [DepotInput(id=1, x=0, y=0, vehicles=1, capacity=500)]
    
    # 生成20个客户（网格布局）
    customers = []
    for i in range(20):
        x = (i % 5) * 10
        y = (i // 5) * 10
        customers.append(CustomerInput(id=100+i, x=x, y=y, demand=10))
    
    # 原始路径：按顺序访问
    original_path = [100+i for i in range(20)]
    routes = [RouteInput(vehicleId=1, depotId=1, path=original_path, cost=500.0)]
    
    # 阻塞几条路段
    blocked_edges = [
        BlockedEdgeInput(from_node=105, to_node=106),
        BlockedEdgeInput(from_node=110, to_node=111),
        BlockedEdgeInput(from_node=115, to_node=116),
    ]
    
    vehicle_positions = {1: 100}
    
    service = SimpleReplanningService()
    
    # 测试GREEDY
    print("\n--- GREEDY算法 ---")
    result_greedy = service.replan(
        depots=depots,
        customers=customers,
        routes=routes,
        blocked_edges=blocked_edges,
        vehicle_positions=vehicle_positions,
        algorithm='GREEDY'
    )
    print(f"  求解时间: {result_greedy.solve_time:.3f}秒")
    
    # 测试2-OPT
    print("\n--- 2-OPT算法 ---")
    result_2opt = service.replan(
        depots=depots,
        customers=customers,
        routes=routes,
        blocked_edges=blocked_edges,
        vehicle_positions=vehicle_positions,
        algorithm='2OPT',
        params={'max_iterations': 100}
    )
    print(f"  求解时间: {result_2opt.solve_time:.3f}秒")
    
    print(f"\n  GREEDY路径: {result_greedy.new_routes[0].path[:5]}... (前5个)")
    print(f"  2-OPT路径: {result_2opt.new_routes[0].path[:5]}... (前5个)")


if __name__ == '__main__':
    print("\n" + "="*60)
    print("简化版重规划服务测试")
    print("="*60)
    
    try:
        test_basic_replanning()
        test_multiple_vehicles()
        test_no_blockage()
        test_large_scale()
        
        print("\n" + "="*60)
        print("所有测试完成！")
        print("="*60)
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
