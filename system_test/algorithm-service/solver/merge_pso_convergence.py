#!/usr/bin/env python3
"""
合并PSO分仓库收敛数据，生成整体收敛曲线

PSO算法对每个仓库独立运行，convergence数组中包含所有仓库的数据按顺序拼接。
本脚本将相同run_id和generation的数据合并，计算总成本。
"""

import json
import sys
from pathlib import Path
from collections import defaultdict


def merge_convergence_data(convergence_list, num_depots):
    """
    合并分仓库的收敛数据
    
    逻辑：
    1. convergence_list包含所有仓库的数据按顺序拼接
    2. 需要识别每个仓库的数据段（通过generation重新从0开始来判断）
    3. 按generation对齐，相同generation的best_cost和avg_cost分别相加
    4. 如果某仓库迭代次数少，用其最后一个值填充
    
    Args:
        convergence_list: 原始convergence数组（包含所有仓库的数据拼接）
        num_depots: 仓库数量
    
    Returns:
        merged_data: 合并后的收敛数据列表
    """
    if not convergence_list:
        return []
    
    # 步骤1: 分离每个仓库的数据
    # 当generation重新从0或小值开始时，说明是新仓库的数据
    depot_data = []
    current_depot = []
    prev_gen = -1
    
    for entry in convergence_list:
        gen = entry['generation']
        
        # 如果generation回退或重新开始，说明是新仓库
        if gen <= prev_gen and current_depot:
            depot_data.append(current_depot)
            current_depot = []
        
        current_depot.append(entry)
        prev_gen = gen
    
    # 添加最后一个仓库的数据
    if current_depot:
        depot_data.append(current_depot)
    
    print(f"    识别到 {len(depot_data)} 个仓库的收敛数据")
    for i, data in enumerate(depot_data):
        if data:
            print(f"      仓库{i+1}: {len(data)}个记录点, generation范围 {data[0]['generation']}-{data[-1]['generation']}")
    
    # 步骤2: 找出所有出现过的generation
    all_generations = set()
    for depot in depot_data:
        for entry in depot:
            all_generations.add(entry['generation'])
    
    all_generations = sorted(all_generations)
    
    # 步骤3: 为每个仓库创建generation到数据的映射，并记录停止点
    depot_gen_map = []
    depot_stop_gen = []  # 记录每个仓库实际停止的generation
    
    for depot in depot_data:
        gen_map = {}
        for entry in depot:
            gen_map[entry['generation']] = entry
        depot_gen_map.append(gen_map)
        
        # 记录该仓库的最后一个generation（实际停止点）
        if gen_map:
            depot_stop_gen.append(max(gen_map.keys()))
        else:
            depot_stop_gen.append(0)
    
    # 步骤4: 按generation合并
    merged_data = []
    for gen in all_generations:
        total_best_cost = 0.0
        total_avg_cost = 0.0
        active_depots = 0  # 统计在这个generation还在运行的仓库数
        
        for depot_idx, gen_map in enumerate(depot_gen_map):
            if gen in gen_map:
                # 该仓库有这个generation的数据（还在运行）
                total_best_cost += gen_map[gen]['best_cost']
                total_avg_cost += gen_map[gen]['avg_cost']
                active_depots += 1
            else:
                # 该仓库没有这个generation，使用其最后一个值（已停止）
                last_gen = max(gen_map.keys())
                total_best_cost += gen_map[last_gen]['best_cost']
                total_avg_cost += gen_map[last_gen]['avg_cost']
        
        merged_data.append({
            'generation': gen,
            'best_cost': total_best_cost,
            'avg_cost': total_avg_cost,
            'active_depots': active_depots  # 记录活跃仓库数
        })
    
    # 添加元数据：记录整体停止点（所有仓库都停止的generation）
    overall_stop_gen = min(depot_stop_gen) if depot_stop_gen else 0
    
    return merged_data, overall_stop_gen


def extend_convergence_to_max_gen(convergence, max_gen, stop_gen=None):
    """
    将收敛数据延续到最大generation
    
    Args:
        convergence: 合并后的收敛数据
        max_gen: 最大generation
        stop_gen: 实际停止的generation（可选）
    
    Returns:
        extended_convergence: 延续后的收敛数据
    """
    if not convergence:
        return convergence
    
    # 获取最后一个数据点
    last_entry = convergence[-1]
    last_gen = last_entry['generation']
    
    # 如果已经达到或超过max_gen，直接返回
    if last_gen >= max_gen:
        return convergence
    
    # 自动检测generation间隔
    if len(convergence) >= 2:
        interval = convergence[1]['generation'] - convergence[0]['generation']
    else:
        interval = 50  # 默认50代间隔
    
    # 延续到max_gen，使用停止时的最优成本
    extended = convergence.copy()
    current_gen = last_gen + interval
    
    while current_gen <= max_gen:
        extended.append({
            'generation': current_gen,
            'best_cost': last_entry['best_cost'],  # 使用停止时的最优成本
            'avg_cost': last_entry['avg_cost'],
            'active_depots': 0  # 标记为已停止
        })
        current_gen += interval
    
    return extended


def process_pso_results(input_file, output_file=None):
    """
    处理PSO结果文件，合并收敛数据
    
    Args:
        input_file: 输入JSON文件路径
        output_file: 输出JSON文件路径（可选，默认为input_file_merged.json）
    """
    # 读取原始数据
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    num_depots = data.get('num_depots', 4)
    problem = data.get('problem', 'unknown')
    
    print(f"处理问题: {problem}")
    print(f"仓库数量: {num_depots}")
    print(f"BKS: {data.get('bks', 'N/A')}")
    print()
    
    # 配置的最大迭代次数
    config_max_iterations = {
        'small': 350,
        'medium': 525,
        'large': 700
    }
    
    # 处理每个配置的每个run
    for config_name, runs in data.get('runs', {}).items():
        max_iterations = config_max_iterations.get(config_name, 350)
        print(f"配置: {config_name} ({len(runs)} runs, 最大迭代: {max_iterations})")
        
        for run in runs:
            run_id = run['run_id']
            original_convergence = run.get('convergence', [])
            
            if not original_convergence:
                print(f"  Run {run_id}: 无收敛数据")
                continue
            
            # 合并收敛数据（返回合并数据和停止点）
            merged_convergence, stop_gen = merge_convergence_data(original_convergence, num_depots)
            
            # 延续到最大generation
            extended_convergence = extend_convergence_to_max_gen(merged_convergence, max_iterations, stop_gen)
            
            # 添加合并后的数据到run中
            run['convergence_merged'] = extended_convergence
            run['convergence_original'] = original_convergence  # 保留原始数据
            run['stop_generation'] = stop_gen  # 记录停止点
            del run['convergence']  # 移除原始convergence字段
            
            print(f"  Run {run_id}: 合并 {len(original_convergence)} 条记录 -> {len(merged_convergence)} 个generation")
            print(f"    实际停止代数: {stop_gen}, 延续到 {max_iterations} 代 -> {len(extended_convergence)} 个数据点")
            print(f"    最终成本: {extended_convergence[-1]['best_cost']:.2f} (验证: {run['total_cost']:.2f})")
        
        print()
    
    # 保存结果
    if output_file is None:
        input_path = Path(input_file)
        output_file = input_path.parent / f"{input_path.stem}_merged{input_path.suffix}"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"✓ 合并结果已保存到: {output_file}")
    return output_file


def main():
    if len(sys.argv) < 2:
        print("用法: python merge_pso_convergence.py <input_json_file> [output_json_file]")
        print("示例: python merge_pso_convergence.py pso_p01_p23_results/p01_pso_results.json")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not Path(input_file).exists():
        print(f"错误: 文件不存在: {input_file}")
        sys.exit(1)
    
    process_pso_results(input_file, output_file)


if __name__ == '__main__':
    main()
