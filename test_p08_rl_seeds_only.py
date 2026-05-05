#!/usr/bin/env python3
"""
测试P08的RL初始化效果
只生成RL种子并评估成本，不运行GA迭代
"""

import sys
import os
import json
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent / 'system_test' / 'ga_mdvrp_reproduction'))
sys.path.insert(0, str(Path(__file__).parent / 'RL4CO_Integration'))

print("="*70)
print("P08 RL初始化测试 - 仅评估RL生成的种子")
print("="*70)
print()

# 检查是否已有P08的RL种子文件
seed_file = Path('RL4CO_Integration/p08_ga_initial_population.json')

if seed_file.exists():
    print(f"✓ 找到现有的RL种子文件: {seed_file}")
    print()
    
    # 读取并分析
    with open(seed_file, 'r') as f:
        data = json.load(f)
    
    print(f"种子数量: {len(data)}")
    print()
    
    # 提取成本
    costs = []
    for i, seed in enumerate(data):
        if 'totalCost' in seed:
            cost = seed['totalCost']
            costs.append(cost)
            print(f"  种子 {i+1:2d}: 成本 = {cost:.2f}")
    
    if costs:
        import numpy as np
        
        bks = 4420.9451
        min_cost = min(costs)
        max_cost = max(costs)
        avg_cost = np.mean(costs)
        std_cost = np.std(costs)
        
        print()
        print("="*70)
        print("统计结果")
        print("="*70)
        print(f"BKS: {bks:.2f}")
        print()
        print(f"RL生成的{len(costs)}个种子:")
        print(f"  最小成本: {min_cost:.2f} (Gap: {((min_cost - bks) / bks * 100):.2f}%)")
        print(f"  最大成本: {max_cost:.2f} (Gap: {((max_cost - bks) / bks * 100):.2f}%)")
        print(f"  平均成本: {avg_cost:.2f} (Gap: {((avg_cost - bks) / bks * 100):.2f}%)")
        print(f"  标准差:   {std_cost:.2f}")
        print()
        
        # 与PSO对比
        pso_initial = 5925.72
        print("与PSO混合初始化对比:")
        print(f"  PSO混合初始化: {pso_initial:.2f} (Gap: {((pso_initial - bks) / bks * 100):.2f}%)")
        print(f"  RL平均成本:     {avg_cost:.2f} (Gap: {((avg_cost - bks) / bks * 100):.2f}%)")
        print()
        
        if avg_cost < pso_initial:
            diff = pso_initial - avg_cost
            pct = (diff / pso_initial) * 100
            print(f"  ✓ RL更好: 比PSO低 {diff:.2f} ({pct:.2f}%)")
        else:
            diff = avg_cost - pso_initial
            pct = (diff / avg_cost) * 100
            print(f"  ✗ PSO更好: 比RL低 {diff:.2f} ({pct:.2f}%)")
        
        print()
        print("="*70)
        print("关键发现")
        print("="*70)
        print()
        print("这解释了为什么GA第一代(gen 10)的平均成本是7188:")
        print()
        print(f"  RL种子平均成本: {avg_cost:.2f}")
        print(f"  纯随机种子成本: ~15000-16000")
        print(f"  混合后(20 RL + 80随机):")
        print(f"    预期平均 = 0.2 × {avg_cost:.2f} + 0.8 × 15500")
        print(f"             = {0.2 * avg_cost + 0.8 * 15500:.2f}")
        print()
        print("  但实际第一代平均成本是7188，说明:")
        print("  1. RL种子质量非常好")
        print("  2. 第一代GA已经进行了交叉变异")
        print("  3. 好的RL种子通过遗传操作影响了整个种群")
    
else:
    print(f"✗ 未找到RL种子文件: {seed_file}")
    print()
    print("需要先生成RL种子。运行以下命令:")
    print()
    print("  cd RL4CO_Integration")
    print("  python generate_solutions.py --problem p08 --num-samples 20")
    print()
    print("或者使用现有的P08 hybrid运行结果来反推RL种子质量")
