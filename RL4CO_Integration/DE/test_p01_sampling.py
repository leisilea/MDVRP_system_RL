"""
使用RouteFinder预训练模型求解Cordeau p01实例 (Sampling方法)
生成多个解并选择最优
"""

import torch
import time
import sys
import os
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent / "routefinder"))

import numpy as np


def load_cordeau_p01():
    """加载Cordeau p01实例"""
    filepath = Path(__file__).parent.parent / 'MDVRP-Instances' / 'dat' / 'p01'
    
    with open(filepath, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]
    
    # 第1行: type m n t
    type_id, m, n, t = map(int, lines[0].split())
    print(f"实例信息: {n}客户, {t}仓库, {m}车辆/仓库")
    
    # 第2到t+1行: D Q (仓库约束)
    depots_info = []
    for i in range(1, t + 1):
        D, Q = map(float, lines[i].split())
        depots_info.append({'max_distance': D, 'capacity': Q})
    
    # 客户和仓库节点
    customers = []
    depots = []
    
    for i in range(t + 1, len(lines)):
        parts = lines[i].split()
        node_id = int(parts[0])
        x, y = float(parts[1]), float(parts[2])
        service_time = float(parts[3])
        demand = float(parts[4])
        
        node = {
            'id': node_id,
            'x': x,
            'y': y,
            'service_time': service_time,
            'demand': demand
        }
        
        # 最后t个是仓库
        if i >= len(lines) - t:
            depots.append(node)
        else:
            customers.append(node)
    
    return {
        'n_customers': n,
        'n_depots': t,
        'n_vehicles': m,
        'customers': customers,
        'depots': depots,
        'depots_info': depots_info,
    }


def euclidean_distance(x1, y1, x2, y2):
    """计算欧几里得距离"""
    return np.sqrt((x1 - x2)**2 + (y1 - y2)**2)


def assign_customers_to_depots(customers, depots):
    """将客户分配到最近的仓库"""
    assignments = {i: [] for i in range(len(depots))}
    
    for customer in customers:
        min_dist = float('inf')
        nearest_depot = 0
        
        for depot_idx, depot in enumerate(depots):
            dist = euclidean_distance(
                customer['x'], customer['y'],
                depot['x'], depot['y']
            )
            if dist < min_dist:
                min_dist = dist
                nearest_depot = depot_idx
        
        assignments[nearest_depot].append(customer)
    
    return assignments


def convert_to_routefinder_format(depot, customers):
    """转换为RouteFinder TensorDict格式"""
    from tensordict import TensorDict
    
    # 位置: [仓库, 客户1, 客户2, ...]
    locs = torch.tensor(
        [[depot['x'], depot['y']]] + 
        [[c['x'], c['y']] for c in customers],
        dtype=torch.float32
    )
    
    # 需求: [0, 需求1, 需求2, ...]
    demands = torch.tensor(
        [0.0] + [c['demand'] for c in customers],
        dtype=torch.float32
    )
    
    # 创建TensorDict
    td = TensorDict({
        'locs': locs.unsqueeze(0),  # [batch=1, n_nodes, 2]
        'demand': demands.unsqueeze(0),  # [batch=1, n_nodes]
    }, batch_size=[1])
    
    return td


def decode_solution(actions, customers, depot, depot_idx):
    """解码解为路径格式"""
    # actions: [batch, seq_len]
    actions = actions.squeeze(0).cpu().numpy()  # [seq_len]
    
    routes = []
    current_route = []
    
    for action in actions:
        if action == 0:  # 返回仓库
            if current_route:
                routes.append({
                    'depot_id': depot_idx + 1,  # 1-based
                    'customers': current_route.copy(),
                    'depot': depot,
                })
                current_route = []
        else:
            # action是客户索引(1-based in output)
            customer_idx = int(action) - 1
            if 0 <= customer_idx < len(customers):
                current_route.append(customers[customer_idx])
    
    # 最后一条路径
    if current_route:
        routes.append({
            'depot_id': depot_idx + 1,
            'customers': current_route.copy(),
            'depot': depot,
        })
    
    return routes


def calculate_route_cost(route):
    """计算单条路径的成本"""
    depot = route['depot']
    customers = route['customers']
    
    if not customers:
        return 0.0
    
    # 仓库 -> 第一个客户
    cost = euclidean_distance(
        depot['x'], depot['y'],
        customers[0]['x'], customers[0]['y']
    )
    
    # 客户之间
    for i in range(len(customers) - 1):
        cost += euclidean_distance(
            customers[i]['x'], customers[i]['y'],
            customers[i + 1]['x'], customers[i + 1]['y']
        )
    
    # 最后一个客户 -> 仓库
    cost += euclidean_distance(
        customers[-1]['x'], customers[-1]['y'],
        depot['x'], depot['y']
    )
    
    return cost


def solve_p01_with_sampling(n_samples=10):
    """使用RouteFinder求解p01 (Sampling方法)"""
    print("="*60)
    print(f"使用RouteFinder预训练模型求解Cordeau p01 (Sampling x{n_samples})")
    print("="*60)
    
    # 1. 加载p01实例
    print("\n[1/6] 加载p01实例...")
    instance = load_cordeau_p01()
    print(f"  ✓ 加载完成: {instance['n_customers']}客户, {instance['n_depots']}仓库")
    
    # 2. 加载RouteFinder模型
    print("\n[2/6] 加载RouteFinder预训练模型...")
    
    # 应用兼容性补丁
    try:
        # 先应用TorchRL补丁
        from torchrl.data.tensor_specs import Composite
        import torchrl.data.tensor_specs as specs
        if not hasattr(specs, 'CompositeSpec'):
            specs.CompositeSpec = Composite
            print("  ✓ TorchRL兼容性补丁已应用")
    except:
        pass
    
    try:
        # 应用checkpoint加载补丁
        sys.path.insert(0, str(Path(__file__).parent / "routefinder"))
        from fix_checkpoint_loader import CompatibilityUnpickler
        import torch.serialization
        import pickle
        
        # Monkey patch torch.load
        _original_load = torch.serialization._load
        
        def _patched_load(zip_file, map_location, pickle_module, **pickle_load_args):
            pickle_load_args['pickle_module'] = pickle
            pickle_load_args['Unpickler'] = CompatibilityUnpickler
            return _original_load(zip_file, map_location, pickle_module, **pickle_load_args)
        
        torch.serialization._load = _patched_load
        print("  ✓ Checkpoint兼容性补丁已应用")
    except Exception as e:
        print(f"  ⚠️  补丁应用失败: {e}")
    
    try:
        from routefinder.models import RouteFinderBase
        from routefinder.envs import MTVRPEnv
        
        # 创建环境
        env = MTVRPEnv(variant_preset="cvrp_50")
        
        # 加载预训练模型 (使用rf-pomo作为默认模型)
        checkpoint_path = Path(__file__).parent / "routefinder" / "checkpoints" / "50" / "rf-pomo.ckpt"
        
        if not checkpoint_path.exists():
            print(f"  ✗ 找不到checkpoint: {checkpoint_path}")
            print("  可用的checkpoints:")
            ckpt_dir = Path(__file__).parent / "routefinder" / "checkpoints" / "50"
            if ckpt_dir.exists():
                for f in ckpt_dir.glob("*.ckpt"):
                    print(f"    - {f.name}")
            return None
        
        model = RouteFinderBase.load_from_checkpoint(
            checkpoint_path,
            env=env,
            strict=False,
        )
        print(f"  ✓ 模型加载成功: {checkpoint_path}")
        
    except Exception as e:
        print(f"  ✗ 模型加载失败: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    model.eval()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)
    print(f"  ✓ 使用设备: {device}")
    
    # 3. 分配客户到仓库
    print("\n[3/6] 分配客户到最近的仓库...")
    assignments = assign_customers_to_depots(
        instance['customers'],
        instance['depots']
    )
    
    for depot_idx, customers in assignments.items():
        print(f"  仓库{depot_idx + 1}: {len(customers)}个客户")
    
    # 4. 为每个仓库求解CVRP (Sampling)
    print(f"\n[4/6] 为每个仓库求解CVRP (Sampling x{n_samples})...")
    
    best_solution = {
        'routes': [],
        'total_cost': float('inf'),
        'sample_costs': [],
    }
    
    total_solve_time = 0.0
    
    for sample_idx in range(n_samples):
        print(f"\n  === Sample {sample_idx + 1}/{n_samples} ===")
        
        all_routes = []
        total_cost = 0.0
        sample_start = time.time()
        
        for depot_idx, customers in assignments.items():
            if not customers:
                continue
            
            depot = instance['depots'][depot_idx]
            
            # 转换为RouteFinder格式
            td = convert_to_routefinder_format(depot, customers)
            td = td.to(device)
            
            # 求解 (sampling模式)
            with torch.no_grad():
                out = model(td, decode_type="sampling", return_actions=True)
            
            # 解码路径
            routes = decode_solution(
                out['actions'],
                customers,
                depot,
                depot_idx
            )
            
            # 计算成本
            depot_cost = sum(calculate_route_cost(r) for r in routes)
            total_cost += depot_cost
            
            all_routes.extend(routes)
        
        sample_time = time.time() - sample_start
        total_solve_time += sample_time
        
        print(f"    成本: {total_cost:.2f}, 时间: {sample_time:.3f}s")
        
        best_solution['sample_costs'].append(total_cost)
        
        # 更新最优解
        if total_cost < best_solution['total_cost']:
            best_solution['routes'] = all_routes
            best_solution['total_cost'] = total_cost
            print(f"    ✓ 新的最优解!")
    
    # 5. 统计采样结果
    print("\n[5/6] 采样统计")
    print("="*60)
    
    costs = best_solution['sample_costs']
    print(f"最优成本: {min(costs):.2f}")
    print(f"最差成本: {max(costs):.2f}")
    print(f"平均成本: {np.mean(costs):.2f}")
    print(f"标准差: {np.std(costs):.2f}")
    
    # 6. 最终结果
    print("\n[6/6] 最终结果")
    print("="*60)
    
    bks = 576.87  # p01的BKS
    gap = ((best_solution['total_cost'] - bks) / bks) * 100
    
    print(f"总路径数: {len(best_solution['routes'])}")
    print(f"最优成本: {best_solution['total_cost']:.2f}")
    print(f"BKS: {bks:.2f}")
    print(f"Gap: {gap:.2f}%")
    print(f"总求解时间: {total_solve_time:.3f}s")
    print(f"平均每样本: {total_solve_time / n_samples:.3f}s")
    
    if gap < 0:
        print("\n⚠️  警告: 负Gap! 可能的原因:")
        print("  - 距离计算方式不同")
        print("  - 路径解码错误")
    elif gap < 5:
        print("\n✓ 解质量优秀! (Gap < 5%)")
    elif gap < 10:
        print("\n✓ 解质量良好! (Gap < 10%)")
    elif gap < 20:
        print("\n⚠️  解质量一般 (10% < Gap < 20%)")
    else:
        print("\n✗ 解质量较差 (Gap > 20%)")
    
    print("="*60)
    
    return best_solution


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--samples', type=int, default=10, help='采样次数')
    args = parser.parse_args()
    
    try:
        results = solve_p01_with_sampling(n_samples=args.samples)
        
        if results is None:
            print("\n✗ 求解失败")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n✗ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
