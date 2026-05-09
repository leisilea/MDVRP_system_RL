"""
P01单次测试 - ACO和PSO对比
输出：
1. 单次结果
2. 与BKS差距
3. 收敛图像
"""

import sys
import os
from pathlib import Path
import json
import time
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'VPRL'))

from cordeau_parser import load_cordeau_instance
from aco import AntColonySolver
from pso import ParticleSwarmSolver

# BKS数据
BKS = {
    'p01': 576.87
}

# ACO参数
ACO_PARAMS = {
    'antCount': 50,
    'iterations': 150,
    'alpha': 1.0,
    'beta': 5.0,
    'evaporationRate': 0.1,
    'Q': 100
}

# PSO参数（小规模）
PSO_PARAMS = {
    'particleCount': 30,
    'iterations': 150,
    'inertiaWeight': 0.7,
    'cognitiveWeight': 2.0,
    'socialWeight': 2.0
}


def load_instance(instance_name):
    """加载实例"""
    instance_file = f"MDVRP-Instances/dat/{instance_name}"
    instance = load_cordeau_instance(instance_file)
    
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
    
    return depots, customers, instance


def plot_convergence_separate(aco_convergence, pso_convergence, instance_name, bks, output_dir):
    """绘制独立的收敛曲线"""
    
    # ACO收敛曲线
    if aco_convergence:
        plt.figure(figsize=(10, 6))
        aco_generations = [c['generation'] for c in aco_convergence]
        aco_best_costs = [c['best_cost'] for c in aco_convergence]
        plt.plot(aco_generations, aco_best_costs, 'b-', label='ACO Best Cost', linewidth=2)
        plt.axhline(y=bks, color='g', linestyle='--', label=f'BKS={bks:.2f}', linewidth=2)
        
        plt.xlabel('Generation', fontsize=12)
        plt.ylabel('Best Cost', fontsize=12)
        plt.title(f'{instance_name.upper()} - ACO Convergence', fontsize=14, fontweight='bold')
        plt.legend(fontsize=11)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        output_file = output_dir / f'{instance_name}_aco_convergence.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  ACO收敛图像已保存: {output_file}")
    
    # PSO收敛曲线
    if pso_convergence:
        plt.figure(figsize=(10, 6))
        pso_generations = [c['generation'] for c in pso_convergence]
        pso_best_costs = [c['best_cost'] for c in pso_convergence]
        plt.plot(pso_generations, pso_best_costs, 'r-', label='PSO Best Cost', linewidth=2)
        plt.axhline(y=bks, color='g', linestyle='--', label=f'BKS={bks:.2f}', linewidth=2)
        
        plt.xlabel('Generation', fontsize=12)
        plt.ylabel('Best Cost', fontsize=12)
        plt.title(f'{instance_name.upper()} - PSO Convergence', fontsize=14, fontweight='bold')
        plt.legend(fontsize=11)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        output_file = output_dir / f'{instance_name}_pso_convergence.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  PSO收敛图像已保存: {output_file}")


def test_p01():
    """测试P01实例"""
    instance_name = 'p01'
    bks = BKS[instance_name]
    
    print("=" * 80)
    print(f"测试实例: {instance_name.upper()}")
    print(f"BKS: {bks}")
    print("=" * 80)
    
    # 加载实例
    print("\n加载实例...")
    depots, customers, instance = load_instance(instance_name)
    print(f"  客户数: {instance.num_customers}")
    print(f"  仓库数: {instance.num_depots}")
    
    # 创建输出目录
    output_dir = Path("system_test/algorithm-service/solver/aco_pso_p01_test")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results = {}
    
    # ========== 测试ACO ==========
    print("\n" + "=" * 80)
    print("运行ACO")
    print("=" * 80)
    print(f"参数: {ACO_PARAMS}")
    
    aco_start = time.time()
    aco_solver = AntColonySolver(depots, customers, ACO_PARAMS)
    aco_solution = aco_solver.solve()
    aco_time = time.time() - aco_start
    
    aco_cost = aco_solution['totalCost']
    aco_gap = ((aco_cost - bks) / bks) * 100
    aco_convergence = aco_solution.get('convergence', [])
    
    print(f"\nACO结果:")
    print(f"  成本: {aco_cost:.2f}")
    print(f"  Gap: {aco_gap:.2f}%")
    print(f"  时间: {aco_time:.2f}秒")
    print(f"  路径数: {aco_solution['numRoutes']}")
    print(f"  收敛数据点: {len(aco_convergence)}")
    
    results['aco'] = {
        'cost': aco_cost,
        'gap': aco_gap,
        'time': aco_time,
        'num_routes': aco_solution['numRoutes'],
        'convergence': aco_convergence,
        'parameters': ACO_PARAMS
    }
    
    # ========== 测试PSO ==========
    print("\n" + "=" * 80)
    print("运行PSO")
    print("=" * 80)
    print(f"参数: {PSO_PARAMS}")
    
    pso_start = time.time()
    pso_solver = ParticleSwarmSolver(depots, customers, PSO_PARAMS)
    pso_solution = pso_solver.solve()
    pso_time = time.time() - pso_start
    
    pso_cost = pso_solution['totalCost']
    pso_gap = ((pso_cost - bks) / bks) * 100
    pso_convergence = pso_solution.get('convergence', [])
    
    print(f"\nPSO结果:")
    print(f"  成本: {pso_cost:.2f}")
    print(f"  Gap: {pso_gap:.2f}%")
    print(f"  时间: {pso_time:.2f}秒")
    print(f"  路径数: {pso_solution['numRoutes']}")
    print(f"  收敛数据点: {len(pso_convergence)}")
    
    results['pso'] = {
        'cost': pso_cost,
        'gap': pso_gap,
        'time': pso_time,
        'num_routes': pso_solution['numRoutes'],
        'convergence': pso_convergence,
        'parameters': PSO_PARAMS
    }
    
    # ========== 对比分析 ==========
    print("\n" + "=" * 80)
    print("对比分析")
    print("=" * 80)
    
    cost_diff = aco_cost - pso_cost
    gap_diff = aco_gap - pso_gap
    time_diff = aco_time - pso_time
    
    print(f"\n成本对比:")
    print(f"  ACO: {aco_cost:.2f}")
    print(f"  PSO: {pso_cost:.2f}")
    print(f"  差异: {cost_diff:+.2f} ({'ACO更好' if cost_diff > 0 else 'PSO更好'})")
    
    print(f"\nGap对比:")
    print(f"  ACO: {aco_gap:.2f}%")
    print(f"  PSO: {pso_gap:.2f}%")
    print(f"  差异: {gap_diff:+.2f}% ({'ACO更好' if gap_diff > 0 else 'PSO更好'})")
    
    print(f"\n时间对比:")
    print(f"  ACO: {aco_time:.2f}秒")
    print(f"  PSO: {pso_time:.2f}秒")
    print(f"  差异: {time_diff:+.2f}秒 ({'ACO更快' if time_diff < 0 else 'PSO更快'})")
    
    results['comparison'] = {
        'cost_diff': cost_diff,
        'gap_diff': gap_diff,
        'time_diff': time_diff,
        'better_cost': 'ACO' if aco_cost < pso_cost else 'PSO',
        'better_gap': 'ACO' if aco_gap < pso_gap else 'PSO',
        'faster': 'ACO' if aco_time < pso_time else 'PSO'
    }
    
    # ========== 绘制收敛曲线 ==========
    print("\n绘制收敛曲线...")
    plot_convergence_separate(aco_convergence, pso_convergence, instance_name, bks, output_dir)
    
    # ========== 保存结果 ==========
    output_file = output_dir / f'{instance_name}_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'instance': instance_name,
            'bks': bks,
            'num_customers': instance.num_customers,
            'num_depots': instance.num_depots,
            'results': results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n结果已保存: {output_file}")
    
    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    test_p01()
