"""
分析第0代 vs 第10代的差异

关键问题: 
- 数据中的"第一代"是gen 10,不是gen 0
- gen 10 = 初始化 + 10代GA操作(交叉、变异、选择)
- 我们需要找到真正的gen 0数据
"""

import json

print("="*80)
print("第0代 vs 第10代分析")
print("="*80)

# 读取P08详细结果
with open('system_test/algorithm-service/solver/p08_detailed_results/p08_detailed_results.json', 'r') as f:
    data = json.load(f)

print("\n关键发现:")
print("-"*80)

# 检查convergence数据的起始代数
pure_ga_run1 = data['pure_ga_runs'][0]
hybrid_run1 = data['hybrid_runs'][0]

print(f"\n纯GA Run 1 convergence数据:")
print(f"  第一个记录点: generation {pure_ga_run1['convergence'][0][0]}, cost {pure_ga_run1['convergence'][0][1]:.2f}")
print(f"  第二个记录点: generation {pure_ga_run1['convergence'][1][0]}, cost {pure_ga_run1['convergence'][1][1]:.2f}")

print(f"\n混合GA Run 1 convergence数据:")
print(f"  第一个记录点: generation {hybrid_run1['convergence'][0][0]}, cost {hybrid_run1['convergence'][0][1]:.2f}")
print(f"  第二个记录点: generation {hybrid_run1['convergence'][1][0]}, cost {hybrid_run1['convergence'][1][1]:.2f}")

print("\n" + "="*80)
print("问题分析")
print("="*80)

print("""
1. 数据中没有gen 0的记录!
   - convergence数据从gen 10开始记录
   - gen 10已经是经过10代GA操作后的结果

2. 这意味着:
   - 纯GA: gen 0 (随机初始化) → gen 10 (15832) 
   - 混合GA: gen 0 (20% RL + 80% 随机) → gen 10 (7188)
   
3. 10代GA操作包括:
   - 交叉 (Crossover)
   - 变异 (Mutation)  
   - 选择 (Selection) - 保留最优个体
   - 这些操作会显著改善种群质量!

4. 数学问题的真相:
   - 我们用gen 10的数据(7188)去推算gen 0的RL种子成本
   - 但gen 10已经被GA优化过了!
   - 所以计算出负数是正常的 - 因为公式本身就错了

5. 要真正比较初始化质量,需要:
   - gen 0的数据(真正的初始种群)
   - 或者修改Java代码,在gen 0时也记录一次
""")

print("\n" + "="*80)
print("解决方案")
print("="*80)

print("""
方案1: 修改Java代码,记录gen 0数据
  - 修改 GA/Algorithm.java
  - 在初始化评估后,记录一次convergence数据
  - 重新运行实验

方案2: 单独评估RL种子质量
  - 生成20个RL种子(使用RouteFinder)
  - 直接评估这20个种子的成本
  - 不经过GA操作,直接看初始质量

方案3: 理论估算
  - 假设10代GA能改进X%
  - 从gen 10反推gen 0
  - 但这只是估算,不准确
""")

print("\n推荐: 方案2 - 单独评估RL种子")
print("  这样可以直接看到RL初始化的真实质量")
print("  不受GA操作的影响")

print("\n" + "="*80)
print("为什么混合初始化Run 1和Run 2的gen 10成本完全相同?")
print("="*80)

hybrid_gen10_costs = [run['convergence'][0][1] for run in data['hybrid_runs']]
print(f"\n混合GA三次运行的gen 10成本:")
for i, cost in enumerate(hybrid_gen10_costs):
    print(f"  Run {i+1}: {cost:.2f}")

if hybrid_gen10_costs[0] == hybrid_gen10_costs[1]:
    print(f"\n⚠️  Run 1和Run 2完全相同!")
    print(f"   这说明:")
    print(f"   - 可能使用了相同的RL种子")
    print(f"   - 或者RL种子在种群中占主导地位")
    print(f"   - 前10代的GA操作收敛到了相同的结果")
