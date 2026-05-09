"""
PSO P08 完整验证测试
确保所有客户都被服务且满足所有约束
"""

import sys
import os
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入Cordeau实例加载器
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'VPRL'))
from cordeau_parser import load_cordeau_instance

from pso import ParticleSwarmSolver
import json
import time
from datetime import datetime

def validate_solution(solution, instance):
    """
    完整验证解的正确性
    
    检查:
    1. 所有客户都被服务
    2. 每个客户只被服务一次
    3. 容量约束
    4. 路径长度约束
    5. 成本计算正确性
    """
    errors = []
    warnings = []
    
    # 获取所有被服务的客户
    served_customers = set()
    for route in solution['routes']:
        for customer_id in route['path']:
            if customer_id in served_customers:
                errors.append(f"客户 {customer_id} 被服务了多次")
            served_customers.add(customer_id)
    
    # 检查是否所有客户都被服务
    all_customers = set(range(1, instance.num_customers + 1))
    missing_customers = all_customers - served_customers
    extra_customers = served_customers - all_customers
    
    if missing_customers:
        errors.append(f"缺少客户: {sorted(missing_customers)}")
    
    if extra_customers:
        errors.append(f"多余客户: {sorted(extra_customers)}")
    
    # 检查每条路径的约束
    total_cost_calculated = 0.0
    
    for route_idx, route in enumerate(solution['routes']):
        vehicle_id = route['vehicleId']
        depot_id = route['depotId']
        path = route['path']
        reported_cost = route['cost']
        
        # 找到对应的仓库索引
        depot_idx = depot_id - 1
        
        # 检查容量约束
        total_demand = sum(instance.demands[cid - 1] for cid in path)
        capacity = instance.depot_capacities[depot_idx]
        
        if total_demand > capacity:
            errors.append(
                f"路径 {vehicle_id} (仓库{depot_id}): "
                f"需求 {total_demand} > 容量 {capacity}"
            )
        
        # 计算实际路径成本
        actual_cost = 0.0
        
        # 仓库到第一个客户
        if path:
            first_customer_idx = path[0] + instance.num_depots - 1
            actual_cost += instance.distance_matrix[depot_idx, first_customer_idx]
            
            # 客户之间
            for i in range(len(path) - 1):
                from_idx = path[i] + instance.num_depots - 1
                to_idx = path[i + 1] + instance.num_depots - 1
                actual_cost += instance.distance_matrix[from_idx, to_idx]
            
            # 最后一个客户回仓库
            last_customer_idx = path[-1] + instance.num_depots - 1
            actual_cost += instance.distance_matrix[last_customer_idx, depot_idx]
        
        # 检查成本计算
        cost_diff = abs(actual_cost - reported_cost)
        if cost_diff > 0.01:
            warnings.append(
                f"路径 {vehicle_id}: 报告成本 {reported_cost:.2f} "
                f"!= 实际成本 {actual_cost:.2f} (差异: {cost_diff:.2f})"
            )
        
        total_cost_calculated += actual_cost
        
        # 检查路径长度约束
        max_distance = instance.max_route_distances[depot_idx]
        if max_distance > 0 and actual_cost > max_distance:
            errors.append(
                f"路径 {vehicle_id} (仓库{depot_id}): "
                f"距离 {actual_cost:.2f} > 最大距离 {max_distance:.2f}"
            )
    
    # 检查总成本
    total_cost_diff = abs(total_cost_calculated - solution['totalCost'])
    if total_cost_diff > 0.01:
        warnings.append(
            f"总成本: 报告 {solution['totalCost']:.2f} "
            f"!= 计算 {total_cost_calculated:.2f} (差异: {total_cost_diff:.2f})"
        )
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'served_customers': len(served_customers),
        'total_customers': instance.num_customers,
        'calculated_cost': total_cost_calculated
    }


def test_pso_p08():
    """测试PSO在P08上的表现，包含完整验证"""
    
    print("=" * 80)
    print("PSO P08 完整验证测试")
    print("=" * 80)
    
    # 加载P08实例
    print("\n加载P08实例...")
    instance_file = "MDVRP-Instances/dat/p08"
    instance = load_cordeau_instance(instance_file)
    
    print(f"  客户数: {instance.num_customers}")
    print(f"  仓库数: {instance.num_depots}")
    print(f"  车辆容量: {instance.depot_capacities}")
    print(f"  最大路径长度: {instance.max_route_distances}")
    print(f"  BKS: 4420.9451")
    
    # 准备数据
    depots = []
    for i in range(instance.num_depots):
        depots.append({
            'id': i + 1,
            'x': float(instance.depots_coords[i][0]),
            'y': float(instance.depots_coords[i][1]),
            'vehicles': int(instance.depot_vehicles[i]),
            'capacity': int(instance.depot_capacities[i]),
            'maxDistance': float(instance.max_route_distances[i])
        })
    
    customers = []
    for i in range(instance.num_customers):
        customers.append({
            'id': i + 1,
            'x': float(instance.customers_coords[i][0]),
            'y': float(instance.customers_coords[i][1]),
            'demand': int(instance.demands[i])
        })
    
    # 测试配置
    configs = {
        'small': {
            'particleCount': 100,
            'iterations': 350,
            'inertiaWeight': 0.8,
            'cognitiveWeight': 2.0,
            'socialWeight': 2.0
        },
        'medium': {
            'particleCount': 150,
            'iterations': 525,
            'inertiaWeight': 0.8,
            'cognitiveWeight': 2.0,
            'socialWeight': 2.0
        },
        'large': {
            'particleCount': 175,
            'iterations': 700,
            'inertiaWeight': 0.8,
            'cognitiveWeight': 2.0,
            'socialWeight': 2.0
        }
    }
    
    results = {}
    
    # 运行每个配置
    for config_name, params in configs.items():
        print(f"\n{'=' * 80}")
        print(f"配置: {config_name.upper()}")
        print(f"{'=' * 80}")
        print(f"  粒子数: {params['particleCount']}")
        print(f"  迭代数: {params['iterations']}")
        
        config_results = []
        
        # 运行3次
        for run_id in range(1, 4):
            print(f"\n--- 运行 {run_id}/3 ---")
            
            start_time = time.time()
            
            # 创建求解器
            solver = ParticleSwarmSolver(depots, customers, params)
            
            # 求解
            solution = solver.solve()
            
            compute_time = time.time() - start_time
            
            # 验证解
            print(f"\n验证解的正确性...")
            validation = validate_solution(solution, instance)
            
            print(f"  总成本: {solution['totalCost']:.2f}")
            print(f"  路径数: {solution['numRoutes']}")
            print(f"  计算时间: {compute_time:.2f}秒")
            print(f"  服务客户数: {validation['served_customers']}/{validation['total_customers']}")
            
            if validation['valid']:
                print(f"  ✓ 解有效")
            else:
                print(f"  ✗ 解无效")
                for error in validation['errors']:
                    print(f"    错误: {error}")
            
            if validation['warnings']:
                print(f"  警告:")
                for warning in validation['warnings']:
                    print(f"    {warning}")
            
            # 计算Gap
            bks = 4420.9451
            gap = ((solution['totalCost'] - bks) / bks) * 100
            
            print(f"  Gap: {gap:.2f}%")
            
            # 保存结果
            run_result = {
                'run_id': run_id,
                'config': config_name,
                'total_cost': solution['totalCost'],
                'calculated_cost': validation['calculated_cost'],
                'bks': bks,
                'gap': gap,
                'compute_time': compute_time,
                'num_routes': solution['numRoutes'],
                'valid': validation['valid'],
                'served_customers': validation['served_customers'],
                'total_customers': validation['total_customers'],
                'errors': validation['errors'],
                'warnings': validation['warnings'],
                'convergence': solution.get('convergence', []),
                'parameters': params
            }
            
            config_results.append(run_result)
        
        results[config_name] = config_results
        
        # 统计该配置的结果
        print(f"\n{config_name.upper()} 配置统计:")
        costs = [r['total_cost'] for r in config_results]
        gaps = [r['gap'] for r in config_results]
        times = [r['compute_time'] for r in config_results]
        valid_count = sum(1 for r in config_results if r['valid'])
        
        print(f"  平均成本: {sum(costs)/len(costs):.2f}")
        print(f"  最佳成本: {min(costs):.2f}")
        print(f"  最差成本: {max(costs):.2f}")
        print(f"  平均Gap: {sum(gaps)/len(gaps):.2f}%")
        print(f"  平均时间: {sum(times)/len(times):.2f}秒")
        print(f"  有效解: {valid_count}/3")
    
    # 保存结果
    output_file = "system_test/algorithm-service/solver/p08_pso_validation_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'problem': 'p08',
            'num_customers': instance.num_customers,
            'num_depots': instance.num_depots,
            'bks': 4420.9451,
            'test_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'results': results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'=' * 80}")
    print(f"测试完成！结果已保存到: {output_file}")
    print(f"{'=' * 80}")
    
    # 总结
    print(f"\n总结:")
    for config_name in ['small', 'medium', 'large']:
        config_results = results[config_name]
        costs = [r['total_cost'] for r in config_results]
        valid_count = sum(1 for r in config_results if r['valid'])
        print(f"  {config_name}: 平均成本={sum(costs)/len(costs):.2f}, 有效解={valid_count}/3")


if __name__ == "__main__":
    test_pso_p08()
