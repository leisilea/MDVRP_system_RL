#!/usr/bin/env python3
"""
测试RL模型对P08的初始化效果
生成20个RL解并评估成本
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'VPRL'))

import torch
import numpy as np
from pathlib import Path
import json

# 导入VPRL相关模块
from VPRL.vprl_sampler import VPRLSampler
from VPRL.mdvrp_instance import MDVRPInstance

def load_p08_instance():
    """加载P08算例"""
    p08_file = Path('MDVRP-Instances/dat/p08')
    
    with open(p08_file, 'r') as f:
        lines = f.readlines()
    
    # 解析第一行
    first_line = lines[0].strip().split()
    num_vehicles = int(first_line[0])
    num_customers = int(first_line[1])
    num_depots = int(first_line[2])
    
    print(f"P08算例信息:")
    print(f"  车辆数: {num_vehicles}")
    print(f"  客户数: {num_customers}")
    print(f"  仓库数: {num_depots}")
    print()
    
    # 解析客户数据
    customers = []
    for i in range(1, num_customers + 1):
        parts = lines[i].strip().split()
        customer = {
            'id': int(parts[0]),
            'x': float(parts[1]),
            'y': float(parts[2]),
            'service_duration': float(parts[3]),
            'demand': float(parts[4])
        }
        customers.append(customer)
    
    # 解析仓库数据
    depots = []
    for i in range(num_customers + 1, num_customers + num_depots + 1):
        parts = lines[i].strip().split()
        depot = {
            'id': int(parts[0]),
            'x': float(parts[1]),
            'y': float(parts[2]),
            'max_duration': float(parts[3]),
            'max_load': float(parts[4])
        }
        depots.append(depot)
    
    return {
        'num_vehicles': num_vehicles,
        'num_customers': num_customers,
        'num_depots': num_depots,
        'customers': customers,
        'depots': depots
    }


def calculate_solution_cost(solution, instance_data):
    """计算解的总成本"""
    depots = instance_data['depots']
    customers = instance_data['customers']
    
    # 构建坐标字典
    coords = {}
    for depot in depots:
        coords[depot['id']] = (depot['x'], depot['y'])
    for customer in customers:
        coords[customer['id']] = (customer['x'], customer['y'])
    
    def euclidean_distance(id1, id2):
        x1, y1 = coords[id1]
        x2, y2 = coords[id2]
        return np.sqrt((x1 - x2)**2 + (y1 - y2)**2)
    
    total_cost = 0.0
    
    for route_info in solution:
        depot_id = route_info['depotId']
        route = route_info['path']
        
        if not route:
            continue
        
        # 仓库到第一个客户
        cost = euclidean_distance(depot_id, route[0])
        
        # 客户之间
        for i in range(len(route) - 1):
            cost += euclidean_distance(route[i], route[i+1])
        
        # 最后一个客户回仓库
        cost += euclidean_distance(route[-1], depot_id)
        
        total_cost += cost
    
    return total_cost


def main():
    print("="*70)
    print("P08 RL初始化测试")
    print("="*70)
    print()
    
    # 加载P08算例
    instance_data = load_p08_instance()
    
    # 初始化VPRL采样器
    print("初始化VPRL采样器...")
    try:
        sampler = VPRLSampler(
            checkpoint_path='VPRL/checkpoints/mdvrp_model.pt',
            device='cuda' if torch.cuda.is_available() else 'cpu'
        )
        print(f"✓ 模型加载成功 (设备: {sampler.device})")
    except Exception as e:
        print(f"✗ 模型加载失败: {e}")
        print("\n尝试使用CPU...")
        try:
            sampler = VPRLSampler(
                checkpoint_path='VPRL/checkpoints/mdvrp_model.pt',
                device='cpu'
            )
            print("✓ 模型加载成功 (设备: CPU)")
        except Exception as e2:
            print(f"✗ CPU加载也失败: {e2}")
            return
    
    print()
    
    # 生成20个RL解
    num_samples = 20
    print(f"生成{num_samples}个RL解...")
    print()
    
    rl_costs = []
    rl_solutions = []
    
    for i in range(num_samples):
        try:
            # 使用VPRL生成解
            solution = sampler.sample_solution(instance_data)
            
            # 计算成本
            cost = calculate_solution_cost(solution, instance_data)
            rl_costs.append(cost)
            rl_solutions.append(solution)
            
            print(f"  解 {i+1:2d}: 成本 = {cost:.2f}")
            
        except Exception as e:
            print(f"  解 {i+1:2d}: 生成失败 - {e}")
    
    print()
    print("="*70)
    print("统计结果")
    print("="*70)
    
    if rl_costs:
        bks = 4420.9451
        
        min_cost = min(rl_costs)
        max_cost = max(rl_costs)
        avg_cost = np.mean(rl_costs)
        std_cost = np.std(rl_costs)
        
        print(f"BKS: {bks:.2f}")
        print()
        print(f"RL生成的{len(rl_costs)}个解:")
        print(f"  最小成本: {min_cost:.2f} (Gap: {((min_cost - bks) / bks * 100):.2f}%)")
        print(f"  最大成本: {max_cost:.2f} (Gap: {((max_cost - bks) / bks * 100):.2f}%)")
        print(f"  平均成本: {avg_cost:.2f} (Gap: {((avg_cost - bks) / bks * 100):.2f}%)")
        print(f"  标准差:   {std_cost:.2f}")
        print()
        
        # 与PSO混合初始化对比
        pso_initial = 5925.72
        print("与PSO混合初始化对比:")
        print(f"  PSO混合初始化: {pso_initial:.2f} (Gap: {((pso_initial - bks) / bks * 100):.2f}%)")
        print(f"  RL平均成本:     {avg_cost:.2f} (Gap: {((avg_cost - bks) / bks * 100):.2f}%)")
        
        if avg_cost < pso_initial:
            diff = pso_initial - avg_cost
            pct = (diff / pso_initial) * 100
            print(f"  ✓ RL更好: 比PSO低 {diff:.2f} ({pct:.2f}%)")
        else:
            diff = avg_cost - pso_initial
            pct = (diff / avg_cost) * 100
            print(f"  ✗ PSO更好: 比RL低 {diff:.2f} ({pct:.2f}%)")
        
        # 保存结果
        results = {
            'problem': 'p08',
            'bks': bks,
            'num_samples': len(rl_costs),
            'costs': rl_costs,
            'min_cost': float(min_cost),
            'max_cost': float(max_cost),
            'avg_cost': float(avg_cost),
            'std_cost': float(std_cost),
            'solutions': rl_solutions
        }
        
        output_file = 'p08_rl_initialization_results.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print()
        print(f"结果已保存到: {output_file}")
    else:
        print("没有成功生成任何解")


if __name__ == '__main__':
    main()
