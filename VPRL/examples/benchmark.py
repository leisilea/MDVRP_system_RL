"""
Performance benchmark for VPRL-GA integration

This script provides a simple benchmark framework for testing VPRL performance.
Note: Actual benchmarking requires trained RL4CO models and GA_Java setup.
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
    """Benchmark result for a single instance"""
    instance_name: str
    num_customers: int
    num_depots: int
    
    # Timing
    vrpl_time: float
    conversion_time: float
    ga_time: float
    total_time: float
    
    # Quality
    final_cost: float
    oversampling_improvement: float
    
    # Sampling
    num_samples_generated: int
    num_solutions_kept: int


def create_benchmark_config(
    enable_vrpl: bool = True,
    num_solutions: int = 20,
    oversampling_ratio: float = 1.2
) -> VPRLConfig:
    """
    Create configuration for benchmarking
    
    Args:
        enable_vrpl: Whether to enable VRPL
        num_solutions: Number of solutions to generate
        oversampling_ratio: Oversampling ratio
        
    Returns:
        VPRLConfig instance
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
    Benchmark a single instance
    
    Args:
        instance_path: Path to instance file
        config: VPRL configuration
        
    Returns:
        BenchmarkResult
        
    Note:
        This is a placeholder. Actual implementation requires:
        - Trained RL4CO models
        - GA_Java setup
        - Instance loading from Cordeau format
    """
    print(f"\nBenchmarking: {os.path.basename(instance_path)}")
    print(f"  VRPL enabled: {config.enable_vrpl}")
    print(f"  Solutions needed: {config.num_solutions_needed}")
    print(f"  Oversampling ratio: {config.oversampling_ratio}")
    
    # Placeholder timing
    vrpl_time = 0.0
    conversion_time = 0.0
    ga_time = 0.0
    
    if config.enable_vrpl:
        # Simulate VRPL generation time
        num_samples = int(config.num_solutions_needed * config.oversampling_ratio)
        vrpl_time = num_samples * 0.1  # ~0.1s per sample (placeholder)
        conversion_time = 0.05  # Placeholder
    
    # Simulate GA time
    ga_time = 25.0  # Placeholder
    
    total_time = vrpl_time + conversion_time + ga_time
    
    result = BenchmarkResult(
        instance_name=os.path.basename(instance_path),
        num_customers=50,  # Placeholder
        num_depots=4,  # Placeholder
        vrpl_time=vrpl_time,
        conversion_time=conversion_time,
        ga_time=ga_time,
        total_time=total_time,
        final_cost=580.0,  # Placeholder
        oversampling_improvement=7.5,  # Placeholder
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
    Compare performance with and without VRPL
    
    Args:
        instance_path: Path to instance file
        
    Returns:
        Dictionary with comparison results
    """
    print("\n" + "="*60)
    print("Comparison: With vs Without VRPL")
    print("="*60)
    
    # Benchmark without VRPL
    config_no_vrpl = create_benchmark_config(enable_vrpl=False)
    result_no_vrpl = benchmark_instance(instance_path, config_no_vrpl)
    
    # Benchmark with VRPL
    config_with_vrpl = create_benchmark_config(enable_vrpl=True)
    result_with_vrpl = benchmark_instance(instance_path, config_with_vrpl)
    
    # Calculate overhead
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
    Test different oversampling ratios
    
    Args:
        instance_path: Path to instance file
        
    Returns:
        List of benchmark results
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
    Print summary of benchmark results
    
    Args:
        results: List of benchmark results
    """
    print("\n" + "="*60)
    print("Benchmark Summary")
    print("="*60)
    
    print(f"\n{'Instance':<15} {'Customers':<12} {'VRPL':<10} {'GA':<10} {'Total':<10}")
    print("-" * 60)
    
    for result in results:
        print(f"{result.instance_name:<15} {result.num_customers:<12} "
              f"{result.vrpl_time:<10.2f} {result.ga_time:<10.2f} {result.total_time:<10.2f}")
    
    # Calculate averages
    avg_vrpl = np.mean([r.vrpl_time for r in results])
    avg_ga = np.mean([r.ga_time for r in results])
    avg_total = np.mean([r.total_time for r in results])
    avg_improvement = np.mean([r.oversampling_improvement for r in results])
    
    print("-" * 60)
    print(f"{'Average':<15} {'':<12} {avg_vrpl:<10.2f} {avg_ga:<10.2f} {avg_total:<10.2f}")
    print(f"\nAverage oversampling improvement: {avg_improvement:.1f}%")


def main():
    """
    Main benchmark function
    
    Note:
        This is a demonstration script. For actual benchmarking:
        1. Train RL4CO models for different instance sizes
        2. Set up GA_Java environment
        3. Prepare Cordeau instance files
        4. Update instance paths below
    """
    print("\n" + "="*60)
    print("VPRL Performance Benchmark")
    print("="*60)
    print("\nNote: This is a demonstration script with placeholder data.")
    print("For actual benchmarking, you need:")
    print("  1. Trained RL4CO models")
    print("  2. GA_Java setup")
    print("  3. Cordeau instance files")
    
    # Placeholder instance paths
    instances = [
        "data/p01.dat",
        "data/p03.dat",
        "data/p04.dat"
    ]
    
    # Test 1: Basic benchmark
    print("\n" + "="*60)
    print("Test 1: Basic Benchmark")
    print("="*60)
    
    results = []
    config = create_benchmark_config(enable_vrpl=True)
    
    for instance_path in instances:
        result = benchmark_instance(instance_path, config)
        results.append(result)
    
    print_summary(results)
    
    # Test 2: With vs Without VRPL
    print("\n" + "="*60)
    print("Test 2: With vs Without VRPL")
    print("="*60)
    
    comparison = compare_with_without_vrpl(instances[0])
    
    # Test 3: Different oversampling ratios
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
