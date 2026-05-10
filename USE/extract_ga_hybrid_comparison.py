"""
提取GA和Hybrid(GA+RL)的对比数据并按照指定格式整理
格式: 实例 BKS GA平均成本 GA平均时间 GA差距 Hybrid平均成本 Hybrid平均时间 Hybrid差距
"""
import json
from pathlib import Path

# BKS值 (p01-p23)
BKS_VALUES = {
    'p01': 576.87, 'p02': 473.53, 'p03': 640.58, 'p04': 1001.59,
    'p05': 750.03, 'p06': 876.50, 'p07': 881.97, 'p08': 4437.68,
    'p09': 3873.89, 'p10': 3663.02, 'p11': 3554.18, 'p12': 1318.95,
    'p13': 1318.95, 'p14': 1360.12, 'p15': 2505.42, 'p16': 2572.23,
    'p17': 2709.09, 'p18': 3702.85, 'p19': 3827.06, 'p20': 4058.07,
    'p21': 5474.84, 'p22': 5702.16, 'p23': 6078.75
}

# 从已有的统计数据中提取
GA_HYBRID_DATA = {
    'p01': {'ga_cost': 599.40, 'ga_time': 6.72, 'ga_gap': 3.91, 'hybrid_cost': 601.52, 'hybrid_time': 32.12, 'hybrid_gap': 4.27},
    'p02': {'ga_cost': 493.71, 'ga_time': 9.07, 'ga_gap': 4.26, 'hybrid_cost': 495.97, 'hybrid_time': 16.37, 'hybrid_gap': 4.74},
    'p03': {'ga_cost': 670.95, 'ga_time': 11.93, 'ga_gap': 4.74, 'hybrid_cost': 675.45, 'hybrid_time': 20.67, 'hybrid_gap': 5.44},
    'p04': {'ga_cost': 1091.18, 'ga_time': 43.58, 'ga_gap': 8.95, 'hybrid_cost': 1056.11, 'hybrid_time': 57.46, 'hybrid_gap': 5.44},
    'p05': {'ga_cost': 777.02, 'ga_time': 102.57, 'ga_gap': 3.60, 'hybrid_cost': 777.76, 'hybrid_time': 115.52, 'hybrid_gap': 3.70},
    'p06': {'ga_cost': 920.80, 'ga_time': 28.67, 'ga_gap': 5.05, 'hybrid_cost': 926.60, 'hybrid_time': 38.94, 'hybrid_gap': 5.72},
    'p07': {'ga_cost': 949.55, 'ga_time': 21.53, 'ga_gap': 7.66, 'hybrid_cost': 933.19, 'hybrid_time': 30.88, 'hybrid_gap': 5.81},
    'p08': {'ga_cost': 4787.73, 'ga_time': 652.28, 'ga_gap': 7.89, 'hybrid_cost': 4690.70, 'hybrid_time': 623.39, 'hybrid_gap': 5.70},
    'p09': {'ga_cost': 4188.18, 'ga_time': 401.31, 'ga_gap': 8.11, 'hybrid_cost': 4130.61, 'hybrid_time': 400.54, 'hybrid_gap': 6.63},
    'p10': {'ga_cost': 3975.92, 'ga_time': 296.84, 'ga_gap': 8.54, 'hybrid_cost': 3902.48, 'hybrid_time': 294.77, 'hybrid_gap': 6.54},
    'p11': {'ga_cost': 3986.81, 'ga_time': 229.44, 'ga_gap': 12.17, 'hybrid_cost': 3911.04, 'hybrid_time': 246.62, 'hybrid_gap': 10.04},
    'p12': {'ga_cost': 1322.54, 'ga_time': 54.73, 'ga_gap': 0.27, 'hybrid_cost': 1326.12, 'hybrid_time': 67.66, 'hybrid_gap': 0.54},
    'p13': {'ga_cost': 1326.12, 'ga_time': 82.74, 'ga_gap': 0.54, 'hybrid_cost': 1326.12, 'hybrid_time': 90.32, 'hybrid_gap': 0.54},
    'p14': {'ga_cost': 1365.69, 'ga_time': 74.40, 'ga_gap': 0.41, 'hybrid_cost': 1365.69, 'hybrid_time': 91.10, 'hybrid_gap': 0.41},
    'p15': {'ga_cost': 2622.18, 'ga_time': 90.06, 'ga_gap': 4.66, 'hybrid_cost': 2619.61, 'hybrid_time': 102.82, 'hybrid_gap': 4.56},
    'p16': {'ga_cost': 2631.47, 'ga_time': 120.94, 'ga_gap': 2.30, 'hybrid_cost': 2637.75, 'hybrid_time': 145.96, 'hybrid_gap': 2.55},
    'p17': {'ga_cost': 2731.37, 'ga_time': 117.15, 'ga_gap': 0.82, 'hybrid_cost': 2731.37, 'hybrid_time': 142.54, 'hybrid_gap': 0.82},
    'p18': {'ga_cost': 4027.25, 'ga_time': 116.65, 'ga_gap': 8.76, 'hybrid_cost': 4017.37, 'hybrid_time': 121.14, 'hybrid_gap': 8.49},
    'p19': {'ga_cost': 4002.25, 'ga_time': 163.14, 'ga_gap': 4.58, 'hybrid_cost': 4006.11, 'hybrid_time': 191.58, 'hybrid_gap': 4.68},
    'p20': {'ga_cost': 4097.06, 'ga_time': 166.95, 'ga_gap': 0.96, 'hybrid_cost': 4097.06, 'hybrid_time': 198.87, 'hybrid_gap': 0.96},
    'p21': {'ga_cost': 6200.25, 'ga_time': 158.39, 'ga_gap': 13.25, 'hybrid_cost': 6287.27, 'hybrid_time': 166.14, 'hybrid_gap': 14.84},
    'p22': {'ga_cost': 6087.18, 'ga_time': 220.60, 'ga_gap': 6.75, 'hybrid_cost': 6030.81, 'hybrid_time': 268.36, 'hybrid_gap': 5.76},
    'p23': {'ga_cost': 6179.55, 'ga_time': 209.96, 'ga_gap': 1.66, 'hybrid_cost': 6145.58, 'hybrid_time': 259.37, 'hybrid_gap': 1.10},
}

def main():
    print("="*80)
    print("提取GA和Hybrid(GA+RL)对比数据")
    print("="*80)
    
    # 创建制表符分隔的文本
    all_lines = []
    all_lines.append("实例\tBKS\tGA平均成本\tGA平均时间\tGA差距\tHybrid平均成本\tHybrid平均时间\tHybrid差距")
    
    for i in range(1, 24):  # p01 到 p23
        instance = f'p{i:02d}'
        
        if instance not in BKS_VALUES or instance not in GA_HYBRID_DATA:
            continue
        
        bks = BKS_VALUES[instance]
        data = GA_HYBRID_DATA[instance]
        
        # 格式化输出行
        line = f"{instance}\t{bks:.2f}\t{data['ga_cost']:.2f}\t{data['ga_time']:.2f}\t{data['ga_gap']:.2f}%\t{data['hybrid_cost']:.2f}\t{data['hybrid_time']:.2f}\t{data['hybrid_gap']:.2f}%"
        all_lines.append(line)
        print(f"  [OK] {instance}: GA={data['ga_cost']:.2f} ({data['ga_gap']:.2f}%), Hybrid={data['hybrid_cost']:.2f} ({data['hybrid_gap']:.2f}%)")
    
    # 保存到GA_HYBRID.txt
    output_file = Path('system_test/algorithm-service/solver/p01_p23_results_multi_runs/GA_HYBRID.txt')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(all_lines))
    
    print("\n" + "="*80)
    print(f"[完成] 数据已保存到: {output_file}")
    print("="*80)
    
    # 打印预览
    print("\n文件内容预览:")
    print("-"*80)
    for line in all_lines[:5]:  # 显示前5行
        print(line)
    print("...")
    print(f"(共 {len(all_lines)} 行)")
    print("-"*80)
    
    # 计算统计信息
    ga_gaps = [GA_HYBRID_DATA[f'p{i:02d}']['ga_gap'] for i in range(1, 24)]
    hybrid_gaps = [GA_HYBRID_DATA[f'p{i:02d}']['hybrid_gap'] for i in range(1, 24)]
    
    print("\n统计信息:")
    print(f"  GA平均差距: {sum(ga_gaps)/len(ga_gaps):.2f}%")
    print(f"  Hybrid平均差距: {sum(hybrid_gaps)/len(hybrid_gaps):.2f}%")
    print(f"  Hybrid改进: {sum(ga_gaps)/len(ga_gaps) - sum(hybrid_gaps)/len(hybrid_gaps):.2f}%")

if __name__ == "__main__":
    main()
