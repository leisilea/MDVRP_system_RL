"""
测试 /api/replan 端点

验证重规划API端点的基本功能。
"""

import requests
import json


def test_replan_api():
    """测试重规划API端点"""
    
    # API端点
    url = "http://localhost:5000/api/replan"
    
    # 构建测试请求
    request_data = {
        "depots": [
            {"id": 0, "x": 0.0, "y": 0.0, "vehicles": 3, "capacity": 100.0},
            {"id": 1, "x": 50.0, "y": 50.0, "vehicles": 2, "capacity": 100.0}
        ],
        "customers": [
            {"id": 0, "x": 10.0, "y": 10.0, "demand": 20.0},
            {"id": 1, "x": 20.0, "y": 20.0, "demand": 30.0},
            {"id": 2, "x": 30.0, "y": 30.0, "demand": 25.0},
            {"id": 3, "x": 40.0, "y": 40.0, "demand": 15.0},
            {"id": 4, "x": 15.0, "y": 25.0, "demand": 20.0},
            {"id": 5, "x": 35.0, "y": 15.0, "demand": 25.0}
        ],
        "routes": [
            {"vehicleId": 1, "depotId": 0, "path": [0, 1, 2], "cost": 150.0},
            {"vehicleId": 2, "depotId": 0, "path": [4, 5], "cost": 120.0},
            {"vehicleId": 3, "depotId": 1, "path": [3], "cost": 80.0}
        ],
        "blocked_edges": [
            {"from": 1, "to": 2}
        ],
        "vehicle_positions": {
            "1": 0,
            "2": 4,
            "3": 3
        },
        "algorithm": "GA",
        "params": {
            "max_iterations": 100
        }
    }
    
    print("="*60)
    print("测试 /api/replan 端点")
    print("="*60)
    print(f"\n请求URL: {url}")
    print(f"请求数据:")
    print(json.dumps(request_data, indent=2, ensure_ascii=False))
    
    try:
        # 发送POST请求
        response = requests.post(url, json=request_data, timeout=60)
        
        print(f"\n响应状态码: {response.status_code}")
        
        # 解析响应
        response_data = response.json()
        print(f"\n响应数据:")
        print(json.dumps(response_data, indent=2, ensure_ascii=False))
        
        # 验证响应
        if response.status_code == 200:
            assert response_data['success'] == True, "响应success字段应为True"
            assert 'data' in response_data, "响应应包含data字段"
            
            data = response_data['data']
            assert 'new_routes' in data, "data应包含new_routes字段"
            assert 'cost_before' in data, "data应包含cost_before字段"
            assert 'cost_after' in data, "data应包含cost_after字段"
            assert 'algorithm' in data, "data应包含algorithm字段"
            assert 'solve_time' in data, "data应包含solve_time字段"
            
            print("\n✓ 测试通过!")
            print(f"  新路径数: {data['num_routes']}")
            print(f"  成本变化: {data['cost_difference']:.2f} ({data['cost_change_percent']:.2f}%)")
            print(f"  求解时间: {data['solve_time']:.2f}秒")
            
            return True
        else:
            print(f"\n✗ 测试失败: HTTP {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("\n✗ 连接失败: 请确保Flask服务正在运行 (python app.py)")
        return False
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_replan_api_validation():
    """测试API参数验证"""
    
    url = "http://localhost:5000/api/replan"
    
    print("\n" + "="*60)
    print("测试 /api/replan 参数验证")
    print("="*60)
    
    # 测试缺少必要字段
    invalid_request = {
        "depots": [],
        "customers": []
        # 缺少 routes 和 blocked_edges
    }
    
    print(f"\n发送无效请求（缺少必要字段）...")
    
    try:
        response = requests.post(url, json=invalid_request, timeout=10)
        
        print(f"响应状态码: {response.status_code}")
        response_data = response.json()
        
        if response.status_code == 400:
            print("✓ 正确返回400错误")
            print(f"  错误信息: {response_data.get('message', 'N/A')}")
            return True
        else:
            print(f"✗ 应返回400错误，实际返回: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("✗ 连接失败: 请确保Flask服务正在运行")
        return False
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False


if __name__ == '__main__':
    print("\n" + "="*60)
    print("API端点测试套件")
    print("="*60)
    print("\n注意: 请先启动Flask服务 (python app.py)")
    print("按Enter继续...")
    input()
    
    # 测试1: 基本功能
    test1_passed = test_replan_api()
    
    # 测试2: 参数验证
    test2_passed = test_replan_api_validation()
    
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    print(f"基本功能测试: {'✓ 通过' if test1_passed else '✗ 失败'}")
    print(f"参数验证测试: {'✓ 通过' if test2_passed else '✗ 失败'}")
    print("="*60)
