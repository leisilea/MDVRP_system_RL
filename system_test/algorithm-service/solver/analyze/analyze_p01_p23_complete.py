#!/usr/bin/env python3
"""
分析P01-P23完整测试结果
生成收敛曲线、统计报告和对比分析

使用方法:
    python analyze_p01_p23_complete.py
    
    # 或者只分析特定问题
    python analyze_p01_p23_complete.py --problems p01 p08 p21
"""

import json
import argparse
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from typing import Dict, List

def load_results(results_dir: Path) -> Dict:
    """加载所有测试结果"""
    all_results = {}
    
    for json_file in sorted(results_dir.glob("p*_results.json")):
        problem_name = json_file.stem.replace('_results', '')
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_results[problem_name] = data
        except Exception as e:
            print(f"[WARNING] 无法加载 {json_file}: {e}")
    
    return all_results


def extract_convergence_data(runs_data):
    """提取收敛数据"""
    all_convergence = []
    for run in runs_data:
        if 'convergence' in run and run['convergence']:
            convergence = run['convergence']
            generations = [point[0] for point in convergence]
            costs = [point[1] for point in convergence]
            all_convergence.append((generations, costs))
    return all_convergence


def compute_average_convergence(all_convergence):
    """计算平均收敛曲线"""
    if not all_convergence:
        return [], []
    
    generations = all_convergence[0][0]
    
    costs_by_gen = []
    for gen_idx in range(len(generations)):
        costs_at_gen = [conv[1][gen_idx] for conv in all_convergence if gen_idx < len(conv[1])]
        costs_by_gen.append(costs_at_gen)
    
    avg_costs = [np.mean(costs) for costs in costs_by_gen]
    
    return generations, avg_costs


def plot_convergence(problem_name: str, pure_ga_runs, hybrid_runs, output_dir: Path):
    """绘制单个问题的收敛曲线"""
    pure_ga_convergence = extract_convergence_data(pure_ga_runs)
    hybrid_convergence = extract_convergence_data(hybrid_runs)
    
    if not pure_ga_convergence or not hybrid_convergence:
        print(f"[WARNING] {problem_name} 缺少收敛数据，跳过绘图")
        return
    
    pure_ga_gens, pure_ga_avg = compute_average_convergence(pure_ga_convergence)
    hybrid_gens, hybrid_avg = compute_average_convergence(hybrid_convergence)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # 完整收敛曲线
    ax1.plot(pure_ga_gens, pure_ga_avg, 'b-', linewidth=2, label='Pure GA (avg)', alpha=0.8)
    ax1.plot(hybrid_gens, hybrid_avg, 'r-', linewidth=2, label='Hybrid (avg)', alpha=0.8)
    
    for i, (gens, costs) in enumerate(pure_ga_convergence):
        ax1.plot(gens, costs, 'b-', linewidth=0.5, alpha=0.2)
    for i, (gens, costs) in enumerate(hybrid_convergence):
        ax1.plot(gens, costs, 'r-', linewidth=0.5, alpha=0.2)
    
    ax1.set_xlabel('Generation', fontsize=12)
    ax1.set_ylabel('Total Cost', fontsize=12)
    ax1.set_title(f'{problem_name.upper()} Convergence: Pure GA vs Hybrid', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=11)
    ax1.grid(True, alpha=0.3)
    
    # 前100代放大
    max_gen_zoom = min(100, len(pure_ga_gens))
    zoom_idx = max_gen_zoom // 10
    
    if zoom_idx > 0:
        ax2.plot(pure_ga_gens[:zoom_idx], pure_ga_avg[:zoom_idx], 'b-', linewidth=2, 
                 label=f'Pure GA (gen 10: {pure_ga_avg[0]:.1f})', alpha=0.8)
        ax2.plot(hybrid_gens[:zoom_idx], hybrid_avg[:zoom_idx], 'r-', linewidth=2, 
                 label=f'Hybrid (gen 10: {hybrid_avg[0]:.1f})', alpha=0.8)
        
        ax2.scatter([pure_ga_gens[0]], [pure_ga_avg[0]], color='blue', s=100, zorder=5, 
                    marker='o', edgecolors='black', linewidths=2)
        ax2.scatter([hybrid_gens[0]], [hybrid_avg[0]], color='red', s=100, zorder=5, 
                    marker='o', edgecolors='black', linewidths=2)
        
        ax2.set_xlabel('Generation', fontsize=12)
        ax2.set_ylabel('Total Cost', fontsize=12)
        ax2.set_title(f'First {max_gen_zoom} Generations (RL Initialization Effect)', 
                      fontsize=14, fontweight='bold')
        ax2.legend(fontsize=11)
        ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    output_path = output_dir / f'{problem_name}_convergence.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"  保存收敛图: {output_path.name}")


def generate_summary_report(all_results: Dict, output_dir: Path):
    """生成汇总报告"""
    report_lines = []
    report_lines.append("# P01-P23 完整测试汇总报告\n")
    report_lines.append(f"生成时间: {np.datetime64('now')}\n")
    report_lines.append(f"测试问题数: {len(all_results)}\n\n")
    
    report_lines.append("## 测试结果总览\n\n")
    report_lines.append("| 问题 | 客户数 | 仓库数 | 纯GA成本 | 混合成本 | 质量提升 | 纯GA时间(秒) | 混合时间(秒) | 时间开销 | 推荐 |\n")
    report_lines.append("|------|--------|--------|----------|----------|----------|--------------|--------------|----------|------|\n")
    
    summary_stats = {
        'total_problems': 0,
        'quality_wins': 0,
        'quality_losses': 0,
        'quality_ties': 0,
        'total_pure_ga_cost': 0,
        'total_hybrid_cost': 0,
        'total_pure_ga_time': 0,
        'total_hybrid_time': 0
    }
    
    for problem_name in sorted(all_results.keys()):
        data = all_results[problem_name]
        stats = data.get('statistics', {})
        
        pure_ga_cost = stats.get('pure_ga', {}).get('avg_cost', 0)
        hybrid_cost = stats.get('hybrid', {}).get('avg_cost', 0)
        pure_ga_time = stats.get('pure_ga', {}).get('avg_time', 0)
        hybrid_time = stats.get('hybrid', {}).get('avg_time', 0)
        
        if pure_ga_cost > 0 and hybrid_cost > 0:
            quality_improvement = ((pure_ga_cost - hybrid_cost) / pure_ga_cost) * 100
            time_overhead = ((hybrid_time - pure_ga_time) / pure_ga_time) * 100
            
            # 推荐逻辑
            if quality_improvement > 1.0 and time_overhead < 50:
                recommend = "⭐⭐⭐⭐⭐"
            elif quality_improvement > 0.5 and time_overhead < 100:
                recommend = "⭐⭐⭐⭐"
            elif quality_improvement > 0:
                recommend = "⭐⭐⭐"
            elif quality_improvement > -0.5:
                recommend = "⭐⭐"
            else:
                recommend = "⭐"
            
            report_lines.append(
                f"| {problem_name} | {data.get('num_customers', 0)} | {data.get('num_depots', 0)} | "
                f"{pure_ga_cost:.2f} | {hybrid_cost:.2f} | {quality_improvement:+.2f}% | "
                f"{pure_ga_time:.2f} | {hybrid_time:.2f} | {time_overhead:+.2f}% | {recommend} |\n"
            )
            
            summary_stats['total_problems'] += 1
            summary_stats['total_pure_ga_cost'] += pure_ga_cost
            summary_stats['total_hybrid_cost'] += hybrid_cost
            summary_stats['total_pure_ga_time'] += pure_ga_time
            summary_stats['total_hybrid_time'] += hybrid_time
            
            if quality_improvement > 0.1:
                summary_stats['quality_wins'] += 1
            elif quality_improvement < -0.1:
                summary_stats['quality_losses'] += 1
            else:
                summary_stats['quality_ties'] += 1
    
    # 总体统计
    if summary_stats['total_problems'] > 0:
        overall_quality = ((summary_stats['total_pure_ga_cost'] - summary_stats['total_hybrid_cost']) / 
                          summary_stats['total_pure_ga_cost']) * 100
        overall_time = ((summary_stats['total_hybrid_time'] - summary_stats['total_pure_ga_time']) / 
                       summary_stats['total_pure_ga_time']) * 100
        
        report_lines.append("\n## 总体统计\n\n")
        report_lines.append(f"- 测试问题数: {summary_stats['total_problems']}\n")
        report_lines.append(f"- 质量胜: {summary_stats['quality_wins']} | 平: {summary_stats['quality_ties']} | 负: {summary_stats['quality_losses']}\n")
        report_lines.append(f"- 总体质量提升: {overall_quality:+.2f}%\n")
        report_lines.append(f"- 总体时间开销: {overall_time:+.2f}%\n")
        report_lines.append(f"- 平均纯GA成本: {summary_stats['total_pure_ga_cost']/summary_stats['total_problems']:.2f}\n")
        report_lines.append(f"- 平均混合成本: {summary_stats['total_hybrid_cost']/summary_stats['total_problems']:.2f}\n")
        report_lines.append(f"- 平均纯GA时间: {summary_stats['total_pure_ga_time']/summary_stats['total_problems']:.2f}秒\n")
        report_lines.append(f"- 平均混合时间: {summary_stats['total_hybrid_time']/summary_stats['total_problems']:.2f}秒\n")
    
    # 保存报告
    report_file = output_dir / 'SUMMARY_REPORT.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.writelines(report_lines)
    
    print(f"\n汇总报告已保存: {report_file}")
    
    # 打印到控制台
    print("\n" + "="*80)
    for line in report_lines:
        print(line.rstrip())
    print("="*80)


def main():
    parser = argparse.ArgumentParser(description='分析P01-P23完整测试结果')
    parser.add_argument('--problems', nargs='+', help='指定要分析的问题')
    parser.add_argument('--no-plots', action='store_true', help='不生成收敛曲线图')
    
    args = parser.parse_args()
    
    print("="*70)
    print("P01-P23 完整测试结果分析")
    print("="*70)
    
    # 路径配置
    results_dir = Path(__file__).parent / "p01_p23_complete_results"
    
    if not results_dir.exists():
        print(f"\n[ERROR] 结果目录不存在: {results_dir}")
        print("请先运行 test_p01_p23_complete.py")
        return
    
    # 加载结果
    print(f"\n加载测试结果...")
    all_results = load_results(results_dir)
    
    if not all_results:
        print("[ERROR] 没有找到测试结果")
        return
    
    print(f"找到 {len(all_results)} 个问题的测试结果")
    
    # 过滤问题
    if args.problems:
        all_results = {k: v for k, v in all_results.items() if k in args.problems}
        print(f"分析指定的 {len(all_results)} 个问题")
    
    # 生成收敛曲线
    if not args.no_plots:
        print(f"\n生成收敛曲线...")
        for problem_name, data in all_results.items():
            print(f"  处理 {problem_name}...")
            try:
                plot_convergence(
                    problem_name,
                    data.get('pure_ga_runs', []),
                    data.get('hybrid_runs', []),
                    results_dir
                )
            except Exception as e:
                print(f"  [ERROR] {problem_name} 绘图失败: {e}")
    
    # 生成汇总报告
    print(f"\n生成汇总报告...")
    generate_summary_report(all_results, results_dir)
    
    print(f"\n分析完成！")
    print(f"结果保存在: {results_dir}")


if __name__ == '__main__':
    main()
