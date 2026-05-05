"""
计算P08 RL初始化种群中每条路线的真实distance
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


def calculate_distance(x1, y1, x2, y2):
    """计算两点间的欧几里得距离"""
    return np.sqrt((x1 - x2)**2 + (y1 - y2)**2)


def calculate_route_distance(route, depot, customers):
    """
    计算一条路线的总距离
    
    Args:
        route: 客户ID列表 (0-indexed)
        depot: depot信息 {'x': ..., 'y': ...}
        customers: 客户信息字典 {customer_id: {'x': ..., 'y': ..., 'demand': ...}}
    
    Returns:
        总距离
    """
    if not route:
        return 0.0
    
    total_distance = 0.0
    
    # Depot -> 第一个客户
    first_customer = customers[route[0]]
    total_distance += calculate_distance(depot['x'], depot['y'], 
                                         first_customer['x'], first_customer['y'])
    
    # 客户之间
    for i in range(len(route) - 1):
        curr_customer = customers[route[i]]
        next_customer = customers[route[i + 1]]
        total_distance += calculate_distance(curr_customer['x'], curr_customer['y'],
                                             next_customer['x'], next_customer['y'])
    
    # 最后一个客户 -> Depot
    last_customer = customers[route[-1]]
    total_distance += calculate_distance(last_customer['x'], last_customer['y'],
                                         depot['x'], depot['y'])
    
    return total_distance


def main():
    print("="*70)
    print("计算P08 RL初始化种群的真实distance")
    print("="*70)
    
    # 读取P08数据
    print("\n步骤1: 读取P08数据")
    customers, depots = read_p08_data("../MDVRP-Instances/dat/p08")
    print(f"  客户数: {len(customers)}")
    print(f"  Depot数: {len(depots)}")
    
    # 读取RL初始化种群
    print("\n步骤2: 读取RL初始化种群")
    with open("p08_ga_initial_population.json", 'r') as f:
        data = json.load(f)
    
    population = data['population']
    print(f"  种群大小: {len(population)}")
    
    # 计算每条路线的distance
    print("\n步骤3: 计算每条路线的真实distance")
    
    for indiv_idx, individual in enumerate(population):
        chromosome = individual['chromosome']
        total_cost = 0.0
        
        for depot_id_str, routes in chromosome.items():
            depot_id = int(depot_id_str) - 1  # 转换为0-indexed
            depot = depots[depot_id]
            
            for route in routes:
                customer_ids = route['route']
                distance = calculate_route_distance(customer_ids, depot, customers)
                route['distance'] = round(distance, 2)
                total_cost += distance
        
        # 更新individual的fitness
        individual['fitness'] = round(total_cost, 2)
        
        if (indiv_idx + 1) % 5 == 0:
            print(f"  处理进度: {indiv_idx + 1}/{len(population)}")
    
    # 按fitness重新排序
    population.sort(key=lambda x: x['fitness'])
    
    # 保存更新后的数据
    print("\n步骤4: 保存更新后的数据")
    with open("p08_ga_initial_population.json", 'w') as f:
        json.dump(data, f, indent=2)
    
    print("  [OK] 已保存到 p08_ga_initial_population.json")
    
    # 统计
    costs = [p['fitness'] for p in population]
    print(f"\n{'='*70}")
    print(f"P08 RL初始化种群统计 (更新distance后)")
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
    
    # 显示第一个解的详细信息
    print(f"\n第一个解(最优)的详细信息:")
    print(f"总成本: {population[0]['fitness']:.2f}")
    for depot_id_str, routes in population[0]['chromosome'].items():
        print(f"\nDepot {depot_id_str}:")
        depot_total = sum(r['distance'] for r in routes)
        print(f"  路线数: {len(routes)}, 总距离: {depot_total:.2f}")
        for i, route in enumerate(routes[:3]):  # 只显示前3条
            print(f"  Route {i+1}: {len(route['route'])} customers, "
                  f"demand={route['demand']}, distance={route['distance']:.2f}")


if __name__ == "__main__":
    main()
