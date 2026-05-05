"""
P21 MDVRP求解器 - 容量感知贪心分配
使用容量感知的贪心策略：优先分配给负载较轻的depot
"""
import os
import sys
import json
import time
import torch
import numpy as np
from pathlib import Path
from collections import defaultdict
import heapq

sys.path.insert(0, str(Path(__file__).parent / "routefinder"))

from routefinder.envs import MTVRPEnv
from routefinder.models import RouteFinderBase

# TorchRL兼容性修复
import torchrl.data.tensor_specs as specs
if not hasattr(specs, 'CompositeSpec'):
    specs.CompositeSpec = specs.Composite
if not hasattr(specs, 'BoundedTensorSpec'):
    specs.BoundedTensorSpec = specs.Bounded
if not hasattr(specs, 'UnboundedContinuousTensorSpec'):
    specs.UnboundedContinuousTensorSpec = specs.UnboundedContinuous
if not hasattr(specs, 'UnboundedDiscreteTensorSpec'):
    specs.UnboundedDiscreteTensorSpec = specs.UnboundedDiscrete


def read_p21(file_path):
    """读取P21数据"""
    with open(file_path, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]
    
    parts = lines[0].split()
    n_vehicles, n_customers, n_depots = int(parts[1]), int(parts[2]), int(parts[3])
    
    print(f"P21: {n_customers} customers, {n_depots} depots, vehicle_capacity=60")
    
    # Depot信息
    depots_info = []
    for i in range(1, n_depots + 1):
        line = lines[i].split()
        depots_info.append({'capacity': float(line[1])})
    
    # 客户
    customers = []
    for i in range(n_depots + 1, n_depots + 1 + n_customers):
        line = lines[i].split()
        customers.append({
            'id': i - n_depots - 1,  # 0-indexed
            'x': float(line[1]),
            'y': float(line[2]),
            'demand': float(line[4])
        })
    
    # Depot坐标
    depots = []
    for i in range(n_depots + 1 + n_customers, n_depots + 1 + n_customers + n_depots):
        line = lines[i].split()
        depots.append({
            'id': len(depots),  # 0-indexed
            'x': float(line[1]),
            'y': float(line[2]),
            'capacity': depots_info[len(depots)]['capacity']  # 单车容量
        })
    
    return {'customers': customers, 'depots': depots}


def capacity_aware_greedy_split(data):
    """
    容量感知的贪心分配
    
    策略：
    1. 按距离排序所有客户到所有depot的距离
    2. 优先分配给负载较轻的depot（考虑容量利用率）
    3. 避免某个depot过载
    """
    customers = data['customers']
    depots = data['depots']
    
    depot_customers = defaultdict(list)
    depot_demands = defaultdict(float)
    
    # 计算每个客户到每个depot的距离
    customer_depot_distances = []
    for customer in customers:
        cx, cy = customer['x'], customer['y']
        for depot_idx, depot in enumerate(depots):
            dx, dy = depot['x'], depot['y']
            dist = np.sqrt((cx - dx)**2 + (cy - dy)**2)
            customer_depot_distances.append({
                'customer': customer,
                'depot_idx': depot_idx,
                'distance': dist
            })
    
    # 按距离排序
    customer_depot_distances.sort(key=lambda x: x['distance'])
    
    # 贪心分配：优先分配距离近且负载轻的depot
    assigned_customers = set()
    
    for item in customer_depot_distances:
        customer = item['customer']
        depot_idx = item['depot_idx']
        
        # 如果客户已分配，跳过
        if customer['id'] in assigned_customers:
            continue
        
        # 检查容量约束（软约束：允许超过但有惩罚）
        current_demand = depot_demands[depot_idx]
        vehicle_cap = depots[depot_idx]['capacity']
        
        # 计算当前depot的负载率
        current_load_ratio = current_demand / (vehicle_cap * 10)  # 假设最多10辆车
        
        # 如果负载率太高（>0.8），尝试找其他depot
        if current_load_ratio > 0.8:
            # 找到距离最近的3个depot
            nearby_depots = []
            for d_idx, depot in enumerate(depots):
                dx, dy = depot['x'], depot['y']
                dist = np.sqrt((customer['x'] - dx)**2 + (customer['y'] - dy)**2)
                load_ratio = depot_demands[d_idx] / (depot['capacity'] * 10)
                nearby_depots.append((d_idx, dist, load_ratio))
            
            # 按距离排序
            nearby_depots.sort(key=lambda x: x[1])
            
            # 选择负载最轻的前3个中的一个
            best_depot = None
            for d_idx, dist, load_ratio in nearby_depots[:3]:
                if load_ratio < 0.8:
                    best_depot = d_idx
                    break
            
            if best_depot is not None:
                depot_idx = best_depot
        
        # 分配客户
        depot_customers[depot_idx].append(customer)
        depot_demands[depot_idx] += customer['demand']
        assigned_customers.add(customer['id'])
    
    print(f"\n容量感知贪心分配:")
    for i in range(len(depots)):
        n_cust = len(depot_customers[i])
        total_demand = depot_demands[i]
        vehicle_cap = depots[i]['capacity']
        min_vehicles = int(np.ceil(total_demand / vehicle_cap))
        print(f"  Depot {i+1}: {n_cust} customers, demand={total_demand:.0f}, min_vehicles={min_vehicles}")
    
    return depot_customers


def create_npz_for_depot(depot, customers, depot_idx, output_dir):
    """创建单个depot的npz文件"""
    n = len(customers)
    if n == 0:
        return None
    
    # 归一化坐标
    all_x = [c['x'] for c in customers] + [depot['x']]
    all_y = [c['y'] for c in customers] + [depot['y']]
    x_min, x_max = min(all_x), max(all_x)
    y_min, y_max = min(all_y), max(all_y)
    x_range = max(x_max - x_min, 1)
    y_range = max(y_max - y_min, 1)
    
    # 构建locs: [1, n+1, 2]
    locs = np.zeros((1, n + 1, 2), dtype=np.float32)
    locs[0, 0, 0] = (depot['x'] - x_min) / x_range
    locs[0, 0, 1] = (depot['y'] - y_min) / y_range
    
    for i, c in enumerate(customers):
        locs[0, i + 1, 0] = (c['x'] - x_min) / x_range
        locs[0, i + 1, 1] = (c['y'] - y_min) / y_range
    
    # 构建demand_linehaul
    demands = np.array([c['demand'] for c in customers], dtype=np.float32).reshape(1, n)
    
    # 归一化
    max_demand = demands.max()
    if max_demand > 0:
        demands_normalized = demands / max_demand
        capacity_normalized = depot['capacity'] / max_demand
    else:
        demands_normalized = demands
        capacity_normalized = depot['capacity']
    
    vehicle_capacity = np.array([[capacity_normalized]], dtype=np.float32)
    speed = np.ones((1, 1), dtype=np.float32)
    num_depots = np.ones((1, 1), dtype=np.int32)
    
    npz_path = os.path.join(output_dir, f"depot_{depot_idx}.npz")
    np.savez(
        npz_path,
        locs=locs,
        demand_linehaul=demands_normalized,
        vehicle_capacity=vehicle_capacity,
        speed=speed,
        num_depots=num_depots
    )
    
    scale_factor = np.sqrt(x_range**2 + y_range**2)
    total_demand = demands.sum()
    min_vehicles = int(np.ceil(total_demand / depot['capacity']))
    
    return npz_path, scale_factor, min_vehicles


def sample_depot_solutions(env, policy, npz_path, device, num_samples=20):
    """对单个depot采样"""
    td_original = env.load_data(npz_path)
    td_original = td_original.to(device)
    
    solutions = []
    with torch.inference_mode():
        for i in range(num_samples):
            td = td_original.clone()
            td_reset = env.reset(td)
            out = policy(td_reset, env, phase="test", num_starts=1, return_actions=True, decode_type="sampling")
            
            cost = -out['reward'].item()
            actions = out['actions'].cpu()
            num_vehicles = (actions == 0).sum().item()
            
            solutions.append({
                'sample_idx': i,
                'cost': cost,
                'num_vehicles': num_vehicles,
                'actions': actions
            })
    
    solutions.sort(key=lambda x: x['cost'])
    return solutions


def main():
    print("="*70)
    print("P21 MDVRP求解器 - 容量感知贪心分配")
    print("="*70)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n设备: {device}")
    
    # 读取P21
    print(f"\n步骤1: 读取P21")
    data = read_p21("../MDVRP-Instances/dat/p21")
    
    # 容量感知贪心分配
    print(f"\n步骤2: 容量感知贪心分配")
    depot_customers = capacity_aware_greedy_split(data)
    
    # 创建npz文件
    print(f"\n步骤3: 创建npz文件")
    output_dir = "p21_npz_capacity_aware"
    os.makedirs(output_dir, exist_ok=True)
    
    npz_files = []
    for depot_idx in range(len(data['depots'])):
        customers = depot_customers[depot_idx]
        if len(customers) == 0:
            print(f"  [SKIP] Depot {depot_idx+1}: No customers assigned")
            continue
        depot = data['depots'][depot_idx]
        result = create_npz_for_depot(depot, customers, depot_idx, output_dir)
        if result:
            npz_path, scale_factor, min_vehicles = result
            npz_files.append((depot_idx, npz_path, len(customers), scale_factor, min_vehicles))
            print(f"  [OK] Depot {depot_idx+1}: {len(customers)} customers, min_vehicles={min_vehicles}")
    
    # 加载模型
    print(f"\n步骤4: 加载RouteFinder模型")
    model = RouteFinderBase.load_from_checkpoint(
        "routefinder/checkpoints/100/rf-transformer.ckpt",
        map_location="cpu",
        strict=False
    )
    policy = model.policy.to(device).eval()
    env = MTVRPEnv()
    print("[OK] Model loaded")
    
    # 采样
    print(f"\n步骤5: 采样求解")
    all_results = []
    total_start = time.time()
    
    for depot_idx, npz_path, n_customers, scale_factor, min_vehicles in npz_files:
        print(f"\nProcessing Depot {depot_idx+1} ({n_customers} customers, min_vehicles={min_vehicles})...")
        start = time.time()
        solutions = sample_depot_solutions(env, policy, npz_path, device, num_samples=20)
        elapsed = time.time() - start
        
        best_solution = solutions[0]
        best_cost_normalized = best_solution['cost']
        best_cost_real = best_cost_normalized * scale_factor
        best_num_vehicles = best_solution['num_vehicles']
        
        avg_cost_normalized = np.mean([s['cost'] for s in solutions])
        avg_cost_real = avg_cost_normalized * scale_factor
        avg_num_vehicles = np.mean([s['num_vehicles'] for s in solutions])
        
        result = {
            'depot_idx': depot_idx + 1,
            'n_customers': n_customers,
            'min_vehicles': min_vehicles,
            'best_cost_normalized': best_cost_normalized,
            'best_cost_real': best_cost_real,
            'best_num_vehicles': best_num_vehicles,
            'avg_cost_normalized': avg_cost_normalized,
            'avg_cost_real': avg_cost_real,
            'avg_num_vehicles': avg_num_vehicles,
            'scale_factor': scale_factor,
            'time': elapsed
        }
        all_results.append(result)
        
        print(f"  [OK] Best: cost={best_cost_real:.2f}, vehicles={best_num_vehicles}")
        print(f"       Avg: cost={avg_cost_real:.2f}, vehicles={avg_num_vehicles:.1f}, Time: {elapsed:.2f}s")
    
    total_elapsed = time.time() - total_start
    
    # 保存结果
    print(f"\n步骤6: 保存结果")
    os.makedirs("p21_solutions_capacity_aware", exist_ok=True)
    with open("p21_solutions_capacity_aware/results.json", 'w') as f:
        json.dump({
            'metadata': {'total_time': total_elapsed, 'device': str(device), 'method': 'capacity_aware_greedy'},
            'results': all_results
        }, f, indent=2)
    
    # 计算总成本
    total_cost_real = sum(r['best_cost_real'] for r in all_results)
    total_vehicles = sum(r['best_num_vehicles'] for r in all_results)
    
    # 读取BKS
    with open('../MDVRP-Instances/sol/p21.res', 'r') as f:
        bks = float(f.readline().strip())
    
    gap = ((total_cost_real - bks) / bks) * 100
    
    print(f"\n{'='*70}")
    print(f"总耗时: {total_elapsed:.2f}s")
    print(f"总成本 (真实距离): {total_cost_real:.2f}")
    print(f"总车辆数: {total_vehicles}")
    print(f"P21 BKS: {bks:.2f}")
    print(f"Gap: {gap:.2f}%")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
