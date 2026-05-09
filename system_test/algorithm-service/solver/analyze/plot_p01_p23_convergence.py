"""
绘制P01-P23的收敛图并进行数据分析
"""

import json
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import pandas as pd

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# Best known solutions for P01-P23
BEST_KNOWN = {
    'p01': 576.87, 'p02': 473.53, 'p03': 640.58, 'p04': 1001.59,
    'p05': 750.03, 'p06': 876.50, 'p07': 881.97, 'p08': 4437.68,
    'p09': 3873.89, 'p10': 3663.02, 'p11': 3554.18, 'p12': 1318.95,
    'p13': 1318.95, 'p14': 1360.12, 'p15': 2505.42, 'p16': 2572.23,
    'p17': 2709.09, 'p18': 3702.85, 'p19': 3827.06, 'p20': 4058.07,
    'p21': 5474.84, 'p22': 5702.16, 'p23': 6078.75
}

def load_results():
    """加载测试结果"""
    results_file = Path('p01_p23_results_multi_runs/benchmark_results_multi_runs.json')
    
    if not results_file.exists():
        print(f"错误: 找不到结果文件 {results_file}")
        return None
    
    with open(results_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data

def plot_convergence_curves(data, output_dir='p01_p23_results_multi_runs/plots'):
    """绘制收敛曲线"""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # 为每个实例绘制收敛曲线
    for instance_name, instance_data in data.items():
        # 跳过非实例数据
        if not isinstance(instance_data, dict):
            continue
        
        plt.figure(figsize=(12, 8))
        
        # 绘制pure_ga和hybrid的收敛曲线
        for method in ['pure_ga', 'hybrid']:
            if method not in instance_data:
                continue
            
            method_data = instance_data[method]
            if 'convergence' not in method_data or not method_data['convergence']:
                continue
            
            convergence = method_data['convergence']
            generations = [point[0] for point in convergence]
            best_costs = [point[1] for point in convergence]
            
            label = 'Pure GA' if method == 'pure_ga' else 'Hybrid (GA+RL)'
            color = 'blue' if method == 'pure_ga' else 'red'
            plt.plot(generations, best_costs, linewidth=2, label=label, color=color, alpha=0.8)
        
        # 添加最优已知解的水平线
        if instance_name in BEST_KNOWN:
            plt.axhline(y=BEST_KNOWN[instance_name], color='g', 
                       linestyle='--', linewidth=2, label='Best Known', alpha=0.7)
        
        plt.xlabel('Generation', fontsize=12)
        plt.ylabel('Best Cost', fontsize=12)
        plt.title(f'{instance_name.upper()} Convergence Curves', fontsize=14, fontweight='bold')
        plt.legend(loc='upper right')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        # 保存图片
        plt.savefig(output_path / f'{instance_name}_convergence.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"已保存: {instance_name}_convergence.png")

def plot_summary_comparison(data, output_dir='p01_p23_results_multi_runs/plots'):
    """绘制汇总对比图"""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # 提取数据
    instances = []
    best_known = []
    pure_ga_costs = []
    hybrid_costs = []
    pure_ga_gaps = []
    hybrid_gaps = []
    
    for instance_name in sorted(data.keys()):
        if not isinstance(data[instance_name], dict):
            continue
        
        instance_data = data[instance_name]
        
        if 'pure_ga' not in instance_data and 'hybrid' not in instance_data:
            continue
        
        instances.append(instance_name.upper())
        bk = BEST_KNOWN.get(instance_name, 0)
        best_known.append(bk)
        
        # Pure GA数据
        if 'pure_ga' in instance_data:
            cost = instance_data['pure_ga']['total_cost']
            pure_ga_costs.append(cost)
            gap = ((cost - bk) / bk * 100) if bk > 0 else 0
            pure_ga_gaps.append(gap)
        else:
            pure_ga_costs.append(0)
            pure_ga_gaps.append(0)
        
        # Hybrid数据
        if 'hybrid' in instance_data:
            cost = instance_data['hybrid']['total_cost']
            hybrid_costs.append(cost)
            gap = ((cost - bk) / bk * 100) if bk > 0 else 0
            hybrid_gaps.append(gap)
        else:
            hybrid_costs.append(0)
            hybrid_gaps.append(0)
    
    # 1. 成本对比图
    fig, ax = plt.subplots(figsize=(16, 8))
    
    x = np.arange(len(instances))
    width = 0.25
    
    ax.bar(x - width, best_known, width, label='Best Known', color='green', alpha=0.7)
    ax.bar(x, pure_ga_costs, width, label='Pure GA', color='blue', alpha=0.7)
    ax.bar(x + width, hybrid_costs, width, label='Hybrid (GA+RL)', color='red', alpha=0.7)
    
    ax.set_xlabel('Instance', fontsize=12)
    ax.set_ylabel('Cost', fontsize=12)
    ax.set_title('Cost Comparison: Best Known vs Algorithm Results', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(instances, rotation=45, ha='right')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    
    plt.savefig(output_path / 'cost_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("已保存: cost_comparison.png")
    
    # 2. Gap百分比对比图
    fig, ax = plt.subplots(figsize=(16, 6))
    
    x = np.arange(len(instances))
    width = 0.35
    
    ax.bar(x - width/2, pure_ga_gaps, width, label='Pure GA', color='blue', alpha=0.7)
    ax.bar(x + width/2, hybrid_gaps, width, label='Hybrid (GA+RL)', color='red', alpha=0.7)
    
    ax.axhline(y=1, color='green', linestyle='--', linewidth=1, alpha=0.5, label='1% Gap')
    ax.axhline(y=5, color='orange', linestyle='--', linewidth=1, alpha=0.5, label='5% Gap')
    
    ax.set_xlabel('Instance', fontsize=12)
    ax.set_ylabel('Gap (%)', fontsize=12)
    ax.set_title('Gap from Best Known Solution', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(instances, rotation=45, ha='right')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    
    plt.savefig(output_path / 'gap_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("已保存: gap_comparison.png")
    
    # 3. 计算时间对比图
    pure_ga_times = []
    hybrid_times = []
    
    for instance_name in sorted(data.keys()):
        if not isinstance(data[instance_name], dict):
            continue
        
        instance_data = data[instance_name]
        
        if 'pure_ga' in instance_data:
            pure_ga_times.append(instance_data['pure_ga']['compute_time'])
        else:
            pure_ga_times.append(0)
        
        if 'hybrid' in instance_data:
            hybrid_times.append(instance_data['hybrid']['compute_time'])
        else:
            hybrid_times.append(0)
    
    fig, ax = plt.subplots(figsize=(16, 6))
    
    x = np.arange(len(instances))
    width = 0.35
    
    ax.bar(x - width/2, pure_ga_times, width, label='Pure GA', color='blue', alpha=0.7)
    ax.bar(x + width/2, hybrid_times, width, label='Hybrid (GA+RL)', color='red', alpha=0.7)
    
    ax.set_xlabel('Instance', fontsize=12)
    ax.set_ylabel('Compute Time (s)', fontsize=12)
    ax.set_title('Computation Time Comparison', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(instances, rotation=45, ha='right')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    
    plt.savefig(output_path / 'time_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("已保存: time_comparison.png")

def generate_statistics_table(data, output_dir='p01_p23_results_multi_runs'):
    """生成统计表格"""
    output_path = Path(output_dir)
    
    # 准备数据
    table_data = []
    
    for instance_name in sorted(data.keys()):
        if not isinstance(data[instance_name], dict):
            continue
        
        instance_data = data[instance_name]
        
        if 'pure_ga' not in instance_data and 'hybrid' not in instance_data:
            continue
        
        bk = BEST_KNOWN.get(instance_name, 0)
        
        row = {
            'Instance': instance_name.upper(),
            'Best Known': bk
        }
        
        # Pure GA数据
        if 'pure_ga' in instance_data:
            pure_ga = instance_data['pure_ga']
            row['Pure GA Cost'] = pure_ga['total_cost']
            row['Pure GA Gap (%)'] = ((pure_ga['total_cost'] - bk) / bk * 100) if bk > 0 else 0
            row['Pure GA Time (s)'] = pure_ga['compute_time']
        else:
            row['Pure GA Cost'] = 'N/A'
            row['Pure GA Gap (%)'] = 'N/A'
            row['Pure GA Time (s)'] = 'N/A'
        
        # Hybrid数据
        if 'hybrid' in instance_data:
            hybrid = instance_data['hybrid']
            row['Hybrid Cost'] = hybrid['total_cost']
            row['Hybrid Gap (%)'] = ((hybrid['total_cost'] - bk) / bk * 100) if bk > 0 else 0
            row['Hybrid Time (s)'] = hybrid['compute_time']
        else:
            row['Hybrid Cost'] = 'N/A'
            row['Hybrid Gap (%)'] = 'N/A'
            row['Hybrid Time (s)'] = 'N/A'
        
        table_data.append(row)
    
    # 创建DataFrame
    df = pd.DataFrame(table_data)
    
    # 保存为CSV
    csv_file = output_path / 'statistics_summary.csv'
    df.to_csv(csv_file, index=False, float_format='%.2f')
    print(f"\n已保存统计表格: {csv_file}")
    
    # 计算汇总统计
    pure_ga_gaps = [row['Pure GA Gap (%)'] for row in table_data if isinstance(row['Pure GA Gap (%)'], (int, float))]
    hybrid_gaps = [row['Hybrid Gap (%)'] for row in table_data if isinstance(row['Hybrid Gap (%)'], (int, float))]
    
    # 保存为Markdown
    md_file = output_path / 'statistics_summary.md'
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write("# P01-P23 测试结果统计\n\n")
        
        # 手动创建Markdown表格
        f.write("| Instance | Best Known | Pure GA Cost | Pure GA Gap (%) | Pure GA Time (s) | Hybrid Cost | Hybrid Gap (%) | Hybrid Time (s) |\n")
        f.write("|----------|------------|--------------|-----------------|------------------|-------------|----------------|------------------|\n")
        
        for row in table_data:
            f.write(f"| {row['Instance']} | ")
            f.write(f"{row['Best Known']:.2f} | " if isinstance(row['Best Known'], (int, float)) else f"{row['Best Known']} | ")
            f.write(f"{row['Pure GA Cost']:.2f} | " if isinstance(row['Pure GA Cost'], (int, float)) else f"{row['Pure GA Cost']} | ")
            f.write(f"{row['Pure GA Gap (%)']:.2f} | " if isinstance(row['Pure GA Gap (%)'], (int, float)) else f"{row['Pure GA Gap (%)']} | ")
            f.write(f"{row['Pure GA Time (s)']:.2f} | " if isinstance(row['Pure GA Time (s)'], (int, float)) else f"{row['Pure GA Time (s)']} | ")
            f.write(f"{row['Hybrid Cost']:.2f} | " if isinstance(row['Hybrid Cost'], (int, float)) else f"{row['Hybrid Cost']} | ")
            f.write(f"{row['Hybrid Gap (%)']:.2f} | " if isinstance(row['Hybrid Gap (%)'], (int, float)) else f"{row['Hybrid Gap (%)']} | ")
            f.write(f"{row['Hybrid Time (s)']:.2f} |\n" if isinstance(row['Hybrid Time (s)'], (int, float)) else f"{row['Hybrid Time (s)']} |\n")
        
        f.write("\n## 汇总统计\n\n")
        
        if pure_ga_gaps:
            f.write(f"### Pure GA\n")
            f.write(f"- 平均Gap: {np.mean(pure_ga_gaps):.2f}%\n")
            f.write(f"- 最小Gap: {np.min(pure_ga_gaps):.2f}%\n")
            f.write(f"- 最大Gap: {np.max(pure_ga_gaps):.2f}%\n")
            f.write(f"- Gap < 1%的实例数: {len([g for g in pure_ga_gaps if g < 1])}/{len(pure_ga_gaps)}\n")
            f.write(f"- Gap < 5%的实例数: {len([g for g in pure_ga_gaps if g < 5])}/{len(pure_ga_gaps)}\n\n")
        
        if hybrid_gaps:
            f.write(f"### Hybrid (GA+RL)\n")
            f.write(f"- 平均Gap: {np.mean(hybrid_gaps):.2f}%\n")
            f.write(f"- 最小Gap: {np.min(hybrid_gaps):.2f}%\n")
            f.write(f"- 最大Gap: {np.max(hybrid_gaps):.2f}%\n")
            f.write(f"- Gap < 1%的实例数: {len([g for g in hybrid_gaps if g < 1])}/{len(hybrid_gaps)}\n")
            f.write(f"- Gap < 5%的实例数: {len([g for g in hybrid_gaps if g < 5])}/{len(hybrid_gaps)}\n")
    
    print(f"已保存Markdown表格: {md_file}")
    
    # 打印到控制台
    print("\n" + "="*80)
    print("统计摘要")
    print("="*80)
    print(df.to_string(index=False, float_format=lambda x: f'{x:.2f}' if isinstance(x, float) else str(x)))
    print("\n" + "="*80)
    
    if pure_ga_gaps:
        print(f"Pure GA - 平均Gap: {np.mean(pure_ga_gaps):.2f}%")
        print(f"Pure GA - Gap < 5%的实例数: {len([g for g in pure_ga_gaps if g < 5])}/{len(pure_ga_gaps)}")
    
    if hybrid_gaps:
        print(f"Hybrid - 平均Gap: {np.mean(hybrid_gaps):.2f}%")
        print(f"Hybrid - Gap < 5%的实例数: {len([g for g in hybrid_gaps if g < 5])}/{len(hybrid_gaps)}")
    
    print("="*80)

def main():
    """主函数"""
    print("开始分析P01-P23测试结果...\n")
    
    # 加载结果
    data = load_results()
    if data is None:
        return
    
    print(f"加载了 {len([k for k in data.keys() if isinstance(data[k], dict)])} 个实例的结果\n")
    
    # 绘制收敛曲线
    print("正在绘制收敛曲线...")
    plot_convergence_curves(data)
    
    # 绘制汇总对比图
    print("\n正在绘制汇总对比图...")
    plot_summary_comparison(data)
    
    # 生成统计表格
    print("\n正在生成统计表格...")
    generate_statistics_table(data)
    
    print("\n所有图表和统计数据已生成完成！")
    print("结果保存在: p01_p23_results_multi_runs/")

if __name__ == '__main__':
    main()
