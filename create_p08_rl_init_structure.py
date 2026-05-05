"""
创建P08 RL初始化种群的结构示例
基于P21的格式,展示RL初始化后的解的结构
"""
import json
import numpy as np
from collections import defaultdict


def read_p08(file_path):
    """读取P08数据"""
    with open(file_path, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]
    
    parts = lines[0].split()
    n_vehicles, n_customers, n_depots = int(parts[1]), int(parts[2]), int(parts[3])
    
    print(f"P08: {n_customers} customers, {n_depots} depots, {n_vehicles} vehicles")
    
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
            'capacity': depots_info[len(depots)]['capacity']
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
    
    return depot_customers, depot_demands


def calculate_distance(c1, c2):
    """计算两点间距离"""
    return np.sqrt((c1['x'] - c2['x'])**2 + (c1['y'] - c2['y'])**2)


def create_greedy_routes(depot, customers, vehicle_capacity):
    """为一个depot创建贪心路线"""
    routes = []
    remaining = customers.copy()
    
    while remaining:
        route = []
        route_demand = 0
        current_pos = depot
        
        while remaining:
            # 找最近的可行客户
            best_customer = None
            best_dist = float('inf')
            
            for customer in remaining:
                if route_demand + customer['demand'] <= vehicle_capacity:
                    dist = calculate_distance(current_pos, customer)
                    if dist < best_dist:
                        best_dist = dist
                        best_customer = customer
            
            if best_customer is None:
                break
            
            route.append(best_customer['id'])
            route_demand += best_customer['demand']
            current_pos = best_customer
            remaining.remove(best_customer)
        
        if route:
            routes.append({
                'route': route,
                'demand': int(route_demand),
                'distance': 0.0  # 将由GA重新计算
            })
    
    return routes


def main():
    print("="*70)
    print("P08 RL初始化种群结构生成器")
    print("="*70)
    
    # 读取P08
    print(f"\n步骤1: 读取P08数据")
    data = read_p08("MDVRP-Instances/dat/p08")
    
    # 贪心分配
    print(f"\n步骤2: 贪心分配客户到depot")
    depot_customers, depot_demands = greedy_depot_assignment(data)
    
    print(f"\n分配结果:")
    for depot_idx in range(len(data['depots'])):
        n_cust = len(depot_customers[depot_idx])
        total_demand = depot_demands[depot_idx]
        vehicle_cap = data['depots'][depot_idx]['capacity']
        min_vehicles = int(np.ceil(total_demand / vehicle_cap))
        print(f"  Depot {depot_idx+1}: {n_cust} customers, demand={total_demand:.0f}, "
              f"capacity={vehicle_cap:.0f}, min_vehicles={min_vehicles}")
    
    # 创建20个解(使用贪心+随机扰动模拟RL的多样性)
    print(f"\n步骤3: 创建20个初始解")
    population = []
    
    np.random.seed(42)
    
    for i in range(20):
        chromosome = {}
        
        for depot_idx in range(len(data['depots'])):
            depot = data['depots'][depot_idx]
            customers = depot_customers[depot_idx].copy()
            
            # 随机打乱客户顺序(模拟RL的不同采样)
            np.random.shuffle(customers)
            
            # 创建贪心路线
            routes = create_greedy_routes(depot, customers, depot['capacity'])
            
            # depot_id使用1-indexed (与GA-MDVRP一致)
            chromosome[str(depot_idx + 1)] = routes
        
        population.append({
            'chromosome': chromosome,
            'fitness': 0.0,  # 将由GA评估
            'isFeasible': True
        })
    
    # 保存为JSON
    print(f"\n步骤4: 保存结果")
    output_file = "RL4CO_Integration/p08_ga_initial_population.json"
    with open(output_file, 'w') as f:
        json.dump({'population': population}, f, indent=2)
    
    print(f"\n[OK] 保存到: {output_file}")
    
    # 显示第一个解的结构
    print(f"\n{'='*70}")
    print(f"第一个解的结构示例:")
    print(f"{'='*70}")
    first_solution = population[0]
    for depot_id, routes in sorted(first_solution['chromosome'].items()):
        print(f"\nDepot {depot_id}:")
        print(f"  路线数: {len(routes)}")
        for i, route in enumerate(routes[:3]):  # 只显示前3条路线
            print(f"  Route {i+1}: {len(route['route'])} customers, demand={route['demand']}")
            print(f"    Customers: {route['route'][:10]}{'...' if len(route['route']) > 10 else ''}")
    
    print(f"\n{'='*70}")
    print(f"总共生成了 {len(population)} 个初始解")
    print(f"每个解包含 {len(data['depots'])} 个depot的路线规划")
    print(f"{'='*70}")
    
    print(f"\n注意: 这些解使用贪心算法生成,仅用于展示结构")
    print(f"真实的RL初始化需要运行RouteFinder模型")
    print(f"要生成真实的RL解,需要:")
    print(f"  1. 激活虚拟环境: .venv\\Scripts\\activate")
    print(f"  2. 运行: python RL4CO_Integration/generate_p08_rl_seeds.py")


if __name__ == "__main__":
    main()
