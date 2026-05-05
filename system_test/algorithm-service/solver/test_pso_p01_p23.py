"""
PSO P01-P23完整测试：三档参数配置
每个问题 × 3档参数 × 3次运行 = 9次运行

参数配置:
- Small:  particle_count=100, iterations=350, c1=2.0, c2=2.0
- Medium: particle_count=150, iterations=525, c1=2.0, c2=2.0
- Large:  particle_count=175, iterations=700, c1=2.0, c2=2.0
"""
import os
import sys
import json
import time
import argparse
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import numpy as np

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

from pso import ParticleSwarmSolver


# ========================= Cordeau格式加载 (参考test_p01_p23_complete.py) =========================

def read_cordeau_file(filepath: str) -> Dict:
    """读取Cordeau格式的MDVRP数据文件"""
    with open(filepath, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]
    
    # 第一行
    parts = lines[0].split()
    if len(parts) == 4:
        _, n_vehicles, n_customers, n_depots = map(int, parts)
    else:
        n_vehicles, n_customers, n_depots = map(int, parts)
    
    # Depot信息
    depots_info = []
    for i in range(1, n_depots + 1):
        parts = lines[i].split()
        max_dist = int(parts[0])
        capacity = int(parts[1])
        depots_info.append({'max_distance': max_dist, 'capacity': capacity})
    
    # 客户信息
    customers = []
    for i in range(n_depots + 1, n_depots + 1 + n_customers):
        parts = lines[i].split()
        customers.append({
            'id': i - n_depots,
            'x': float(parts[1]),
            'y': float(parts[2]),
            'demand': float(parts[4])
        })
    
    # Depot坐标
    depots = []
    for i in range(n_depots + 1 + n_customers, n_depots + 1 + n_customers + n_depots):
        parts = lines[i].split()
        depot_idx = i - (n_depots + 1 + n_customers)
        depots.append({
            'id': depot_idx + 1,
            'x': float(parts[1]),
            'y': float(parts[2]),
            'vehicles': n_vehicles,
            'capacity': depots_info[depot_idx]['capacity'],
            'maxDistance': depots_info[depot_idx]['max_distance'],
            'max_distance': depots_info[depot_idx]['max_distance']
        })
    
    return {
        'depots': depots,
        'customers': customers
    }


def load_bks(filepath: str) -> float:
    """从.res文件读取BKS值(第一行)"""
    try:
        with open(filepath, 'r') as f:
            return float(f.readline().strip())
    except:
        return 0.0


def validate_solution(result: Dict, instance_data: Dict) -> tuple:
    """验证解的可行性"""
    try:
        routes = result.get('routes', [])
        if not routes:
            return False, "没有路径"
        
        depots = {d['id']: d for d in instance_data['depots']}
        customers_dict = {c['id']: c for c in instance_data['customers']}
        
        # 检查每条路径
        for route_info in routes:
            path = route_info.get('path', [])
            depot_id = route_info.get('depotId', 1)
            
            if not path:
                continue
            
            depot = depots.get(depot_id)
            if not depot:
                return False, f"未知仓库ID: {depot_id}"
            
            # 检查容量约束
            total_demand = sum(customers_dict[c]['demand'] for c in path if c in customers_dict)
            if total_demand > depot['capacity']:
                return False, f"路径{route_info.get('vehicleId')}超出容量: {total_demand} > {depot['capacity']}"
            
            # 检查路径长度约束
            max_dist = depot.get('maxDistance', 0)
            if max_dist > 0:
                route_dist = route_info.get('cost', 0)
                if route_dist > max_dist * 1.01:  # 允许1%误差
                    return False, f"路径{route_info.get('vehicleId')}超出最大距离: {route_dist:.2f} > {max_dist:.2f}"
        
        return True, None
    except Exception as e:
        return False, str(e)


# ========================= 参数配置 =========================

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


# ========================= 测试函数 =========================

def run_pso_single(
    problem_name: str,
    instance_data: Dict,
    bks: float,
    config_name: str,
    config: Dict,
    run_id: int
) -> Dict:
    """运行PSO单次"""
    print(f"\n{'='*70}")
    print(f"{problem_name.upper()} - PSO-{config_name.upper()} - 运行 #{run_id+1}/3")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"参数: particles={config['particleCount']}, iterations={config['iterations']}, "
          f"c1={config['cognitiveWeight']}, c2={config['socialWeight']}")
    print(f"BKS: {bks:.2f}")
    print(f"{'='*70}")
    
    start_time = time.time()
    
    try:
        # 创建PSO求解器
        solver = ParticleSwarmSolver(
            depots=instance_data['depots'],
            customers=instance_data['customers'],
            params=config
        )
        
        # 求解
        result = solver.solve()
        
        compute_time = time.time() - start_time
        total_cost = result['totalCost']
        
        # 验证解
        valid, errors = validate_solution(result, instance_data)
        
        # 计算gap
        gap = (total_cost - bks) / bks * 100 if bks > 0 else 0
        
        print(f"\n结果:")
        print(f"  总成本: {total_cost:.2f}")
        print(f"  BKS: {bks:.2f}")
        print(f"  Gap: {gap:.2f}%")
        print(f"  计算时间: {compute_time:.2f}秒 ({compute_time/60:.2f}分钟)")
        print(f"  路径数: {len(result['routes'])}")
        print(f"  验证: {'通过' if valid else f'失败 - {errors}'}")
        print(f"  结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return {
            'run_id': run_id + 1,
            'config': config_name,
            'total_cost': total_cost,
            'bks': bks,
            'gap': gap,
            'compute_time': compute_time,
            'num_routes': len(result['routes']),
            'valid': valid,
            'errors': errors if not valid else None,
            'convergence': result.get('convergence', []),
            'start_time': datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S'),
            'end_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'parameters': config
        }
        
    except Exception as e:
        compute_time = time.time() - start_time
        print(f"\n[ERROR] 运行失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            'run_id': run_id + 1,
            'config': config_name,
            'total_cost': float('inf'),
            'bks': bks,
            'gap': float('inf'),
            'compute_time': compute_time,
            'num_routes': 0,
            'valid': False,
            'error': str(e),
            'parameters': config
        }


def test_single_problem(
    problem_name: str,
    data_dir: Path,
    sol_dir: Path,
    output_dir: Path,
    configs_to_test: List[str]
):
    """测试单个问题"""
    print(f"\n{'#'*70}")
    print(f"# 开始测试: {problem_name.upper()}")
    print(f"{'#'*70}")
    
    # 读取问题数据
    problem_file = data_dir / problem_name
    sol_file = sol_dir / f"{problem_name}.res"
    
    if not problem_file.exists():
        print(f"[ERROR] 问题文件不存在: {problem_file}")
        return None
    
    print(f"\n读取{problem_name.upper()}数据: {problem_file}")
    instance_data = read_cordeau_file(str(problem_file))
    
    # 读取BKS
    bks = 0.0
    if sol_file.exists():
        bks = load_bks(str(sol_file))
        print(f"BKS: {bks:.2f}")
    else:
        print(f"[WARNING] BKS文件不存在: {sol_file}")
    
    print(f"  客户数: {len(instance_data['customers'])}")
    print(f"  仓库数: {len(instance_data['depots'])}")
    
    results = {
        'problem': problem_name,
        'num_customers': len(instance_data['customers']),
        'num_depots': len(instance_data['depots']),
        'bks': bks,
        'test_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'runs': {}
    }
    
    # 对每个配置运行3次
    for config_name in configs_to_test:
        if config_name not in PSO_CONFIGS:
            print(f"[WARNING] 未知配置: {config_name}")
            continue
        
        config = PSO_CONFIGS[config_name]
        results['runs'][config_name] = []
        
        print(f"\n{'='*70}")
        print(f"配置: {config_name.upper()}")
        print(f"{'='*70}")
        
        for run_id in range(3):
            result = run_pso_single(
                problem_name,
                instance_data,
                bks,
                config_name,
                config,
                run_id
            )
            results['runs'][config_name].append(result)
            
            # 每次运行后保存
            save_results(output_dir, results)
    
    # 计算统计数据
    compute_statistics(results)
    
    # 保存最终结果
    save_results(output_dir, results)
    
    print(f"\n{'#'*70}")
    print(f"# {problem_name.upper()} 测试完成")
    print(f"{'#'*70}\n")
    
    return results


def compute_statistics(results: Dict):
    """计算统计数据"""
    results['statistics'] = {}
    bks = results['bks']
    
    for config_name, runs in results['runs'].items():
        times = [r['compute_time'] for r in runs if 'error' not in r]
        costs = [r['total_cost'] for r in runs if 'error' not in r and r['total_cost'] < float('inf')]
        gaps = [r['gap'] for r in runs if 'error' not in r and r['gap'] < float('inf')]
        valid_runs = [r for r in runs if r.get('valid', False)]
        
        results['statistics'][config_name] = {
            'times': times,
            'costs': costs,
            'gaps': gaps,
            'avg_time': float(np.mean(times)) if times else 0,
            'std_time': float(np.std(times)) if times else 0,
            'min_time': float(np.min(times)) if times else 0,
            'max_time': float(np.max(times)) if times else 0,
            'avg_cost': float(np.mean(costs)) if costs else 0,
            'std_cost': float(np.std(costs)) if costs else 0,
            'min_cost': float(np.min(costs)) if costs else 0,
            'max_cost': float(np.max(costs)) if costs else 0,
            'avg_gap': float(np.mean(gaps)) if gaps else 0,
            'std_gap': float(np.std(gaps)) if gaps else 0,
            'min_gap': float(np.min(gaps)) if gaps else 0,
            'max_gap': float(np.max(gaps)) if gaps else 0,
            'num_valid_runs': len(valid_runs),
            'num_total_runs': len(runs)
        }
    
    # 打印统计
    print(f"\n{'='*70}")
    print(f"{results['problem'].upper()} - 统计结果 (BKS={bks:.2f})")
    print(f"{'='*70}")
    
    for config_name in results['runs'].keys():
        stats = results['statistics'].get(config_name, {})
        if stats.get('num_valid_runs', 0) > 0:
            print(f"\n{config_name.upper()} 统计 ({stats['num_valid_runs']}/{stats['num_total_runs']}次有效运行):")
            print(f"  平均时间: {stats['avg_time']:.2f}秒 ({stats['avg_time']/60:.2f}分钟)")
            print(f"  时间范围: {stats['min_time']:.2f}s - {stats['max_time']:.2f}s")
            print(f"  平均成本: {stats['avg_cost']:.2f}")
            print(f"  成本范围: {stats['min_cost']:.2f} - {stats['max_cost']:.2f}")
            print(f"  平均Gap: {stats['avg_gap']:.2f}%")
            print(f"  Gap范围: {stats['min_gap']:.2f}% - {stats['max_gap']:.2f}%")


def save_results(output_dir: Path, results: Dict):
    """保存结果到JSON文件"""
    problem_name = results['problem']
    output_file = output_dir / f"{problem_name}_pso_results.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def load_progress(output_dir: Path, configs_to_test: List[str]) -> Dict:
    """加载已完成的测试进度"""
    progress = {}
    
    if not output_dir.exists():
        return progress
    
    for json_file in output_dir.glob("p*_pso_results.json"):
        problem_name = json_file.stem.replace('_pso_results', '')
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 检查是否所有配置都完成了3次运行
                all_complete = True
                for config_name in configs_to_test:
                    if config_name not in data.get('runs', {}):
                        all_complete = False
                        break
                    if len(data['runs'][config_name]) < 3:
                        all_complete = False
                        break
                
                if all_complete:
                    progress[problem_name] = True
                    print(f"[INFO] 发现已完成的测试: {problem_name}")
        except:
            pass
    
    return progress


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='PSO P01-P23完整测试')
    parser.add_argument('--problems', nargs='+', help='指定要测试的问题，例如: p01 p08 p21')
    parser.add_argument('--configs', nargs='+', choices=['small', 'medium', 'large'],
                       default=['small', 'medium', 'large'],
                       help='指定要测试的参数配置')
    parser.add_argument('--start-from', help='从指定问题开始测试，例如: p08')
    parser.add_argument('--skip-completed', action='store_true', default=True,
                       help='跳过已完成的测试（默认启用）')
    
    args = parser.parse_args()
    
    print("="*70)
    print("PSO P01-P23完整测试：三档参数配置")
    print("="*70)
    print("\n参数配置:")
    for config_name in args.configs:
        config = PSO_CONFIGS[config_name]
        print(f"  {config_name.upper()}: particles={config['particleCount']}, "
              f"iterations={config['iterations']}, "
              f"c1={config['cognitiveWeight']}, c2={config['socialWeight']}")
    print(f"  注: w(惯性权重)从0.9线性递减到0.4")
    
    # 配置路径
    base_dir = Path(__file__).parent.parent.parent.parent
    data_dir = base_dir / "MDVRP-Instances" / "dat"
    sol_dir = base_dir / "MDVRP-Instances" / "sol"
    output_dir = Path(__file__).parent / "pso_p01_p23_results"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 确定要测试的问题列表
    if args.problems:
        problems = args.problems
        print(f"\n指定测试问题: {', '.join(problems)}")
    else:
        problems = [f"p{i:02d}" for i in range(1, 24)]  # p01-p23
        print(f"\n测试所有问题: p01-p23")
    
    # 如果指定了起始问题
    if args.start_from:
        try:
            start_idx = problems.index(args.start_from)
            problems = problems[start_idx:]
            print(f"从 {args.start_from} 开始测试")
        except ValueError:
            print(f"[WARNING] 起始问题 {args.start_from} 不在列表中，将测试所有问题")
    
    # 加载已完成的进度
    completed = load_progress(output_dir, args.configs) if args.skip_completed else {}
    
    if completed:
        print(f"\n已完成的测试: {len(completed)}个")
        problems = [p for p in problems if p not in completed]
        print(f"剩余待测试: {len(problems)}个")
    
    if not problems:
        print("\n所有测试已完成！")
        return
    
    # 汇总结果
    all_results = {}
    
    # 开始测试
    runs_per_problem = len(args.configs) * 3
    print(f"\n总共需要测试 {len(problems)} 个问题")
    print(f"每个问题运行次数: {len(args.configs)} 配置 × 3 次 = {runs_per_problem} 次")
    print(f"预计总运行次数: {len(problems)} × {runs_per_problem} = {len(problems) * runs_per_problem} 次")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    overall_start_time = time.time()
    
    for idx, problem_name in enumerate(problems, 1):
        print(f"\n\n{'='*70}")
        print(f"进度: {idx}/{len(problems)} - {problem_name.upper()}")
        print(f"{'='*70}")
        
        try:
            result = test_single_problem(
                problem_name,
                data_dir,
                sol_dir,
                output_dir,
                args.configs
            )
            if result:
                all_results[problem_name] = result
        except Exception as e:
            print(f"\n[ERROR] {problem_name} 测试失败: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    overall_time = time.time() - overall_start_time
    
    # 保存汇总结果
    summary = {
        'test_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_problems': len(problems),
        'configs_tested': args.configs,
        'total_time': overall_time,
        'pso_configs': {k: v for k, v in PSO_CONFIGS.items() if k in args.configs},
        'results': all_results
    }
    
    summary_file = output_dir / 'pso_summary.json'
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    # 打印汇总统计
    print(f"\n{'='*70}")
    print("所有测试完成！汇总统计")
    print(f"{'='*70}")
    print(f"总耗时: {overall_time:.2f}秒 ({overall_time/3600:.2f}小时)")
    print(f"\n{'Problem':>8s} {'Config':>8s} {'AvgCost':>10s} {'AvgGap%':>9s} {'AvgTime':>9s}")
    print(f"{'='*70}")
    
    for prob_name in sorted(all_results.keys()):
        prob_data = all_results[prob_name]
        for config_name in args.configs:
            if config_name in prob_data.get('statistics', {}):
                stats = prob_data['statistics'][config_name]
                print(f"{prob_name:>8s} {config_name:>8s} {stats['avg_cost']:10.2f} "
                      f"{stats['avg_gap']:8.2f}% {stats['avg_time']:8.1f}s")
    
    print(f"\n结果保存在: {output_dir}")
    print(f"汇总文件: {summary_file}")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    main()
