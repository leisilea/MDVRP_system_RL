#!/usr/bin/env python3
"""分析PSO初始化成本和最终成本"""

import json

with open('system_test/algorithm-service/solver/pso_p01_p23_results/p08_pso_results_merged.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print('P08 PSO 初始化 vs 最终成本分析')
print('='*60)
bks = data['bks']
print(f'BKS: {bks}\n')

for config_name, runs in data['runs'].items():
    print(f'\n{config_name.upper()} 配置:')
    print('-'*60)
    for run in runs:
        conv = run['convergence_merged']
        initial_cost = conv[0]['best_cost']
        final_cost = conv[-1]['best_cost']
        improvement = initial_cost - final_cost
        improvement_pct = (improvement / initial_cost) * 100
        
        print(f'  Run {run["run_id"]}:')
        print(f'    初始成本: {initial_cost:.2f}')
        print(f'    最终成本: {final_cost:.2f}')
        print(f'    改进量:   {improvement:.2f} ({improvement_pct:.2f}%)')
        print(f'    初始Gap:  {((initial_cost - bks) / bks * 100):.2f}%')
        print(f'    最终Gap:  {((final_cost - bks) / bks * 100):.2f}%')
        print()

# 计算平均值
print('\n' + '='*60)
print('总结:')
print('='*60)
for config_name, runs in data['runs'].items():
    improvements = []
    for run in runs:
        conv = run['convergence_merged']
        initial_cost = conv[0]['best_cost']
        final_cost = conv[-1]['best_cost']
        improvement_pct = ((initial_cost - final_cost) / initial_cost) * 100
        improvements.append(improvement_pct)
    
    avg_improvement = sum(improvements) / len(improvements)
    print(f'{config_name.upper()}: 平均改进 {avg_improvement:.2f}%')
