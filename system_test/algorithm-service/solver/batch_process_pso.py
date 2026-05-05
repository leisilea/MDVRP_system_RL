#!/usr/bin/env python3
"""
批量处理所有PSO结果文件

对P02-P23的所有PSO结果进行：
1. 合并收敛数据
2. 绘制收敛曲线
"""

import subprocess
import sys
from pathlib import Path


def process_all_pso_files(results_dir):
    """
    批量处理所有PSO结果文件
    
    Args:
        results_dir: 结果目录路径
    """
    results_dir = Path(results_dir)
    
    if not results_dir.exists():
        print(f"错误: 目录不存在: {results_dir}")
        return
    
    # 查找所有PSO结果文件（排除已合并的文件）
    pso_files = sorted([f for f in results_dir.glob('p*_pso_results.json') 
                       if not f.name.endswith('_merged.json')])
    
    if not pso_files:
        print(f"未找到PSO结果文件: {results_dir}")
        return
    
    print(f"找到 {len(pso_files)} 个PSO结果文件")
    print()
    
    success_count = 0
    failed_files = []
    
    for i, pso_file in enumerate(pso_files, 1):
        problem = pso_file.stem.replace('_pso_results', '')
        
        print(f"{'='*80}")
        print(f"[{i}/{len(pso_files)}] 处理: {problem.upper()}")
        print(f"{'='*80}")
        
        try:
            # 1. 合并收敛数据
            merged_file = pso_file.parent / f"{pso_file.stem}_merged.json"
            
            print(f"\n步骤1: 合并收敛数据...")
            result = subprocess.run(
                ['python', 'merge_pso_convergence.py', str(pso_file), str(merged_file)],
                cwd=pso_file.parent.parent,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                print(f"  ✗ 合并失败: {result.stderr}")
                failed_files.append((problem, "合并失败"))
                continue
            
            # 只显示关键信息
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if '处理问题' in line or 'BKS' in line or 'Run' in line or '✓' in line:
                    print(f"  {line}")
            
            # 2. 绘制收敛曲线
            print(f"\n步骤2: 绘制收敛曲线...")
            result = subprocess.run(
                ['python', 'plot_pso_convergence.py', str(merged_file), str(pso_file.parent)],
                cwd=pso_file.parent.parent,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                print(f"  ✗ 绘图失败: {result.stderr}")
                failed_files.append((problem, "绘图失败"))
                continue
            
            # 只显示关键信息
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if '✓' in line or '图表已保存' in line:
                    print(f"  {line}")
            
            print(f"\n✓ {problem.upper()} 处理完成")
            success_count += 1
            
        except subprocess.TimeoutExpired:
            print(f"  ✗ 处理超时")
            failed_files.append((problem, "超时"))
        except Exception as e:
            print(f"  ✗ 处理失败: {e}")
            failed_files.append((problem, str(e)))
        
        print()
    
    # 总结
    print(f"{'='*80}")
    print(f"批量处理完成")
    print(f"{'='*80}")
    print(f"成功: {success_count}/{len(pso_files)}")
    
    if failed_files:
        print(f"失败: {len(failed_files)}")
        for problem, reason in failed_files:
            print(f"  - {problem}: {reason}")
    else:
        print("所有文件处理成功！")
    
    print(f"{'='*80}")


def main():
    if len(sys.argv) < 2:
        print("用法: python batch_process_pso.py <results_directory>")
        print("示例: python batch_process_pso.py pso_p01_p23_results/")
        sys.exit(1)
    
    results_dir = sys.argv[1]
    process_all_pso_files(results_dir)


if __name__ == '__main__':
    main()
