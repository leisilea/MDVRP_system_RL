#!/usr/bin/env python3
"""
绘制P08收敛曲线对比图（中文版）
对比纯GA和混合GA（RL初始化）的收敛过程
"""

import json
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
from pathlib import Path

# 设置中文字体
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.use('Agg')  # 使用非交互式后端


def plot_p08_convergence_comparison():
    """绘制P08收敛曲线对比图"""
    
    # 读取数据
    data_file = Path('system_test/algorithm-service/solver/p08_detailed_results/p08_detailed_results.json')
    
    if not data_file.exists():
        print(f"错误: 找不到数据文件 {data_file}")
        return
    
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("="*70)
    print("绘制P08收敛曲线对比图（中文版）")
    print("="*70)
    print()
    
    # 提取纯GA数据
    pure_ga_runs = data.get('pure_ga_runs', [])
    hybrid_ga_runs = data.get('hybrid_ga_runs', [])
    
    if not pure_ga_runs or not hybrid_ga_runs:
        print("错误: 数据文件中缺少必要的运行数据")
        return
    
    # 计算平均收敛曲线
    def calculate_average_convergence(runs):
        """计算多次运行的平均收敛曲线"""
        all_convergence = []
        for run in runs:
            convergence = run.get('convergence', [])
            if convergence:
                all_convergence.append(convergence)
        
        if not all_convergence:
            return [], []
        
        # 假设所有运行的代数相同
        generations = [point[0] for point in all_convergence[0]]
        
        # 计算每一代的平均成本
        avg_costs = []
        for gen_idx in range(len(generations)):
            costs_at_gen = [run[gen_idx][1] for run in all_convergence]
            avg_costs.append(np.mean(costs_at_gen))
        
        return generations, avg_costs
    
    pure_ga_gens, pure_ga_costs = calculate_average_convergence(pure_ga_runs)
    hybrid_ga_gens, hybrid_ga_costs = calculate_average_convergence(hybrid_ga_runs)
    
    if not pure_ga_gens or not hybrid_ga_gens:
        print("错误: 无法提取收敛数据")
        return
    
    # 创建图表
    plt.figure(figsize=(12, 7))
    
    # 绘制纯GA曲线
    plt.plot(pure_ga_gens, pure_ga_costs, 'b-o', 
             label='纯GA（随机初始化）', 
             linewidth=2, markersize=4, alpha=0.7, markevery=5)
    
    # 绘制混合GA曲线
    plt.plot(hybrid_ga_gens, hybrid_ga_costs, 'r-s', 
             label='混合GA（20% RL种子初始化）', 
             linewidth=2, markersize=4, alpha=0.7, markevery=5)
    
    # 添加BKS参考线
    bks = 4420.95
    plt.axhline(y=bks, color='g', linestyle='--', linewidth=2, 
                label=f'BKS = {bks:.2f}')
    
    # 设置标签和标题
    plt.xlabel('迭代代数', fontsize=13, fontweight='bold')
    plt.ylabel('最优成本', fontsize=13, fontweight='bold')
    plt.title('P08算例收敛曲线对比（纯GA vs 混合GA）', 
              fontsize=15, fontweight='bold', pad=15)
    
    # 设置图例
    plt.legend(fontsize=11, loc='upper right', framealpha=0.9)
    
    # 添加网格
    plt.grid(True, alpha=0.3, linestyle='--')
    
    # 设置坐标轴范围
    plt.xlim(left=0)
    plt.ylim(bottom=4000)
    
    # 调整布局
    plt.tight_layout()
    
    # 保存图表
    output_file = Path('system_test/algorithm-service/solver/p08_detailed_results/p08_convergence_comparison.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✓ 图表已保存: {output_file}")
    print()
    
    # 打印统计信息
    print("统计信息:")
    print(f"  纯GA:")
    print(f"    初始成本: {pure_ga_costs[0]:.2f}")
    print(f"    最终成本: {pure_ga_costs[-1]:.2f}")
    print(f"    改进率: {((pure_ga_costs[0] - pure_ga_costs[-1]) / pure_ga_costs[0] * 100):.2f}%")
    print(f"    与BKS差距: {((pure_ga_costs[-1] - bks) / bks * 100):.2f}%")
    print()
    print(f"  混合GA:")
    print(f"    初始成本: {hybrid_ga_costs[0]:.2f}")
    print(f"    最终成本: {hybrid_ga_costs[-1]:.2f}")
    print(f"    改进率: {((hybrid_ga_costs[0] - hybrid_ga_costs[-1]) / hybrid_ga_costs[0] * 100):.2f}%")
    print(f"    与BKS差距: {((hybrid_ga_costs[-1] - bks) / bks * 100):.2f}%")
    print()
    print(f"  混合GA优势:")
    final_advantage = ((pure_ga_costs[-1] - hybrid_ga_costs[-1]) / pure_ga_costs[-1] * 100)
    print(f"    最终解优势: {final_advantage:.2f}%")
    print()
    print("="*70)


if __name__ == '__main__':
    plot_p08_convergence_comparison()
