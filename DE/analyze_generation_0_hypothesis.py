"""
分析第0代(初始化)的假设场景

基于第10代数据,反推第0代可能的情况
"""

import numpy as np

print("="*80)
print("P08 第0代(初始化)假设分析")
print("="*80)

# 已知数据
gen10_pure = 15832.27  # 纯GA第10代平均成本
gen10_hybrid = 7188.15  # 混合GA第10代平均成本
final_pure = 4817.06  # 纯GA最终成本
final_hybrid = 4722.13  # 混合GA最终成本
bks = 4420.95  # BKS

print(f"\n已知数据:")
print(f"  纯GA第10代: {gen10_pure:.2f}")
print(f"  混合GA第10代: {gen10_hybrid:.2f}")
print(f"  纯GA最终: {final_pure:.2f}")
print(f"  混合GA最终: {final_hybrid:.2f}")
print(f"  BKS: {bks:.2f}")

# 假设每次迭代的平均改进率
print(f"\n" + "="*80)
print(f"假设场景分析")
print(f"="*80)

# 场景1: 假设每次迭代改进5%
improvement_rate_1 = 0.05
gen0_pure_1 = gen10_pure / ((1 - improvement_rate_1) ** 10)
gen0_hybrid_1 = gen10_hybrid / ((1 - improvement_rate_1) ** 10)

print(f"\n场景1: 假设每次迭代改进5%")
print(f"  纯GA第0代估计: {gen0_pure_1:.2f}")
print(f"  混合GA第0代估计: {gen0_hybrid_1:.2f}")

# 反推RL种子成本
# gen0_hybrid = 0.2 * RL_cost + 0.8 * gen0_pure
rl_cost_1 = (gen0_hybrid_1 - 0.8 * gen0_pure_1) / 0.2
print(f"  反推RL种子平均成本: {rl_cost_1:.2f}")
print(f"  RL vs 随机: {((rl_cost_1 - gen0_pure_1) / gen0_pure_1 * 100):.1f}%")

# 场景2: 假设每次迭代改进7%
improvement_rate_2 = 0.07
gen0_pure_2 = gen10_pure / ((1 - improvement_rate_2) ** 10)
gen0_hybrid_2 = gen10_hybrid / ((1 - improvement_rate_2) ** 10)

print(f"\n场景2: 假设每次迭代改进7%")
print(f"  纯GA第0代估计: {gen0_pure_2:.2f}")
print(f"  混合GA第0代估计: {gen0_hybrid_2:.2f}")

rl_cost_2 = (gen0_hybrid_2 - 0.8 * gen0_pure_2) / 0.2
print(f"  反推RL种子平均成本: {rl_cost_2:.2f}")
print(f"  RL vs 随机: {((rl_cost_2 - gen0_pure_2) / gen0_pure_2 * 100):.1f}%")

# 场景3: 假设每次迭代改进10%
improvement_rate_3 = 0.10
gen0_pure_3 = gen10_pure / ((1 - improvement_rate_3) ** 10)
gen0_hybrid_3 = gen10_hybrid / ((1 - improvement_rate_3) ** 10)

print(f"\n场景3: 假设每次迭代改进10%")
print(f"  纯GA第0代估计: {gen0_pure_3:.2f}")
print(f"  混合GA第0代估计: {gen0_hybrid_3:.2f}")

rl_cost_3 = (gen0_hybrid_3 - 0.8 * gen0_pure_3) / 0.2
print(f"  反推RL种子平均成本: {rl_cost_3:.2f}")
print(f"  RL vs 随机: {((rl_cost_3 - gen0_pure_3) / gen0_pure_3 * 100):.1f}%")

print(f"\n" + "="*80)
print(f"结论")
print(f"="*80)

print(f"""
基于不同的改进率假设,RL种子的可能质量:

1. 如果每次迭代改进5%:
   - RL种子平均成本: {rl_cost_1:.2f}
   - 比随机好: {abs((rl_cost_1 - gen0_pure_1) / gen0_pure_1 * 100):.1f}%
   - 与BKS的Gap: {((rl_cost_1 - bks) / bks * 100):.1f}%

2. 如果每次迭代改进7%:
   - RL种子平均成本: {rl_cost_2:.2f}
   - 比随机好: {abs((rl_cost_2 - gen0_pure_2) / gen0_pure_2 * 100):.1f}%
   - 与BKS的Gap: {((rl_cost_2 - bks) / bks * 100):.1f}%

3. 如果每次迭代改进10%:
   - RL种子平均成本: {rl_cost_3:.2f}
   - 比随机好: {abs((rl_cost_3 - gen0_pure_3) / gen0_pure_3 * 100):.1f}%
   - 与BKS的Gap: {((rl_cost_3 - bks) / bks * 100):.1f}%

注意: 这些都是基于假设的推测!
要获得真实数据,需要:
1. 运行RouteFinder生成P08的RL种子
2. 或修改Java代码记录第0代数据
""")

print(f"\n" + "="*80)
print(f"参考: PSO混合初始化的表现")
print(f"="*80)

print(f"""
根据之前的分析,PSO的混合初始化(Large config):
- 初始平均成本: 5925.72
- 最终平均成本: 5265.01
- 改进: 11.15%
- 初始化做了90%的工作

如果RL初始化类似,那么:
- RL种子可能在6000-8000范围
- 比随机初始化(~16000)好60-70%
- 但这只是推测,需要实际数据验证
""")
