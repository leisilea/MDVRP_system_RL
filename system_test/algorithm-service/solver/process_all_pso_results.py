#!/usr/bin/env python3
"""
批量处理所有PSO结果文件

1. 合并收敛数据
2. 绘制收敛曲线
"""

import json
import sys
from pathlib import Path
import subprocess


def process_pso_results(results_dir):
    """
    处理指定目录下的所有PSO结果文件
    
    Args:
        results_dir: 结果目录路径
    """
    results_dir = Path(results_dir)
    
    if not results_dir.exists():
        print(f"错误: 目录不存在: {results_dir}")
        return
    
    # 查找所有PSO结果文件（排除已合并的文件）
    pso_files = list(results_dir.glob('*_pso_results.json'))
    
    if not pso_files:
        print(f"未找到PSO结果文件: {results_dir}")
        return
    
    print(f"找到 {len(pso_files)} 个PSO结果文件")
    print()
    
    for pso_file in sorted(pso_files):
        print(f"{'='*80}")
        print(f"处理文件: {pso_file.name}")
        print(f"{'='*80}")
        
        # 1. 合并收敛数据
        merged_file = pso_file.parent / f"{pso_file.stem}_merged.json"
        
        print("\n步骤1: 合并收敛数据...")
        result = subprocess.run(
            ['python', 'merge_pso_convergence.py', str(pso_file), str(merged_file)],
            cwd=pso_file.parent.parent,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"  ✗ 合并失败: {result.stderr}")
            continue
        
        print(result.stdout)
        
        # 2. 绘制收敛曲线
        print("\n步骤2: 绘制收敛曲线...")
        result = subprocess.run(
            ['python', 'plot_pso_convergence.py', str(merged_file), str(pso_file.parent)],
            cwd=pso_file.parent.parent,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"  ✗ 绘图失败: {result.stderr}")
            continue
        
        print(result.stdout)
        print()
    
    print(f"{'='*80}")
    print("✓ 所有文件处理完成")
    print(f"{'='*80}")


def main():
    if len(sys.argv) < 2:
        print("用法: python process_all_pso_results.py <results_directory>")
        print("示例: python process_all_pso_results.py pso_p01_p23_results/")
        sys.exit(1)
    
    results_dir = sys.argv[1]
    process_pso_results(results_dir)


if __name__ == '__main__':
    main()
