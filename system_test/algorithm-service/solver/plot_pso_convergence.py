#!/usr/bin/env python3
"""
绘制PSO收敛曲线

读取合并后的PSO结果文件，绘制收敛曲线图
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


def plot_convergence(data, output_dir=None):
    """
    绘制收敛曲线
    
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
        
        # 创建图表
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        fig.suptitle(f'PSO收敛曲线 - {problem.upper()} - {config_name.upper()}', 
                     fontsize=16, fontweight='bold')
        
        # 绘制每个run的收敛曲线
        for run in runs:
            run_id = run['run_id']
            convergence = run.get('convergence_merged', [])
            stop_gen = run.get('stop_generation', None)  # 获取实际停止代数
            
            if not convergence:
                print(f"  Run {run_id}: 无收敛数据")
                continue
            
            generations = [entry['generation'] for entry in convergence]
            best_costs = [entry['best_cost'] for entry in convergence]
            avg_costs = [entry['avg_cost'] for entry in convergence]
            
            # 找到停止点的索引
            if stop_gen is not None:
                stop_idx = next((i for i, g in enumerate(generations) if g == stop_gen), len(generations) - 1)
            else:
                # 如果没有stop_generation字段，使用旧逻辑检测
                stop_idx = len(best_costs) - 1
                for i in range(len(best_costs) - 1, 0, -1):
                    if abs(best_costs[i] - best_costs[i-1]) > 1e-6:
                        stop_idx = i
                        break
            
            stop_generation = generations[stop_idx]
            
            # 分段绘制：停止前用实线，停止后用虚线
            # best_cost
            if stop_idx < len(generations) - 1:
                # 有延续部分
                line1 = ax1.plot(generations[:stop_idx+1], best_costs[:stop_idx+1], 
                        marker='o', label=f'Run {run_id}', linewidth=2)[0]
                line_color = line1.get_color()  # 获取线条颜色
                ax1.plot(generations[stop_idx:], best_costs[stop_idx:], 
                        linestyle='--', marker='o', linewidth=1.5, alpha=0.6, color=line_color)
                # 标记停止点，使用相同颜色
                ax1.axvline(x=stop_generation, color=line_color, linestyle=':', 
                           linewidth=1.5, alpha=0.5)
            else:
                # 没有延续部分
                ax1.plot(generations, best_costs, marker='o', 
                        label=f'Run {run_id}', linewidth=2)
            
            # avg_cost (同样处理)
            if stop_idx < len(generations) - 1:
                line2 = ax2.plot(generations[:stop_idx+1], avg_costs[:stop_idx+1], 
                        marker='s', label=f'Run {run_id}', linewidth=2)[0]
                line_color = line2.get_color()  # 获取线条颜色
                ax2.plot(generations[stop_idx:], avg_costs[stop_idx:], 
                        linestyle='--', marker='s', linewidth=1.5, alpha=0.6, color=line_color)
                ax2.axvline(x=stop_generation, color=line_color, linestyle=':', 
                           linewidth=1.5, alpha=0.5)
            else:
                ax2.plot(generations, avg_costs, marker='s', 
                        label=f'Run {run_id}', linewidth=2)
            
            print(f"  Run {run_id}: {len(convergence)}个数据点, "
                  f"初始成本={best_costs[0]:.2f}, 最终成本={best_costs[-1]:.2f}, "
                  f"停止代数={stop_generation}")
        
        # 添加BKS参考线
        if bks:
            ax1.axhline(y=bks, color='red', linestyle='--', linewidth=2, label=f'BKS={bks}')
            ax2.axhline(y=bks, color='red', linestyle='--', linewidth=2, label=f'BKS={bks}')
        
        # 设置ax1（best_cost）
        ax1.set_xlabel('Generation', fontsize=12)
        ax1.set_ylabel('Best Cost', fontsize=12)
        ax1.set_title('最优成本收敛曲线', fontsize=14)
        ax1.legend(loc='best')
        ax1.grid(True, alpha=0.3)
        
        # 设置ax2（avg_cost）
        ax2.set_xlabel('Generation', fontsize=12)
        ax2.set_ylabel('Average Cost', fontsize=12)
        ax2.set_title('平均成本收敛曲线', fontsize=14)
        ax2.legend(loc='best')
        ax2.grid(True, alpha=0.3)
        
        # 保存图表
        output_file = output_dir / f'{problem}_pso_{config_name}_convergence.png'
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"  [OK] 图表已保存: {output_file}")


def plot_comparison(data, output_dir=None):
    """
    绘制不同配置的对比图
    
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
    
    # 创建对比图
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle(f'PSO配置对比 - {problem.upper()}', fontsize=16, fontweight='bold')
    
    colors = {'small': 'blue', 'medium': 'green', 'large': 'orange'}
    
    # 按照large、medium、small的顺序绘制，这样small在最上层
    config_order = ['large', 'medium', 'small']
    
    for config_name in config_order:
        if config_name not in data.get('runs', {}):
            continue
        runs = data['runs'][config_name]
        print(f"\n处理配置: {config_name}")
        
        # 计算平均收敛曲线
        all_generations = set()
        for run in runs:
            convergence = run.get('convergence_merged', [])
            for entry in convergence:
                all_generations.add(entry['generation'])
        
        all_generations = sorted(all_generations)
        
        # 为每个run创建generation到数据的映射
        run_gen_maps = []
        for run in runs:
            convergence = run.get('convergence_merged', [])
            gen_map = {}
            for entry in convergence:
                gen_map[entry['generation']] = entry
            run_gen_maps.append(gen_map)
        
        # 对每个generation，计算所有run的平均值
        # 如果某个run没有该generation，使用其最后一个generation的值
        avg_best_costs = []
        avg_avg_costs = []
        
        # 同时记录每个run的停止代数
        stop_generations = []
        for run in runs:
            convergence = run.get('convergence_merged', [])
            if not convergence:
                continue
            best_costs = [entry['best_cost'] for entry in convergence]
            generations_list = [entry['generation'] for entry in convergence]
            
            # 找到停止代数
            stop_idx = len(best_costs) - 1
            for i in range(len(best_costs) - 1, 0, -1):
                if abs(best_costs[i] - best_costs[i-1]) > 1e-6:
                    stop_idx = i
                    break
            stop_generations.append(generations_list[stop_idx])
        
        for gen in all_generations:
            best_costs_at_gen = []
            avg_costs_at_gen = []
            
            for gen_map in run_gen_maps:
                if gen in gen_map:
                    # 该run有这个generation的数据
                    best_costs_at_gen.append(gen_map[gen]['best_cost'])
                    avg_costs_at_gen.append(gen_map[gen]['avg_cost'])
                else:
                    # 该run没有这个generation，使用其最后一个值
                    last_gen = max(gen_map.keys())
                    best_costs_at_gen.append(gen_map[last_gen]['best_cost'])
                    avg_costs_at_gen.append(gen_map[last_gen]['avg_cost'])
            
            if best_costs_at_gen:
                avg_best_costs.append(sum(best_costs_at_gen) / len(best_costs_at_gen))
                avg_avg_costs.append(sum(avg_costs_at_gen) / len(avg_costs_at_gen))
        
        # 计算平均停止代数
        avg_stop_gen = sum(stop_generations) / len(stop_generations) if stop_generations else None
        
        # 绘制平均曲线
        color = colors.get(config_name, 'gray')
        
        # 找到平均停止代数的索引
        if avg_stop_gen:
            stop_idx_avg = 0
            for i, gen in enumerate(all_generations):
                if gen <= avg_stop_gen:
                    stop_idx_avg = i
            
            # 分段绘制
            if stop_idx_avg < len(all_generations) - 1:
                # 停止前：实线
                ax1.plot(all_generations[:stop_idx_avg+1], avg_best_costs[:stop_idx_avg+1], 
                        marker='o', label=f'{config_name}', linewidth=2, color=color)
                # 停止后：虚线
                ax1.plot(all_generations[stop_idx_avg:], avg_best_costs[stop_idx_avg:], 
                        linestyle='--', marker='o', linewidth=1.5, color=color, alpha=0.6)
                
                ax2.plot(all_generations[:stop_idx_avg+1], avg_avg_costs[:stop_idx_avg+1], 
                        marker='s', label=f'{config_name}', linewidth=2, color=color)
                ax2.plot(all_generations[stop_idx_avg:], avg_avg_costs[stop_idx_avg:], 
                        linestyle='--', marker='s', linewidth=1.5, color=color, alpha=0.6)
                
                # 标记平均停止代数
                ax1.axvline(x=avg_stop_gen, color=color, linestyle=':', 
                           linewidth=1.5, alpha=0.4)
                ax2.axvline(x=avg_stop_gen, color=color, linestyle=':', 
                           linewidth=1.5, alpha=0.4)
            else:
                ax1.plot(all_generations, avg_best_costs, marker='o', 
                        label=f'{config_name}', linewidth=2, color=color)
                ax2.plot(all_generations, avg_avg_costs, marker='s', 
                        label=f'{config_name}', linewidth=2, color=color)
        else:
            ax1.plot(all_generations, avg_best_costs, marker='o', 
                    label=f'{config_name}', linewidth=2, color=color)
            ax2.plot(all_generations, avg_avg_costs, marker='s', 
                    label=f'{config_name}', linewidth=2, color=color)
        
        print(f"  {config_name}: {len(all_generations)}个generation, "
              f"平均最终成本={avg_best_costs[-1]:.2f}, "
              f"平均停止代数={avg_stop_gen:.0f}" if avg_stop_gen else f"平均最终成本={avg_best_costs[-1]:.2f}")
    
    # 添加BKS参考线
    if bks:
        ax1.axhline(y=bks, color='red', linestyle='--', linewidth=2, label=f'BKS={bks}')
        ax2.axhline(y=bks, color='red', linestyle='--', linewidth=2, label=f'BKS={bks}')
    
    # 设置ax1
    ax1.set_xlabel('Generation', fontsize=12)
    ax1.set_ylabel('Average Best Cost', fontsize=12)
    ax1.set_title('平均最优成本对比', fontsize=14)
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)
    
    # 设置ax2
    ax2.set_xlabel('Generation', fontsize=12)
    ax2.set_ylabel('Average Avg Cost', fontsize=12)
    ax2.set_title('平均成本对比', fontsize=14)
    ax2.legend(loc='best')
    ax2.grid(True, alpha=0.3)
    
    # 保存图表
    output_file = output_dir / f'{problem}_pso_config_comparison.png'
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"\n[OK] 对比图已保存: {output_file}")


def main():
    if len(sys.argv) < 2:
        print("用法: python plot_pso_convergence.py <merged_json_file> [output_dir]")
        print("示例: python plot_pso_convergence.py pso_p01_p23_results/p01_pso_results_merged.json")
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
    plot_convergence(data, output_dir)
    
    # 绘制配置对比图
    plot_comparison(data, output_dir)
    
    print("\n[OK] 所有图表已生成完成")


if __name__ == '__main__':
    main()
