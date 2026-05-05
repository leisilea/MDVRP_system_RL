"""
P21 MDVRP求解器 - 贪心分配版本
使用贪心策略将客户分配到最近的depot
"""
import os
import sys
import json
import time
import torch
import numpy as np
from pathlib import Path
from collections import defaultdict

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
    
    print(f"P21: {n_customers} customers, {n_depots} depots")
    
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
            'id': i - n_depots,  # 客户ID从1开始
            'x': float(line[1]),
            'y': float(line[2]),
            'demand': float(line[4])
        })
    
    # Depot坐标
    depots = []
    for i in range(n_depots + 1 + n_customers, n_depots + 1 + n_customers + n_depots):
        line = lines[i].split()
        depots.append({
            'id': len(depots) + 1,  # Depot ID从1开始
            'x': float(line[1]),
            'y': float(line[2]),
            'capacity': depots_info[len(depots)]['capacity']
        })
    
    return {'customers': customers, 'depots': depots}


def greedy_assign(data):
    """贪心分配：每个客户分配到最近的depot"""
    customers = data['customers']
    depots = data['depots']
    
    depot_customers = defaultdict(list)
    depot_demands = {i: 0 for i in range(len(depots))}
    
    # 计算每个客户到每个depot的距离，分配到最近的depot
    for customer in customers:
        cx, cy = customer['x'], customer['y']
        min_dist = float('inf')
        best_depot = 0
        
        for depot_idx, depot in enumerate(depots):
            dx, dy = depot['x'], depot['y']
            dist = np.sqrt((cx - dx)**2 + (cy - dy)**2)
            
            if dist < min_dist:
                min_dist = dist
                best_depot = depot_idx
        
        depot_customers[best_depot].append(customer)
        depot_demands[best_depot] += customer['demand']
    
    print(f"\nGreedy Assignment:")
    for i in range(len(depots)):
        capacity = depots[i]['capacity']
        demand = depot_demands[i]
        utilization = (demand / capacity) * 100 if capacity > 0 else 0
        print(f"  Depot {i+1}: {len(depot_customers[i])} customers, demand={demand:.0f}/{capacity:.0f} ({utilization:.1f}%)")
    
    return depot_customers


def create_npz_for_depot(depot, customers, depot_idx, output_dir):
    """创建单个depot的npz文件（官方格式）"""
    n = len(customers)
    if n == 0:
        return None, None
    
    # 归一化坐标
    all_x = [c['x'] for c in customers] + [depot['x']]
    all_y = [c['y'] for c in customers] + [depot['y']]
    x_min, x_max = min(all_x), max(all_x)
    y_min, y_max = min(all_y), max(all_y)
    x_range = max(x_max - x_min, 1)
    y_range = max(y_max - y_min, 1)
    
    # 构建locs: [1, n+1, 2] - depot在第一个位置
    locs = np.zeros((1, n + 1, 2), dtype=np.float32)
    locs[0, 0, 0] = (depot['x'] - x_min) / x_range
    locs[0, 0, 1] = (depot['y'] - y_min) / y_range
    
    for i, c in enumerate(customers):
        locs[0, i + 1, 0] = (c['x'] - x_min) / x_range
        locs[0, i + 1, 1] = (c['y'] - y_min) / y_range
    
    # 构建demand_linehaul: [1, n] - 只有客户的需求
    demands = np.array([c['demand'] for c in customers], dtype=np.float32).reshape(1, n)
    
    # 归一化需求
    max_demand = demands.max()
    if max_demand > 0:
        demands = demands / max_demand
        capacity = depot['capacity'] / max_demand
    else:
        capacity = depot['capacity']
    
    # 其他字段
    vehicle_capacity = np.array([[capacity]], dtype=np.float32)
    speed = np.ones((1, 1), dtype=np.float32)
    num_depots = np.ones((1, 1), dtype=np.int32)
    
    # 保存npz
    npz_path = os.path.join(output_dir, f"depot_{depot_idx}.npz")
    np.savez(
        npz_path,
        locs=locs,
        demand_linehaul=demands,
        vehicle_capacity=vehicle_capacity,
        speed=speed,
        num_depots=num_depots
    )
    
    # 返回归一化信息用于还原真实成本
    scale_factor = np.sqrt(x_range**2 + y_range**2)  # 对角线长度作为缩放因子
    return npz_path, scale_factor


def sample_depot_solutions(env, policy, npz_path, device, num_samples=20):
    """对单个depot采样"""
    td_original = env.load_data(npz_path)
    td_original = td_original.to(device)
    
    solutions = []
    with torch.inference_mode():
        for i in range(num_samples):
            # 每次都从原始td创建一个新的副本
            td = td_original.clone()
            td_reset = env.reset(td)
            out = policy(td_reset, env, phase="test", num_starts=1, return_actions=True, decode_type="sampling")
            
            cost = -out['reward'].item()
            solutions.append({'sample_idx': i, 'cost': cost})
    
    solutions.sort(key=lambda x: x['cost'])
    return solutions


def main():
    print("="*70)
    print("P21 MDVRP求解器 - 贪心分配版本")
    print("="*70)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n设备: {device}")
    
    # 读取P21
    print(f"\n步骤1: 读取P21")
    data = read_p21("../MDVRP-Instances/dat/p21")
    
    # 贪心分配
    print(f"\n步骤2: 贪心分配")
    depot_customers = greedy_assign(data)
    
    # 创建npz文件
    print(f"\n步骤3: 创建npz文件")
    output_dir = "p21_npz_greedy"
    os.makedirs(output_dir, exist_ok=True)
    
    npz_files = []
    for depot_idx in range(len(data['depots'])):
        customers = depot_customers[depot_idx]
        if len(customers) == 0:
            print(f"  [SKIP] Depot {depot_idx+1}: No customers assigned")
            continue
        depot = data['depots'][depot_idx]
        result = create_npz_for_depot(depot, customers, depot_idx, output_dir)
        if result[0]:
            npz_path, scale_factor = result
            npz_files.append((depot_idx, npz_path, len(customers), scale_factor))
            print(f"  [OK] Depot {depot_idx+1}: {npz_path} (scale: {scale_factor:.2f})")
    
    # 加载模型
    print(f"\n步骤4: 加载模型")
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
    
    for depot_idx, npz_path, n_customers, scale_factor in npz_files:
        print(f"\nProcessing Depot {depot_idx+1} ({n_customers} customers)...")
        start = time.time()
        solutions = sample_depot_solutions(env, policy, npz_path, device, num_samples=20)
        elapsed = time.time() - start
        
        # 还原真实成本
        best_cost_normalized = solutions[0]['cost']
        best_cost_real = best_cost_normalized * scale_factor
        avg_cost_normalized = np.mean([s['cost'] for s in solutions])
        avg_cost_real = avg_cost_normalized * scale_factor
        
        result = {
            'depot_idx': depot_idx + 1,  # 1-based
            'n_customers': n_customers,
            'best_cost_normalized': best_cost_normalized,
            'best_cost_real': best_cost_real,
            'avg_cost_normalized': avg_cost_normalized,
            'avg_cost_real': avg_cost_real,
            'scale_factor': scale_factor,
            'solutions': solutions,
            'time': elapsed
        }
        all_results.append(result)
        
        print(f"  [OK] Best (normalized): {best_cost_normalized:.4f}, Best (real): {best_cost_real:.2f}")
        print(f"       Avg (normalized): {avg_cost_normalized:.4f}, Avg (real): {avg_cost_real:.2f}, Time: {elapsed:.2f}s")
    
    total_elapsed = time.time() - total_start
    
    # 保存结果
    print(f"\n步骤6: 保存结果")
    os.makedirs("p21_solutions_greedy", exist_ok=True)
    with open("p21_solutions_greedy/results.json", 'w') as f:
        json.dump({
            'metadata': {'total_time': total_elapsed, 'device': str(device), 'method': 'greedy'},
            'results': all_results
        }, f, indent=2)
    
    # 计算总成本
    total_cost_normalized = sum(r['best_cost_normalized'] for r in all_results)
    total_cost_real = sum(r['best_cost_real'] for r in all_results)
    
    # 读取BKS
    with open('../MDVRP-Instances/sol/p21.res', 'r') as f:
        bks = float(f.readline().strip())
    
    gap = ((total_cost_real - bks) / bks) * 100
    
    print(f"\n{'='*70}")
    print(f"总耗时: {total_elapsed:.2f}s")
    print(f"总成本 (归一化): {total_cost_normalized:.4f}")
    print(f"总成本 (真实距离): {total_cost_real:.2f}")
    print(f"P21 BKS: {bks:.2f}")
    print(f"Gap: {gap:.2f}%")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
