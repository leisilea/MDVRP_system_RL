"""
创建ACO算法的汇总表格
格式参照PSO,排成两列(12条+11条)
"""
import json
from pathlib import Path

# 选定的12个实例（与PSO一致）
SELECTED_INSTANCES = [
    'p01', 'p02', 'p04', 'p07',  # Small (4个)
    'p12', 'p15', 'p16', 'p18',  # Medium (4个)
    'p08', 'p10', 'p21', 'p23'   # Large (4个)
]

# 规模信息
SCALE_INFO = {
    'p01': '50-4', 'p02': '50-4', 'p04': '100-2', 'p07': '100-4',
    'p08': '249-2', 'p10': '249-4', 'p12': '80-2', 'p15': '160-4',
    'p16': '199-4', 'p18': '240-6', 'p21': '360-4', 'p23': '360-5'
}

# BKS值
BKS_VALUES = {
    'p01': 576.87, 'p02': 473.53, 'p04': 1001.59, 'p07': 881.97,
    'p08': 4420.95, 'p10': 3631.35, 'p12': 1318.95, 'p15': 2505.42,
    'p16': 2572.23, 'p18': 3702.85, 'p21': 5474.84, 'p23': 5711.05
}

def read_aco_results(instance_name):
    """读取ACO结果"""
    # 尝试两个可能的路径
    paths = [
        Path('system_test/algorithm-service/solver/aco_pso_p01_p23_results') / instance_name / f'{instance_name}_results.json',
        Path('system_test/algorithm-service/solver/system_test/algorithm-service/solver/aco_pso_p01_p23_results') / instance_name / f'{instance_name}_results.json'
    ]
    
    for json_file in paths:
        if json_file.exists():
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            aco_stats = data['aco']['statistics']
            return {
                'avg_cost': aco_stats['avg_cost'],
                'avg_time': aco_stats['avg_time'],
                'avg_gap': aco_stats['avg_gap']
            }
    
    return None

def main():
    print("="*70)
    print("创建ACO算法汇总表格")
    print("="*70)
    
    # 收集所有数据
    all_data = []
    for instance in SELECTED_INSTANCES:
        result = read_aco_results(instance)
        if result:
            all_data.append({
                'instance': instance,
                'scale': SCALE_INFO[instance],
                'bks': BKS_VALUES[instance],
                'avg_cost': result['avg_cost'],
                'avg_time': result['avg_time'],
                'gap': result['avg_gap']
            })
        else:
            print(f"  [WARNING] 未找到 {instance} 的数据")
    
    # 分成两列: 前6条和后6条
    col1_data = all_data[:6]
    col2_data = all_data[6:]
    
    # 创建Markdown表格
    md_lines = []
    md_lines.append("# ACO算法实验结果汇总表")
    md_lines.append("")
    md_lines.append("| 实例 | 规模 | BKS | ACO平均成本 | 平均时间(s) | 差距(%) | | 实例 | 规模 | BKS | ACO平均成本 | 平均时间(s) | 差距(%) |")
    md_lines.append("|------|------|-----|-------------|-------------|---------|---|------|------|-----|-------------|-------------|---------|")
    
    for i in range(6):
        if i < len(col1_data):
            d1 = col1_data[i]
            line = f"| {d1['instance']} | {d1['scale']} | {d1['bks']:.2f} | {d1['avg_cost']:.2f} | {d1['avg_time']:.2f} | {d1['gap']:.2f}% |"
        else:
            line = "| | | | | | |"
        
        if i < len(col2_data):
            d2 = col2_data[i]
            line += f" | {d2['instance']} | {d2['scale']} | {d2['bks']:.2f} | {d2['avg_cost']:.2f} | {d2['avg_time']:.2f} | {d2['gap']:.2f}% |"
        else:
            line += " | | | | | | |"
        
        md_lines.append(line)
    
    # 保存Markdown
    md_content = '\n'.join(md_lines)
    with open('ACO_SUMMARY_TABLE.md', 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    print("\n[OK] Markdown表格已保存到: ACO_SUMMARY_TABLE.md")
    
    # 创建制表符分隔的文本(用于Word) - 不包含规模列
    txt_lines = []
    txt_lines.append("实例\tBKS\tACO平均成本\t平均时间(s)\t差距(%)\t\t实例\tBKS\tACO平均成本\t平均时间(s)\t差距(%)")
    
    for i in range(6):
        if i < len(col1_data):
            d1 = col1_data[i]
            line = f"{d1['instance']}\t{d1['bks']:.2f}\t{d1['avg_cost']:.2f}\t{d1['avg_time']:.2f}\t{d1['gap']:.2f}%"
        else:
            line = "\t\t\t\t"
        
        if i < len(col2_data):
            d2 = col2_data[i]
            line += f"\t\t{d2['instance']}\t{d2['bks']:.2f}\t{d2['avg_cost']:.2f}\t{d2['avg_time']:.2f}\t{d2['gap']:.2f}%"
        else:
            line += "\t\t\t\t\t\t"
        
        txt_lines.append(line)
    
    # 保存文本文件
    txt_content = '\n'.join(txt_lines)
    with open('ACO_SUMMARY_FOR_WORD.txt', 'w', encoding='utf-8') as f:
        f.write(txt_content)
    
    print("[OK] Word导入文件已保存到: ACO_SUMMARY_FOR_WORD.txt")
    
    # 打印预览
    print("\n" + "="*70)
    print("表格预览:")
    print("="*70)
    print(md_content)
    print("="*70)

if __name__ == "__main__":
    main()
