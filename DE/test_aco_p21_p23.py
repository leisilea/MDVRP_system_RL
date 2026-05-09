#!/usr/bin/env python3
"""
运行ACO算法测试 - P21-P23
每个问题运行3次
"""

import sys
import os
from pathlib import Path
import json
import time
import numpy as np

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'VPRL'))

from cordeau_parser import load_cordeau_instance
from aco import AntColonySolver

# BKS数据
BKS = {
    'p21': 5474.84,
    'p22': 5702.16,
    'p23': 6078.75
}


def get_aco_params(num_customers):
    """ACO自适应参数"""
    return {
        'antCount': 100,
        'iterations': min(400, max(200, 2 * num_customers)),
        'alpha': 1.0,
        'beta': 5.0,
        'evaporationRate': 0.1,
        'Q': 100
    }


def load_instance(instance_name):
    """加载实例"""
    # 从项目根目录开始的路径
    project_root = Path(__file__).parent.parent.parent.parent
    instance_file = project_root / "MDVRP-Instances" / "dat" / instance_name
    instance = load_cordeau_instance(str(instance_file))
    
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
    
    return depots, customers, instance


def test_instance(instance_name, output_base_dir):
    """测试单个实例"""
    bks = BKS[instance_name]
    
    print("\n" + "=" * 80)
    print(f"测试实例: {instance_name.upper()}")
    print(f"BKS: {bks}")
    print("=" * 80)
    
    # 加载实例
    depots, customers, instance = load_instance(instance_name)
    print(f"客户数: {instance.num_customers}, 仓库数: {instance.num_depots}")
    
    # 创建输出目录
    output_dir = output_base_dir / instance_name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results = {
        'instance': instance_name,
        'bks': bks,
        'num_customers': instance.num_customers,
        'num_depots': instance.num_depots,
        'aco': {'runs': []}
    }
    
    # ========== 测试ACO (3次) ==========
    print("\n" + "-" * 80)
    print("运行ACO (3次)")
    print("-" * 80)
    
    aco_params = get_aco_params(instance.num_customers)
    print(f"参数: {aco_params}")
    
    for run_id in range(1, 4):
        print(f"\n[ACO Run {run_id}/3]")
        start_time = time.time()
        
        aco_solver = AntColonySolver(depots, customers, aco_params)
        aco_solution = aco_solver.solve()
        
        run_time = time.time() - start_time
        cost = aco_solution['totalCost']
        gap = ((cost - bks) / bks) * 100
        convergence = aco_solution.get('convergence', [])
        
        print(f"  成本: {cost:.2f}, Gap: {gap:.2f}%, 时间: {run_time:.2f}秒")
        
        results['aco']['runs'].append({
            'run_id': run_id,
            'cost': cost,
            'gap': gap,
            'time': run_time,
            'num_routes': aco_solution['numRoutes'],
            'convergence': convergence
        })
    
    # ACO统计
    aco_costs = [r['cost'] for r in results['aco']['runs']]
    aco_gaps = [r['gap'] for r in results['aco']['runs']]
    aco_times = [r['time'] for r in results['aco']['runs']]
    
    results['aco']['statistics'] = {
        'avg_cost': float(np.mean(aco_costs)),
        'std_cost': float(np.std(aco_costs)),
        'var_cost': float(np.var(aco_costs)),
        'min_cost': float(np.min(aco_costs)),
        'max_cost': float(np.max(aco_costs)),
        'avg_gap': float(np.mean(aco_gaps)),
        'std_gap': float(np.std(aco_gaps)),
        'var_gap': float(np.var(aco_gaps)),
        'avg_time': float(np.mean(aco_times)),
        'deviation_sum': float(sum(abs(c - np.mean(aco_costs)) for c in aco_costs)),
        'all_costs': aco_costs,
        'all_gaps': aco_gaps,
        'all_times': aco_times
    }
    
    print(f"\nACO统计:")
    print(f"  平均成本: {results['aco']['statistics']['avg_cost']:.2f} ± {results['aco']['statistics']['std_cost']:.2f}")
    print(f"  方差: {results['aco']['statistics']['var_cost']:.2f}")
    print(f"  成本范围: [{results['aco']['statistics']['min_cost']:.2f}, {results['aco']['statistics']['max_cost']:.2f}]")
    print(f"  平均Gap: {results['aco']['statistics']['avg_gap']:.2f}% ± {results['aco']['statistics']['std_gap']:.2f}%")
    print(f"  平均时间: {results['aco']['statistics']['avg_time']:.2f}秒")
    
    # 保存结果
    output_file = output_dir / f'{instance_name}_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n结果已保存: {output_file}")
    
    return results


def main():
    """运行P21-P23的ACO测试"""
    problems = ['p21', 'p22', 'p23']
    
    print("=" * 80)
    print("开始运行 ACO 算法测试 - P21-P23")
    print("=" * 80)
    print(f"问题列表: {problems}")
    print(f"每个问题运行 3 次")
    print("=" * 80)
    print()
    
    # 创建输出目录
    output_base_dir = Path("system_test/algorithm-service/solver/aco_pso_p01_p23_results")
    output_base_dir.mkdir(parents=True, exist_ok=True)
    
    all_results = {}
    total_start = time.time()
    
    for idx, instance_name in enumerate(problems, 1):
        print(f"\n\n{'#' * 80}")
        print(f"进度: {idx}/3 - {instance_name.upper()}")
        print(f"{'#' * 80}")
        
        try:
            results = test_instance(instance_name, output_base_dir)
            all_results[instance_name] = results
        except Exception as e:
            print(f"\n错误: {instance_name} 测试失败: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    total_time = time.time() - total_start
    
    print()
    print("=" * 80)
    print("P21-P23 ACO测试完成!")
    print(f"总耗时: {total_time/60:.2f}分钟")
    print("=" * 80)


if __name__ == '__main__':
    main()
