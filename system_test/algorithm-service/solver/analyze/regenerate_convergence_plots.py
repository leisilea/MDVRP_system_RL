"""
重新生成ACO和PSO的收敛图
从已有的结果JSON文件中读取数据并重新绘制收敛图
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# 结果目录
RESULTS_DIR = Path(__file__).parent / 'aco_pso_results'
RESULTS_FILE = RESULTS_DIR / 'all_results.json'

def plot_convergence(results, instance_name, algorithm):
    """绘制平均收敛曲线"""
    # 收集所有运行的收敛数据
    all_convergence = [r['convergence'] for r in results if r.get('convergence')]
    
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
    
    print(f"  ✓ 收敛图已保存: {output_path}")


def main():
    """主函数"""
    if not RESULTS_FILE.exists():
        print(f"错误: 结果文件不存在: {RESULTS_FILE}")
        print("请先运行 run_aco_pso_experiments.py 生成结果数据")
        return
    
    # 读取结果
    print(f"正在读取结果文件: {RESULTS_FILE}")
    with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
        all_results = json.load(f)
    
    print(f"\n{'='*60}")
    print("开始重新生成收敛图")
    print(f"{'='*60}\n")
    
    # 重新生成ACO收敛图
    print("处理ACO算法...")
    aco_count = 0
    for instance_name, data in sorted(all_results['ACO'].items()):
        print(f"  [{instance_name}] 生成收敛图...")
        plot_convergence(data['runs'], instance_name, 'ACO')
        aco_count += 1
    
    print(f"\n✓ ACO: 已生成 {aco_count} 个收敛图\n")
    
    # 重新生成PSO收敛图
    print("处理PSO算法...")
    pso_count = 0
    for instance_name, data in sorted(all_results['PSO'].items()):
        print(f"  [{instance_name}] 生成收敛图...")
        plot_convergence(data['runs'], instance_name, 'PSO')
        pso_count += 1
    
    print(f"\n✓ PSO: 已生成 {pso_count} 个收敛图\n")
    
    print(f"{'='*60}")
    print(f"完成! 共生成 {aco_count + pso_count} 个收敛图")
    print(f"保存位置: {RESULTS_DIR}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
