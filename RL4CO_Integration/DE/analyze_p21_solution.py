"""分析P21最优解"""

with open('../MDVRP-Instances/sol/p21.res', 'r') as f:
    lines = f.readlines()

total_cost = float(lines[0].strip())
print(f'Total Cost: {total_cost}')
print(f'\nDepot Analysis:')

depot_stats = {}
for line in lines[1:]:
    if line.strip():
        parts = line.strip().split()
        depot = int(parts[0])
        route = int(parts[1])
        cost = float(parts[2])
        load = int(parts[3])
        
        if depot not in depot_stats:
            depot_stats[depot] = {'routes': 0, 'total_cost': 0, 'customers': set(), 'max_load': 0}
        
        depot_stats[depot]['routes'] += 1
        depot_stats[depot]['total_cost'] += cost
        depot_stats[depot]['max_load'] = max(depot_stats[depot]['max_load'], load)
        
        # Count customers (exclude 0 which is depot)
        customers = [int(x) for x in parts[4:] if int(x) != 0]
        depot_stats[depot]['customers'].update(customers)

for depot in sorted(depot_stats.keys()):
    stats = depot_stats[depot]
    print(f'Depot {depot}: {stats["routes"]} routes, {len(stats["customers"])} customers, cost={stats["total_cost"]:.2f}, max_load={stats["max_load"]}')

print(f'\nTotal customers: {sum(len(s["customers"]) for s in depot_stats.values())}')
