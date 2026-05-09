"""
快速测试ACO和PSO - 在p01上运行
"""

import os
import sys
from multiprocessing import freeze_support

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    """主测试函数"""
    from run_aco_pso_experiments import run_aco_single, run_pso_single, plot_average_convergence
    
    # 测试p01
    instance_name = 'p01'

    print("="*60)
    print("快速测试: ACO和PSO在p01上运行")
    print("="*60)

    # 测试ACO
    print("\n测试ACO...")
    aco_results = []
    for i in range(3):
        result = run_aco_single(instance_name, i)
        aco_results.append(result)
        print(f"Run {i+1}: Cost={result['total_cost']:.2f}, Time={result['compute_time']:.2f}s")

    # 绘制ACO收敛图
    plot_average_convergence(aco_results, instance_name, 'ACO')

    # 测试PSO
    print("\n测试PSO...")
    pso_results = []
    for i in range(3):
        result = run_pso_single(instance_name, i, 'small')
        pso_results.append(result)
        print(f"Run {i+1}: Cost={result['total_cost']:.2f}, Time={result['compute_time']:.2f}s")

    # 绘制PSO收敛图
    plot_average_convergence(pso_results, instance_name, 'PSO')

    print("\n测试完成!")


if __name__ == '__main__':
    freeze_support()  # Windows多进程支持
    main()
