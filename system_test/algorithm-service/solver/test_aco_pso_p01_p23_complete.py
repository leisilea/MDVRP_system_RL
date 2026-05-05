"""
P01-P23完整测试 - ACO和PSO对比
- ACO: 自适应参数，每个实例运行3次
- PSO: 小中大配置，每个配置运行3次（共9次）
- 输出: 单次结果、三次平均、Gap、标准差、收敛图像
"""

import sys
import os
from pathlib import Path
import json
import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'VPRL'))

from cordeau_parser import load_cordeau_instance
from aco import AntColonySolver
from pso import ParticleSwarmSolver

# BKS数据
BKS = {
    'p01': 576.87, 'p02': 473.53, 'p03': 640.58, 'p04': 1001.59, 'p05': 750.03,
    'p06': 876.50, 'p07': 881.97, 'p08': 4437.68, 'p09': 3873.89, 'p10': 3663.02,
    'p11': 3554.18, 'p12': 1318.95, 'p13': 1318.95, 'p14': 1360.12, 'p15': 2505.42,
    'p16': 2572.23, 'p17': 2709.09, 'p18': 3702.85, 'p19': 3827.06, 'p20': 4058.07,
    'p21': 5474.84, 'p22': 5702.16, 'p23': 6078.75
}

# 实例规模分类
SCALE_CONFIG = {
    'small': ['p01', 'p02', 'p03', 'p04', 'p05', 'p06', 'p07', 'p12', 'p13', 'p14'],
    'medium': ['p15', 'p16', 'p17'],
    'large': ['p08', 'p09', 'p10', 'p11', 'p18', 'p19', 'p20', 'p21', 'p22', 'p23']
}

# PSO参数配置
PSO_CONFIGS = {
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


def get_aco_params(num_customers):
    """ACO自适应参数"""
    if num_customers <= 100:
        return {
            'antCount': 50,
            'iterations': min(200, max(100, 2 * num_customers)),
            'alpha': 1.0,
            'beta': 5.0,
            'evaporationRate': 0.1,
            'Q': 100
        }
    elif num_customers <= 200:
        return {
            'antCount': 75,
            'iterations': min(300, max(150, 2 * num_customers)),
            'alpha': 1.0,
            'beta': 5.0,
            'evaporationRate': 0.1,
            'Q': 100
        }
    else:
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
    instance_file = f"MDVRP-Instances/dat/{instance_name}"
    instance = load_cordeau_instance(instance_file)
    
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


def plot_convergence_separate(convergence_data, instance_name, bks, algorithm, output_dir):
    """绘制单个算法的收敛曲线（3次运行）"""
    if not convergence_data:
        return
    
    plt.figure(figsize=(10, 6))
    
    colors = ['b-', 'r-', 'g-']
    for run_id, conv in enumerate(convergence_data, 1):
        if conv:
            generations = [c['generation'] for c in conv]
            best_costs = [c['best_cost'] for c in conv]
            plt.plot(generations, best_costs, colors[run_id-1], 
                    label=f'Run {run_id}', linewidth=2, alpha=0.7)
    
    # BKS线
    plt.axhline(y=bks, color='black', linestyle='--', 
                label=f'BKS={bks:.2f}', linewidth=2)
    
    plt.xlabel('Generation', fontsize=12)
    plt.ylabel('Best Cost', fontsize=12)
    plt.title(f'{instance_name.upper()} - {algorithm} Convergence (3 Runs)', 
              fontsize=14, fontweight='bold')
    plt.legend(fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    output_file = output_dir / f'{instance_name}_{algorithm.lower()}_convergence.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()


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
        'aco': {'runs': []},
        'pso': {'small': {'runs': []}, 'medium': {'runs': []}, 'large': {'runs': []}}
    }
    
    # ========== 测试ACO (3次) ==========
    print("\n" + "-" * 80)
    print("运行ACO (3次)")
    print("-" * 80)
    
    aco_params = get_aco_params(instance.num_customers)
    print(f"参数: {aco_params}")
    
    aco_convergence_data = []
    
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
        
        aco_convergence_data.append(convergence)
    
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
        'all_costs': aco_costs,  # 保留所有成本用于后续分析
        'all_gaps': aco_gaps,
        'all_times': aco_times
    }
    
    print(f"\nACO统计:")
    print(f"  平均成本: {results['aco']['statistics']['avg_cost']:.2f} ± {results['aco']['statistics']['std_cost']:.2f}")
    print(f"  方差: {results['aco']['statistics']['var_cost']:.2f}")
    print(f"  成本范围: [{results['aco']['statistics']['min_cost']:.2f}, {results['aco']['statistics']['max_cost']:.2f}]")
    print(f"  平均Gap: {results['aco']['statistics']['avg_gap']:.2f}% ± {results['aco']['statistics']['std_gap']:.2f}%")
    print(f"  平均时间: {results['aco']['statistics']['avg_time']:.2f}秒")
    print(f"  偏差和: {results['aco']['statistics']['deviation_sum']:.2f}")
    
    # 绘制ACO收敛曲线
    plot_convergence_separate(aco_convergence_data, instance_name, bks, 'ACO', output_dir)
    
    # ========== 测试PSO (小中大各3次) ==========
    # 确定实例规模
    instance_scale = None
    for scale, instances in SCALE_CONFIG.items():
        if instance_name in instances:
            instance_scale = scale
            break
    
    for config_name in ['small', 'medium', 'large']:
        print("\n" + "-" * 80)
        print(f"运行PSO - {config_name.upper()}配置 (3次)")
        print("-" * 80)
        
        pso_params = PSO_CONFIGS[config_name]
        print(f"参数: {pso_params}")
        
        pso_convergence_data = []
        
        for run_id in range(1, 4):
            print(f"\n[PSO {config_name.upper()} Run {run_id}/3]")
            start_time = time.time()
            
            pso_solver = ParticleSwarmSolver(depots, customers, pso_params)
            pso_solution = pso_solver.solve()
            
            run_time = time.time() - start_time
            cost = pso_solution['totalCost']
            gap = ((cost - bks) / bks) * 100
            convergence = pso_solution.get('convergence', [])
            
            print(f"  成本: {cost:.2f}, Gap: {gap:.2f}%, 时间: {run_time:.2f}秒")
            
            results['pso'][config_name]['runs'].append({
                'run_id': run_id,
                'cost': cost,
                'gap': gap,
                'time': run_time,
                'num_routes': pso_solution['numRoutes'],
                'convergence': convergence
            })
            
            pso_convergence_data.append(convergence)
        
        # PSO统计
        pso_costs = [r['cost'] for r in results['pso'][config_name]['runs']]
        pso_gaps = [r['gap'] for r in results['pso'][config_name]['runs']]
        pso_times = [r['time'] for r in results['pso'][config_name]['runs']]
        
        results['pso'][config_name]['statistics'] = {
            'avg_cost': float(np.mean(pso_costs)),
            'std_cost': float(np.std(pso_costs)),
            'var_cost': float(np.var(pso_costs)),
            'min_cost': float(np.min(pso_costs)),
            'max_cost': float(np.max(pso_costs)),
            'avg_gap': float(np.mean(pso_gaps)),
            'std_gap': float(np.std(pso_gaps)),
            'var_gap': float(np.var(pso_gaps)),
            'avg_time': float(np.mean(pso_times)),
            'deviation_sum': float(sum(abs(c - np.mean(pso_costs)) for c in pso_costs)),
            'all_costs': pso_costs,  # 保留所有成本用于后续分析
            'all_gaps': pso_gaps,
            'all_times': pso_times
        }
        
        print(f"\nPSO {config_name.upper()}统计:")
        print(f"  平均成本: {results['pso'][config_name]['statistics']['avg_cost']:.2f} ± {results['pso'][config_name]['statistics']['std_cost']:.2f}")
        print(f"  方差: {results['pso'][config_name]['statistics']['var_cost']:.2f}")
        print(f"  成本范围: [{results['pso'][config_name]['statistics']['min_cost']:.2f}, {results['pso'][config_name]['statistics']['max_cost']:.2f}]")
        print(f"  平均Gap: {results['pso'][config_name]['statistics']['avg_gap']:.2f}% ± {results['pso'][config_name]['statistics']['std_gap']:.2f}%")
        print(f"  平均时间: {results['pso'][config_name]['statistics']['avg_time']:.2f}秒")
        print(f"  偏差和: {results['pso'][config_name]['statistics']['deviation_sum']:.2f}")
        
        # 绘制PSO收敛曲线
        plot_convergence_separate(pso_convergence_data, instance_name, bks, 
                                 f'PSO_{config_name.upper()}', output_dir)
    
    # 保存结果
    output_file = output_dir / f'{instance_name}_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n结果已保存: {output_file}")
    
    return results


def main():
    """主函数"""
    print("=" * 80)
    print("P01-P23完整测试 - ACO vs PSO")
    print("=" * 80)
    print("ACO: 自适应参数，每个实例3次")
    print("PSO: 小中大配置，每个配置3次（共9次）")
    print("=" * 80)
    
    # 创建输出目录
    output_base_dir = Path("system_test/algorithm-service/solver/aco_pso_p01_p23_results")
    output_base_dir.mkdir(parents=True, exist_ok=True)
    
    # 测试所有实例
    all_results = {}
    instances = [f'p{i:02d}' for i in range(1, 24)]
    
    total_start = time.time()
    
    for idx, instance_name in enumerate(instances, 1):
        print(f"\n\n{'#' * 80}")
        print(f"进度: {idx}/23 - {instance_name.upper()}")
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
    
    # 保存汇总结果
    summary_file = output_base_dir / 'summary_results.json'
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump({
            'total_time': total_time,
            'results': all_results
        }, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 80)
    print("所有测试完成！")
    print(f"总耗时: {total_time/3600:.2f}小时")
    print(f"结果保存在: {output_base_dir}")
    print("=" * 80)


if __name__ == "__main__":
    main()
