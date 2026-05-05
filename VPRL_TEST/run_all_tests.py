"""
Run all VPRL tests
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import test modules
import test_instance_decomposer
import test_solution_converter
import test_config
import test_integration


def main():
    """Run all test suites"""
    print("\n" + "="*70)
    print(" "*20 + "VPRL TEST SUITE")
    print("="*70)
    
    test_suites = [
        ("Instance Decomposer", test_instance_decomposer.run_all_tests),
        ("Solution Converter", test_solution_converter.run_all_tests),
        ("Configuration Management", test_config.run_all_tests),
        ("Integration Tests", test_integration.run_all_tests),
    ]
    
    results = {}
    
    for suite_name, test_func in test_suites:
        print(f"\n{'='*70}")
        print(f"Running: {suite_name}")
        print(f"{'='*70}")
        
        try:
            success = test_func()
            results[suite_name] = "PASSED" if success else "FAILED"
        except Exception as e:
            print(f"\n✗ Test suite crashed: {e}")
            import traceback
            traceback.print_exc()
            results[suite_name] = "CRASHED"
    
    # Summary
    print("\n" + "="*70)
    print(" "*25 + "TEST SUMMARY")
    print("="*70)
    
    for suite_name, result in results.items():
        status_symbol = "✓" if result == "PASSED" else "✗"
        print(f"{status_symbol} {suite_name:<40} {result}")
    
    print("="*70)
    
    # Overall result
    all_passed = all(result == "PASSED" for result in results.values())
    
    if all_passed:
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
