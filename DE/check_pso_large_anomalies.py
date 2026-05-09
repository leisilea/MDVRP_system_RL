"""
检查PSO Large配置的异常成本
扫描所有P01-P23的结果，找出PSO large配置中出现异常低成本的实例
"""

import json
from pathlib import Path

# BKS数据
BKS = {
    'p01': 576.87, 'p02': 473.53, 'p03': 640.58, 'p04': 1001.59, 'p05': 750.03,
    'p06': 876.50, 'p07': 881.97, 'p08': 4437.68, 'p09': 3873.89, 'p10': 3663.02,
    'p11': 3554.18, 'p12': 1318.95, 'p13': 1318.95, 'p14': 1360.12, 'p15': 2505.42,
    'p16': 2572.23, 'p17': 2709.09, 'p18': 3702.85, 'p19': 3827.06, 'p20': 4058.07,
    'p21': 5474.84, 'p22': 5702.16, 'p23': 6078.75
}

def check_anomalies():
    """检查所有实例的PSO large配置是否有异常"""
    results_dir = Path("system_test/algorithm-service/solver/aco_pso_p01_p23_results")
    
    anomalies = []
    
    for i in range(1, 24):
        instance_name = f'p{i:02d}'
        result_file = results_dir / instance_name / f'{instance_name}_results.json'
        
        if not result_file.exists():
            print(f"⚠️  {instance_name}: 结果文件不存在")
            continue
        
        try:
            with open(result_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            bks = BKS[instance_name]
            
            # 检查PSO large配置的所有运行
            if 'pso' in data and 'large' in data['pso']:
                large_data = data['pso']['large']
                
                if 'runs' in large_data:
                    for run in large_data['runs']:
                        cost = run['cost']
                        gap = run['gap']
                        
                        # 检查是否异常：成本远低于BKS（不太可能）或gap为负
                        if cost < bks * 0.5 or gap < -10:
                            anomalies.append({
                                'instance': instance_name,
                                'run_id': run['run_id'],
                                'cost': cost,
                                'bks': bks,
                                'gap': gap,
                                'reason': 'cost_too_low' if cost < bks * 0.5 else 'negative_gap'
                            })
                            print(f"❌ {instance_name} Run {run['run_id']}: 成本={cost:.2f}, BKS={bks:.2f}, Gap={gap:.2f}%")
                        
                        # 检查收敛数据中的最后一个点
                        if 'convergence' in run and run['convergence']:
                            last_conv = run['convergence'][-1]
                            conv_cost = last_conv['best_cost']
                            
                            # 如果收敛数据的最后成本与最终成本差异很大
                            if abs(conv_cost - cost) > cost * 0.1:
                                print(f"⚠️  {instance_name} Run {run['run_id']}: 收敛数据不一致")
                                print(f"    最终成本={cost:.2f}, 收敛最后点={conv_cost:.2f}, 差异={abs(conv_cost - cost):.2f}")
                
                # 检查统计数据
                if 'statistics' in large_data:
                    stats = large_data['statistics']
                    avg_cost = stats['avg_cost']
                    
                    if avg_cost < bks * 0.5:
                        print(f"❌ {instance_name} 统计: 平均成本={avg_cost:.2f}, BKS={bks:.2f}")
                        anomalies.append({
                            'instance': instance_name,
                            'run_id': 'average',
                            'cost': avg_cost,
                            'bks': bks,
                            'gap': stats['avg_gap'],
                            'reason': 'avg_cost_too_low'
                        })
            else:
                print(f"⚠️  {instance_name}: 没有PSO large配置数据")
        
        except Exception as e:
            print(f"❌ {instance_name}: 读取失败 - {e}")
    
    print("\n" + "=" * 80)
    print(f"检查完成！发现 {len(anomalies)} 个异常")
    print("=" * 80)
    
    if anomalies:
        print("\n异常实例列表:")
        for anomaly in anomalies:
            print(f"  - {anomaly['instance']} Run {anomaly['run_id']}: "
                  f"成本={anomaly['cost']:.2f}, BKS={anomaly['bks']:.2f}, "
                  f"Gap={anomaly['gap']:.2f}%, 原因={anomaly['reason']}")
    
    return anomalies

if __name__ == "__main__":
    check_anomalies()
