#!/usr/bin/env python3
"""
生成GA vs Hybrid完整对比表格
从benchmark_results_multi_runs.json提取数据，生成包含所有P01-P23实例的对比表格
"""

import json
import pandas as pd
from pathlib import Path

# BKS值（已知最优解）
BEST_KNOWN = {
    'p01': 576.87, 'p02': 473.53, 'p03': 640.58, 'p04': 1001.59,
    'p05': 750.03, 'p06': 876.50, 'p07': 881.97, 'p08': 4437.68,
    'p09': 3873.89, 'p10': 3663.02, 'p11': 3554.18, 'p12': 1318.95,
    'p13': 1318.95, 'p14': 1360.12, 'p15': 2505.42, 'p16': 2572.23,
    'p17': 2709.09, 'p18': 3702.85, 'p19': 3827.06, 'p20': 4058.07,
    'p21': 5474.84, 'p22': 5702.16, 'p23': 6078.75
}

def load_benchmark_results():
    """加载benchmark结果"""
    json_file = Path('system_test/algorithm-service/solver/p01_p23_results_multi_runs/benchmark_results_multi_runs.json')
    with open(json_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_comparison_table():
    """创建GA vs Hybrid对比表格"""
    data = load_benchmark_results()
    
    table_rows = []
    
    for instance_name in sorted(BEST_KNOWN.keys()):
        if instance_name not in data:
            print(f"警告: {instance_name} 数据缺失")
            continue
        
        instance_data = data[instance_name]
        bks = BEST_KNOWN[instance_name]
        
        # 提取Pure GA数据
        pure_ga = instance_data.get('pure_ga', {})
        ga_cost = pure_ga.get('total_cost', None)
        ga_time = pure_ga.get('compute_time', None)
        ga_gap = ((ga_cost - bks) / bks * 100) if ga_cost else None
        
        # 提取Hybrid数据
        hybrid = instance_data.get('hybrid', {})
        hybrid_cost = hybrid.get('total_cost', None)
        hybrid_time = hybrid.get('compute_time', None)
        hybrid_gap = ((hybrid_cost - bks) / bks * 100) if hybrid_cost else None
        
        row = {
            'Instance': instance_name.upper(),
            'BKS': bks,
            'GA_Cost': ga_cost,
            'GA_Time': ga_time,
            'GA_Gap': ga_gap,
            'Hybrid_Cost': hybrid_cost,
            'Hybrid_Time': hybrid_time,
            'Hybrid_Gap': hybrid_gap
        }
        
        table_rows.append(row)
    
    # 创建DataFrame
    df = pd.DataFrame(table_rows)
    
    # 保存为CSV
    csv_file = 'GA_vs_Hybrid_Complete_Results.csv'
    df.to_csv(csv_file, index=False, float_format='%.2f')
    print(f"✓ 已保存CSV文件: {csv_file}")
    
    # 创建Markdown表格
    md_file = 'GA_vs_Hybrid_Complete_Results.md'
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write("# GA vs Hybrid 完整对比结果 (P01-P23)\n\n")
        f.write("## 数据说明\n\n")
        f.write("- **Instance**: 测试实例名称\n")
        f.write("- **BKS**: Best Known Solution（已知最优解）\n")
        f.write("- **GA_Cost**: 纯GA算法的平均成本（3次运行的平均值）\n")
        f.write("- **GA_Time**: 纯GA算法的平均运行时间（秒）\n")
        f.write("- **GA_Gap**: 纯GA与BKS的偏差百分比\n")
        f.write("- **Hybrid_Cost**: GA+RL混合算法的平均成本（3次运行的平均值）\n")
        f.write("- **Hybrid_Time**: GA+RL混合算法的平均运行时间（秒）\n")
        f.write("- **Hybrid_Gap**: Hybrid与BKS的偏差百分比\n\n")
        f.write("## 完整对比表格\n\n")
        
        # 写入表头
        f.write("| Instance | BKS | GA Cost | GA Time (s) | GA Gap (%) | Hybrid Cost | Hybrid Time (s) | Hybrid Gap (%) |\n")
        f.write("|----------|-----|---------|-------------|------------|-------------|-----------------|----------------|\n")
        
        # 写入数据行
        for _, row in df.iterrows():
            f.write(f"| {row['Instance']} | {row['BKS']:.2f} | {row['GA_Cost']:.2f} | {row['GA_Time']:.2f} | {row['GA_Gap']:.2f} | {row['Hybrid_Cost']:.2f} | {row['Hybrid_Time']:.2f} | {row['Hybrid_Gap']:.2f} |\n")
        
        # 添加汇总统计
        f.write("\n## 汇总统计\n\n")
        f.write(f"- **GA平均Gap**: {df['GA_Gap'].mean():.2f}%\n")
        f.write(f"- **Hybrid平均Gap**: {df['Hybrid_Gap'].mean():.2f}%\n")
        f.write(f"- **GA平均时间**: {df['GA_Time'].mean():.2f}秒\n")
        f.write(f"- **Hybrid平均时间**: {df['Hybrid_Time'].mean():.2f}秒\n")
        f.write(f"- **Hybrid相对GA的Gap改进**: {df['GA_Gap'].mean() - df['Hybrid_Gap'].mean():.2f}%\n")
        
        # 统计Hybrid优于GA的实例数
        hybrid_better = (df['Hybrid_Gap'] < df['GA_Gap']).sum()
        f.write(f"- **Hybrid优于GA的实例数**: {hybrid_better}/{len(df)} ({hybrid_better/len(df)*100:.1f}%)\n")
    
    print(f"✓ 已保存Markdown文件: {md_file}")
    
    # 打印预览
    print("\n表格预览（前5行）:")
    print(df.head().to_string(index=False))
    
    print(f"\n汇总统计:")
    print(f"  GA平均Gap: {df['GA_Gap'].mean():.2f}%")
    print(f"  Hybrid平均Gap: {df['Hybrid_Gap'].mean():.2f}%")
    print(f"  Hybrid相对GA的Gap改进: {df['GA_Gap'].mean() - df['Hybrid_Gap'].mean():.2f}%")
    print(f"  Hybrid优于GA的实例数: {hybrid_better}/{len(df)} ({hybrid_better/len(df)*100:.1f}%)")

if __name__ == '__main__':
    create_comparison_table()
