#!/usr/bin/env python3
"""
绘制P08 PSO收敛曲线（中文版，分开两张图）

读取P08的PSO结果文件，绘制中文版收敛曲线图
"""

import json
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def plot_p08_convergence_chinese(data, output_dir=None):
    """
    绘制P08收敛曲线（中文版，分开两张图，统一y轴）
    
    Args:
        data: 合并后的PSO结果数据
        output_dir: 输出目录（可选）
    """
    problem = data.get('problem', 'unknown')
    bks = data.get('bks', None)
    
    if output_dir is None:
        output_dir = Path('.')
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    # 为每个配置绘制图表
    for config_name, runs in data.get('runs', {}).items():
        print(f"\n绘制配置: {config_name}")
        
        # 收集所有成本数据以统一y轴范围
        all_best_costs = []
        all_avg_costs = []
        
        for run in runs:
            convergence = run.get('convergence_merged', [])
            if convergence:
                all_best_costs.extend([entry['best_cost'] for entry in convergence])
                all_avg_costs.extend([entry['avg_cost'] for entry in convergence])
        
        # 计算统一的y轴范围（留10%的边距）
        if all_best_costs and all_avg_costs:
            min_cost = min(min(all_best_costs), min(all_avg_costs))
            max_cost = max(max(all_best_costs), max(all_avg_costs))
            margin = (max_cost - min_cost) * 0.1
            y_min = min_cost - margin
            y_max = max_cost + margin
        else:
            y_min, y_max = None, None
        
        # ========== 图1: 最优成本收敛曲线 ==========
        fig1, ax1 = plt.subplots(1, 1, figsize=(10, 6))
        fig1.suptitle(f'PSO最优成本收敛曲线 - {problem.upper()} - {config_name.upper()}', 
                     fontsize=16, fontweight='bold')
        
        # 绘制每个run的收敛曲线
        for run in runs:
            run_id = run['run_id']
            convergence = run.get('convergence_merged', [])
            stop_gen = run.get('stop_generation', None)
            
            if not convergence:
                print(f"  Run {run_id}: 无收敛数据")
                continue
            
            generations = [entry['generation'] for entry in convergence]
            best_costs = [entry['best_cost'] for entry in convergence]
            
            # 找到停止点的索引
            if stop_gen is not None:
                stop_idx = next((i for i, g in enumerate(generations) if g == stop_gen), len(generations) - 1)
            else:
                stop_idx = len(best_costs) - 1
                for i in range(len(best_costs) - 1, 0, -1):
                    if abs(best_costs[i] - best_costs[i-1]) > 1e-6:
                        stop_idx = i
                        break
            
            stop_generation = generations[stop_idx]
            
            # 分段绘制：停止前用实线，停止后用虚线
            if stop_idx < len(generations) - 1:
                line1 = ax1.plot(generations[:stop_idx+1], best_costs[:stop_idx+1], 
                        marker='o', label=f'运行 {run_id}', linewidth=2)[0]
                line_color = line1.get_color()
                ax1.plot(generations[stop_idx:], best_costs[stop_idx:], 
                        linestyle='--', marker='o', linewidth=1.5, alpha=0.6, color=line_color)
                ax1.axvline(x=stop_generation, color=line_color, linestyle=':', 
                           linewidth=1.5, alpha=0.5)
            else:
                ax1.plot(generations, best_costs, marker='o', 
                        label=f'运行 {run_id}', linewidth=2)
            
            print(f"  Run {run_id}: {len(convergence)}个数据点, "
                  f"初始成本={best_costs[0]:.2f}, 最终成本={best_costs[-1]:.2f}, "
                  f"停止代数={stop_generation}")
        
        # 添加BKS参考线
        if bks:
            ax1.axhline(y=bks, color='red', linestyle='--', linewidth=2, label=f'BKS={bks}')
        
        # 设置ax1
        ax1.set_xlabel('迭代代数', fontsize=14)
        ax1.set_ylabel('成本', fontsize=14)
        ax1.set_title('最优成本收敛曲线', fontsize=14)
        ax1.legend(loc='best', fontsize=11)
        ax1.grid(True, alpha=0.3)
        
        # 统一y轴范围
        if y_min is not None and y_max is not None:
            ax1.set_ylim(y_min, y_max)
        
        # 保存图表1
        output_file1 = output_dir / f'{problem}_pso_{config_name}_最优成本.png'
        plt.tight_layout()
        plt.savefig(output_file1, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  [OK] 图表已保存: {output_file1}")
        
        # ========== 图2: 平均成本收敛曲线 ==========
        fig2, ax2 = plt.subplots(1, 1, figsize=(10, 6))
        fig2.suptitle(f'PSO平均成本收敛曲线 - {problem.upper()} - {config_name.upper()}', 
                     fontsize=16, fontweight='bold')
        
        # 绘制每个run的收敛曲线
        for run in runs:
            run_id = run['run_id']
            convergence = run.get('convergence_merged', [])
            stop_gen = run.get('stop_generation', None)
            
            if not convergence:
                continue
            
            generations = [entry['generation'] for entry in convergence]
            avg_costs = [entry['avg_cost'] for entry in convergence]
            
            # 找到停止点的索引
            if stop_gen is not None:
                stop_idx = next((i for i, g in enumerate(generations) if g == stop_gen), len(generations) - 1)
            else:
                stop_idx = len(avg_costs) - 1
                for i in range(len(avg_costs) - 1, 0, -1):
                    if abs(avg_costs[i] - avg_costs[i-1]) > 1e-6:
                        stop_idx = i
                        break
            
            stop_generation = generations[stop_idx]
            
            # 分段绘制
            if stop_idx < len(generations) - 1:
                line2 = ax2.plot(generations[:stop_idx+1], avg_costs[:stop_idx+1], 
                        marker='s', label=f'运行 {run_id}', linewidth=2)[0]
                line_color = line2.get_color()
                ax2.plot(generations[stop_idx:], avg_costs[stop_idx:], 
                        linestyle='--', marker='s', linewidth=1.5, alpha=0.6, color=line_color)
                ax2.axvline(x=stop_generation, color=line_color, linestyle=':', 
                           linewidth=1.5, alpha=0.5)
            else:
                ax2.plot(generations, avg_costs, marker='s', 
                        label=f'运行 {run_id}', linewidth=2)
        
        # 添加BKS参考线
        if bks:
            ax2.axhline(y=bks, color='red', linestyle='--', linewidth=2, label=f'BKS={bks}')
        
        # 设置ax2
        ax2.set_xlabel('迭代代数', fontsize=14)
        ax2.set_ylabel('成本', fontsize=14)
        ax2.set_title('平均成本收敛曲线', fontsize=14)
        ax2.legend(loc='best', fontsize=11)
        ax2.grid(True, alpha=0.3)
        
        # 统一y轴范围
        if y_min is not None and y_max is not None:
            ax2.set_ylim(y_min, y_max)
        
        # 保存图表2
        output_file2 = output_dir / f'{problem}_pso_{config_name}_平均成本.png'
        plt.tight_layout()
        plt.savefig(output_file2, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  [OK] 图表已保存: {output_file2}")


def main():
    if len(sys.argv) < 2:
        print("用法: python plot_pso_p08_chinese.py <merged_json_file> [output_dir]")
        print("示例: python plot_pso_p08_chinese.py pso_p01_p23_results/p08_pso_results_merged.json")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not Path(input_file).exists():
        print(f"错误: 文件不存在: {input_file}")
        sys.exit(1)
    
    # 读取数据
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"读取文件: {input_file}")
    print(f"问题: {data.get('problem', 'unknown')}")
    print(f"BKS: {data.get('bks', 'N/A')}")
    
    # 绘制收敛曲线
    plot_p08_convergence_chinese(data, output_dir)
    
    print("\n[OK] 所有图表已生成完成")


if __name__ == '__main__':
    main()
