"""
分析RouteFinder报告的成本与真实欧几里得距离之间的差异
"""
import json
import numpy as np

def read_p08_data(file_path):
    """读取P08数据"""
    with open(file_path, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]
    
    parts = lines[0].split()
    n_vehicles, n_customers, n_depots = int(parts[1]), int(parts[2]), int(parts[3])
    
    # Depot信息
    depots_info = []
    for i in range(1, n_depots + 1):
        line = lines[i].split()
        depots_info.append({'capacity': float(line[1])})
    
    # 客户坐标和需求
    customers = {}
    for i in range(n_depots + 1, n_depots + 1 + n_customers):
        line = lines[i].split()
        customer_id = i - n_depots - 1  # 0-indexed
        customers[customer_id] = {
            'x': float(line[1]),
            'y': float(line[2]),
            'demand': float(line[4])
        }
    
    # Depot坐标
    depots = {}
    for i in range(n_depots + 1 + n_customers, n_depots + 1 + n_customers + n_depots):
        line = lines[i].split()
        depot_id = i - (n_depots + 1 + n_customers)  # 0-indexed
        depots[depot_id] = {
            'x': float(line[1]),
            'y': float(line[2]),
            'capacity': depots_info[depot_id]['capacity']
        }
    
    return customers, depots


def main():
    print("="*70)
    print("分析RouteFinder成本与真实欧几里得距离的差异")
    print("="*70)
    
    # 读取P08数据
    customers, depots = read_p08_data("../MDVRP-Instances/dat/p08")
    
    # 读取RL初始化种群
    with open("p08_ga_initial_population.json", 'r') as f:
        data = json.load(f)
    
    population = data['population']
    
    print(f"\n原始报告的成本 (来自generate_p08_rl_seeds.py):")
    print(f"  最优: 10500.12")
    print(f"  平均: 11988.46")
    
    print(f"\n真实欧几里得距离 (来自calculate_real_distances.py):")
    print(f"  最优: {population[0]['fitness']:.2f}")
    avg_cost = np.mean([p['fitness'] for p in population])
    print(f"  平均: {avg_cost:.2f}")
    
    ratio = population[0]['fitness'] / 10500.12
    print(f"\n比率: {ratio:.4f}")
    print(f"这意味着真实距离是RouteFinder报告成本的 {ratio:.2f} 倍")
    
    print(f"\n可能的原因:")
    print(f"1. RouteFinder使用的是归一化坐标空间的距离")
    print(f"2. scale_factor的计算可能不正确")
    print(f"3. RouteFinder可能使用了不同的距离度量")
    
    # 分析scale_factor
    print(f"\n分析scale_factor:")
    print(f"  generate_p08_rl_seeds.py使用: scale_factor = sqrt(x_range^2 + y_range^2)")
    
    # 计算每个depot的scale_factor
    for depot_idx in range(len(depots)):
        depot = depots[depot_idx]
        
        # 找到属于这个depot的客户
        depot_customers = []
        for cust_id, cust in customers.items():
            # 简单假设:根据距离判断
            dist_to_depot = np.sqrt((cust['x'] - depot['x'])**2 + (cust['y'] - depot['y'])**2)
            depot_customers.append((cust_id, dist_to_depot))
        
        # 取最近的一半客户作为这个depot的客户(粗略估计)
        depot_customers.sort(key=lambda x: x[1])
        n_customers_per_depot = len(customers) // len(depots)
        depot_customer_ids = [c[0] for c in depot_customers[:n_customers_per_depot]]
        
        # 计算坐标范围
        all_x = [customers[cid]['x'] for cid in depot_customer_ids] + [depot['x']]
        all_y = [customers[cid]['y'] for cid in depot_customer_ids] + [depot['y']]
        x_range = max(all_x) - min(all_x)
        y_range = max(all_y) - min(all_y)
        scale_factor = np.sqrt(x_range**2 + y_range**2)
        
        print(f"  Depot {depot_idx+1}: x_range={x_range:.2f}, y_range={y_range:.2f}, scale_factor={scale_factor:.2f}")
    
    print(f"\n结论:")
    print(f"RouteFinder报告的成本 (10500) 是在归一化坐标空间 (0-1) 中计算的,")
    print(f"然后乘以scale_factor得到的。但这个'还原'后的成本并不等于")
    print(f"真实坐标系中的欧几里得距离 ({population[0]['fitness']:.2f})。")
    print(f"\n这是因为:")
    print(f"1. 归一化时使用了 (coord - min) / range")
    print(f"2. 还原时只是乘以 sqrt(x_range^2 + y_range^2)")
    print(f"3. 但真实距离应该直接在原始坐标系中计算")
    
    print(f"\n{'='*70}")
    print(f"正确的做法:")
    print(f"{'='*70}")
    print(f"1. RouteFinder的成本只能用于比较不同解的相对质量")
    print(f"2. 要得到真实成本,必须在原始坐标系中重新计算距离")
    print(f"3. 因此,calculate_real_distances.py的结果 ({population[0]['fitness']:.2f}) 才是正确的")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
