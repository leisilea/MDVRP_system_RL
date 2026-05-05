"""
使用RouteFinder生成P01的sampling解
基于官方test.py实现
"""

# TorchRL兼容性补丁
try:
    from torchrl.data.tensor_specs import Composite
    import torchrl.data.tensor_specs as specs
    if not hasattr(specs, 'CompositeSpec'):
        specs.CompositeSpec = Composite
        print("✓ TorchRL兼容性补丁已应用")
except:
    pass

import sys
import torch
import numpy as np
from pathlib import Path

# 添加routefinder到路径
sys.path.insert(0, str(Path(__file__).parent / "routefinder"))

from routefinder.envs import MTVRPEnv
from routefinder.models import RouteFinderBase
from tensordict import TensorDict


def load_p01():
    """加载P01数据"""
    filepath = Path(__file__).parent.parent / 'MDVRP-Instances' / 'dat' / 'p01'
    
    with open(filepath, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]
    
    # 解析第一行
    type_id, m, n, t = map(int, lines[0].split())
    
    # 解析仓库信息
    depots_info = []
    for i in range(1, t + 1):
        D, Q = map(float, lines[i].split())
        depots_info.append({'max_distance': D, 'capacity': Q})
    
    # 解析客户和仓库
    customers = []
    depots = []
    
    for i in range(t + 1, len(lines)):
        parts = lines[i].split()
        node_id = int(parts[0])
        x, y = float(parts[1]), float(parts[2])
        demand = float(parts[4])
        
        node = {'id': node_id, 'x': x, 'y': y, 'demand': demand}
        
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


def create_tensordict(depot, customers):
    """创建TensorDict格式的数据"""
    # 坐标: [仓库, 客户1, 客户2, ...]
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
    
    return TensorDict({
        'locs': locs.unsqueeze(0),
        'demand': demands.unsqueeze(0),
    }, batch_size=[1])


def decode_actions(actions, customers):
    """解码actions为路径"""
    actions = actions.squeeze(0).cpu().numpy()
    
    routes = []
    current_route = []
    
    for action in actions:
        if action == 0:  # 返回仓库
            if current_route:
                routes.append(current_route.copy())
                current_route = []
        else:
            customer_idx = int(action) - 1
            if 0 <= customer_idx < len(customers):
                current_route.append(customers[customer_idx])
    
    if current_route:
        routes.append(current_route)
    
    return routes


def calculate_cost(routes, depot):
    """计算总成本"""
    total_cost = 0.0
    
    for route in routes:
        if not route:
            continue
        
        # 仓库 -> 第一个客户
        cost = euclidean_distance(
            depot['x'], depot['y'],
            route[0]['x'], route[0]['y']
        )
        
        # 客户之间
        for i in range(len(route) - 1):
            cost += euclidean_distance(
                route[i]['x'], route[i]['y'],
                route[i + 1]['x'], route[i + 1]['y']
            )
        
        # 最后一个客户 -> 仓库
        cost += euclidean_distance(
            route[-1]['x'], route[-1]['y'],
            depot['x'], depot['y']
        )
        
        total_cost += cost
    
    return total_cost


def main():
    print("="*60)
    print("使用RouteFinder生成P01的Sampling解")
    print("="*60)
    
    # 1. 加载数据
    print("\n[1/5] 加载P01数据...")
    instance = load_p01()
    print(f"  ✓ {instance['n_customers']}客户, {instance['n_depots']}仓库")
    
    # 2. 加载模型
    print("\n[2/5] 加载RouteFinder模型...")
    
    # 创建环境
    env = MTVRPEnv()
    
    # 加载checkpoint
    checkpoint_path = Path(__file__).parent / "routefinder" / "checkpoints" / "50" / "rf-pomo.ckpt"
    
    if not checkpoint_path.exists():
        print(f"  ✗ 找不到checkpoint: {checkpoint_path}")
        return
    
    # PyTorch 2.6需要设置weights_only=False
    import warnings
    warnings.filterwarnings("ignore", category=FutureWarning)
    
    model = RouteFinderBase.load_from_checkpoint(
        checkpoint_path,
        map_location="cpu",
        strict=False,
        weights_only=False
    )
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    policy = model.policy.to(device).eval()
    print(f"  ✓ 模型加载成功, 设备: {device}")
    
    # 3. 分配客户到仓库
    print("\n[3/5] 分配客户到最近的仓库...")
    assignments = assign_customers_to_depots(
        instance['customers'],
        instance['depots']
    )
    
    for depot_idx, customers in assignments.items():
        print(f"  仓库{depot_idx + 1}: {len(customers)}个客户")
    
    # 4. Sampling求解
    print("\n[4/5] 使用Sampling方法求解...")
    n_samples = 10
    
    best_cost = float('inf')
    best_solution = None
    all_costs = []
    
    for sample_idx in range(n_samples):
        all_routes = []
        total_cost = 0.0
        
        for depot_idx, customers in assignments.items():
            if not customers:
                continue
            
            depot = instance['depots'][depot_idx]
            
            # 创建TensorDict
            td = create_tensordict(depot, customers)
            td = td.to(device)
            
            # Sampling求解
            with torch.no_grad():
                out = policy(td, env, phase="test", decode_type="sampling", return_actions=True)
            
            # 解码路径
            routes = decode_actions(out['actions'], customers)
            
            # 计算成本
            depot_cost = calculate_cost(routes, depot)
            total_cost += depot_cost
            
            all_routes.extend([(depot_idx + 1, route) for route in routes])
        
        all_costs.append(total_cost)
        
        if total_cost < best_cost:
            best_cost = total_cost
            best_solution = all_routes
            print(f"  Sample {sample_idx + 1}/{n_samples}: {total_cost:.2f} ✓ 新最优")
        else:
            print(f"  Sample {sample_idx + 1}/{n_samples}: {total_cost:.2f}")
    
    # 5. 结果统计
    print("\n[5/5] 结果统计")
    print("="*60)
    
    bks = 576.87
    gap = ((best_cost - bks) / bks) * 100
    
    print(f"最优成本: {best_cost:.2f}")
    print(f"最差成本: {max(all_costs):.2f}")
    print(f"平均成本: {np.mean(all_costs):.2f}")
    print(f"标准差: {np.std(all_costs):.2f}")
    print(f"BKS: {bks:.2f}")
    print(f"Gap: {gap:.2f}%")
    print(f"总路径数: {len(best_solution)}")
    
    # 打印最优解的路径
    print("\n最优解路径:")
    for depot_id, route in best_solution:
        customer_ids = [c['id'] for c in route]
        print(f"  仓库{depot_id}: {customer_ids}")
    
    print("="*60)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n✗ 执行失败: {e}")
        import traceback
        traceback.print_exc()
