"""
提取所有ACO实例的数据并按照指定格式整理到ACO.txt
格式: 实例 最优 平均成本 平均时间 平均BKS
例如: p01 576.87 642.26 391.75 11.34%
"""
import json
from pathlib import Path

# BKS值 (p01-p23)
BKS_VALUES = {
    'p01': 576.87, 'p02': 473.53, 'p03': 640.00, 'p04': 1001.59,
    'p05': 750.03, 'p06': 876.50, 'p07': 881.97, 'p08': 4420.95,
    'p09': 3900.22, 'p10': 3631.35, 'p11': 3554.18, 'p12': 1318.95,
    'p13': 1318.95, 'p14': 1360.12, 'p15': 2505.42, 'p16': 2572.23,
    'p17': 2709.09, 'p18': 3702.85, 'p19': 3827.06, 'p20': 4058.07,
    'p21': 5474.84, 'p22': 5702.16, 'p23': 5711.05
}

def read_aco_results(instance_name):
    """读取ACO结果"""
    json_file = Path('system_test/algorithm-service/solver/aco_pso_p01_p23_results') / instance_name / f'{instance_name}_results.json'
    
    if not json_file.exists():
        return None
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        aco_stats = data['aco']['statistics']
        return {
            'min_cost': aco_stats['min_cost'],
            'avg_cost': aco_stats['avg_cost'],
            'avg_time': aco_stats['avg_time'],
            'avg_gap': aco_stats['avg_gap']
        }
    except Exception as e:
        print(f"  [ERROR] 读取 {instance_name} 失败: {e}")
        return None

def main():
    print("="*70)
    print("提取所有ACO实例数据")
    print("="*70)
    
    # 收集所有实例数据 (p01-p23)
    all_lines = []
    all_lines.append("实例\t最优\t平均成本\t平均时间\t平均BKS")
    
    for i in range(1, 24):  # p01 到 p23
        instance = f'p{i:02d}'
        
        if instance not in BKS_VALUES:
            continue
        
        result = read_aco_results(instance)
        if result:
            bks = BKS_VALUES[instance]
            min_cost = result['min_cost']
            avg_cost = result['avg_cost']
            avg_time = result['avg_time']
            avg_gap = result['avg_gap']
            
            # 格式化输出行
            line = f"{instance}\t{bks:.2f}\t{avg_cost:.2f}\t{avg_time:.2f}\t{avg_gap:.2f}%"
            all_lines.append(line)
            print(f"  [OK] {instance}: BKS={bks:.2f}, 平均成本={avg_cost:.2f}, 平均时间={avg_time:.2f}s, 差距={avg_gap:.2f}%")
        else:
            print(f"  [SKIP] {instance}: 未找到数据")
    
    # 保存到ACO.txt
    output_file = Path('system_test/algorithm-service/solver/aco_pso_p01_p23_results/ACO.txt')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(all_lines))
    
    print("\n" + "="*70)
    print(f"[完成] 数据已保存到: {output_file}")
    print("="*70)
    
    # 打印预览
    print("\n文件内容预览:")
    print("-"*70)
    for line in all_lines[:5]:  # 显示前5行
        print(line)
    print("...")
    print(f"(共 {len(all_lines)} 行)")
    print("-"*70)

if __name__ == "__main__":
    main()
