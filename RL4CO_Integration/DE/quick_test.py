"""
快速测试 RL4CO 预训练模型
"""

import sys
import os

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from use_pretrained_model import generate_solutions_with_pretrained


def main():
    print("\n" + "="*60)
    print("RL4CO 预训练模型快速测试")
    print("="*60)
    print("\n这将使用 RL4CO 的预训练模型生成解")
    print("无需训练，直接使用！\n")
    
    # 测试配置
    configs = [
        {
            "name": "小规模测试（20 客户）",
            "problem": "cvrp",
            "size": 20,
            "num_instances": 5,
            "num_solutions": 10,
            "method": "sampling",
        },
        {
            "name": "中等规模测试（50 客户）",
            "problem": "cvrp",
            "size": 50,
            "num_instances": 3,
            "num_solutions": 20,
            "method": "sampling",
        },
    ]
    
    all_results = []
    
    for i, config in enumerate(configs, 1):
        print(f"\n{'='*60}")
        print(f"测试 {i}/{len(configs)}: {config['name']}")
        print(f"{'='*60}")
        
        try:
            results = generate_solutions_with_pretrained(**config)
            all_results.append({
                'name': config['name'],
                'size': config['size'],
                'avg_cost': results['avg_cost'],
                'total_time': results['total_time'],
                'num_instances': config['num_instances'],
                'num_solutions': config['num_solutions'],
            })
            print(f"✓ 测试成功！")
        except Exception as e:
            print(f"✗ 测试失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 打印总结
    if all_results:
        print("\n" + "="*60)
        print("测试总结")
        print("="*60)
        print(f"{'测试名称':<30} {'规模':<8} {'平均成本':<12} {'耗时(s)':<10}")
        print("-"*60)
        for r in all_results:
            print(f"{r['name']:<30} {r['size']:<8} {r['avg_cost']:<12.2f} {r['total_time']:<10.2f}")
        print("="*60)
        print("\n✓ 所有测试完成！")
        print("\n下一步:")
        print("  1. 使用 use_pretrained_model.py 生成更多解")
        print("  2. 调整参数（num_solutions, temperature）优化结果")
        print("  3. 集成到你的系统中")
    else:
        print("\n✗ 所有测试失败")
        print("\n可能的原因:")
        print("  1. RL4CO 未正确安装: pip install rl4co")
        print("  2. 网络问题，无法下载预训练模型")
        print("  3. 依赖包缺失")


if __name__ == "__main__":
    main()
