#!/usr/bin/env python3
"""
汇总PSO结果数据

从P01-P23的merged JSON文件中提取数据,生成汇总表格
"""

import json
from pathlib import Path
import statistics


def summarize_pso_results(results_dir):
    """
    汇总PSO结果
    
    Args:
        results_dir: 结果目录路径
    """
    results_dir = Path(results_dir)
    
    # 收集所有问题的数据
    summary_data = []
    
    for i in range(1, 24):
        problem = f"p{i:02d}"
        merged_file = results_dir / f"{problem}_pso_results_merged.json"
        
        if not merged_file.exists():
            print(f"警告: 文件不存在: {merged_file}")
            continue
        
        with open(merged_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        bks = data.get('bks', 0)
        
        # 为每个配置收集数据
        for config_name in ['small', 'medium', 'large']:
            if config_name not in data.get('runs', {}):
                continue
            
            runs = data['runs'][config_name]
            
            # 收集所有run的成本和时间
            costs = []
            times = []
            gaps = []
            
            for run in runs:
                cost = run.get('total_cost', 0)
                time = run.get('compute_time', 0)
                gap = run.get('gap', 0)
                
                costs.append(cost)
                times.append(time)
                gaps.append(gap)
            
            if costs:
                avg_cost = statistics.mean(costs)
                avg_time = statistics.mean(times)
                avg_gap = statistics.mean(gaps)
                
                summary_data.append({
                    'problem': problem.upper(),
                    'config': config_name,
                    'bks': bks,
                    'avg_cost': avg_cost,
                    'avg_time': avg_time,
                    'avg_gap': avg_gap,
                    'num_runs': len(costs)
                })
    
    return summary_data


def print_markdown_table(summary_data):
    """打印Markdown格式的表格"""
    
    print("\n# PSO算法结果汇总 (P01-P23)\n")
    print("## 按配置分组\n")
    
    for config in ['small', 'medium', 'large']:
        config_data = [d for d in summary_data if d['config'] == config]
        
        if not config_data:
            continue
        
        print(f"### {config.upper()}配置\n")
        print("| 问题 | BKS | 平均成本 | 平均时间(s) | 平均Gap(%) | 运行次数 |")
        print("|------|-----|----------|-------------|------------|----------|")
        
        for item in config_data:
            print(f"| {item['problem']} | {item['bks']:.2f} | "
                  f"{item['avg_cost']:.2f} | {item['avg_time']:.2f} | "
                  f"{item['avg_gap']:.2f} | {item['num_runs']} |")
        
        print()
    
    print("\n## 完整对比表\n")
    print("| 问题 | BKS | Small成本 | Small时间 | Small Gap | Medium成本 | Medium时间 | Medium Gap | Large成本 | Large时间 | Large Gap |")
    print("|------|-----|-----------|-----------|-----------|------------|------------|------------|-----------|-----------|-----------|")
    
    # 按问题分组
    problems = sorted(set(d['problem'] for d in summary_data))
    
    for problem in problems:
        problem_data = {d['config']: d for d in summary_data if d['problem'] == problem}
        
        bks = problem_data.get('small', problem_data.get('medium', problem_data.get('large', {})))['bks']
        
        row = f"| {problem} | {bks:.2f} |"
        
        for config in ['small', 'medium', 'large']:
            if config in problem_data:
                d = problem_data[config]
                row += f" {d['avg_cost']:.2f} | {d['avg_time']:.2f} | {d['avg_gap']:.2f} |"
            else:
                row += " - | - | - |"
        
        print(row)


def print_csv_table(summary_data):
    """打印CSV格式的表格"""
    
    print("\n\n# CSV格式\n")
    print("Problem,BKS,Config,Avg_Cost,Avg_Time,Avg_Gap,Num_Runs")
    
    for item in summary_data:
        print(f"{item['problem']},{item['bks']:.2f},{item['config']},"
              f"{item['avg_cost']:.2f},{item['avg_time']:.2f},"
              f"{item['avg_gap']:.2f},{item['num_runs']}")


def main():
    results_dir = Path('pso_p01_p23_results')
    
    if not results_dir.exists():
        print(f"错误: 目录不存在: {results_dir}")
        return
    
    print("正在汇总PSO结果...")
    summary_data = summarize_pso_results(results_dir)
    
    print(f"已收集 {len(summary_data)} 条数据记录")
    
    # 打印Markdown表格
    print_markdown_table(summary_data)
    
    # 打印CSV表格
    print_csv_table(summary_data)
    
    # 保存到文件
    output_file = results_dir / 'PSO_SUMMARY.md'
    with open(output_file, 'w', encoding='utf-8') as f:
        import sys
        from io import StringIO
        
        # 重定向stdout到StringIO
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        print_markdown_table(summary_data)
        print_csv_table(summary_data)
        
        content = sys.stdout.getvalue()
        sys.stdout = old_stdout
        
        f.write(content)
    
    print(f"\n\n汇总结果已保存到: {output_file}")


if __name__ == '__main__':
    main()
