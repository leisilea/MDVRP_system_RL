"""
Basic usage example for VPRL-Enhanced GA solver
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from VPRL import VPRLSampler, VPRLConfig


def main():
    """Basic usage example"""
    
    print("="*60)
    print("VPRL-Enhanced GA Solver - Basic Usage Example")
    print("="*60)
    
    # Method 1: Use default configuration
    print("\n1. Using default configuration:")
    sampler = VPRLSampler()
    
    # Method 2: Load from config file
    print("\n2. Loading from config file:")
    config = VPRLConfig.from_file("VPRL/config.json")
    sampler = VPRLSampler(config=config)
    
    # Method 3: Custom configuration
    print("\n3. Using custom configuration:")
    config = VPRLConfig(
        model_path="models/vrpl_cvrp100.ckpt",
        num_solutions_needed=20,
        oversampling_ratio=1.2,
        sampling_temperature=1.0,
        vrpl_ratio=0.5,
        enable_vrpl=True,
        convergence_report_interval=10,
        assignment_strategy="nearest",
        device="cuda"
    )
    sampler = VPRLSampler(config=config)
    
    # Load MDVRP instance
    print("\n4. Loading MDVRP instance:")
    instance_file = "MDVRP-Instances/dat/p01"
    
    if not os.path.exists(instance_file):
        print(f"Instance file not found: {instance_file}")
        print("Please ensure MDVRP-Instances directory exists")
        return
    
    # Solve with VRPL enhancement
    print("\n5. Solving with VRPL enhancement:")
    result = sampler.solve(
        instance_data=instance_file,
        enable_vrpl=True,
        num_solutions_needed=20,
        vrpl_ratio=0.5
    )
    
    # Display results
    print("\n" + "="*60)
    print("Results:")
    print("="*60)
    print(f"Total cost: {result['total_cost']:.2f}")
    print(f"Compute time: {result['compute_time']:.2f}s")
    print(f"Number of routes: {result['num_vehicles']}")
    
    # Display performance metrics
    if result['performance_metrics']:
        metrics = result['performance_metrics']
        print(f"\nPerformance Metrics:")
        print(f"  Model used: {metrics.model_used}")
        print(f"  VRPL generation time: {metrics.vrpl_generation_time:.2f}s")
        print(f"  Samples generated: {metrics.vrpl_num_samples_generated}")
        print(f"  Solutions kept: {metrics.vrpl_num_solutions_kept}")
        print(f"  Oversampling improvement: {metrics.oversampling_improvement:.1f}%")
        print(f"  GA iterations: {metrics.ga_iterations}")
        print(f"  Valid solutions: {metrics.num_valid_solutions}")
        print(f"  Invalid solutions: {metrics.num_invalid_solutions}")
        
        # Display convergence curve
        if metrics.convergence_curve:
            print(f"\nConvergence curve ({len(metrics.convergence_curve)} points):")
            for point in metrics.convergence_curve[:5]:  # Show first 5
                print(f"  Generation {point.generation}: {point.best_cost:.2f} "
                      f"(at {point.timestamp:.1f}s)")
            if len(metrics.convergence_curve) > 5:
                print(f"  ... ({len(metrics.convergence_curve) - 5} more points)")
    
    print("\n" + "="*60)
    print("Example completed!")
    print("="*60)


if __name__ == "__main__":
    main()
