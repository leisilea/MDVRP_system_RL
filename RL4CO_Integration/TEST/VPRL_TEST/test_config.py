"""
Unit tests for Configuration Management
"""

import sys
import os
import json
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from VPRL.config import VPRLConfig


def test_default_config():
    """Test default configuration"""
    print("\n" + "="*60)
    print("Test: Default Configuration")
    print("="*60)
    
    config = VPRLConfig()
    
    print(f"Model path: {config.model_path}")
    print(f"Num solutions needed: {config.num_solutions_needed}")
    print(f"Oversampling ratio: {config.oversampling_ratio}")
    print(f"VRPL ratio: {config.vrpl_ratio}")
    print(f"Device: {config.device}")
    
    # Verify defaults
    assert config.num_solutions_needed == 20, "Default should be 20"
    assert config.oversampling_ratio == 1.2, "Default should be 1.2"
    assert config.vrpl_ratio == 0.5, "Default should be 0.5"
    assert config.enable_vrpl == True, "Default should be True"
    assert config.convergence_report_interval == 10, "Default should be 10"
    
    print("\n✓ Test passed!")
    return True


def test_config_file_io():
    """Test configuration file I/O"""
    print("\n" + "="*60)
    print("Test: Configuration File I/O")
    print("="*60)
    
    # Create config
    config = VPRLConfig(
        model_path="test_model.ckpt",
        num_solutions_needed=30,
        oversampling_ratio=1.5,
        vrpl_ratio=0.6
    )
    
    # Write to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        filepath = f.name
    
    try:
        config.to_file(filepath)
        
        # Read back
        loaded_config = VPRLConfig.from_file(filepath)
        
        print(f"Original model path: {config.model_path}")
        print(f"Loaded model path: {loaded_config.model_path}")
        print(f"Original num solutions: {config.num_solutions_needed}")
        print(f"Loaded num solutions: {loaded_config.num_solutions_needed}")
        
        # Verify
        assert loaded_config.model_path == config.model_path, "Model path should match"
        assert loaded_config.num_solutions_needed == config.num_solutions_needed, "Num solutions should match"
        assert loaded_config.oversampling_ratio == config.oversampling_ratio, "Oversampling ratio should match"
        assert loaded_config.vrpl_ratio == config.vrpl_ratio, "VRPL ratio should match"
        
        print("\n✓ Test passed!")
        return True
        
    finally:
        if os.path.exists(filepath):
            os.unlink(filepath)


def test_model_selection():
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
            999999: "model_200.ckpt"
        }
    )
    
    # Test different sizes
    test_cases = [
        (20, "model_20.ckpt"),
        (30, "model_20.ckpt"),
        (50, "model_50.ckpt"),
        (100, "model_100.ckpt"),
        (200, "model_200.ckpt")
    ]
    
    for num_customers, expected_model in test_cases:
        selected_model = config.get_model_for_size(num_customers)
        print(f"Customers: {num_customers:3d} → Model: {selected_model}")
        assert selected_model == expected_model, f"Should select {expected_model} for {num_customers} customers"
    
    print("\n✓ Test passed!")
    return True


def test_fixed_model_selection():
    """Test fixed model selection"""
    print("\n" + "="*60)
    print("Test: Fixed Model Selection")
    print("="*60)
    
    config = VPRLConfig(
        model_path="fixed_model.ckpt",
        model_selection_strategy="fixed"
    )
    
    # Should always return fixed model
    for num_customers in [20, 50, 100, 200]:
        selected_model = config.get_model_for_size(num_customers)
        print(f"Customers: {num_customers:3d} → Model: {selected_model}")
        assert selected_model == "fixed_model.ckpt", "Should always use fixed model"
    
    print("\n✓ Test passed!")
    return True


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("Running Configuration Management Tests")
    print("="*60)
    
    tests = [
        test_default_config,
        test_config_file_io,
        test_model_selection,
        test_fixed_model_selection
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("="*60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
