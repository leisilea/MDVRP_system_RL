"""
ACO和PSO算法在P01-P23上的完整实验
- ACO: 所有实例运行3次
- PSO: 按规模分档运行3次
"""

import os
import sys
import json
import time
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from multiprocessing import freeze_support

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aco import AntColonySolver
from pso import ParticleSwarmSolver

# 导入Cordeau实例加载器
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'VPRL'))
from cordeau_parser import load_cordeau_instance


# ========================= 配置参数 =========================

# 实例规模分类
SCALE_CONFIG = {
    'small': {
        'instances': ['p01', 'p02', 'p03', 'p04', 'p05', 'p06', 'p07'],
        'pso_params': {
            'particleCount': 100,
            'iterations': 350
        }
    },
    'medium': {
        'instances': ['p08', 'p09', 'p10', 'p11', 'p12', 'p15', 'p18'],
        'pso_params': {
            'particleCount': 150,
            'iterations': 525
        }
    },
    'large': {
        'instances': ['p13', 'p14', 'p16', 'p17', 'p19', 'p20', 'p21', 'p22', 'p23'],
        'pso_params': {
            'particleCount': 175,
            'iterations': 700
        }
    }
}

# ACO固定参数
ACO_PARAMS = {
    'alpha': 1.0,
    'beta': 2.0,
    'rho': 0.15,
    'Q': 100
}

# PSO固定参数
PSO_FIXED_PARAMS = {
    'cognitiveWeight': 2.0,
    'socialWeight': 2.0,
    'inertiaWeight': 0.8  # 初始值，会线性递减到0.4
}

# 实验配置
NUM_RUNS_ACO = 3
NUM_RUNS_PSO = 3

# 数据目录
DATA_DIR = Path(__file__).parent.parent.parent.parent / 'MDVRP-Instances' / 'dat'
RESULTS_DIR = Path(__file__).parent / 'aco_pso_results'
RESULTS_DIR.mkdir(exist_ok=True)


# ========================= 辅助函数 =========================

def get_instance_scale(instance_name):
    """获取实例所属规模"""
    for scale, config in SCALE_CONFIG.items():
        if instance_name in config['instances']:
            return scale
    return None


def calculate_adaptive_aco_params(num_customers):
    """计算ACO自适应参数"""
    num_ants = min(50, max(15, num_customers // 2))
    max_iterations = min(200, max(50, num_customers * 2))
    return num_ants, max_iterations


def load_instance_data(instance_name):
    """加载实例数据"""
    instance_path = DATA_DIR / instance_name
    if not instance_path.exists():
        raise FileNotFoundError(f"实例文件不存在: {instance_path}")
    
    instance = load_cordeau_instance(str(instance_path))
    
    # 转换为solver需要的格式
    depots = []
    for i in range(instance.num_depots):
        depots.append({
            'id': i + 1,
            'x': float(instance.depots_coords[i][0]),
            'y': float(instance.depots_coords[i][1]),
            'vehicles': int(instance.depot_vehicles[i]),
            'capacity': int(instance.depot_capacities[i]),
            'maxDistance': float(instance.max_route_distances[i]) if hasattr(instance, 'max_route_distances') else 0.0
        })
    
    customers = []
    for i in range(instance.num_customers):
        customers.append({
            'id': i + 1,
            'x': float(instance.customers_coords[i][0]),
            'y': float(instance.customers_coords[i][1]),
            'demand': int(instance.demands[i])
        })
    
    return depots, customers, instance.num_customers


def run_aco_single(instance_name, run_id):
    """运行单次ACO实验"""
    print(f"\n{'='*60}")
    print(f"ACO - {instance_name} - Run {run_id + 1}/{NUM_RUNS_ACO}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    # 加载数据
    print(f"[{time.strftime('%H:%M:%S')}] 加载实例数据...")
    depots, customers, num_customers = load_instance_data(instance_name)
    print(f"[{time.strftime('%H:%M:%S')}] 实例加载完成: {num_customers} 个客户, {len(depots)} 个仓库")
    
    # 计算自适应参数
    num_ants, max_iterations = calculate_adaptive_aco_params(num_customers)
    
    # 构建参数
    params = ACO_PARAMS.copy()
    params['num_ants'] = num_ants
    params['max_iterations'] = max_iterations
    
    print(f"[{time.strftime('%H:%M:%S')}] 参数: 蚂蚁数={num_ants}, 迭代数={max_iterations}, α={params['alpha']}, β={params['beta']}, ρ={params['rho']}")
    print(f"[{time.strftime('%H:%M:%S')}] 开始求解...")
    
    # 运行求解
    solver = AntColonySolver(depots, customers, params)
    result = solver.solve()
    
    elapsed_time = time.time() - start_time
    
    print(f"[{time.strftime('%H:%M:%S')}] ✓ 求解完成!")
    print(f"  成本: {result['totalCost']:.2f}")
    print(f"  路径数: {result['numRoutes']}")
    print(f"  耗时: {elapsed_time:.2f}s")
    
    return {
        'instance': instance_name,
        'run_id': run_id,
        'algorithm': 'ACO',
        'params': params,
        'total_cost': result['totalCost'],
        'compute_time': result['computeTime'],
        'num_routes': result['numRoutes'],
        'convergence': result.get('convergence', [])
    }


def run_pso_single(instance_name, run_id, scale):
    """运行单次PSO实验"""
    print(f"\n{'='*60}")
    print(f"PSO - {instance_name} ({scale}) - Run {run_id + 1}/{NUM_RUNS_PSO}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    # 加载数据
    print(f"[{time.strftime('%H:%M:%S')}] 加载实例数据...")
    depots, customers, num_customers = load_instance_data(instance_name)
    print(f"[{time.strftime('%H:%M:%S')}] 实例加载完成: {num_customers} 个客户, {len(depots)} 个仓库")
    
    # 获取规模对应的参数
    pso_params = SCALE_CONFIG[scale]['pso_params'].copy()
    pso_params.update(PSO_FIXED_PARAMS)
    
    print(f"[{time.strftime('%H:%M:%S')}] 参数: 粒子数={pso_params['particleCount']}, 迭代数={pso_params['iterations']}, "
          f"c1={pso_params['cognitiveWeight']}, c2={pso_params['socialWeight']}, w={pso_params['inertiaWeight']}")
    print(f"[{time.strftime('%H:%M:%S')}] 开始求解...")
    
    # 运行求解
    solver = ParticleSwarmSolver(depots, customers, pso_params)
    result = solver.solve()
    
    elapsed_time = time.time() - start_time
    
    print(f"[{time.strftime('%H:%M:%S')}] ✓ 求解完成!")
    print(f"  成本: {result['totalCost']:.2f}")
    print(f"  路径数: {result['numRoutes']}")
    print(f"  耗时: {elapsed_time:.2f}s")
    
    return {
        'instance': instance_name,
        'run_id': run_id,
        'algorithm': 'PSO',
        'scale': scale,
        'params': pso_params,
        'total_cost': result['totalCost'],
        'compute_time': result['computeTime'],
        'num_routes': result['numRoutes'],
        'convergence': result.get('convergence', [])
    }


def calculate_statistics(results):
    """计算统计数据"""
    costs = [r['total_cost'] for r in results]
    times = [r['compute_time'] for r in results]
    
    return {
        'avg_cost': float(np.mean(costs)),
        'std_cost': float(np.std(costs)),
        'min_cost': float(np.min(costs)),
        'max_cost': float(np.max(costs)),
        'avg_time': float(np.mean(times)),
        'std_time': float(np.std(times)),
        'min_time': float(np.min(times)),
        'max_time': float(np.max(times))
    }


def plot_average_convergence(results, instance_name, algorithm):
    """绘制平均收敛曲线"""
    # 收集所有运行的收敛数据
    all_convergence = [r['convergence'] for r in results if r['convergence']]
    
    if not all_convergence:
        print(f"  警告: {instance_name} - {algorithm} 没有收敛数据")
        return
    
    # 找到最短的收敛序列长度
    min_length = min(len(conv) for conv in all_convergence)
    
    if min_length == 0:
        print(f"  警告: {instance_name} - {algorithm} 收敛数据为空")
        return
    
    # 截断所有序列到相同长度
    truncated_convergence = [conv[:min_length] for conv in all_convergence]
    
    # 计算平均值
    generations = [truncated_convergence[0][i]['generation'] for i in range(min_length)]
    avg_best_costs = []
    avg_avg_costs = []
    
    for i in range(min_length):
        best_costs = [conv[i]['best_cost'] for conv in truncated_convergence]
        avg_costs = [conv[i]['avg_cost'] for conv in truncated_convergence]
        avg_best_costs.append(np.mean(best_costs))
        avg_avg_costs.append(np.mean(avg_costs))
    
    # 绘图
    plt.figure(figsize=(10, 6))
    plt.plot(generations, avg_best_costs, 'b-', linewidth=2, label='Average Best Cost')
    plt.plot(generations, avg_avg_costs, 'r--', linewidth=1.5, label='Average Population Cost')
    
    plt.xlabel('Generation', fontsize=12)
    plt.ylabel('Cost', fontsize=12)
    plt.title(f'{algorithm} Convergence - {instance_name} (Average of {len(results)} runs)', fontsize=14)
    plt.legend(fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    # 保存图片
    output_path = RESULTS_DIR / f'{instance_name}_{algorithm}_convergence.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"  收敛图已保存: {output_path}")


# ========================= 主实验流程 =========================

def run_all_experiments():
    """运行所有实验"""
    all_results = {
        'ACO': {},
        'PSO': {}
    }
    
    # 获取所有实例
    all_instances = []
    for scale_config in SCALE_CONFIG.values():
        all_instances.extend(scale_config['instances'])
    
    all_instances.sort()
    
    print(f"\n{'#'*60}")
    print(f"开始实验: {len(all_instances)} 个实例")
    print(f"ACO: 每个实例运行 {NUM_RUNS_ACO} 次")
    print(f"PSO: 按规模分档运行 {NUM_RUNS_PSO} 次")
    print(f"{'#'*60}\n")
    
    # ==================== ACO 实验 ====================
    print(f"\n{'#'*60}")
    print("第一阶段: ACO 实验")
    print(f"{'#'*60}\n")
    
    aco_total = len(all_instances)
    aco_completed = 0
    
    for instance_name in all_instances:
        instance_results = []
        
        print(f"\n[ACO进度: {aco_completed}/{aco_total}] 开始实例 {instance_name}")
        
        for run_id in range(NUM_RUNS_ACO):
            try:
                run_start = time.time()
                print(f"  [Run {run_id+1}/{NUM_RUNS_ACO}] 开始求解...")
                
                result = run_aco_single(instance_name, run_id)
                instance_results.append(result)
                
                run_elapsed = time.time() - run_start
                print(f"  [Run {run_id+1}/{NUM_RUNS_ACO}] ✓ 完成 | Cost={result['total_cost']:.2f} | Time={result['compute_time']:.2f}s | 总耗时={run_elapsed:.2f}s")
            except Exception as e:
                print(f"  [Run {run_id+1}/{NUM_RUNS_ACO}] ✗ 失败: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        if instance_results:
            # 计算统计
            stats = calculate_statistics(instance_results)
            all_results['ACO'][instance_name] = {
                'runs': instance_results,
                'statistics': stats
            }
            
            print(f"\n  [{instance_name}] 统计结果:")
            print(f"    各次成本: {', '.join([f'{r['total_cost']:.2f}' for r in instance_results])}")
            print(f"    平均成本: {stats['avg_cost']:.2f} ± {stats['std_cost']:.2f}")
            print(f"    成本范围: [{stats['min_cost']:.2f}, {stats['max_cost']:.2f}]")
            print(f"    平均时间: {stats['avg_time']:.2f}s ± {stats['std_time']:.2f}s")
            
            # 绘制收敛图
            print(f"  正在生成收敛图...")
            plot_average_convergence(instance_results, instance_name, 'ACO')
        
        aco_completed += 1
        print(f"\n[ACO总进度: {aco_completed}/{aco_total}] 已完成 {instance_name}")
        print(f"{'='*60}")
    
    # ==================== PSO 实验 ====================
    print(f"\n{'#'*60}")
    print("第二阶段: PSO 实验")
    print(f"{'#'*60}\n")
    
    pso_total_instances = sum(len(config['instances']) for config in SCALE_CONFIG.values())
    pso_completed = 0
    
    for scale, config in SCALE_CONFIG.items():
        print(f"\n{'='*60}")
        print(f"处理规模: {scale.upper()}")
        print(f"  实例: {', '.join(config['instances'])}")
        print(f"  参数: 粒子数={config['pso_params']['particleCount']}, 迭代数={config['pso_params']['iterations']}")
        print(f"{'='*60}\n")
        
        for instance_name in config['instances']:
            instance_results = []
            
            print(f"\n[PSO进度: {pso_completed}/{pso_total_instances}] 开始实例 {instance_name} ({scale})")
            
            for run_id in range(NUM_RUNS_PSO):
                try:
                    run_start = time.time()
                    print(f"  [Run {run_id+1}/{NUM_RUNS_PSO}] 开始求解...")
                    
                    result = run_pso_single(instance_name, run_id, scale)
                    instance_results.append(result)
                    
                    run_elapsed = time.time() - run_start
                    print(f"  [Run {run_id+1}/{NUM_RUNS_PSO}] ✓ 完成 | Cost={result['total_cost']:.2f} | Time={result['compute_time']:.2f}s | 总耗时={run_elapsed:.2f}s")
                except Exception as e:
                    print(f"  [Run {run_id+1}/{NUM_RUNS_PSO}] ✗ 失败: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            if instance_results:
                # 计算统计
                stats = calculate_statistics(instance_results)
                all_results['PSO'][instance_name] = {
                    'runs': instance_results,
                    'statistics': stats,
                    'scale': scale
                }
                
                print(f"\n  [{instance_name}] 统计结果:")
                print(f"    各次成本: {', '.join([f'{r['total_cost']:.2f}' for r in instance_results])}")
                print(f"    平均成本: {stats['avg_cost']:.2f} ± {stats['std_cost']:.2f}")
                print(f"    成本范围: [{stats['min_cost']:.2f}, {stats['max_cost']:.2f}]")
                print(f"    平均时间: {stats['avg_time']:.2f}s ± {stats['std_time']:.2f}s")
                
                # 绘制收敛图
                print(f"  正在生成收敛图...")
                plot_average_convergence(instance_results, instance_name, 'PSO')
            
            pso_completed += 1
            print(f"\n[PSO总进度: {pso_completed}/{pso_total_instances}] 已完成 {instance_name}")
            print(f"{'='*60}")
    
    # ==================== 保存结果 ====================
    results_file = RESULTS_DIR / 'all_results.json'
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'#'*60}")
    print(f"实验完成! 结果已保存到: {results_file}")
    print(f"{'#'*60}\n")
    
    # 生成汇总报告
    generate_summary_report(all_results)


def generate_summary_report(all_results):
    """生成汇总报告"""
    report_file = RESULTS_DIR / 'summary_report.md'
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# ACO和PSO算法实验汇总报告\n\n")
        f.write(f"实验时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # ACO结果
        f.write("## ACO算法结果\n\n")
        f.write("| 实例 | Run1 | Run2 | Run3 | 平均成本 | 标准差 | 最小成本 | 最大成本 | 平均时间(s) |\n")
        f.write("|------|------|------|------|----------|--------|----------|----------|-------------|\n")
        
        for instance_name in sorted(all_results['ACO'].keys()):
            stats = all_results['ACO'][instance_name]['statistics']
            runs = all_results['ACO'][instance_name]['runs']
            run_costs = [f"{r['total_cost']:.2f}" for r in runs]
            # 补齐到3次运行
            while len(run_costs) < 3:
                run_costs.append("-")
            
            f.write(f"| {instance_name} | {run_costs[0]} | {run_costs[1]} | {run_costs[2]} | "
                   f"{stats['avg_cost']:.2f} | {stats['std_cost']:.2f} | "
                   f"{stats['min_cost']:.2f} | {stats['max_cost']:.2f} | {stats['avg_time']:.2f} |\n")
        
        # PSO结果
        f.write("\n## PSO算法结果\n\n")
        
        for scale in ['small', 'medium', 'large']:
            f.write(f"\n### {scale.upper()}规模\n\n")
            f.write("| 实例 | Run1 | Run2 | Run3 | 平均成本 | 标准差 | 最小成本 | 最大成本 | 平均时间(s) | 粒子数 | 迭代数 |\n")
            f.write("|------|------|------|------|----------|--------|----------|----------|-------------|--------|--------|\n")
            
            for instance_name in sorted(all_results['PSO'].keys()):
                if all_results['PSO'][instance_name]['scale'] == scale:
                    stats = all_results['PSO'][instance_name]['statistics']
                    runs = all_results['PSO'][instance_name]['runs']
                    params = runs[0]['params']
                    
                    run_costs = [f"{r['total_cost']:.2f}" for r in runs]
                    # 补齐到3次运行
                    while len(run_costs) < 3:
                        run_costs.append("-")
                    
                    f.write(f"| {instance_name} | {run_costs[0]} | {run_costs[1]} | {run_costs[2]} | "
                           f"{stats['avg_cost']:.2f} | {stats['std_cost']:.2f} | "
                           f"{stats['min_cost']:.2f} | {stats['max_cost']:.2f} | {stats['avg_time']:.2f} | "
                           f"{params['particleCount']} | {params['iterations']} |\n")
    
    print(f"汇总报告已保存: {report_file}")



if __name__ == "__main__":
    freeze_support()  # Windows多进程支持
    run_all_experiments()
