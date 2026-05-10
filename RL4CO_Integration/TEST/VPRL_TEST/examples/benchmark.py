"""
VPRL-GA 集成的性能基准测试

此脚本提供了一个简单的基准测试框架,用于测试 VPRL 性能。
注意: 实际的基准测试需要训练好的 RL4CO 模型和 GA_Java 环境设置。
"""

import os
import sys
import time
import numpy as np
from dataclasses import dataclass
from typing import Dict, List

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from config import VPRLConfig


@dataclass
class BenchmarkResult:
    """单个实例的基准测试结果"""
    instance_name: str
    num_customers: int
    num_depots: int
    
    # 时间统计
    vrpl_time: float
    conversion_time: float
    ga_time: float
    total_time: float
    
    # 质量统计
    final_cost: float
    oversampling_improvement: float
    
    # 采样统计
    num_samples_generated: int
    num_solutions_kept: int


def create_benchmark_config(
    enable_vrpl: bool = True,
    num_solutions: int = 20,
    oversampling_ratio: float = 1.2
) -> VPRLConfig:
    """
    创建基准测试配置
    
    参数:
        enable_vrpl: 是否启用 VRPL
        num_solutions: 生成的解数量
        oversampling_ratio: 过采样比例
        
    返回:
        VPRLConfig 实例
    """
    return VPRLConfig(
        enable_vrpl=enable_vrpl,
        num_solutions_needed=num_solutions,
        oversampling_ratio=oversampling_ratio,
        log_level="INFO"
    )


def benchmark_instance(
    instance_path: str,
    config: VPRLConfig
) -> BenchmarkResult:
    """
    对单个实例进行基准测试
    
    参数:
        instance_path: 实例文件路径
        config: VPRL 配置
        
    返回:
        BenchmarkResult
        
    注意:
        这是一个占位符实现。实际实现需要:
        - 训练好的 RL4CO 模型
        - GA_Java 环境设置
        - 从 Cordeau 格式加载实例
    """
    print(f"\nBenchmarking: {os.path.basename(instance_path)}")
    print(f"  VRPL enabled: {config.enable_vrpl}")
    print(f"  Solutions needed: {config.num_solutions_needed}")
    print(f"  Oversampling ratio: {config.oversampling_ratio}")
    
    # 占位符时间统计
    vrpl_time = 0.0
    conversion_time = 0.0
    ga_time = 0.0
    
    if config.enable_vrpl:
        # 模拟 VRPL 生成时间
        num_samples = int(config.num_solutions_needed * config.oversampling_ratio)
        vrpl_time = num_samples * 0.1  # 每个样本约 0.1 秒(占位符)
        conversion_time = 0.05  # 占位符
    
    # 模拟 GA 时间
    ga_time = 25.0  # 占位符
    
    total_time = vrpl_time + conversion_time + ga_time
    
    result = BenchmarkResult(
        instance_name=os.path.basename(instance_path),
        num_customers=50,  # 占位符
        num_depots=4,  # 占位符
        vrpl_time=vrpl_time,
        conversion_time=conversion_time,
        ga_time=ga_time,
        total_time=total_time,
        final_cost=580.0,  # 占位符
        oversampling_improvement=7.5,  # 占位符
        num_samples_generated=int(config.num_solutions_needed * config.oversampling_ratio),
        num_solutions_kept=config.num_solutions_needed
    )
    
    print(f"  Results:")
    print(f"    VRPL time: {vrpl_time:.2f}s")
    print(f"    Conversion time: {conversion_time:.2f}s")
    print(f"    GA time: {ga_time:.2f}s")
    print(f"    Total time: {total_time:.2f}s")
    print(f"    Oversampling improvement: {result.oversampling_improvement:.1f}%")
    
    return result


def compare_with_without_vrpl(instance_path: str) -> Dict:
    """
    比较使用和不使用 VRPL 的性能
    
    参数:
        instance_path: 实例文件路径
        
    返回:
        包含比较结果的字典
    """
    print("\n" + "="*60)
    print("Comparison: With vs Without VRPL")
    print("="*60)
    
    # 不使用 VRPL 的基准测试
    config_no_vrpl = create_benchmark_config(enable_vrpl=False)
    result_no_vrpl = benchmark_instance(instance_path, config_no_vrpl)
    
    # 使用 VRPL 的基准测试
    config_with_vrpl = create_benchmark_config(enable_vrpl=True)
    result_with_vrpl = benchmark_instance(instance_path, config_with_vrpl)
    
    # 计算开销
    vrpl_overhead = (result_with_vrpl.total_time - result_no_vrpl.total_time) / result_no_vrpl.total_time * 100
    
    print("\n" + "="*60)
    print("Comparison Results:")
    print("="*60)
    print(f"Without VRPL: {result_no_vrpl.total_time:.2f}s")
    print(f"With VRPL:    {result_with_vrpl.total_time:.2f}s")
    print(f"VRPL overhead: {vrpl_overhead:.1f}%")
    print(f"Oversampling improvement: {result_with_vrpl.oversampling_improvement:.1f}%")
    
    return {
        'without_vrpl': result_no_vrpl,
        'with_vrpl': result_with_vrpl,
        'vrpl_overhead_percent': vrpl_overhead
    }


def test_oversampling_ratios(instance_path: str) -> List[BenchmarkResult]:
    """
    测试不同的过采样比例
    
    参数:
        instance_path: 实例文件路径
        
    返回:
        基准测试结果列表
    """
    print("\n" + "="*60)
    print("Testing Different Oversampling Ratios")
    print("="*60)
    
    ratios = [1.0, 1.2, 1.5, 2.0]
    results = []
    
    for ratio in ratios:
        config = create_benchmark_config(
            enable_vrpl=True,
            num_solutions=20,
            oversampling_ratio=ratio
        )
        result = benchmark_instance(instance_path, config)
        results.append(result)
    
    print("\n" + "="*60)
    print("Oversampling Ratio Comparison:")
    print("="*60)
    print(f"{'Ratio':<10} {'Samples':<10} {'Time':<10} {'Improvement':<15}")
    print("-" * 60)
    
    for result in results:
        ratio = result.num_samples_generated / result.num_solutions_kept
        print(f"{ratio:<10.1f} {result.num_samples_generated:<10} "
              f"{result.vrpl_time:<10.2f} {result.oversampling_improvement:<15.1f}%")
    
    return results


def print_summary(results: List[BenchmarkResult]):
    """
    打印基准测试结果摘要
    
    参数:
        results: 基准测试结果列表
    """
    print("\n" + "="*60)
    print("Benchmark Summary")
    print("="*60)
    
    print(f"\n{'Instance':<15} {'Customers':<12} {'VRPL':<10} {'GA':<10} {'Total':<10}")
    print("-" * 60)
    
    for result in results:
        print(f"{result.instance_name:<15} {result.num_customers:<12} "
              f"{result.vrpl_time:<10.2f} {result.ga_time:<10.2f} {result.total_time:<10.2f}")
    
    # 计算平均值
    avg_vrpl = np.mean([r.vrpl_time for r in results])
    avg_ga = np.mean([r.ga_time for r in results])
    avg_total = np.mean([r.total_time for r in results])
    avg_improvement = np.mean([r.oversampling_improvement for r in results])
    
    print("-" * 60)
    print(f"{'Average':<15} {'':<12} {avg_vrpl:<10.2f} {avg_ga:<10.2f} {avg_total:<10.2f}")
    print(f"\nAverage oversampling improvement: {avg_improvement:.1f}%")


def main():
    """
    主基准测试函数
    
    注意:
        这是一个演示脚本。实际的基准测试需要:
        1. 为不同实例规模训练 RL4CO 模型
        2. 设置 GA_Java 环境
        3. 准备 Cordeau 实例文件
        4. 更新下面的实例路径
    """
    print("\n" + "="*60)
    print("VPRL Performance Benchmark")
    print("="*60)
    print("\nNote: This is a demonstration script with placeholder data.")
    print("For actual benchmarking, you need:")
    print("  1. Trained RL4CO models")
    print("  2. GA_Java setup")
    print("  3. Cordeau instance files")
    
    # 占位符实例路径
    instances = [
        "data/p01.dat",
        "data/p03.dat",
        "data/p04.dat"
    ]
    
    # 测试 1: 基本基准测试
    print("\n" + "="*60)
    print("Test 1: Basic Benchmark")
    print("="*60)
    
    results = []
    config = create_benchmark_config(enable_vrpl=True)
    
    for instance_path in instances:
        result = benchmark_instance(instance_path, config)
        results.append(result)
    
    print_summary(results)
    
    # 测试 2: 使用与不使用 VRPL 的对比
    print("\n" + "="*60)
    print("Test 2: With vs Without VRPL")
    print("="*60)
    
    comparison = compare_with_without_vrpl(instances[0])
    
    # 测试 3: 不同的过采样比例
    print("\n" + "="*60)
    print("Test 3: Oversampling Ratios")
    print("="*60)
    
    oversampling_results = test_oversampling_ratios(instances[0])
    
    print("\n" + "="*60)
    print("Benchmark Complete")
    print("="*60)
    print("\nKey Findings (Placeholder):")
    print("  • VRPL overhead: ~5% of total time")
    print("  • Oversampling (1.2x) adds ~20% to VRPL time")
    print("  • Quality improvement: 5-10% from oversampling")
    print("  • Recommended ratio: 1.2 (best quality/time trade-off)")


if __name__ == "__main__":
    main()
