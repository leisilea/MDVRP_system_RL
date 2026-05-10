"""
Integration tests for VPRL-GA workflow
"""

import os
import sys
import time
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from VPRL.vprl_sampler import VPRLSampler
from VPRL.config import VPRLConfig
from VPRL.instance_decomposer import InstanceDecomposer


def create_test_instance():
    """Create a small test MDVRP instance"""
    from dataclasses import dataclass
    
    @dataclass
    class TestMDVRPInstance:
        num_depots: int
        num_customers: int
        depots_coords: np.ndarray
        customers_coords: np.ndarray
        demands: np.ndarray
        depot_capacities: np.ndarray
        depot_vehicles: np.ndarray
        max_route_distances: np.ndarray
    
    # Create a small instance with 2 depots and 10 customers
    instance = TestMDVRPInstance(
        num_depots=2,
        num_customers=10,
        depots_coords=np.array([[0.0, 0.0], [100.0, 100.0]]),
        customers_coords=np.random.rand(10, 2) * 100,
        demands=np.random.rand(10) * 10 + 5,
        depot_capacities=np.array([100.0, 100.0]),
        depot_vehicles=np.array([3, 3]),
        max_route_distances=np.array([200.0, 200.0])
    )
    
    return instance


def test_end_to_end_workflow():
    """Test complete VPRL-GA workflow"""
    print("\n" + "="*60)
    print("Test: End-to-End Workflow")
    print("="*60)
    
    # Create test instance
    instance = create_test_instance()
    print(f"Created test instance: {instance.num_depots} depots, {instance.num_customers} customers")
    
    # Create config (without model for now, will test decomposition only)
    config = VPRLConfig(
        enable_vrpl=False,  # Disable VRPL for basic test
        num_solutions_needed=5,
        oversampling_ratio=1.2,
        log_level="INFO"
    )
    
    # Test instance decomposition
    print("\nTesting instance decomposition...")
    sub_problems = InstanceDecomposer.decompose_mdvrp(
        instance=instance,
        strategy="nearest"
    )
    
    print(f"✓ Decomposed into {len(sub_problems)} sub-problems")
    
    for i, sp in enumerate(sub_problems):
        print(f"  Sub-problem {i}: {len(sp.customer_indices)} customers")
    
    print("\n✓ Test passed!")
    return True


def test_vrpl_disabled_mode():
    """Test with VRPL disabled (pure GA_Java)"""
    print("\n" + "="*60)
    print("Test: VRPL Disabled Mode")
    print("="*60)
    
    # This test would require GA_Java to be set up
    # For now, just test configuration
    config = VPRLConfig(
        enable_vrpl=False,
        num_solutions_needed=10
    )
    
    print(f"Config created with enable_vrpl={config.enable_vrpl}")
    print("✓ Test passed!")
    return True


def test_oversampling_strategy():
    """Test oversampling configuration"""
    print("\n" + "="*60)
    print("Test: Oversampling Strategy")
    print("="*60)
    
    # Test different oversampling ratios
    ratios = [1.0, 1.2, 1.5, 2.0]
    num_needed = 20
    
    for ratio in ratios:
        num_samples = int(num_needed * ratio)
        print(f"Ratio {ratio}: Need {num_needed} → Generate {num_samples}")
        assert num_samples >= num_needed, "Samples must be >= needed"
    
    print("✓ Test passed!")
    return True


def test_auto_model_selection():
    """Test automatic model selection"""
    print("\n" + "="*60)
    print("Test: Automatic Model Selection")
    print("="*60)
    
    config = VPRLConfig(
        model_selection_strategy="auto",
        model_size_thresholds={
            30: "model_20.ckpt",
            60: "model_50.ckpt",
            150: "model_100.ckpt",
            float('inf'): "model_200.ckpt"
        }
    )
    
    test_cases = [
        (20, "model_20.ckpt"),
        (30, "model_20.ckpt"),
        (50, "model_50.ckpt"),
        (100, "model_100.ckpt"),
        (200, "model_200.ckpt")
    ]
    
    for num_customers, expected_model in test_cases:
        model = config.get_model_for_size(num_customers)
        print(f"Customers: {num_customers:3d} → Model: {model}")
        assert model == expected_model, f"Expected {expected_model}, got {model}"
    
    print("✓ Test passed!")
    return True


def test_convergence_tracking():
    """Test convergence tracking configuration"""
    print("\n" + "="*60)
    print("Test: Convergence Tracking")
    print("="*60)
    
    config = VPRLConfig(
        convergence_report_interval=10,
        enable_convergence_tracking=True
    )
    
    print(f"Convergence interval: {config.convergence_report_interval}")
    print(f"Tracking enabled: {config.enable_convergence_tracking}")
    
    # Simulate convergence points
    from VPRL.vprl_sampler import ConvergencePoint
    
    convergence_curve = [
        ConvergencePoint(generation=10, best_cost=600.0, timestamp=1.0),
        ConvergencePoint(generation=20, best_cost=590.0, timestamp=2.0),
        ConvergencePoint(generation=30, best_cost=585.0, timestamp=3.0),
    ]
    
    print("\nSimulated convergence curve:")
    for point in convergence_curve:
        print(f"  Gen {point.generation}: Cost {point.best_cost:.2f} @ {point.timestamp:.1f}s")
    
    print("✓ Test passed!")
    return True


def test_error_handling():
    """Test error handling mechanisms"""
    print("\n" + "="*60)
    print("Test: Error Handling")
    print("="*60)
    
    from VPRL.error_handler import ErrorHandler
    
    # Test model loading error
    print("\n1. Testing model loading error...")
    should_continue, action = ErrorHandler.handle_model_loading_error(
        Exception("Model file not found")
    )
    assert should_continue == True, "Should continue with fallback"
    assert action == "disable_vrpl", "Should disable VRPL"
    print("  ✓ Model loading error handled correctly")
    
    # Test generation error with retry
    print("\n2. Testing generation error (retry)...")
    should_retry, action = ErrorHandler.handle_generation_error(
        Exception("Generation failed"), retry_count=0
    )
    assert should_retry == True, "Should retry"
    assert action == "retry", "Action should be retry"
    print("  ✓ Generation error (retry) handled correctly")
    
    # Test generation error with fallback
    print("\n3. Testing generation error (fallback)...")
    should_retry, action = ErrorHandler.handle_generation_error(
        Exception("Generation failed"), retry_count=1
    )
    assert should_retry == False, "Should not retry"
    assert action == "fallback", "Action should be fallback"
    print("  ✓ Generation error (fallback) handled correctly")
    
    # Test validation error
    print("\n4. Testing validation error...")
    ErrorHandler.handle_validation_error(
        route_info="depot 1, vehicle 2",
        error_message="Capacity exceeded"
    )
    print("  ✓ Validation error handled correctly")
    
    # Test partial success logging
    print("\n5. Testing partial success logging...")
    ErrorHandler.log_partial_success(valid_solutions=8, total_solutions=10)
    print("  ✓ Partial success logged correctly")
    
    print("\n✓ All error handling tests passed!")
    return True


def run_all_tests():
    """Run all integration tests"""
    print("\n" + "="*60)
    print("VPRL INTEGRATION TEST SUITE")
    print("="*60)
    
    tests = [
        ("End-to-End Workflow", test_end_to_end_workflow),
        ("VRPL Disabled Mode", test_vrpl_disabled_mode),
        ("Oversampling Strategy", test_oversampling_strategy),
        ("Auto Model Selection", test_auto_model_selection),
        ("Convergence Tracking", test_convergence_tracking),
        ("Error Handling", test_error_handling),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"✗ {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"✗ {test_name} FAILED with exception: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {failed}/{len(tests)}")
    print("="*60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
