"""
Instance Decomposer: Convert MDVRP to multiple CVRP sub-problems
"""

import numpy as np
import torch
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from tensordict import TensorDict
from sklearn.cluster import KMeans


@dataclass
class CVRPSubProblem:
    """CVRP sub-problem for a single depot"""
    depot_id: int
    depot_coords: np.ndarray       # [2]
    customer_indices: List[int]    # Global customer IDs
    customer_coords: np.ndarray    # [N, 2]
    demands: np.ndarray            # [N]
    capacity: float
    distance_limit: float
    tensordict: Optional[TensorDict] = None


class InstanceDecomposer:
    """Decompose MDVRP into CVRP sub-problems"""
    
    @staticmethod
    def decompose_mdvrp(instance, strategy: str = "nearest") -> List[CVRPSubProblem]:
        """
        Decompose MDVRP into CVRP sub-problems (one per depot)
        
        Args:
            instance: MDVRPInstance object
            strategy: Customer assignment strategy ("nearest", "balanced", "kmeans")
            
        Returns:
            List of CVRP sub-problems
        """
        num_depots = instance.num_depots
        num_customers = instance.num_customers
        
        # Assign customers to depots
        assignments = InstanceDecomposer.assign_customers_to_depots(
            customers=instance.customers_coords,
            depots=instance.depots_coords,
            strategy=strategy
        )
        
        # Create CVRP sub-problems
        sub_problems = []
        for depot_id in range(num_depots):
            customer_indices = assignments.get(depot_id, [])
            
            if len(customer_indices) == 0:
                # Skip empty depots
                continue
            
            # Extract data for this depot's customers
            customer_coords = instance.customers_coords[customer_indices]
            customer_demands = instance.demands[customer_indices]
            
            # Create sub-problem
            sub_problem = CVRPSubProblem(
                depot_id=depot_id,
                depot_coords=instance.depots_coords[depot_id],
                customer_indices=customer_indices,
                customer_coords=customer_coords,
                demands=customer_demands,
                capacity=float(instance.depot_capacities[depot_id]),
                distance_limit=float(instance.max_route_distances[depot_id]) 
                    if instance.max_route_distances is not None else 0.0
            )
            
            # Convert to TensorDict
            sub_problem.tensordict = InstanceDecomposer.convert_to_tensordict(
                depot_coords=sub_problem.depot_coords,
                customer_coords=sub_problem.customer_coords,
                demands=sub_problem.demands,
                capacity=sub_problem.capacity,
                distance_limit=sub_problem.distance_limit
            )
            
            sub_problems.append(sub_problem)
        
        return sub_problems
    
    @staticmethod
    def assign_customers_to_depots(
        customers: np.ndarray,
        depots: np.ndarray,
        strategy: str = "nearest") -> Dict[int, List[int]]:
        """
        Assign customers to depots
        
        Args:
            customers: Customer coordinates [N, 2]
            depots: Depot coordinates [M, 2]
            strategy: Assignment strategy ("nearest", "balanced", "kmeans")
            
        Returns:
            Dictionary mapping depot_id to list of customer indices
        """
        num_customers = len(customers)
        num_depots = len(depots)
        
        if strategy == "nearest":
            # Assign each customer to nearest depot
            assignments = {i: [] for i in range(num_depots)}
            
            for cust_idx in range(num_customers):
                cust_coord = customers[cust_idx]
                distances = np.linalg.norm(depots - cust_coord, axis=1)
                nearest_depot = np.argmin(distances)
                assignments[nearest_depot].append(cust_idx)
        
        elif strategy == "balanced":
            # Balance customer count across depots
            assignments = {i: [] for i in range(num_depots)}
            
            # Calculate distances from each customer to each depot
            distances = np.zeros((num_customers, num_depots))
            for i in range(num_customers):
                for j in range(num_depots):
                    distances[i, j] = np.linalg.norm(customers[i] - depots[j])
            
            # Sort customers by minimum distance to any depot
            min_distances = np.min(distances, axis=1)
            sorted_customers = np.argsort(min_distances)
            
            # Assign customers in round-robin fashion
            for idx, cust_idx in enumerate(sorted_customers):
                depot_id = idx % num_depots
                assignments[depot_id].append(int(cust_idx))
        
        elif strategy == "kmeans":
            # Use K-means clustering
            if num_depots > 1:
                kmeans = KMeans(n_clusters=num_depots, init=depots, n_init=1, random_state=42)
                labels = kmeans.fit_predict(customers)
                
                assignments = {i: [] for i in range(num_depots)}
                for cust_idx, label in enumerate(labels):
                    assignments[int(label)].append(cust_idx)
            else:
                # Single depot: assign all customers
                assignments = {0: list(range(num_customers))}
        
        else:
            raise ValueError(f"Unknown assignment strategy: {strategy}")
        
        return assignments
    
    @staticmethod
    def convert_to_tensordict(
        depot_coords: np.ndarray,
        customer_coords: np.ndarray,
        demands: np.ndarray,
        capacity: float,
        distance_limit: float) -> TensorDict:
        """
        Convert CVRP sub-problem to RL4CO TensorDict format
        
        Creates a complete TensorDict compatible with MTVRPGenerator,
        including all fields required when subsample=True.
        
        Args:
            depot_coords: Depot coordinates [2]
            customer_coords: Customer coordinates [N, 2]
            demands: Customer demands [N]
            capacity: Vehicle capacity
            distance_limit: Maximum route distance
            
        Returns:
            TensorDict compatible with RL4CO MTVRP environment
        """
        num_customers = len(customer_coords)
        
        # Combine depot and customer coordinates
        # RL4CO expects: [depot, customer1, customer2, ...]
        locs = np.vstack([depot_coords.reshape(1, 2), customer_coords])
        
        # Demands: depot has 0 demand
        demand_linehaul = np.concatenate([[0.0], demands])
        
        # Scale demands by capacity (MTVRPGenerator expects scaled demands when scale_demand=True)
        demand_linehaul_scaled = demand_linehaul / capacity
        
        # Convert to tensors and add batch dimension
        td = TensorDict({
            'locs': torch.tensor(locs, dtype=torch.float32).unsqueeze(0),  # [1, N+1, 2]
            'demand_linehaul': torch.tensor(demand_linehaul_scaled, dtype=torch.float32).unsqueeze(0),  # [1, N+1] (scaled)
            'demand_backhaul': torch.zeros(1, num_customers + 1, dtype=torch.float32),  # [1, N+1]
            'backhaul_class': torch.tensor([1.0], dtype=torch.float32).unsqueeze(0),  # [1, 1] - Classic backhaul
            'distance_limit': torch.tensor([distance_limit], dtype=torch.float32).unsqueeze(0),  # [1, 1]
            'time_windows': torch.tensor(
                [[0.0, float('inf')]] * (num_customers + 1), 
                dtype=torch.float32
            ).unsqueeze(0),  # [1, N+1, 2]
            'service_time': torch.zeros(1, num_customers + 1, dtype=torch.float32),  # [1, N+1]
            'vehicle_capacity': torch.tensor([1.0], dtype=torch.float32).unsqueeze(0),  # [1, 1] - Scaled capacity
            'capacity_original': torch.tensor([capacity], dtype=torch.float32).unsqueeze(0),  # [1, 1] - Unscaled capacity
            'open_route': torch.tensor([False], dtype=torch.bool).unsqueeze(0),  # [1, 1]
            'speed': torch.tensor([1.0], dtype=torch.float32).unsqueeze(0),  # [1, 1]
        }, batch_size=[1])
        
        return td
