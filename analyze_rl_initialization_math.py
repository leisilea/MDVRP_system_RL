"""
分析RL混合初始化的数学问题

用户观察: 如果只有20%的RL初始化种子,怎么在第一代把平均成本拉低到7000?
这在数学上不符合常理。

让我们验证这个数学问题。
"""

import json

# 读取P08详细结果
with open('system_test/algorithm-service/solver/p08_detailed_results/p08_detailed_results.json', 'r') as f:
    data = json.load(f)

print("=" * 80)
print("P08 初始化数学分析")
print("=" * 80)

# 纯GA的第一代(gen 10)平均成本
pure_ga_gen10 = []
for run in data['pure_ga_runs']:
    gen10_cost = run['convergence'][0][1]  # [10, cost]
    pure_ga_gen10.append(gen10_cost)
    print(f"纯GA Run {run['run_id']} 第一代(gen 10): {gen10_cost:.2f}")

avg_pure_ga_gen10 = sum(pure_ga_gen10) / len(pure_ga_gen10)
print(f"\n纯GA第一代平均成本: {avg_pure_ga_gen10:.2f}")

# 混合GA的第一代(gen 10)平均成本
hybrid_gen10 = []
for run in data['hybrid_runs']:
    gen10_cost = run['convergence'][0][1]  # [10, cost]
    hybrid_gen10.append(gen10_cost)
    print(f"\n混合GA Run {run['run_id']} 第一代(gen 10): {gen10_cost:.2f}")

avg_hybrid_gen10 = sum(hybrid_gen10) / len(hybrid_gen10)
print(f"\n混合GA第一代平均成本: {avg_hybrid_gen10:.2f}")

print("\n" + "=" * 80)
print("数学验证")
print("=" * 80)

# 假设: 混合初始化 = 20% RL种子 + 80% 随机种子
# 公式: hybrid_cost = 0.2 * RL_cost + 0.8 * random_cost
# 已知: hybrid_cost ≈ 7188, random_cost ≈ 15833
# 求解: RL_cost = (hybrid_cost - 0.8 * random_cost) / 0.2

print(f"\n假设混合初始化配置:")
print(f"  - 20% RL种子")
print(f"  - 80% 随机种子")
print(f"\n已知数据:")
print(f"  - 混合GA第一代平均: {avg_hybrid_gen10:.2f}")
print(f"  - 纯随机第一代平均: {avg_pure_ga_gen10:.2f}")

# 计算理论上的RL种子成本
theoretical_rl_cost = (avg_hybrid_gen10 - 0.8 * avg_pure_ga_gen10) / 0.2

print(f"\n根据公式计算:")
print(f"  RL_cost = ({avg_hybrid_gen10:.2f} - 0.8 × {avg_pure_ga_gen10:.2f}) / 0.2")
print(f"  RL_cost = ({avg_hybrid_gen10:.2f} - {0.8 * avg_pure_ga_gen10:.2f}) / 0.2")
print(f"  RL_cost = {avg_hybrid_gen10 - 0.8 * avg_pure_ga_gen10:.2f} / 0.2")
print(f"  RL_cost = {theoretical_rl_cost:.2f}")

print("\n" + "=" * 80)
print("结论")
print("=" * 80)

if theoretical_rl_cost < 0:
    print("❌ 数学上不可能!")
    print(f"   计算出的RL种子成本为负数: {theoretical_rl_cost:.2f}")
    print("\n可能的原因:")
    print("  1. 第一代(gen 10)已经包含了交叉/变异操作的效果")
    print("  2. RL种子比例不是20%,可能更高")
    print("  3. 初始化策略与我们理解的不同")
    print("  4. 需要查看gen 0的数据(真正的初始种群)")
elif theoretical_rl_cost < avg_pure_ga_gen10:
    print("✓ RL种子确实比随机初始化好很多!")
    print(f"  RL种子平均成本: {theoretical_rl_cost:.2f}")
    print(f"  随机种子平均成本: {avg_pure_ga_gen10:.2f}")
    print(f"  改进幅度: {(1 - theoretical_rl_cost/avg_pure_ga_gen10)*100:.1f}%")
else:
    print("⚠️  计算结果异常,RL种子反而比随机差")

print("\n" + "=" * 80)
print("关键观察")
print("=" * 80)

print("\n注意到混合GA的Run 1和Run 2第一代成本完全相同:")
print(f"  Run 1: {hybrid_gen10[0]:.2f}")
print(f"  Run 2: {hybrid_gen10[1]:.2f}")
print(f"  Run 3: {hybrid_gen10[2]:.2f}")
print("\n这暗示:")
print("  - Run 1和Run 2可能使用了相同的RL种子")
print("  - 或者RL种子在初始化中占主导地位")
print("  - 需要查看实际的初始化代码和RL种子生成过程")

print("\n" + "=" * 80)
print("下一步行动")
print("=" * 80)
print("\n1. 查看run_ga_with_routefinder.py中的初始化代码")
print("2. 确认RL种子的实际比例和生成方式")
print("3. 如果可能,生成P08的RL种子并评估其质量")
print("4. 检查是否有gen 0的数据(真正的初始种群,未经过GA操作)")
