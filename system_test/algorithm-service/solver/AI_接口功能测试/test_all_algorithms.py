"""
测试所有5种算法的调用接口
"""
import requests
import json
import time

# API 基础URL
BASE_URL = "http://localhost:5000"

# 测试数据 - 简单的MDVRP实例
test_data = {
    "depots": [
        {"id": 1, "x": 0, "y": 0, "vehicles": 3, "capacity": 100, "maxDistance": 200}
    ],
    "customers": [
        {"id": 1, "x": 10, "y": 20, "demand": 15},
        {"id": 2, "x": 30, "y": 40, "demand": 20},
        {"id": 3, "x": 50, "y": 10, "demand": 25},
        {"id": 4, "x": 20, "y": 50, "demand": 10},
        {"id": 5, "x": 40, "y": 30, "demand": 18}
    ],
    "params": {
        "max_iterations": 100,  # 减少迭代次数以加快测试
        "population_size": 20
    }
}

# 5种算法配置
algorithms = [
    {
        "name": "PSO - 粒子群算法",
        "algorithm": "PSO",
        "params": {
            "max_iterations": 100,
            "num_particles": 20
        }
    },
    {
        "name": "ACO - 蚁群算法",
        "algorithm": "ACO",
        "params": {
            "max_iterations": 100,
            "num_ants": 20
        }
    },
    {
        "name": "GA - 遗传算法(正常初始化)",
        "algorithm": "genetic",
        "params": {
            "max_iterations": 100,
            "population_size": 20
        }
    },
    {
        "name": "GA Hybrid - 遗传算法(混合强化学习初始化)",
        "algorithm": "GA_RL_HYBRID",
        "params": {
            "max_iterations": 100,
            "population_size": 20,
            "num_rl_samples": 10,
            "use_gpu": False  # 测试时使用CPU
        }
    },
    {
        "name": "GA Multiprocessing - 遗传算法(多进程)",
        "algorithm": "ga_multiprogramming",
        "params": {
            "max_iterations": 100,
            "population_size": 20,
            "num_processes": 2
        }
    }
]


def test_health():
    """测试健康检查接口"""
    print("=" * 60)
    print("测试健康检查接口...")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ 健康检查成功")
            print(f"  服务: {data.get('service')}")
            print(f"  版本: {data.get('version')}")
            print(f"  状态: {data.get('status')}")
            return True
        else:
            print(f"✗ 健康检查失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ 健康检查失败: {str(e)}")
        return False


def test_algorithm(algo_config):
    """测试单个算法"""
    print("\n" + "=" * 60)
    print(f"测试算法: {algo_config['name']}")
    print("=" * 60)
    
    # 准备请求数据
    request_data = test_data.copy()
    request_data['params'] = algo_config['params'].copy()
    request_data['params']['algorithm'] = algo_config['algorithm']
    
    print(f"算法ID: {algo_config['algorithm']}")
    print(f"参数: {json.dumps(algo_config['params'], indent=2, ensure_ascii=False)}")
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/api/solve",
            json=request_data,
            timeout=300  # 5分钟超时
        )
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                solution = data.get('data', {})
                print(f"\n✓ 求解成功!")
                print(f"  总成本: {solution.get('totalCost', 0):.2f}")
                print(f"  计算时间: {solution.get('computeTime', 0):.3f}秒")
                print(f"  路径数: {solution.get('numRoutes', 0)}")
                print(f"  实际耗时: {elapsed_time:.3f}秒")
                print(f"  算法: {solution.get('algorithm', 'unknown')}")
                
                # 显示路径信息
                routes = solution.get('routes', [])
                if routes:
                    print(f"\n  路径详情:")
                    for i, route in enumerate(routes[:3]):  # 只显示前3条路径
                        print(f"    路径 {i+1}: 车辆{route.get('vehicleId')} "
                              f"仓库{route.get('depotId')} "
                              f"访问{len(route.get('path', []))}个客户 "
                              f"成本{route.get('cost', 0):.2f}")
                    if len(routes) > 3:
                        print(f"    ... 还有 {len(routes) - 3} 条路径")
                
                return True
            else:
                print(f"\n✗ 求解失败: {data.get('error', 'unknown error')}")
                print(f"  消息: {data.get('message', '')}")
                return False
        else:
            print(f"\n✗ HTTP错误: {response.status_code}")
            try:
                error_data = response.json()
                print(f"  错误: {error_data.get('error', 'unknown')}")
                print(f"  消息: {error_data.get('message', '')}")
            except:
                print(f"  响应: {response.text[:200]}")
            return False
            
    except requests.Timeout:
        print(f"\n✗ 请求超时 (>300秒)")
        return False
    except Exception as e:
        print(f"\n✗ 异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_list_algorithms():
    """测试算法列表接口"""
    print("\n" + "=" * 60)
    print("测试算法列表接口...")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/api/algorithms", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                algorithms = data.get('data', {}).get('algorithms', [])
                print(f"\n✓ 获取算法列表成功，共 {len(algorithms)} 个算法:")
                for algo in algorithms:
                    status_icon = "✓" if algo.get('status') == 'available' else "✗"
                    print(f"  {status_icon} {algo.get('id')}: {algo.get('name')}")
                    if algo.get('aliases'):
                        print(f"     别名: {', '.join(algo.get('aliases'))}")
                return True
            else:
                print(f"✗ 获取失败: {data.get('error')}")
                return False
        else:
            print(f"✗ HTTP错误: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ 异常: {str(e)}")
        return False


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("MDVRP 算法服务 - 完整测试")
    print("=" * 60)
    print(f"API地址: {BASE_URL}")
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        'health': False,
        'list_algorithms': False,
        'algorithms': {}
    }
    
    # 1. 健康检查
    results['health'] = test_health()
    if not results['health']:
        print("\n⚠ 服务未启动或无法访问，请先启动服务:")
        print("  cd system_test/algorithm-service")
        print("  python app.py")
        return
    
    # 2. 算法列表
    results['list_algorithms'] = test_list_algorithms()
    
    # 3. 测试每个算法
    for algo_config in algorithms:
        algo_id = algo_config['algorithm']
        results['algorithms'][algo_id] = test_algorithm(algo_config)
        time.sleep(1)  # 间隔1秒
    
    # 4. 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    print(f"\n健康检查: {'✓ 通过' if results['health'] else '✗ 失败'}")
    print(f"算法列表: {'✓ 通过' if results['list_algorithms'] else '✗ 失败'}")
    
    print(f"\n算法测试结果:")
    success_count = 0
    for algo_config in algorithms:
        algo_id = algo_config['algorithm']
        success = results['algorithms'].get(algo_id, False)
        status = '✓ 通过' if success else '✗ 失败'
        print(f"  {status} - {algo_config['name']}")
        if success:
            success_count += 1
    
    print(f"\n总计: {success_count}/{len(algorithms)} 个算法测试通过")
    
    if success_count == len(algorithms):
        print("\n🎉 所有测试通过！")
    else:
        print(f"\n⚠ {len(algorithms) - success_count} 个算法测试失败")


if __name__ == '__main__':
    main()
