"""
直接测试简化版重规划服务（通过Flask API）
"""

import requests
import json

BASE_URL = "http://localhost:5000"


def test_basic_replanning():
    """测试基本重规划功能"""
    print("\n" + "="*60)
    print("测试1: 基本重规划（单车辆，单阻塞路段）")
    print("="*60)
    
    data = {
        "depots": [
            {"id": 1, "x": 0, "y": 0, "vehicles": 2, "capacity": 100}
        ],
        "customers": [
            {"id": 101, "x": 10, "y": 10, "demand": 10},
            {"id": 102, "x": 20, "y": 10, "demand": 15},
            {"id": 103, "x": 30, "y": 10, "demand": 20},
            {"id": 104, "x": 40, "y": 10, "demand": 10},
        ],
        "routes": [
            {
                "vehicleId": 1,
                "depotId": 1,
                "path": [101, 102, 103, 104],
                "cost": 100.0
            }
        ],
        "blocked_edges": [
            {"from": 102, "to": 103}
        ],
        "vehicle_positions": {
            "1": 101
        },
        "algorithm": "GREEDY"
    }
    
    print("\n发送请求...")
    response = requests.post(f"{BASE_URL}/api/replan", json=data)
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n✓ 成功!")
        print(f"  重规划车辆: {result['data']['replanned_route_ids']}")
        print(f"  求解时间: {result['data']['solve_time']:.3f}秒")
        print(f"  新路径:")
        for route in result['data']['new_routes']:
            print(f"    车辆{route['vehicleId']}: {route['path']}")
    else:
        print(f"\n✗ 失败: {response.status_code}")
        print(response.text)


def test_2opt_algorithm():
    """测试2-OPT算法"""
    print("\n" + "="*60)
    print("测试2: 2-OPT算法优化")
    print("="*60)
    
    data = {
        "depots": [
            {"id": 1, "x": 0, "y": 0, "vehicles": 1, "capacity": 500}
        ],
        "customers": [
            {"id": 100+i, "x": (i % 5) * 10, "y": (i // 5) * 10, "demand": 10}
            for i in range(10)
        ],
        "routes": [
            {
                "vehicleId": 1,
                "depotId": 1,
                "path": [100+i for i in range(10)],
                "cost": 500.0
            }
        ],
        "blocked_edges": [
            {"from": 102, "to": 103},
            {"from": 105, "to": 106}
        ],
        "vehicle_positions": {
            "1": 100
        },
        "algorithm": "2OPT",
        "params": {
            "max_iterations": 50
        }
    }
    
    print("\n发送请求...")
    response = requests.post(f"{BASE_URL}/api/replan", json=data)
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n✓ 成功!")
        print(f"  算法: {result['data']['algorithm']}")
        print(f"  求解时间: {result['data']['solve_time']:.3f}秒")
        print(f"  新路径: {result['data']['new_routes'][0]['path']}")
    else:
        print(f"\n✗ 失败: {response.status_code}")
        print(response.text)


def test_multiple_vehicles():
    """测试多车辆重规划"""
    print("\n" + "="*60)
    print("测试3: 多车辆重规划")
    print("="*60)
    
    data = {
        "depots": [
            {"id": 1, "x": 0, "y": 0, "vehicles": 3, "capacity": 100}
        ],
        "customers": [
            {"id": 101, "x": 10, "y": 10, "demand": 10},
            {"id": 102, "x": 20, "y": 10, "demand": 15},
            {"id": 103, "x": 30, "y": 10, "demand": 20},
            {"id": 104, "x": 10, "y": 20, "demand": 10},
            {"id": 105, "x": 20, "y": 20, "demand": 15},
            {"id": 106, "x": 30, "y": 20, "demand": 20},
        ],
        "routes": [
            {"vehicleId": 1, "depotId": 1, "path": [101, 102, 103], "cost": 100.0},
            {"vehicleId": 2, "depotId": 1, "path": [104, 105, 106], "cost": 100.0},
            {"vehicleId": 3, "depotId": 1, "path": [], "cost": 0.0},
        ],
        "blocked_edges": [
            {"from": 102, "to": 103},
            {"from": 105, "to": 106},
        ],
        "vehicle_positions": {
            "1": 101,
            "2": 104
        },
        "algorithm": "2OPT"
    }
    
    print("\n发送请求...")
    response = requests.post(f"{BASE_URL}/api/replan", json=data)
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n✓ 成功!")
        print(f"  受影响车辆: {result['data']['replanned_route_ids']}")
        print(f"  求解时间: {result['data']['solve_time']:.3f}秒")
        print(f"  新路径:")
        for route in result['data']['new_routes']:
            if route['path']:
                print(f"    车辆{route['vehicleId']}: {route['path']}")
    else:
        print(f"\n✗ 失败: {response.status_code}")
        print(response.text)


def test_no_blockage():
    """测试无阻塞情况"""
    print("\n" + "="*60)
    print("测试4: 无阻塞路段（应该不重规划）")
    print("="*60)
    
    data = {
        "depots": [{"id": 1, "x": 0, "y": 0, "vehicles": 1, "capacity": 100}],
        "customers": [
            {"id": 101, "x": 10, "y": 10, "demand": 10},
            {"id": 102, "x": 20, "y": 10, "demand": 15},
        ],
        "routes": [
            {"vehicleId": 1, "depotId": 1, "path": [101, 102], "cost": 50.0}
        ],
        "blocked_edges": [],  # 无阻塞
        "algorithm": "GREEDY"
    }
    
    print("\n发送请求...")
    response = requests.post(f"{BASE_URL}/api/replan", json=data)
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n✓ 成功!")
        print(f"  受影响车辆数: {len(result['data']['replanned_route_ids'])}")
        print(f"  应该为0（无阻塞）")
    else:
        print(f"\n✗ 失败: {response.status_code}")
        print(response.text)


if __name__ == '__main__':
    print("\n" + "="*60)
    print("简化版重规划服务API测试")
    print("="*60)
    print("\n请确保Flask服务正在运行: python app.py")
    print("服务地址: http://localhost:5000")
    
    try:
        # 测试服务是否运行
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        if response.status_code == 200:
            print("✓ 服务正在运行\n")
        else:
            print("✗ 服务响应异常\n")
            exit(1)
    except requests.exceptions.ConnectionError:
        print("✗ 无法连接到服务，请先启动Flask服务\n")
        exit(1)
    
    try:
        test_basic_replanning()
        test_2opt_algorithm()
        test_multiple_vehicles()
        test_no_blockage()
        
        print("\n" + "="*60)
        print("所有测试完成！")
        print("="*60)
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
