"""
使用 RL4CO 预训练模型生成解
无需训练，直接使用官方预训练模型
"""

import torch
import time
from rl4co.models import AttentionModel
from rl4co.envs.routing import CVRPEnv, CVRPGenerator
from rl4co.utils.pylogger import get_pylogger

log = get_pylogger(__name__)


def load_pretrained_model(problem="cvrp", size=50, with_distance_limit=False, capacity=40, distance_limit=None):
    """
    加载 RL4CO 预训练模型或创建新模型
    
    Args:
        problem: 问题类型 ("cvrp", "tsp", "op", etc.)
        size: 问题规模 (20, 50, 100)
        with_distance_limit: 是否使用距离限制（VRPL 变体）
        capacity: 车辆容量
        distance_limit: 最大距离限制
    
    Returns:
        model: 加载的模型
    """
    print("="*60)
    print("加载 RL4CO 模型")
    print("="*60)
    print(f"问题类型: {problem.upper()}")
    print(f"问题规模: {size} 客户")
    if with_distance_limit:
        print(f"容量约束: {capacity}")
        print(f"距离约束: {distance_limit if distance_limit else '自动计算'}")
    print("="*60)
    
    # 对于带距离限制的问题，使用 MTVRP 环境
    if with_distance_limit:
        from rl4co.envs.routing import MTVRPEnv, MTVRPGenerator
        from rl4co.models import AttentionModelPolicy, POMO
        
        print("\n创建 MTVRP 环境（容量 + 距离限制）...")
        
        # 如果没有指定距离限制，根据问题规模自动设置
        if distance_limit is None:
            distance_limit = size * 3  # 经验值
        
        generator = MTVRPGenerator(
            num_loc=size,
            variant_preset="vrpl",  # 容量 + 距离限制
            capacity=capacity,
            distance_limit=distance_limit,
            min_demand=1,
            max_demand=10,
            subsample=False,  # 关键：使用 variant_preset 时必须设为 False
        )
        
        env = MTVRPEnv(generator=generator)
        
        # 创建策略
        policy = AttentionModelPolicy(
            env_name=env.name,
            embed_dim=128,
            num_heads=8,
            num_encoder_layers=3,
            normalization="instance",
        )
        
        # 创建 POMO 模型
        model = POMO(env=env, policy=policy)
        print("✓ 创建 MTVRP 模型（未训练）")
        print("⚠️  警告: 模型未训练，解质量可能较差")
        print("⚠️  建议运行 train_rl4co_cvrp.py 训练模型")
        
    else:
        # 标准 CVRP（仅容量约束）
        try:
            # 尝试从 HuggingFace 加载预训练模型
            model_name = f"ai4co/rl4co-{problem}-{size}"
            print(f"\n尝试从 HuggingFace 加载: {model_name}")
            
            model = AttentionModel.from_pretrained(model_name)
            print("✓ 成功加载预训练模型！")
            
        except Exception as e:
            print(f"✗ 从 HuggingFace 加载失败: {e}")
            print("\n创建新模型...")
            
            if problem == "cvrp":
                generator = CVRPGenerator(num_loc=size, capacity=capacity)
                env = CVRPEnv(generator=generator)
            else:
                raise ValueError(f"不支持的问题类型: {problem}")
            
            model = AttentionModel(env=env)
            print("✓ 创建新模型（未训练）")
            print("⚠️  警告: 模型未训练，解质量可能较差")
    
    model.eval()
    return model


def generate_solutions_with_pretrained(
    problem="cvrp",
    size=50,
    num_instances=10,
    num_solutions=100,
    method="sampling",
    temperature=1.0,
    with_distance_limit=False,
    capacity=40,
    distance_limit=None,
):
    """
    使用预训练模型生成解
    
    Args:
        problem: 问题类型
        size: 问题规模
        num_instances: 实例数量
        num_solutions: 每实例解数
        method: 生成方法
        temperature: 采样温度
        with_distance_limit: 是否使用距离限制
        capacity: 车辆容量
        distance_limit: 最大距离限制
    """
    print("\n" + "="*60)
    print("使用模型生成解")
    print("="*60)
    
    # 加载模型
    model = load_pretrained_model(
        problem=problem, 
        size=size,
        with_distance_limit=with_distance_limit,
        capacity=capacity,
        distance_limit=distance_limit
    )
    
    # 检查设备
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)
    print(f"\n使用设备: {device}")
    
    # 生成测试数据
    print(f"\n生成 {num_instances} 个测试实例...")
    env = model.env
    td = env.reset(batch_size=[num_instances])
    td = td.to(device)
    
    # 生成解
    print(f"\n开始生成解（方法: {method}）...")
    start_time = time.time()
    
    all_solutions = []
    all_costs = []
    
    with torch.no_grad():
        if method == "sampling":
            # 采样方法
            for i in range(num_solutions):
                # 重要：每次采样前重置环境状态
                td_reset = td.clone()
                
                out = model.policy(
                    td_reset, 
                    decode_type="sampling",
                    temperature=temperature,
                    return_actions=True
                )
                cost = env.get_reward(td_reset, out['actions'])
                all_solutions.append(out['actions'].cpu())
                all_costs.append(cost.cpu())
                
                if (i + 1) % 10 == 0:
                    elapsed = time.time() - start_time
                    avg_time = elapsed / (i + 1)
                    eta = avg_time * (num_solutions - i - 1)
                    print(f"  进度: {i + 1}/{num_solutions} "
                          f"({elapsed:.1f}s, ETA: {eta:.1f}s)")
        
        elif method == "greedy":
            # 贪心方法（最快）
            print("  使用贪心解码...")
            out = model.policy(
                td,
                decode_type="greedy",
                return_actions=True
            )
            all_solutions.append(out['actions'].cpu())
            all_costs.append(env.get_reward(td, out['actions']).cpu())
        
        else:
            raise ValueError(f"不支持的方法: {method}")
    
    total_time = time.time() - start_time
    
    # 整理结果
    if len(all_solutions) > 1:
        all_solutions = torch.stack(all_solutions, dim=1)
        all_costs = torch.stack(all_costs, dim=1)
        
        # 找到最优解
        best_indices = torch.argmin(all_costs, dim=1)
        best_solutions = all_solutions[torch.arange(num_instances), best_indices]
        best_costs = all_costs[torch.arange(num_instances), best_indices]
        
        avg_cost = all_costs.mean().item()
        std_cost = all_costs.std().item()
        best_avg_cost = best_costs.mean().item()
    else:
        all_solutions = all_solutions[0]
        all_costs = all_costs[0]
        best_solutions = all_solutions
        best_costs = all_costs
        avg_cost = all_costs.mean().item()
        std_cost = 0.0
        best_avg_cost = avg_cost
    
    # 打印结果
    print("\n" + "="*60)
    print("生成完成！")
    print("="*60)
    print(f"总耗时: {total_time:.2f}s")
    print(f"平均每解: {total_time / (num_instances * len(all_costs)):.4f}s")
    print(f"\n成本统计:")
    print(f"  平均成本: {avg_cost:.2f}")
    if std_cost > 0:
        print(f"  标准差: {std_cost:.2f}")
        print(f"  最优解平均: {best_avg_cost:.2f}")
        print(f"  改进幅度: {(avg_cost - best_avg_cost) / avg_cost * 100:.2f}%")
    print("="*60)
    
    return {
        'solutions': all_solutions,
        'costs': all_costs,
        'best_solutions': best_solutions,
        'best_costs': best_costs,
        'avg_cost': avg_cost,
        'total_time': total_time,
    }


def quick_demo():
    """
    快速演示：生成 10 个实例，每个 10 个解
    带容量和距离约束
    """
    print("\n" + "="*60)
    print("RL4CO 模型快速演示（容量 + 距离约束）")
    print("="*60)
    
    # 小规模快速测试，带距离限制
    results = generate_solutions_with_pretrained(
        problem="cvrp",
        size=20,  # 20 客户（快速）
        num_instances=5,
        num_solutions=10,
        method="sampling",
        temperature=1.0,
        with_distance_limit=True,  # 启用距离限制
        capacity=40,
        distance_limit=60,  # 距离限制
    )
    
    print("\n演示完成！")
    print(f"平均成本: {results['avg_cost']:.2f}")
    print(f"总耗时: {results['total_time']:.2f}s")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="使用 RL4CO 预训练模型")
    parser.add_argument("--problem", type=str, default="cvrp", 
                       choices=["cvrp", "tsp", "op"],
                       help="问题类型")
    parser.add_argument("--size", type=int, default=50,
                       choices=[20, 50, 100],
                       help="问题规模")
    parser.add_argument("--num_instances", type=int, default=10,
                       help="实例数量")
    parser.add_argument("--num_solutions", type=int, default=100,
                       help="每实例解数")
    parser.add_argument("--method", type=str, default="sampling",
                       choices=["sampling", "greedy"],
                       help="生成方法")
    parser.add_argument("--temperature", type=float, default=1.0,
                       help="采样温度")
    parser.add_argument("--with_distance_limit", action="store_true",
                       help="启用距离限制（VRPL 变体）")
    parser.add_argument("--capacity", type=float, default=40,
                       help="车辆容量")
    parser.add_argument("--distance_limit", type=float, default=None,
                       help="最大距离限制")
    parser.add_argument("--demo", action="store_true",
                       help="运行快速演示")
    
    args = parser.parse_args()
    
    if args.demo:
        quick_demo()
    else:
        generate_solutions_with_pretrained(
            problem=args.problem,
            size=args.size,
            num_instances=args.num_instances,
            num_solutions=args.num_solutions,
            method=args.method,
            temperature=args.temperature,
            with_distance_limit=args.with_distance_limit,
            capacity=args.capacity,
            distance_limit=args.distance_limit,
        )
