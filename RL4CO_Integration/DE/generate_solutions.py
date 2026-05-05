"""
使用训练好的 RL4CO 模型生成多个不同的解
"""

import torch
import numpy as np
import time
from rl4co.models import POMO
from rl4co.envs.routing import MTVRPEnv


def generate_diverse_solutions(
    model_path,
    num_instances=10,
    num_solutions_per_instance=100,
    method="sampling",
    temperature=1.0,
    save_path="solutions.pt"
):
    """
    生成多个不同的解
    
    Args:
        model_path: 模型检查点路径
        num_instances: 实例数量
        num_solutions_per_instance: 每个实例生成的解数量
        method: 生成方法 ("sampling", "pomo", "beam_search")
        temperature: 采样温度（仅用于 sampling）
        save_path: 保存路径
    
    Returns:
        results: 包含所有解的字典
    """
    print("="*60)
    print("RL4CO 解生成器")
    print("="*60)
    print(f"模型: {model_path}")
    print(f"实例数: {num_instances}")
    print(f"每实例解数: {num_solutions_per_instance}")
    print(f"生成方法: {method}")
    print("="*60)
    
    # 加载模型
    print("\n加载模型...")
    model = POMO.load_from_checkpoint(model_path)
    model.eval()
    
    # 检查设备
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)
    print(f"使用设备: {device}")
    
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
            # 方法 1: 采样（快速，多样性高）
            for i in range(num_solutions_per_instance):
                out = model.policy(
                    td, 
                    decode_type="sampling",
                    temperature=temperature,
                    return_actions=True
                )
                cost = env.get_reward(td, out['actions'])
                all_solutions.append(out['actions'].cpu())
                all_costs.append(cost.cpu())
                
                if (i + 1) % 10 == 0:
                    elapsed = time.time() - start_time
                    avg_time = elapsed / (i + 1)
                    eta = avg_time * (num_solutions_per_instance - i - 1)
                    print(f"  进度: {i + 1}/{num_solutions_per_instance} "
                          f"({elapsed:.1f}s, ETA: {eta:.1f}s)")
        
        elif method == "pomo":
            # 方法 2: POMO（高质量）
            print(f"  使用 POMO 生成 {num_solutions_per_instance} 个起点...")
            out = model.policy(
                td,
                decode_type="greedy",
                num_starts=num_solutions_per_instance,
                return_actions=True
            )
            # out['actions'] shape: [num_instances, num_starts, seq_len]
            for i in range(num_solutions_per_instance):
                sol = out['actions'][:, i, :]
                cost = env.get_reward(td, sol)
                all_solutions.append(sol.cpu())
                all_costs.append(cost.cpu())
        
        elif method == "beam_search":
            # 方法 3: 束搜索
            print(f"  使用束搜索（beam_width={num_solutions_per_instance}）...")
            out = model.policy(
                td,
                decode_type="beam_search",
                beam_width=num_solutions_per_instance,
                return_actions=True
            )
            # 返回 beam_width 个解
            for i in range(num_solutions_per_instance):
                sol = out['actions'][:, i, :]
                cost = env.get_reward(td, sol)
                all_solutions.append(sol.cpu())
                all_costs.append(cost.cpu())
        
        else:
            raise ValueError(f"未知方法: {method}")
    
    total_time = time.time() - start_time
    
    # 整理结果
    all_solutions = torch.stack(all_solutions, dim=1)  # [num_instances, num_solutions, seq_len]
    all_costs = torch.stack(all_costs, dim=1)  # [num_instances, num_solutions]
    
    # 找到每个实例的最优解
    best_indices = torch.argmin(all_costs, dim=1)
    best_solutions = all_solutions[torch.arange(num_instances), best_indices]
    best_costs = all_costs[torch.arange(num_instances), best_indices]
    
    # 统计信息
    results = {
        'all_solutions': all_solutions,
        'all_costs': all_costs,
        'best_solutions': best_solutions,
        'best_costs': best_costs,
        'avg_cost': all_costs.mean().item(),
        'std_cost': all_costs.std().item(),
        'best_avg_cost': best_costs.mean().item(),
        'worst_cost': all_costs.max().item(),
        'best_cost': all_costs.min().item(),
        'total_time': total_time,
        'avg_time_per_solution': total_time / (num_instances * num_solutions_per_instance),
        'method': method,
        'temperature': temperature if method == "sampling" else None,
    }
    
    # 打印统计
    print("\n" + "="*60)
    print("生成完成！")
    print("="*60)
    print(f"总耗时: {total_time:.2f}s")
    print(f"平均每解: {results['avg_time_per_solution']*1000:.2f}ms")
    print(f"\n成本统计:")
    print(f"  所有解平均: {results['avg_cost']:.2f}")
    print(f"  标准差: {results['std_cost']:.2f}")
    print(f"  最优解平均: {results['best_avg_cost']:.2f}")
    print(f"  最好: {results['best_cost']:.2f}")
    print(f"  最差: {results['worst_cost']:.2f}")
    print(f"  改进幅度: {(results['avg_cost'] - results['best_avg_cost']) / results['avg_cost'] * 100:.2f}%")
    print("="*60)
    
    # 保存结果
    if save_path:
        torch.save(results, save_path)
        print(f"\n结果已保存到: {save_path}")
    
    return results


def compare_methods(model_path, num_instances=10, num_solutions=50):
    """
    对比不同生成方法的性能
    """
    print("\n" + "="*60)
    print("对比不同生成方法")
    print("="*60)
    
    methods = [
        ("sampling", {"temperature": 1.0}),
        ("sampling", {"temperature": 1.5}),
        ("pomo", {}),
    ]
    
    results_comparison = {}
    
    for method, kwargs in methods:
        method_name = f"{method}_T{kwargs.get('temperature', 'N/A')}"
        print(f"\n测试方法: {method_name}")
        print("-"*60)
        
        results = generate_diverse_solutions(
            model_path=model_path,
            num_instances=num_instances,
            num_solutions_per_instance=num_solutions,
            method=method,
            temperature=kwargs.get('temperature', 1.0),
            save_path=f"solutions_{method_name}.pt"
        )
        
        results_comparison[method_name] = {
            'avg_cost': results['avg_cost'],
            'best_avg_cost': results['best_avg_cost'],
            'std_cost': results['std_cost'],
            'total_time': results['total_time'],
            'avg_time_per_solution': results['avg_time_per_solution'],
        }
    
    # 打印对比表格
    print("\n" + "="*60)
    print("方法对比")
    print("="*60)
    print(f"{'方法':<20} {'平均成本':<12} {'最优成本':<12} {'标准差':<10} {'总时间(s)':<12} {'每解(ms)':<10}")
    print("-"*60)
    
    for method_name, stats in results_comparison.items():
        print(f"{method_name:<20} "
              f"{stats['avg_cost']:<12.2f} "
              f"{stats['best_avg_cost']:<12.2f} "
              f"{stats['std_cost']:<10.2f} "
              f"{stats['total_time']:<12.2f} "
              f"{stats['avg_time_per_solution']*1000:<10.2f}")
    
    print("="*60)
    
    return results_comparison


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="生成 CVRP 解")
    parser.add_argument("--model", type=str, required=True, help="模型检查点路径")
    parser.add_argument("--num_instances", type=int, default=10, help="实例数量")
    parser.add_argument("--num_solutions", type=int, default=100, help="每实例解数")
    parser.add_argument("--method", type=str, default="sampling", 
                       choices=["sampling", "pomo", "beam_search"],
                       help="生成方法")
    parser.add_argument("--temperature", type=float, default=1.0, help="采样温度")
    parser.add_argument("--output", type=str, default="solutions.pt", help="输出文件")
    parser.add_argument("--compare", action="store_true", help="对比不同方法")
    
    args = parser.parse_args()
    
    if args.compare:
        compare_methods(
            model_path=args.model,
            num_instances=args.num_instances,
            num_solutions=args.num_solutions
        )
    else:
        generate_diverse_solutions(
            model_path=args.model,
            num_instances=args.num_instances,
            num_solutions_per_instance=args.num_solutions,
            method=args.method,
            temperature=args.temperature,
            save_path=args.output
        )
