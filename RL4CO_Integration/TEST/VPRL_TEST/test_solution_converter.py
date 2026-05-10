"""
Unit tests for Solution Converter
"""

import sys
import os
import numpy as np
import torch
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from VPRL.solution_converter import SolutionConverter, Route


def test_index_conversion():
    """Test 0-based to 1-based index conversion"""
    print("\n" + "="*60)
    print("Test: Index Conversion (0-based → 1-based)")
    print("="*60)
    
    # Mock data
    actions = torch.tensor([0, 1, 2, 3, 0])  # RL4CO format: 0=depot, 1+=customers
    depot_id = 0  # 0-based
    customer_mapping = {0: 0, 1: 1, 2: 2}  # local → global (0-based)
    depot_coords = np.array([50.0, 50.0])
    customer_coords = np.array([[10.0, 10.0], [20.0, 20.0], [30.0, 30.0]])
    demands = np.array([10.0, 15.0, 20.0])
    capacity = 100.0
    
    routes = SolutionConverter.convert_rl4co_to_cordeau(
        actions=actions,
        depot_id=depot_id,
        customer_mapping=customer_mapping,
        depot_coords=depot_coords,
        customer_coords=customer_coords,
        demands=demands,
        capacity=capacity
    )
    
    print(f"Actions (RL4CO): {actions.tolist()}")
    print(f"Number of routes: {len(routes)}")
    
    for i, route in enumerate(routes):
        print(f"\nRoute {i+1}:")
        print(f"  Depot ID (1-based): {route.depot_id}")
        print(f"  Customers (1-based): {route.customers}")
        print(f"  Cost: {route.cost:.2f}")
        print(f"  Load: {route.load:.2f}")
    
    # Verify conversion
    assert len(routes) > 0, "Should have at least one route"
    assert routes[0].depot_id == 1, "Depot ID should be 1-based"
    
    # Verify customers are 1-based
    for route in routes:
        for customer_id in route.customers:
            assert customer_id >= 1, f"Customer ID should be 1-based, got {customer_id}"
    
    print("\n✓ Test passed!")
    return True


def test_route_validation():
    """Test route validation logic"""
    print("\n" + "="*60)
    print("Test: Route Validation")
    print("="*60)
    
    # Valid route
    valid_route = Route(
        depot_id=1,
        vehicle_id=1,
        customers=[1, 2, 3],
        cost=100.0,
        load=45.0
    )
    
    is_valid, error_msg = SolutionConverter.validate_route(
        route=valid_route,
        capacity=50.0,
        distance_limit=150.0
    )
    
    print(f"Valid route: {is_valid}, Error: {error_msg}")
    assert is_valid, "Valid route should pass validation"
    
    # Capacity exceeded
    invalid_route_capacity = Route(
        depot_id=1,
        vehicle_id=1,
        customers=[1, 2, 3],
        cost=100.0,
        load=60.0  # Exceeds capacity
    )
    
    is_valid, error_msg = SolutionConverter.validate_route(
        route=invalid_route_capacity,
        capacity=50.0,
        distance_limit=150.0
    )
    
    print(f"Capacity exceeded: {is_valid}, Error: {error_msg}")
    assert not is_valid, "Should fail capacity validation"
    assert "Capacity exceeded" in error_msg, "Should mention capacity"
    
    # Distance exceeded
    invalid_route_distance = Route(
        depot_id=1,
        vehicle_id=1,
        customers=[1, 2, 3],
        cost=200.0,  # Exceeds distance limit
        load=45.0
    )
    
    is_valid, error_msg = SolutionConverter.validate_route(
        route=invalid_route_distance,
        capacity=50.0,
        distance_limit=150.0
    )
    
    print(f"Distance exceeded: {is_valid}, Error: {error_msg}")
    assert not is_valid, "Should fail distance validation"
    assert "Distance exceeded" in error_msg, "Should mention distance"
    
    # Empty route
    empty_route = Route(
        depot_id=1,
        vehicle_id=1,
        customers=[],
        cost=0.0,
        load=0.0
    )
    
    is_valid, error_msg = SolutionConverter.validate_route(
        route=empty_route,
        capacity=50.0,
        distance_limit=150.0
    )
    
    print(f"Empty route: {is_valid}, Error: {error_msg}")
    assert not is_valid, "Should fail empty route validation"
    
    print("\n✓ Test passed!")
    return True


def test_initial_solution_file_format():
    """Test initial solution file format"""
    print("\n" + "="*60)
    print("Test: Initial Solution File Format")
    print("="*60)
    
    routes = [
        Route(depot_id=1, vehicle_id=1, customers=[1, 2, 3], cost=50.0, load=30.0),
        Route(depot_id=1, vehicle_id=2, customers=[4, 5], cost=40.0, load=25.0),
        Route(depot_id=2, vehicle_id=1, customers=[6, 7, 8], cost=60.0, load=35.0),
    ]
    
    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.init', delete=False) as f:
        filepath = f.name
    
    try:
        SolutionConverter.write_initial_solution_file(
            routes=routes,
            filepath=filepath,
            instance_name="test_instance"
        )
        
        # Read and verify
        with open(filepath, 'r') as f:
            content = f.read()
        
        print("File content:")
        print(content)
        
        # Verify format
        assert "# Initial solutions for GA-MDVRP" in content, "Should have header"
        assert "# Instance: test_instance" in content, "Should have instance name"
        assert "SOLUTION 1" in content, "Should have solution marker"
        assert "COST" in content, "Should have cost"
        assert "ROUTE" in content, "Should have routes"
        
        # Verify route format
        assert "ROUTE 1 1: 0 1 2 3 0" in content, "Should have correct route format"
        assert "ROUTE 2 1: 0 6 7 8 0" in content, "Should have depot 2 routes"
        
        print("\n✓ Test passed!")
        return True
        
    finally:
        # Cleanup
        if os.path.exists(filepath):
            os.unlink(filepath)


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("Running Solution Converter Tests")
    print("="*60)
    
    tests = [
        test_index_conversion,
        test_route_validation,
        test_initial_solution_file_format
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
