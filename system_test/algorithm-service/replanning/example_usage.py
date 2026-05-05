"""
ReplanningService 使用示例

演示如何使用重规划服务进行道路阻塞场景下的路径重规划。
"""

from replanning import (
    ReplanningService,
    DepotInput,
    CustomerInput,
    RouteInput,
    BlockedEdgeInput
)


def example_basic_replanning():
    """基本重规划示例"""
    print("="*60)
    print("示例1: 基本重规划流程")
    print("="*60)
    
    # 创建重规划服务
    service = ReplanningService()
    
    # 定义仓库
    depots = [
        DepotInput(id=0, x=0.0, y=0.0, vehicles=3, capacity=100.0),
        DepotInput(id=1, x=50.0, y=50.0, vehicles=2, capacity=100.0)
    ]
    
    # 定义客户
    customers = [
        CustomerInput(id=0, x=10.0, y=10.0, demand=20.0),
        CustomerInput(id=1, x=20.0, y=20.0, demand=30.0),
        CustomerInput(id=2, x=30.0, y=30.0, demand=25.0),
        CustomerInput(id=3, x=40.0, y=40.0, demand=15.0),
        CustomerInput(id=4, x=15.0, y=25.0, demand=20.0),
        CustomerInput(id=5, x=35.0, y=15.0, demand=25.0),
    ]
    
    # 定义当前路径（车辆正在执行的路径）
    routes = [
        RouteInput(vehicleId=1, depotId=0, path=[0, 1, 2], cost=150.0),
        RouteInput(vehicleId=2, depotId=0, path=[4, 5], cost=120.0),
        RouteInput(vehicleId=3, depotId=1, path=[3], cost=80.0),
    ]
    
    # 定义阻塞路段（客户1到客户2的路段被阻塞）
    blocked_edges = [
        BlockedEdgeInput(from_node=1, to_node=2)
    ]
    
    # 指定车辆当前位置
    # 车辆1在客户0，车辆2在客户4，车辆3在客户3
    vehicle_positions = {
        1: 0,  # 车辆1已经服务了客户0，正在前往客户1
        2: 4,  # 车辆2已经服务了客户4，正在前往客户5
        3: 3   # 车辆3正在服务客户3
    }
    
    try:
        # 执行重规划
        response = service.replan(
            depots=depots,
            customers=customers,
            routes=routes,
            blocked_edges=blocked_edges,
            vehicle_positions=vehicle_positions,
            algorithm='GA'
        )
        
        # 打印结果
        print(f"\n重规划结果:")
        print(f"  算法: {response.algorithm}")
        print(f"  求解时间: {response.solve_time:.2f}秒")
        print(f"  新路径数: {len(response.new_routes)}")
        print(f"  临时仓库数: {len(response.temporary_depots)}")
        print(f"\n成本对比:")
        print(f"  重规划前: {response.cost_before:.2f}")
        print(f"  重规划后: {response.cost_after:.2f}")
        print(f"  差异: {response.cost_difference:.2f} ({response.cost_change_percent:.2f}%)")
        
        print(f"\n新路径详情:")
        for i, route in enumerate(response.new_routes, 1):
            print(f"  路径{i}: 车辆{route.vehicleId} 从仓库{route.depotId} "
                  f"访问客户 {route.path}, 成本: {route.cost:.2f}")
        
        print(f"\n临时仓库详情:")
        for i, td in enumerate(response.temporary_depots, 1):
            print(f"  临时仓库{i}: 车辆{td.vehicle_id} 在客户{td.original_customer_id} "
                  f"位置({td.x:.1f}, {td.y:.1f}), 剩余容量: {td.remaining_capacity:.1f}")
        
        return response
        
    except Exception as e:
        print(f"\n重规划失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def example_multiple_blocked_edges():
    """多个阻塞路段示例"""
    print("\n" + "="*60)
    print("示例2: 多个阻塞路段")
    print("="*60)
    
    service = ReplanningService()
    
    depots = [
        DepotInput(id=0, x=0.0, y=0.0, vehicles=2, capacity=100.0)
    ]
    
    customers = [
        CustomerInput(id=0, x=10.0, y=10.0, demand=20.0),
        CustomerInput(id=1, x=20.0, y=20.0, demand=30.0),
        CustomerInput(id=2, x=30.0, y=30.0, demand=25.0),
        CustomerInput(id=3, x=40.0, y=40.0, demand=15.0),
    ]
    
    routes = [
        RouteInput(vehicleId=1, depotId=0, path=[0, 1, 2, 3], cost=200.0),
    ]
    
    # 多个阻塞路段
    blocked_edges = [
        BlockedEdgeInput(from_node=0, to_node=1),  # 客户0到客户1
        BlockedEdgeInput(from_node=2, to_node=3),  # 客户2到客户3
    ]
    
    vehicle_positions = {1: 0}
    
    try:
        response = service.replan(
            depots=depots,
            customers=customers,
            routes=routes,
            blocked_edges=blocked_edges,
            vehicle_positions=vehicle_positions,
            algorithm='GA'
        )
        
        print(f"\n重规划成功!")
        print(f"  阻塞路段数: {len(blocked_edges)}")
        print(f"  新路径数: {len(response.new_routes)}")
        print(f"  成本变化: {response.cost_difference:.2f} ({response.cost_change_percent:.2f}%)")
        
        return response
        
    except Exception as e:
        print(f"\n重规划失败: {e}")
        return None


def example_no_replanning_needed():
    """无需重规划示例（所有客户已服务）"""
    print("\n" + "="*60)
    print("示例3: 无需重规划（所有客户已服务）")
    print("="*60)
    
    service = ReplanningService()
    
    depots = [
        DepotInput(id=0, x=0.0, y=0.0, vehicles=1, capacity=100.0)
    ]
    
    customers = [
        CustomerInput(id=0, x=10.0, y=10.0, demand=20.0),
        CustomerInput(id=1, x=20.0, y=20.0, demand=30.0),
    ]
    
    routes = [
        RouteInput(vehicleId=1, depotId=0, path=[0, 1], cost=100.0),
    ]
    
    blocked_edges = []
    
    # 车辆已经服务完所有客户，在最后一个客户位置
    vehicle_positions = {1: 1}
    
    try:
        response = service.replan(
            depots=depots,
            customers=customers,
            routes=routes,
            blocked_edges=blocked_edges,
            vehicle_positions=vehicle_positions,
            algorithm='GA'
        )
        
        print(f"\n重规划结果:")
        print(f"  新路径数: {len(response.new_routes)}")
        print(f"  说明: 所有客户已服务，无需重规划")
        
        return response
        
    except Exception as e:
        print(f"\n重规划失败: {e}")
        return None


if __name__ == '__main__':
    print("\n" + "="*60)
    print("ReplanningService 使用示例")
    print("="*60)
    
    # 示例1: 基本重规划
    result1 = example_basic_replanning()
    
    # 示例2: 多个阻塞路段
    result2 = example_multiple_blocked_edges()
    
    # 示例3: 无需重规划
    result3 = example_no_replanning_needed()
    
    print("\n" + "="*60)
    print("所有示例完成!")
    print("="*60)
