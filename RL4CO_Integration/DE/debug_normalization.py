"""
调试归一化和成本还原
检查是否在归一化/反归一化过程中出现问题
"""
import numpy as np
import torch
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "routefinder"))

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

from routefinder.envs import MTVRPEnv
from routefinder.models import RouteFinderBase


def read_p21():
    """读取P21数据"""
    with open("../MDVRP-Instances/dat/p21", 'r') as f:
        lines = [line.strip() for line in f if line.strip()]
    
    parts = lines[0].split()
    n_vehicles, n_customers, n_depots = int(parts[1]), int(parts[2]), int(parts[3])
    
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
            'x': float(line[1]),
            'y': float(line[2]),
            'demand': float(line[4])
        })
    
    # Depot坐标
    depots = []
    for i in range(n_depots + 1 + n_customers, n_depots + 1 + n_customers + n_depots):
        line = lines[i].split()
        depots.append({
            'x': float(line[1]),
            'y': float(line[2]),
            'capacity': depots_info[len(depots)]['capacity']
        })
    
    return {'customers': customers, 'depots': depots}


def test_single_depot():
    """测试单个depot的归一化和成本计算"""
    print("="*70)
    print("测试单个depot的归一化")
    print("="*70)
    
    data = read_p21()
    
    # 取第一个depot和前40个客户
    depot = data['depots'][0]
    customers = data['customers'][:40]
    
    print(f"\nDepot坐标: ({depot['x']}, {depot['y']})")
    print(f"客户数量: {len(customers)}")
    print(f"前3个客户坐标:")
    for i in range(3):
        print(f"  Customer {i}: ({customers[i]['x']}, {customers[i]['y']}) demand={customers[i]['demand']}")
    
    # 计算真实距离（手动）
    print(f"\n手动计算真实距离:")
    total_real_dist = 0
    # Depot -> Customer 0
    dist = np.sqrt((depot['x'] - customers[0]['x'])**2 + (depot['y'] - customers[0]['y'])**2)
    print(f"  Depot -> Customer 0: {dist:.2f}")
    total_real_dist += dist
    
    # Customer 0 -> Customer 1
    dist = np.sqrt((customers[0]['x'] - customers[1]['x'])**2 + (customers[0]['y'] - customers[1]['y'])**2)
    print(f"  Customer 0 -> Customer 1: {dist:.2f}")
    total_real_dist += dist
    
    # Customer 1 -> Depot
    dist = np.sqrt((customers[1]['x'] - depot['x'])**2 + (customers[1]['y'] - depot['y'])**2)
    print(f"  Customer 1 -> Depot: {dist:.2f}")
    total_real_dist += dist
    
    print(f"  简单路径总距离: {total_real_dist:.2f}")
    
    # 归一化
    print(f"\n归一化过程:")
    all_x = [c['x'] for c in customers] + [depot['x']]
    all_y = [c['y'] for c in customers] + [depot['y']]
    x_min, x_max = min(all_x), max(all_x)
    y_min, y_max = min(all_y), max(all_y)
    x_range = max(x_max - x_min, 1)
    y_range = max(y_max - y_min, 1)
    
    print(f"  X范围: [{x_min:.2f}, {x_max:.2f}], range={x_range:.2f}")
    print(f"  Y范围: [{y_min:.2f}, {y_max:.2f}], range={y_range:.2f}")
    
    # 归一化坐标
    depot_norm = {
        'x': (depot['x'] - x_min) / x_range,
        'y': (depot['y'] - y_min) / y_range
    }
    customers_norm = [
        {
            'x': (c['x'] - x_min) / x_range,
            'y': (c['y'] - y_min) / y_range
        }
        for c in customers
    ]
    
    print(f"  归一化后Depot: ({depot_norm['x']:.4f}, {depot_norm['y']:.4f})")
    print(f"  归一化后Customer 0: ({customers_norm[0]['x']:.4f}, {customers_norm[0]['y']:.4f})")
    
    # 计算归一化距离
    print(f"\n归一化距离:")
    total_norm_dist = 0
    # Depot -> Customer 0
    dist = np.sqrt((depot_norm['x'] - customers_norm[0]['x'])**2 + (depot_norm['y'] - customers_norm[0]['y'])**2)
    print(f"  Depot -> Customer 0: {dist:.4f}")
    total_norm_dist += dist
    
    # Customer 0 -> Customer 1
    dist = np.sqrt((customers_norm[0]['x'] - customers_norm[1]['x'])**2 + (customers_norm[0]['y'] - customers_norm[1]['y'])**2)
    print(f"  Customer 0 -> Customer 1: {dist:.4f}")
    total_norm_dist += dist
    
    # Customer 1 -> Depot
    dist = np.sqrt((customers_norm[1]['x'] - depot_norm['x'])**2 + (customers_norm[1]['y'] - depot_norm['y'])**2)
    print(f"  Customer 1 -> Depot: {dist:.4f}")
    total_norm_dist += dist
    
    print(f"  简单路径归一化总距离: {total_norm_dist:.4f}")
    
    # 还原
    scale_factor = np.sqrt(x_range**2 + y_range**2)
    restored_dist = total_norm_dist * scale_factor
    
    print(f"\n还原过程:")
    print(f"  Scale factor (对角线长度): {scale_factor:.2f}")
    print(f"  还原后距离: {total_norm_dist:.4f} * {scale_factor:.2f} = {restored_dist:.2f}")
    print(f"  真实距离: {total_real_dist:.2f}")
    print(f"  误差: {abs(restored_dist - total_real_dist):.2f}")
    
    # 检查：对角线长度是否是正确的scale factor
    print(f"\n验证scale factor:")
    print(f"  X range: {x_range:.2f}")
    print(f"  Y range: {y_range:.2f}")
    print(f"  对角线: sqrt({x_range:.2f}^2 + {y_range:.2f}^2) = {scale_factor:.2f}")
    
    # 更好的scale factor应该是什么？
    # 如果坐标归一化是 [0, 1]，那么距离的scale应该考虑实际的坐标范围
    print(f"\n尝试其他scale factor:")
    # 方法1：使用平均范围
    avg_range = (x_range + y_range) / 2
    print(f"  平均范围: {avg_range:.2f}, 还原距离: {total_norm_dist * avg_range:.2f}")
    
    # 方法2：使用最大范围
    max_range = max(x_range, y_range)
    print(f"  最大范围: {max_range:.2f}, 还原距离: {total_norm_dist * max_range:.2f}")


def test_routefinder_on_depot():
    """测试RouteFinder在单个depot上的表现"""
    print("\n" + "="*70)
    print("测试RouteFinder在单个depot上的表现")
    print("="*70)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # 加载模型
    model = RouteFinderBase.load_from_checkpoint(
        "routefinder/checkpoints/100/rf-transformer.ckpt",
        map_location="cpu",
        strict=False
    )
    policy = model.policy.to(device).eval()
    env = MTVRPEnv()
    
    # 加载npz
    npz_path = "p21_npz_fixed/depot_0.npz"
    td = env.load_data(npz_path)
    td = td.to(device)
    td_reset = env.reset(td)
    
    # 运行推理
    with torch.inference_mode():
        out = policy(td_reset, env, phase="test", num_starts=1, return_actions=True, decode_type="greedy")
    
    cost_normalized = -out['reward'].item()
    actions = out['actions'].cpu().numpy()[0]
    
    print(f"\nRouteFinder结果:")
    print(f"  归一化成本: {cost_normalized:.4f}")
    print(f"  Actions长度: {len(actions)}")
    print(f"  返回depot次数: {(actions == 0).sum()}")
    print(f"  前10个actions: {actions[:10]}")
    
    # 读取scale factor
    data = np.load(npz_path)
    locs = data['locs'][0]  # [n+1, 2]
    
    print(f"\nNPZ数据:")
    print(f"  locs shape: {locs.shape}")
    print(f"  Depot (归一化): {locs[0]}")
    print(f"  Customer 0 (归一化): {locs[1]}")
    
    # 从solve_p21_fixed.py的结果中获取scale_factor
    import json
    with open("p21_solutions_fixed/results.json", 'r') as f:
        results = json.load(f)
    
    depot_0_result = results['results'][0]
    scale_factor = depot_0_result['scale_factor']
    best_cost_real = depot_0_result['best_cost_real']
    
    print(f"\n从结果文件读取:")
    print(f"  Scale factor: {scale_factor:.2f}")
    print(f"  Best cost (real): {best_cost_real:.2f}")
    print(f"  Best cost (normalized): {depot_0_result['best_cost_normalized']:.4f}")
    
    # 验证还原
    restored_cost = cost_normalized * scale_factor
    print(f"\n验证还原:")
    print(f"  {cost_normalized:.4f} * {scale_factor:.2f} = {restored_cost:.2f}")


if __name__ == "__main__":
    test_single_depot()
    test_routefinder_on_depot()
