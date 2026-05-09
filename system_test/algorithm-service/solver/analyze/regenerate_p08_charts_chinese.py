#!/usr/bin/env python3
"""
重新生成P08的所有图表（中文版）
包括：ACO收敛图和PSO的small/medium/large收敛图
"""

import json
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
from pathlib import Path

# 设置中文字体
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.use('Agg')


def plot_aco_convergence_chinese(data, output_dir):
    """绘制ACO收敛曲线（中文版）- 显示三次运行"""
    
    aco_data = data.get('aco', {})
    runs = aco_data.get('runs', [])
    
    if not runs:
        print("  [警告] 没有ACO运行数据")
        return
    
    # 创建图表
    plt.figure(figsize=(12, 7))
    
    # 定义颜色和标记
    colors = ['b', 'r', 'g']
    markers = ['o', 's', '^']
    
    # 绘制每次运行的最优成本曲线
    for idx, run in enumerate(runs[:3]):  # 只取前3次运行
        convergence = run.get('convergence', [])
        if not convergence:
            continue
        
        run_id = run.get('run_id', idx + 1)
        generations = [c['generation'] for c in convergence]
        best_costs = [c['best_cost'] for c in convergence]
        
        plt.plot(generations, best_costs, 
                color=colors[idx], marker=markers[idx],
                label=f'run{run_id}', 
                linewidth=2, markersize=4, alpha=0.8, markevery=5)
    
    # 添加BKS参考线
    bks = data.get('bks', 4420.95)
    plt.axhline(y=bks, color='g', linestyle='--', linewidth=2, 
                label=f'BKS = {bks:.2f}')
    
    # 设置标签和标题
    plt.xlabel('迭代次数', fontsize=13, fontweight='bold')
    plt.ylabel('成本', fontsize=13, fontweight='bold')
    plt.title('P08 - ACO算法收敛曲线', fontsize=15, fontweight='bold', pad=15)
    
    # 设置图例
    plt.legend(fontsize=11, loc='upper right', framealpha=0.9)
    
    # 添加网格
    plt.grid(True, alpha=0.3, linestyle='--')
    
    # 调整布局
    plt.tight_layout()
    
    # 保存图表
    output_file = output_dir / 'p08_aco_convergence.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"  ✓ ACO收敛图已保存: {output_file}")


def plot_pso_convergence_chinese(data, config_name, output_dir):
    """绘制PSO收敛曲线（中文版）- 显示三次运行"""
    
    pso_data = data.get('pso', {})
    config_data = pso_data.get(config_name, {})
    runs = config_data.get('runs', [])
    
    if not runs:
        print(f"  [警告] 没有PSO {config_name}配置的运行数据")
        return
    
    # 配置名称映射
    config_name_map = {
        'small': '小规模配置',
        'medium': '中等规模配置',
        'large': '大规模配置'
    }
    
    config_display = config_name_map.get(config_name, config_name)
    
    # 创建图表
    plt.figure(figsize=(12, 7))
    
    # 定义颜色和标记
    colors = ['b', 'r', 'g']
    markers = ['o', 's', '^']
    
    # 绘制每次运行的最优成本曲线
    for idx, run in enumerate(runs[:3]):  # 只取前3次运行
        convergence = run.get('convergence', [])
        if not convergence:
            continue
        
        run_id = run.get('run_id', idx + 1)
        generations = [c['generation'] for c in convergence]
        best_costs = [c['best_cost'] for c in convergence]
        
        plt.plot(generations, best_costs, 
                color=colors[idx], marker=markers[idx],
                label=f'run{run_id}', 
                linewidth=2, markersize=4, alpha=0.8, markevery=5)
    
    # 添加BKS参考线
    bks = data.get('bks', 4420.95)
    plt.axhline(y=bks, color='g', linestyle='--', linewidth=2, 
                label=f'BKS = {bks:.2f}')
    
    # 设置标签和标题
    plt.xlabel('迭代次数', fontsize=13, fontweight='bold')
    plt.ylabel('成本', fontsize=13, fontweight='bold')
    plt.title(f'P08 - PSO算法收敛曲线（{config_display}）', 
              fontsize=15, fontweight='bold', pad=15)
    
    # 设置图例
    plt.legend(fontsize=11, loc='upper right', framealpha=0.9)
    
    # 添加网格
    plt.grid(True, alpha=0.3, linestyle='--')
    
    # 调整布局
    plt.tight_layout()
    
    # 保存图表
    output_file = output_dir / f'p08_pso_{config_name}_convergence.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"  ✓ PSO {config_display}收敛图已保存: {output_file}")


def main():
    print("="*70)
    print("重新生成P08图表（中文版）")
    print("="*70)
    print()
    
    # 读取数据
    data_file = Path('system_test/algorithm-service/solver/aco_pso_p01_p23_results/p08/p08_results.json')
    
    if not data_file.exists():
        print(f"错误: 找不到数据文件 {data_file}")
        return
    
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    output_dir = data_file.parent
    
    print(f"数据文件: {data_file}")
    print(f"输出目录: {output_dir}")
    print()
    
    # 生成ACO收敛图
    print("生成ACO收敛图...")
    plot_aco_convergence_chinese(data, output_dir)
    print()
    
    # 生成PSO收敛图（三种配置）
    print("生成PSO收敛图...")
    for config in ['small', 'medium', 'large']:
        plot_pso_convergence_chinese(data, config, output_dir)
    
    print()
    print("="*70)
    print("所有图表已重新生成完成！")
    print("="*70)


if __name__ == '__main__':
    main()
