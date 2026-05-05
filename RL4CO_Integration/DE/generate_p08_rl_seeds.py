"""
生成P08的RL初始化种群
参照P21的方法,使用RouteFinder生成20个解,然后评估它们的质量
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
sys.path.insert(0, str(Path(__file__).parent.parent / "system_test/algorithm-service/solver"))

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


def read_p08(file_path):
    """读取P08数据"""
    with open(file_path, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]
    
    parts = lines[0].split()
    n_vehicles, n_customers, n_depots = int(parts[1]), int(parts[2]), int(parts[3])
    
    print(f"P08: {n_customers} customers, {n_depots} depots")
    
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
    
    return {'customers': customers, 'depots': depots, 'n_vehicles': n_vehicles}


def greedy_depot_assignment(data):
    """贪心分配客户到depot"""
    depot_customers = defaultdict(list)
    depot_demands = defaultdict(float)
    
    for customer in data['customers']:
        cx, cy = customer['x'], customer['y']
        min_dist = float('inf')
        best_depot = 0
        
        for depot_idx, depot in enumerate(data['depots']):
            dx, dy = depot['x'], depot['y']
            dist = np.sqrt((cx - dx)**2 + (cy - dy)**2)
            
            if dist < min_dist:
                min_dist = dist
                best_depot = depot_idx
        
        depot_customers[best_depot].append(customer)
        depot_demands[best_depot] += customer['demand']
    
    print(f"\n贪心分配结果:")
    for i in range(len(data['depots'])):
        n_cust = len(depot_customers[i])
        total_demand = depot_demands[i]
        vehicle_cap = data['depots'][i]['capacity']
        min_vehicles = int(np.ceil(total_demand / vehicle_cap))
        print(f"  Depot {i+1}: {n_cust} customers, demand={total_demand:.0f}, min_vehicles={min_vehicles}")
    
    return depot_customers


def create_npz_for_depot(depot, customers, depot_idx, output_dir):
    """创建单个depot的npz文件（官方格式）"""
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
    
    # 构建locs: [1, n+1, 2] - depot在第一个位置
    locs = np.zeros((1, n + 1, 2), dtype=np.float32)
    locs[0, 0, 0] = (depot['x'] - x_min) / x_range
    locs[0, 0, 1] = (depot['y'] - y_min) / y_range
    
    for i, c in enumerate(customers):
        locs[0, i + 1, 0] = (c['x'] - x_min) / x_range
        locs[0, i + 1, 1] = (c['y'] - y_min) / y_range
    
    # 构建demand_linehaul: [1, n] - 只有客户的需求
    demands = np.array([c['demand'] for c in customers], dtype=np.float32).reshape(1, n)
    
    # 归一化需求和容量
    max_demand = demands.max()
    if max_demand > 0:
        demands_normalized = demands / max_demand
        capacity_normalized = depot['capacity'] / max_demand  # 单车容量归一化
    else:
        demands_normalized = demands
        capacity_normalized = depot['capacity']
    
    # 其他字段
    vehicle_capacity = np.array([[capacity_normalized]], dtype=np.float32)
    speed = np.ones((1, 1), dtype=np.float32)
    num_depots = np.ones((1, 1), dtype=np.int32)
    
    # 保存npz
    npz_path = os.path.join(output_dir, f"depot_{depot_idx}.npz")
    np.savez(
        npz_path,
        locs=locs,
        demand_linehaul=demands_normalized,
        vehicle_capacity=vehicle_capacity,
        speed=speed,
        num_depots=num_depots
    )
    
    # 返回归一化信息用于还原真实成本
    scale_factor = np.sqrt(x_range**2 + y_range**2)
    
    # 计算理论最少车辆数
    total_demand = demands.sum()
    min_vehicles = int(np.ceil(total_demand / depot['capacity']))
    
    return npz_path, scale_factor, min_vehicles, customers


def sample_depot_solutions(env, policy, npz_path, device, num_samples=20):
    """对单个depot采样多个解"""
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


def actions_to_routes(actions, customers):
    """
    将actions转换为routes格式
    
    Args:
        actions: RouteFinder的action序列 (1-indexed, 0表示返回depot)
        customers: 该depot的customer列表 (包含全局id)
    
    Returns:
        routes列表,其中route包含全局customer ID
    """
    routes = []
    current_route = []
    
    for action in actions.squeeze().tolist():
        if action == 0:  # 返回depot
            if current_route:
                # 计算route的demand
                demand = sum(customers[local_idx]['demand'] for local_idx in current_route)
                # 转换为全局customer ID
                global_route = [customers[local_idx]['id'] for local_idx in current_route]
                routes.append({
                    'route': global_route,
                    'demand': int(demand),
                    'distance': 0.0  # 将由GA重新计算
                })
                current_route = []
        else:
            # action是1-indexed,转换为0-indexed局部customer索引
            current_route.append(action - 1)
    
    # 处理最后一条route
    if current_route:
        demand = sum(customers[local_idx]['demand'] for local_idx in current_route)
        global_route = [customers[local_idx]['id'] for local_idx in current_route]
        routes.append({
            'route': global_route,
            'demand': int(demand),
            'distance': 0.0
        })
    
    return routes


def main():
    print("="*70)
    print("P08 RL初始化种群生成器")
    print("使用RouteFinder生成20个解")
    print("="*70)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n设备: {device}")
    print(f"CUDA可用: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA设备: {torch.cuda.get_device_name(0)}")
    
    # 读取P08
    print(f"\n步骤1: 读取P08数据")
    data = read_p08("../MDVRP-Instances/dat/p08")
    
    # 贪心分配
    print(f"\n步骤2: 贪心分配客户到depot")
    depot_customers = greedy_depot_assignment(data)
    
    # 创建npz文件
    print(f"\n步骤3: 创建npz文件")
    output_dir = "p08_npz_rl_init"
    os.makedirs(output_dir, exist_ok=True)
    
    npz_files = []
    depot_customer_mapping = {}  # 保存每个depot的customer列表
    for depot_idx in range(len(data['depots'])):
        customers = depot_customers[depot_idx]
        if len(customers) == 0:
            print(f"  [SKIP] Depot {depot_idx+1}: No customers assigned")
            continue
        depot = data['depots'][depot_idx]
        result = create_npz_for_depot(depot, customers, depot_idx, output_dir)
        if result:
            npz_path, scale_factor, min_vehicles, cust_list = result
            npz_files.append((depot_idx, npz_path, len(customers), scale_factor, min_vehicles))
            depot_customer_mapping[depot_idx] = cust_list
            print(f"  [OK] Depot {depot_idx+1}: {len(customers)} customers, min_vehicles={min_vehicles}")
    
    # 加载RouteFinder模型
    print(f"\n步骤4: 加载RouteFinder模型")
    model = RouteFinderBase.load_from_checkpoint(
        "routefinder/checkpoints/100/rf-transformer.ckpt",
        map_location="cpu",
        strict=False
    )
    policy = model.policy.to(device).eval()
    env = MTVRPEnv()
    print("[OK] Model loaded")
    
    # 采样20个解
    print(f"\n步骤5: 使用RouteFinder生成20个解")
    all_depot_solutions = {}  # {depot_idx: [solutions]}
    
    for depot_idx, npz_path, n_customers, scale_factor, min_vehicles in npz_files:
        print(f"\nProcessing Depot {depot_idx+1} ({n_customers} customers)...")
        start = time.time()
        solutions = sample_depot_solutions(env, policy, npz_path, device, num_samples=20)
        elapsed = time.time() - start
        
        # 还原真实成本
        for sol in solutions:
            sol['cost_real'] = sol['cost'] * scale_factor
        
        all_depot_solutions[depot_idx] = solutions
        
        best_cost = solutions[0]['cost_real']
        avg_cost = np.mean([s['cost_real'] for s in solutions])
        
        print(f"  [OK] Best: {best_cost:.2f}, Avg: {avg_cost:.2f}, Time: {elapsed:.2f}s")
    
    # 组合成20个完整解
    print(f"\n步骤6: 组合成20个完整解")
    population = []
    
    for i in range(20):
        # 为每个depot选择第i个解
        chromosome = {}
        total_cost = 0.0
        
        for depot_idx in sorted(all_depot_solutions.keys()):
            solutions = all_depot_solutions[depot_idx]
            sol = solutions[i % len(solutions)]  # 如果不足20个,循环使用
            
            # 转换actions为routes
            customers = depot_customer_mapping[depot_idx]
            routes = actions_to_routes(sol['actions'], customers)
            
            # depot_id使用1-indexed (与GA-MDVRP一致)
            chromosome[str(depot_idx + 1)] = routes
            total_cost += sol['cost_real']
        
        population.append({
            'chromosome': chromosome,
            'fitness': total_cost,
            'isFeasible': True
        })
    
    # 按fitness排序
    population.sort(key=lambda x: x['fitness'])
    
    # 保存为JSON
    print(f"\n步骤7: 保存结果")
    output_file = "p08_ga_initial_population.json"
    with open(output_file, 'w') as f:
        json.dump({'population': population}, f, indent=2)
    
    print(f"\n[OK] 保存到: {output_file}")
    
    # 统计
    costs = [p['fitness'] for p in population]
    print(f"\n{'='*70}")
    print(f"P08 RL初始化种群统计 (20个解)")
    print(f"{'='*70}")
    print(f"最优成本: {min(costs):.2f}")
    print(f"最差成本: {max(costs):.2f}")
    print(f"平均成本: {np.mean(costs):.2f}")
    print(f"标准差:   {np.std(costs):.2f}")
    
    # 读取BKS
    with open('../MDVRP-Instances/sol/p08.res', 'r') as f:
        bks = float(f.readline().strip())
    
    best_gap = ((min(costs) - bks) / bks) * 100
    avg_gap = ((np.mean(costs) - bks) / bks) * 100
    
    print(f"\nP08 BKS: {bks:.2f}")
    print(f"最优解Gap: {best_gap:.2f}%")
    print(f"平均Gap:   {avg_gap:.2f}%")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
