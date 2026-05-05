"""
将RouteFinder的采样解转换为GA-MDVRP Java能接受的格式
用于初始化GA种群，加快收敛
"""
import json
import numpy as np
from collections import defaultdict


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
    
    return {'customers': customers, 'depots': depots}


def get_depot_customer_mapping(data):
    """获取depot到客户的映射（贪心分配）"""
    customers = data['customers']
    depots = data['depots']
    
    depot_customers = defaultdict(list)
    customer_to_depot = {}  # customer_id -> depot_id
    
    # 贪心分配：每个客户分配到最近的depot
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
        customer_to_depot[customer['id']] = best_depot
    
    return depot_customers, customer_to_depot


def actions_to_routes(actions, depot_customers_list, data):
    """
    将RouteFinder的actions转换为路线列表
    
    Args:
        actions: RouteFinder输出的actions数组 [customer_ids...]，0表示返回depot
        depot_customers_list: 该depot的客户列表（按npz中的顺序）
        data: P21数据
    
    Returns:
        routes: List of routes, each route is a dict with 'customers', 'demand', 'distance'
    """
    routes = []
    current_route = []
    
    for action in actions:
        if action == 0:
            # 返回depot，结束当前路线
            if current_route:
                # 计算路线的需求和距离
                route_customers_global = [depot_customers_list[cid]['id'] + 1 for cid in current_route]  # +1转为1-indexed
                route_demand = sum(depot_customers_list[cid]['demand'] for cid in current_route)
                
                # 计算距离（简化：不计算实际距离，由GA重新计算）
                routes.append({
                    'route': route_customers_global,  # 全局客户ID（1-indexed for Java）
                    'demand': int(route_demand),
                    'distance': 0.0  # GA会重新计算
                })
                current_route = []
        else:
            # 添加客户到当前路线
            # action是npz中的索引（1-indexed，0是depot）
            customer_idx = action - 1  # 转换为depot_customers_list的索引
            current_route.append(customer_idx)
    
    # 处理最后一条路线（如果没有返回depot）
    if current_route:
        route_customers_global = [depot_customers_list[cid]['id'] + 1 for cid in current_route]  # +1转为1-indexed
        route_demand = sum(depot_customers_list[cid]['demand'] for cid in current_route)
        routes.append({
            'route': route_customers_global,
            'demand': int(route_demand),
            'distance': 0.0
        })
    
    return routes


def convert_solution_to_ga_format(results_data, data, depot_customers, num_solutions=10):
    """
    转换RouteFinder的解为GA-MDVRP格式
    
    GA-MDVRP Individual格式:
    {
        "chromosome": {
            "depot_id": [
                {
                    "route": [customer_ids...],  // 1-indexed
                    "demand": int,
                    "distance": double
                },
                ...
            ],
            ...
        },
        "fitness": double,
        "isFeasible": boolean
    }
    """
    ga_individuals = []
    
    # 为每个采样解创建一个Individual
    # 我们需要组合所有depot的最佳解
    for sol_idx in range(num_solutions):
        chromosome = {}
        total_cost = 0.0
        
        for depot_result in results_data['results']:
            depot_idx = depot_result['depot_idx'] - 1  # 转换为0-indexed
            depot_customers_list = depot_customers[depot_idx]
            
            # 获取该depot的第sol_idx个解
            if sol_idx < len(depot_result['solutions']):
                solution = depot_result['solutions'][sol_idx]
                actions = solution['actions']
                cost = solution['cost']
                
                # 转换actions为routes
                routes = actions_to_routes(actions, depot_customers_list, data)
                
                # 转换为GA格式（depot_id是1-indexed）
                chromosome[depot_idx + 1] = routes
                total_cost += cost * depot_result['scale_factor']
        
        # 创建Individual
        individual = {
            'chromosome': chromosome,
            'fitness': total_cost,
            'isFeasible': True  # RouteFinder的解都是可行的
        }
        ga_individuals.append(individual)
    
    return ga_individuals


def main():
    print("="*70)
    print("转换RouteFinder解为GA-MDVRP格式")
    print("="*70)
    
    # 读取P21数据
    print("\n步骤1: 读取P21数据")
    data = read_p21()
    print(f"  {len(data['customers'])} customers, {len(data['depots'])} depots")
    
    # 获取depot-customer映射
    print("\n步骤2: 获取depot-customer映射")
    depot_customers, customer_to_depot = get_depot_customer_mapping(data)
    for depot_idx in range(len(data['depots'])):
        print(f"  Depot {depot_idx+1}: {len(depot_customers[depot_idx])} customers")
    
    # 读取RouteFinder结果
    print("\n步骤3: 读取RouteFinder结果")
    with open("p21_solutions_fixed/results.json", 'r') as f:
        results_data = json.load(f)
    
    print(f"  找到 {len(results_data['results'])} 个depot的结果")
    
    # 转换为GA格式
    print("\n步骤4: 转换为GA格式")
    num_solutions = 20  # 导出前20个解作为初始种群（20% of population size 100）
    ga_individuals = convert_solution_to_ga_format(results_data, data, depot_customers, num_solutions)
    
    print(f"  生成 {len(ga_individuals)} 个Individual")
    print(f"  最佳fitness: {ga_individuals[0]['fitness']:.2f}")
    
    # 保存为JSON
    print("\n步骤5: 保存为JSON")
    output_data = {
        'population': ga_individuals,
        'metadata': {
            'source': 'RouteFinder',
            'problem': 'P21',
            'num_individuals': len(ga_individuals),
            'best_fitness': ga_individuals[0]['fitness']
        }
    }
    
    output_file = "p21_ga_initial_population.json"
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"  保存到: {output_file}")
    
    # 打印示例
    print("\n示例Individual结构:")
    print(f"  Depot数量: {len(ga_individuals[0]['chromosome'])}")
    for depot_id, routes in list(ga_individuals[0]['chromosome'].items())[:2]:
        print(f"  Depot {depot_id}: {len(routes)} routes")
        if routes:
            print(f"    Route 0: {len(routes[0]['route'])} customers, demand={routes[0]['demand']}")
    
    print(f"\n{'='*70}")
    print(f"转换完成！")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
