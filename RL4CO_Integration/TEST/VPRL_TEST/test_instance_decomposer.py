"""
Unit tests for Instance Decomposer
"""

import sys
import os
import numpy as np
import torch

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from VPRL.instance_decomposer import InstanceDecomposer, CVRPSubProblem


class MockMDVRPInstance:
    """Mock MDVRP instance for testing"""
    def __init__(self, num_depots=2, num_customers=10):
        self.num_depots = num_depots
        self.num_customers = num_customers
        
        # Random coordinates
        np.random.seed(42)
        self.depots_coords = np.random.rand(num_depots, 2) * 100
        self.customers_coords = np.random.rand(num_customers, 2) * 100
        self.demands = np.random.randint(5, 20, num_customers).astype(float)
        self.depot_capacities = np.full(num_depots, 100.0)
        self.depot_vehicles = np.full(num_depots, 5)
        self.max_route_distances = np.full(num_depots, 200.0)


def test_customer_assignment_nearest():
    """Test nearest depot assignment strategy"""
    print("\n" + "="*60)
    print("Test: Customer Assignment - Nearest Strategy")
    print("="*60)
    
    customers = np.array([[10, 10], [20, 20], [80, 80], [90, 90]])
    depots = np.array([[15, 15], [85, 85]])
    
    assignments = InstanceDecomposer.assign_customers_to_depots(
        customers=customers,
        depots=depots,
        strategy="nearest"
    )
    
    print(f"Customers: {customers.tolist()}")
    print(f"Depots: {depots.tolist()}")
    print(f"Assignments: {assignments}")
    
    # Verify assignments
    assert 0 in assignments[0] or 1 in assignments[0], "Depot 0 should have nearby customers"
    assert 2 in assignments[1] or 3 in assignments[1], "Depot 1 should have nearby customers"
    
    # Verify all customers assigned
    all_assigned = []
    for depot_customers in assignments.values():
        all_assigned.extend(depot_customers)
    assert len(all_assigned) == len(customers), "All customers should be assigned"
    
    print("✓ Test passed!")
    return True


def test_customer_assignment_balanced():
    """Test balanced assignment strategy"""
    print("\n" + "="*60)
    print("Test: Customer Assignment - Balanced Strategy")
    print("="*60)
    
    customers = np.random.rand(10, 2) * 100
    depots = np.random.rand(2, 2) * 100
    
    assignments = InstanceDecomposer.assign_customers_to_depots(
        customers=customers,
        depots=depots,
        strategy="balanced"
    )
    
    print(f"Depot 0 customers: {len(assignments[0])}")
    print(f"Depot 1 customers: {len(assignments[1])}")
    
    # Verify balance (should be 5-5 or 6-4)
    assert abs(len(assignments[0]) - len(assignments[1])) <= 1, "Should be balanced"
    
    print("✓ Test passed!")
    return True


def test_tensordict_conversion():
    """Test TensorDict format conversion"""
    print("\n" + "="*60)
    print("Test: TensorDict Conversion")
    print("="*60)
    
    depot_coords = np.array([50.0, 50.0])
    customer_coords = np.array([[10.0, 10.0], [20.0, 20.0], [30.0, 30.0]])
    demands = np.array([10.0, 15.0, 20.0])
    capacity = 100.0
    distance_limit = 200.0
    
    td = InstanceDecomposer.convert_to_tensordict(
        depot_coords=depot_coords,
        customer_coords=customer_coords,
        demands=demands,
        capacity=capacity,
        distance_limit=distance_limit
    )
    
    print(f"TensorDict keys: {td.keys()}")
    print(f"Locs shape: {td['locs'].shape}")
    print(f"Demand shape: {td['demand_linehaul'].shape}")
    print(f"Capacity: {td['capacity']}")
    print(f"Distance limit: {td['distance_limit']}")
    
    # Verify structure
    assert 'locs' in td, "Should have locs"
    assert 'demand_linehaul' in td, "Should have demand_linehaul"
    assert 'capacity' in td, "Should have capacity"
    assert 'distance_limit' in td, "Should have distance_limit"
    
    # Verify shapes
    assert td['locs'].shape == (4, 2), "Locs should be [depot + customers, 2]"
    assert td['demand_linehaul'].shape == (4,), "Demands should be [depot + customers]"
    assert td['demand_linehaul'][0] == 0.0, "Depot demand should be 0"
    
    # Verify types
    assert isinstance(td['locs'], torch.Tensor), "Should be tensor"
    assert td['locs'].dtype == torch.float32, "Should be float32"
    
    print("✓ Test passed!")
    return True


def test_mdvrp_decomposition():
    """Test MDVRP decomposition"""
    print("\n" + "="*60)
    print("Test: MDVRP Decomposition")
    print("="*60)
    
    instance = MockMDVRPInstance(num_depots=2, num_customers=10)
    
    sub_problems = InstanceDecomposer.decompose_mdvrp(
        instance=instance,
        strategy="nearest"
    )
    
    print(f"Number of sub-problems: {len(sub_problems)}")
    
    for i, sub_problem in enumerate(sub_problems):
        print(f"\nSub-problem {i}:")
        print(f"  Depot ID: {sub_problem.depot_id}")
        print(f"  Customers: {len(sub_problem.customer_indices)}")
        print(f"  Capacity: {sub_problem.capacity}")
        print(f"  Distance limit: {sub_problem.distance_limit}")
        print(f"  TensorDict: {sub_problem.tensordict is not None}")
    
    # Verify decomposition
    assert len(sub_problems) > 0, "Should have at least one sub-problem"
    
    # Verify all customers assigned
    total_customers = sum(len(sp.customer_indices) for sp in sub_problems)
    assert total_customers == instance.num_customers, "All customers should be assigned"
    
    # Verify TensorDict created
    for sp in sub_problems:
        assert sp.tensordict is not None, "TensorDict should be created"
    
    print("\n✓ Test passed!")
    return True


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("Running Instance Decomposer Tests")
    print("="*60)
    
    tests = [
        test_customer_assignment_nearest,
        test_customer_assignment_balanced,
        test_tensordict_conversion,
        test_mdvrp_decomposition
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
