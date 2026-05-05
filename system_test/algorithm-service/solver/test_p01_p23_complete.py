"""
P01-P23完整测试：每个问题运行3次纯GA + 3次混合求解器
记录详细的时间、成本和收敛数据

测试配置:
- 每个问题: 3次纯GA + 3次混合求解器
- 总共: 23个问题 × 6次运行 = 138次运行
- 预计时间: 根据问题规模，小问题几分钟，大问题可能需要几小时
- 结果保存: 每完成一次运行就保存，避免数据丢失

使用方法:
    python test_p01_p23_complete.py
    
    # 或者只测试特定问题
    python test_p01_p23_complete.py --problems p01 p08 p21
    
    # 或者从某个问题开始继续
    python test_p01_p23_complete.py --start-from p08
"""
import os
import sys
import json
import time
import subprocess
import re
import tempfile
import argparse
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

from ga_mdvrp_rl_hybrid import GAMDVRPRLHybrid


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
            'x': float(parts[1]),
            'y': float(parts[2]),
            'vehicle_count': n_vehicles,
            'capacity': depots_info[depot_idx]['capacity']
        })
    
    return {
        'depots': depots,
        'customers': customers,
        'max_distance': depots_info[0]['max_distance']
    }


def write_cordeau_format(f, instance_data: Dict):
    """写入Cordeau格式"""
    depots = instance_data['depots']
    customers = instance_data['customers']
    
    num_depots = len(depots)
    num_customers = len(customers)
    vehicles_per_depot = depots[0].get('vehicle_count', 5)
    
    # 第一行
    f.write(f"2 {vehicles_per_depot} {num_customers} {num_depots}\n")
    
    # Depot信息
    max_distance = int(instance_data.get('max_distance', 0))
    for depot in depots:
        capacity = int(depot['capacity'])
        f.write(f"{max_distance} {capacity}\n")
    
    # 客户信息
    for i, customer in enumerate(customers, 1):
        x = int(round(customer['x']))
        y = int(round(customer['y']))
        demand = int(customer['demand'])
        service_time = 0
        f.write(f"{i} {x} {y} {service_time} {demand}\n")
    
    # Depot坐标
    for i, depot in enumerate(depots, 1):
        x = int(round(depot['x']))
        y = int(round(depot['y']))
        f.write(f"{i} {x} {y}\n")


def extract_cost_from_output(output: str) -> float:
    """从输出提取成本"""
    pattern = r'Total distance best solution:\s*([\d.]+)'
    match = re.search(pattern, output)
    if match:
        return float(match.group(1))
    return 0.0


def extract_convergence_from_output(output: str) -> List[Tuple[int, float]]:
    """从输出提取收敛数据"""
    convergence = []
    pattern = r'Generation:\s*(\d+)\s*\|.*?Best distance:\s*([\d.]+)'
    matches = re.findall(pattern, output)
    
    for gen, cost in matches:
        convergence.append((int(gen), float(cost)))
    
    return convergence


def run_pure_ga_single(problem_name: str, instance_data: Dict, ga_mdvrp_path: Path, run_id: int) -> Dict:
    """运行纯GA单次"""
    print(f"\n{'='*70}")
    print(f"{problem_name.upper()} - 纯GA - 运行 #{run_id+1}/3")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")
    
    # 创建临时问题文件
    problems_dir = ga_mdvrp_path / "data" / "problems"
    problems_dir.mkdir(parents=True, exist_ok=True)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.dat', delete=False, 
                                    dir=problems_dir) as f:
        problem_file = f.name
        write_cordeau_format(f, instance_data)
    
    problem_name_rel = os.path.relpath(problem_file, ga_mdvrp_path)
    solution_file = ga_mdvrp_path / "data" / "solutions" / f"{problem_name}_pure_ga_run{run_id}.res"
    
    start_time = time.time()
    
    try:
        # 运行Java GA
        cmd = [
            'java', '-cp', 'bin;lib/*', 'MainCLI',
            problem_name_rel,
            str(solution_file)
        ]
        
        print("开始运行Java GA...")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=7200,  # 2小时超时
            cwd=str(ga_mdvrp_path)
        )
        
        compute_time = time.time() - start_time
        
        # 解析结果
        total_cost = extract_cost_from_output(result.stdout)
        convergence = extract_convergence_from_output(result.stdout)
        
        print(f"\n结果:")
        print(f"  总成本: {total_cost:.2f}")
        print(f"  计算时间: {compute_time:.2f}秒 ({compute_time/60:.2f}分钟)")
        print(f"  收敛数据点: {len(convergence)}")
        print(f"  结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return {
            'run_id': run_id + 1,
            'total_cost': total_cost,
            'compute_time': compute_time,
            'convergence': convergence,
            'start_time': datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S'),
            'end_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
    except subprocess.TimeoutExpired:
        compute_time = time.time() - start_time
        print(f"\n[ERROR] 超时！运行时间: {compute_time:.2f}秒")
        return {
            'run_id': run_id + 1,
            'total_cost': 0,
            'compute_time': compute_time,
            'convergence': [],
            'error': 'Timeout after 7200 seconds'
        }
    except Exception as e:
        compute_time = time.time() - start_time
        print(f"\n[ERROR] 运行失败: {e}")
        return {
            'run_id': run_id + 1,
            'total_cost': 0,
            'compute_time': compute_time,
            'convergence': [],
            'error': str(e)
        }
    finally:
        # 清理临时文件
        if os.path.exists(problem_file):
            os.unlink(problem_file)


def run_hybrid_solver_single(problem_name: str, instance_data: Dict, run_id: int, ga_mdvrp_path: Path) -> Dict:
    """运行混合求解器单次"""
    print(f"\n{'='*70}")
    print(f"{problem_name.upper()} - 混合求解器 - 运行 #{run_id+1}/3")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")
    
    solver = GAMDVRPRLHybrid(
        rl_seed_ratio=0.2,
        num_rl_samples=20,
        use_gpu=True,
        model_type='auto'
    )
    
    start_time = time.time()
    
    # 修改_run_ga_with_seeds以捕获输出
    captured_stdout = []
    
    def wrapped_run(instance_data_inner, seed_json_path):
        import tempfile
        
        # 创建临时问题文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dat', delete=False, 
                                        dir=solver.ga_mdvrp_path / "data" / "problems") as f:
            problem_file = f.name
            solver._write_cordeau_format(f, instance_data_inner)
        
        problem_name_rel = os.path.relpath(problem_file, solver.ga_mdvrp_path)
        solution_file = solver.ga_mdvrp_path / "data" / "solutions" / f"{problem_name}_hybrid_run{run_id}.res"
        
        try:
            # 运行Java GA
            cmd = [
                'java', '-cp', 'bin;lib/*', 'MainCLI',
                problem_name_rel,
                str(solution_file),
                os.path.abspath(seed_json_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=7200,  # 2小时超时
                cwd=str(solver.ga_mdvrp_path)
            )
            
            captured_stdout.append(result.stdout)
            
            # 解析结果
            total_cost = solver._extract_cost_from_output(result.stdout)
            routes = []
            
        finally:
            if os.path.exists(problem_file):
                os.unlink(problem_file)
        
        return {
            'total_cost': total_cost,
            'routes': routes,
            'num_vehicles': 0
        }
    
    solver._run_ga_with_seeds = wrapped_run
    
    try:
        result = solver.solve(instance_data)
        compute_time = time.time() - start_time
        
        # 提取收敛数据
        convergence = []
        if captured_stdout:
            convergence = extract_convergence_from_output(captured_stdout[0])
        
        print(f"\n结果:")
        print(f"  总成本: {result['total_cost']:.2f}")
        print(f"  计算时间: {compute_time:.2f}秒 ({compute_time/60:.2f}分钟)")
        print(f"  收敛数据点: {len(convergence)}")
        print(f"  结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return {
            'run_id': run_id + 1,
            'total_cost': result['total_cost'],
            'compute_time': compute_time,
            'convergence': convergence,
            'start_time': datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S'),
            'end_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
    except Exception as e:
        compute_time = time.time() - start_time
        print(f"\n[ERROR] 运行失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            'run_id': run_id + 1,
            'total_cost': float('inf'),
            'compute_time': compute_time,
            'convergence': [],
            'error': str(e)
        }


def test_single_problem(problem_name: str, data_dir: Path, output_dir: Path, ga_mdvrp_path: Path):
    """测试单个问题"""
    print(f"\n{'#'*70}")
    print(f"# 开始测试: {problem_name.upper()}")
    print(f"{'#'*70}")
    
    # 读取问题数据
    problem_file = data_dir / problem_name
    
    if not problem_file.exists():
        print(f"[ERROR] 问题文件不存在: {problem_file}")
        return None
    
    print(f"\n读取{problem_name.upper()}数据: {problem_file}")
    instance_data = read_cordeau_file(str(problem_file))
    print(f"  客户数: {len(instance_data['customers'])}")
    print(f"  仓库数: {len(instance_data['depots'])}")
    print(f"  最大距离: {instance_data['max_distance']}")
    
    results = {
        'problem': problem_name,
        'num_customers': len(instance_data['customers']),
        'num_depots': len(instance_data['depots']),
        'max_distance': instance_data['max_distance'],
        'test_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'pure_ga_runs': [],
        'hybrid_runs': []
    }
    
    # 运行纯GA 3次
    print(f"\n{'='*70}")
    print(f"第一部分：纯GA测试（3次运行）")
    print(f"{'='*70}")
    
    for run_id in range(3):
        result = run_pure_ga_single(problem_name, instance_data, ga_mdvrp_path, run_id)
        results['pure_ga_runs'].append(result)
        
        # 每次运行后保存
        save_results(output_dir, results)
    
    # 运行混合求解器 3次
    print(f"\n{'='*70}")
    print(f"第二部分：混合求解器测试（3次运行）")
    print(f"{'='*70}")
    
    for run_id in range(3):
        result = run_hybrid_solver_single(problem_name, instance_data, run_id, ga_mdvrp_path)
        results['hybrid_runs'].append(result)
        
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
    import numpy as np
    
    # 纯GA统计
    pure_ga_times = [r['compute_time'] for r in results['pure_ga_runs'] if 'error' not in r]
    pure_ga_costs = [r['total_cost'] for r in results['pure_ga_runs'] if 'error' not in r and r['total_cost'] > 0]
    
    # 混合求解器统计
    hybrid_times = [r['compute_time'] for r in results['hybrid_runs'] if 'error' not in r]
    hybrid_costs = [r['total_cost'] for r in results['hybrid_runs'] if 'error' not in r and r['total_cost'] < float('inf')]
    
    results['statistics'] = {
        'pure_ga': {
            'times': pure_ga_times,
            'costs': pure_ga_costs,
            'avg_time': float(np.mean(pure_ga_times)) if pure_ga_times else 0,
            'std_time': float(np.std(pure_ga_times)) if pure_ga_times else 0,
            'avg_cost': float(np.mean(pure_ga_costs)) if pure_ga_costs else 0,
            'std_cost': float(np.std(pure_ga_costs)) if pure_ga_costs else 0
        },
        'hybrid': {
            'times': hybrid_times,
            'costs': hybrid_costs,
            'avg_time': float(np.mean(hybrid_times)) if hybrid_times else 0,
            'std_time': float(np.std(hybrid_times)) if hybrid_times else 0,
            'avg_cost': float(np.mean(hybrid_costs)) if hybrid_costs else 0,
            'std_cost': float(np.std(hybrid_costs)) if hybrid_costs else 0
        }
    }
    
    # 打印统计
    print(f"\n{'='*70}")
    print(f"{results['problem'].upper()} - 统计结果")
    print(f"{'='*70}")
    
    if pure_ga_times:
        print(f"\n纯GA统计 ({len(pure_ga_times)}次有效运行):")
        print(f"  平均时间: {results['statistics']['pure_ga']['avg_time']:.2f}秒 ({results['statistics']['pure_ga']['avg_time']/60:.2f}分钟)")
        if pure_ga_costs:
            print(f"  平均成本: {results['statistics']['pure_ga']['avg_cost']:.2f}")
    
    if hybrid_times:
        print(f"\n混合求解器统计 ({len(hybrid_times)}次有效运行):")
        print(f"  平均时间: {results['statistics']['hybrid']['avg_time']:.2f}秒 ({results['statistics']['hybrid']['avg_time']/60:.2f}分钟)")
        if hybrid_costs:
            print(f"  平均成本: {results['statistics']['hybrid']['avg_cost']:.2f}")
    
    # 对比
    if pure_ga_costs and hybrid_costs:
        cost_improvement = results['statistics']['pure_ga']['avg_cost'] - results['statistics']['hybrid']['avg_cost']
        cost_improvement_pct = (cost_improvement / results['statistics']['pure_ga']['avg_cost']) * 100
        time_overhead = results['statistics']['hybrid']['avg_time'] - results['statistics']['pure_ga']['avg_time']
        time_overhead_pct = (time_overhead / results['statistics']['pure_ga']['avg_time']) * 100
        
        print(f"\n对比:")
        print(f"  质量提升: {cost_improvement:.2f} ({cost_improvement_pct:+.2f}%)")
        print(f"  时间开销: {time_overhead:+.2f}秒 ({time_overhead_pct:+.2f}%)")


def save_results(output_dir: Path, results: Dict):
    """保存结果到JSON文件"""
    problem_name = results['problem']
    output_file = output_dir / f"{problem_name}_results.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def load_progress(output_dir: Path) -> Dict:
    """加载已完成的测试进度"""
    progress = {}
    
    if not output_dir.exists():
        return progress
    
    for json_file in output_dir.glob("p*_results.json"):
        problem_name = json_file.stem.replace('_results', '')
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 检查是否完成（有3次纯GA和3次混合运行）
                if len(data.get('pure_ga_runs', [])) == 3 and len(data.get('hybrid_runs', [])) == 3:
                    progress[problem_name] = True
                    print(f"[INFO] 发现已完成的测试: {problem_name}")
        except:
            pass
    
    return progress


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='P01-P23完整测试')
    parser.add_argument('--problems', nargs='+', help='指定要测试的问题，例如: p01 p08 p21')
    parser.add_argument('--start-from', help='从指定问题开始测试，例如: p08')
    parser.add_argument('--skip-completed', action='store_true', default=True, 
                       help='跳过已完成的测试（默认启用）')
    
    args = parser.parse_args()
    
    print("="*70)
    print("P01-P23完整测试：纯GA vs 混合求解器")
    print("="*70)
    
    # 配置路径
    base_dir = Path(__file__).parent.parent.parent.parent
    data_dir = base_dir / "MDVRP-Instances" / "dat"
    output_dir = Path(__file__).parent / "p01_p23_complete_results"
    ga_mdvrp_path = base_dir / "system_test" / "ga_mdvrp_reproduction" / "GA-MDVRP"
    
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
    completed = load_progress(output_dir) if args.skip_completed else {}
    
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
    print(f"\n总共需要测试 {len(problems)} 个问题")
    print(f"预计总运行次数: {len(problems)} × 6 = {len(problems) * 6} 次")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    overall_start_time = time.time()
    
    for idx, problem_name in enumerate(problems, 1):
        print(f"\n\n{'='*70}")
        print(f"进度: {idx}/{len(problems)} - {problem_name.upper()}")
        print(f"{'='*70}")
        
        try:
            result = test_single_problem(problem_name, data_dir, output_dir, ga_mdvrp_path)
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
        'total_time': overall_time,
        'results': all_results
    }
    
    summary_file = output_dir / 'summary.json'
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*70}")
    print("所有测试完成！")
    print(f"{'='*70}")
    print(f"总耗时: {overall_time:.2f}秒 ({overall_time/3600:.2f}小时)")
    print(f"结果保存在: {output_dir}")
    print(f"汇总文件: {summary_file}")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    main()
