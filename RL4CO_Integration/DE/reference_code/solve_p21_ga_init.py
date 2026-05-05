"""
P21 MDVRP求解器 - GA初始化版本
使用GA-MDVRP的客户-depot分配，然后用RouteFinder优化每个depot的路线
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
from ga_mdvrp_java import GAMDVRPJava

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


def extract_depot_assignment_from_ga(ga_result, data):
    """
    从GA-MDVRP的结果中提取客户-depot分配
    
    Args:
        ga_result: GA-MDVRP的求解结果
        data: P21数据（包含customers和depots）
    
    Returns:
        depot_customers: {depot_id: [customer_list]}
    """
    depot_customers = defaultdict(list)
    depot_demands = defaultdict(float)
    
    # 从GA的routes中提取分配
    for route in ga_result['routes']:
        depot_id = route['depot_id']
        for customer_id in route['customers']:
            # customer_id是0-indexed
            customer = data['customers'][customer_id]
            depot_customers[depot_id].append(customer)
            depot_demands[depot_id] += customer['demand']
    
    print(f"\nGA-MDVRP分配结果:")
    for depot_id in sorted(depot_customers.keys()):
        n_cust = len(depot_customers[depot_id])
        total_demand = depot_demands[depot_id]
        vehicle_cap = data['depots'][depot_id]['capacity']
        min_vehicles = int(np.ceil(total_demand / vehicle_cap))
        print(f"  Depot {depot_id+1}: {n_cust} customers, demand={total_demand:.0f}, min_vehicles={min_vehicles}")
    
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
    print("P21 MDVRP求解器 - GA初始化版本")
    print("使用GA-MDVRP的分配 + RouteFinder优化")
    print("="*70)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n设备: {device}")
    
    # 读取P21
    print(f"\n步骤1: 读取P21")
    data = read_p21("../MDVRP-Instances/dat/p21")
    
    # 使用GA-MDVRP获取初始分配
    print(f"\n步骤2: 使用GA-MDVRP获取客户-depot分配")
    try:
        ga_solver = GAMDVRPJava()
        # 使用绝对路径
        p21_path = os.path.abspath("../MDVRP-Instances/dat/p21")
        print(f"  P21文件路径: {p21_path}")
        ga_result = ga_solver.solve(None, dataset_file=p21_path)
        
        print(f"\nGA-MDVRP结果:")
        print(f"  总成本: {ga_result['total_cost']:.2f}")
        print(f"  路径数: {ga_result['num_vehicles']}")
        print(f"  计算时间: {ga_result['compute_time']:.2f}秒")
        
        # 提取depot分配
        depot_customers = extract_depot_assignment_from_ga(ga_result, data)
        
    except Exception as e:
        print(f"\n[WARNING] GA-MDVRP执行失败: {e}")
        print(f"回退到贪心分配...")
        
        # 回退到贪心分配
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
        
        print(f"\n贪心分配（回退）:")
        for i in range(len(data['depots'])):
            n_cust = len(depot_customers[i])
            total_demand = depot_demands[i]
            vehicle_cap = data['depots'][i]['capacity']
            min_vehicles = int(np.ceil(total_demand / vehicle_cap))
            print(f"  Depot {i+1}: {n_cust} customers, demand={total_demand:.0f}, min_vehicles={min_vehicles}")
    
    # 创建npz文件
    print(f"\n步骤3: 创建npz文件")
    output_dir = "p21_npz_ga_init"
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
    
    # 采样
    print(f"\n步骤5: 使用RouteFinder优化每个depot的路线")
    all_results = []
    total_start = time.time()
    
    for depot_idx, npz_path, n_customers, scale_factor, min_vehicles in npz_files:
        print(f"\nProcessing Depot {depot_idx+1} ({n_customers} customers, min_vehicles={min_vehicles})...")
        start = time.time()
        solutions = sample_depot_solutions(env, policy, npz_path, device, num_samples=20)
        elapsed = time.time() - start
        
        # 还原真实成本
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
    os.makedirs("p21_solutions_ga_init", exist_ok=True)
    with open("p21_solutions_ga_init/results.json", 'w') as f:
        json.dump({
            'metadata': {
                'total_time': total_elapsed,
                'device': str(device),
                'method': 'ga_init_routefinder',
                'ga_cost': ga_result.get('total_cost', 0) if 'ga_result' in locals() else 0
            },
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
    print(f"总成本 (RouteFinder优化后): {total_cost_real:.2f}")
    if 'ga_result' in locals() and ga_result['total_cost'] > 0:
        print(f"总成本 (GA原始): {ga_result['total_cost']:.2f}")
        improvement = ((ga_result['total_cost'] - total_cost_real) / ga_result['total_cost']) * 100
        print(f"改进: {improvement:.2f}%")
    print(f"总车辆数: {total_vehicles}")
    print(f"P21 BKS: {bks:.2f}")
    print(f"Gap to BKS: {gap:.2f}%")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
