#!/usr/bin/env python3
"""
统计大规模实例P08-P11、P18-P20、P21-P23的Gap改进
"""

# 数据来源：GA_vs_Hybrid_Complete_Results.csv
data = {
    # P08-P11: 249客户，2-5仓库
    'P08': {'bks': 4437.68, 'ga_gap': 7.89, 'hybrid_gap': 5.70, 'customers': 249, 'depots': 2},
    'P09': {'bks': 3873.89, 'ga_gap': 8.11, 'hybrid_gap': 6.63, 'customers': 249, 'depots': 3},
    'P10': {'bks': 3663.02, 'ga_gap': 8.54, 'hybrid_gap': 6.54, 'customers': 249, 'depots': 4},
    'P11': {'bks': 3554.18, 'ga_gap': 12.17, 'hybrid_gap': 10.04, 'customers': 249, 'depots': 5},
    
    # P18-P20: 240客户，6仓库
    'P18': {'bks': 3702.85, 'ga_gap': 8.76, 'hybrid_gap': 8.49, 'customers': 240, 'depots': 6},
    'P19': {'bks': 3827.06, 'ga_gap': 4.58, 'hybrid_gap': 4.68, 'customers': 240, 'depots': 6},
    'P20': {'bks': 4058.07, 'ga_gap': 0.96, 'hybrid_gap': 0.96, 'customers': 240, 'depots': 6},
    
    # P21-P23: 360客户，9仓库
    'P21': {'bks': 5474.84, 'ga_gap': 13.25, 'hybrid_gap': 14.84, 'customers': 360, 'depots': 9},
    'P22': {'bks': 5702.16, 'ga_gap': 6.75, 'hybrid_gap': 5.76, 'customers': 360, 'depots': 9},
    'P23': {'bks': 6078.75, 'ga_gap': 1.66, 'hybrid_gap': 1.10, 'customers': 360, 'depots': 9},
}

# 分组
groups = {
    'P08-P11 (249客户)': ['P08', 'P09', 'P10', 'P11'],
    'P18-P20 (240客户)': ['P18', 'P19', 'P20'],
    'P21-P23 (360客户)': ['P21', 'P22', 'P23'],
}

print("=" * 100)
print("大规模实例分组统计分析")
print("=" * 100)

for group_name, instances in groups.items():
    print(f"\n{group_name}")
    print("-" * 100)
    
    # 统计数据
    ga_gaps = []
    hybrid_gaps = []
    improvements = []
    
    for inst in instances:
        d = data[inst]
        ga_gap = d['ga_gap']
        hybrid_gap = d['hybrid_gap']
        improvement = ga_gap - hybrid_gap
        
        ga_gaps.append(ga_gap)
        hybrid_gaps.append(hybrid_gap)
        improvements.append(improvement)
        
        status = "✓" if improvement > 0 else ("✗" if improvement < 0 else "-")
        print(f"{inst}: GA {ga_gap:.2f}% → Hybrid {hybrid_gap:.2f}% | 改进: {improvement:+.2f}% {status}")
    
    # 计算平均值
    avg_ga = sum(ga_gaps) / len(ga_gaps)
    avg_hybrid = sum(hybrid_gaps) / len(hybrid_gaps)
    avg_improvement = sum(improvements) / len(improvements)
    
    # 统计改进/退化/持平数量
    improved = sum(1 for x in improvements if x > 0)
    degraded = sum(1 for x in improvements if x < 0)
    unchanged = sum(1 for x in improvements if x == 0)
    
    print(f"\n平均统计:")
    print(f"  GA平均Gap:     {avg_ga:.2f}%")
    print(f"  Hybrid平均Gap: {avg_hybrid:.2f}%")
    print(f"  平均改进:      {avg_improvement:+.2f}%")
    print(f"  改进实例数:    {improved}/{len(instances)}")
    print(f"  退化实例数:    {degraded}/{len(instances)}")
    print(f"  持平实例数:    {unchanged}/{len(instances)}")

# 总体统计
print("\n" + "=" * 100)
print("总体统计（所有大规模实例）")
print("=" * 100)

all_instances = []
for instances in groups.values():
    all_instances.extend(instances)

all_ga_gaps = [data[inst]['ga_gap'] for inst in all_instances]
all_hybrid_gaps = [data[inst]['hybrid_gap'] for inst in all_instances]
all_improvements = [data[inst]['ga_gap'] - data[inst]['hybrid_gap'] for inst in all_instances]

avg_ga_all = sum(all_ga_gaps) / len(all_ga_gaps)
avg_hybrid_all = sum(all_hybrid_gaps) / len(all_hybrid_gaps)
avg_improvement_all = sum(all_improvements) / len(all_improvements)

improved_all = sum(1 for x in all_improvements if x > 0)
degraded_all = sum(1 for x in all_improvements if x < 0)
unchanged_all = sum(1 for x in all_improvements if x == 0)

print(f"\n总体平均:")
print(f"  GA平均Gap:     {avg_ga_all:.2f}%")
print(f"  Hybrid平均Gap: {avg_hybrid_all:.2f}%")
print(f"  平均改进:      {avg_improvement_all:+.2f}%")
print(f"  改进实例数:    {improved_all}/{len(all_instances)} ({improved_all/len(all_instances)*100:.1f}%)")
print(f"  退化实例数:    {degraded_all}/{len(all_instances)} ({degraded_all/len(all_instances)*100:.1f}%)")
print(f"  持平实例数:    {unchanged_all}/{len(all_instances)} ({unchanged_all/len(all_instances)*100:.1f}%)")

# 按客户数和仓库数分析
print("\n" + "=" * 100)
print("按配置特征分析")
print("=" * 100)

print("\n按客户数分组:")
customer_groups = {
    240: ['P18', 'P19', 'P20'],
    249: ['P08', 'P09', 'P10', 'P11'],
    360: ['P21', 'P22', 'P23'],
}

for customers, instances in customer_groups.items():
    improvements = [data[inst]['ga_gap'] - data[inst]['hybrid_gap'] for inst in instances]
    avg_imp = sum(improvements) / len(improvements)
    print(f"  {customers}客户: 平均改进 {avg_imp:+.2f}%")

print("\n按仓库数分组:")
depot_groups = {}
for inst, d in data.items():
    depots = d['depots']
    if depots not in depot_groups:
        depot_groups[depots] = []
    depot_groups[depots].append(inst)

for depots in sorted(depot_groups.keys()):
    instances = depot_groups[depots]
    improvements = [data[inst]['ga_gap'] - data[inst]['hybrid_gap'] for inst in instances]
    avg_imp = sum(improvements) / len(improvements)
    print(f"  {depots}仓库: 平均改进 {avg_imp:+.2f}% (实例: {', '.join(instances)})")

print("\n" + "=" * 100)
