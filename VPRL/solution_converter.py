"""
Solution Converter: Convert RL4CO solutions to Cordeau format
"""

import numpy as np
import torch
from typing import List, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Route:
    """Route in Cordeau format"""
    depot_id: int          # 1-based depot ID
    vehicle_id: int        # Vehicle ID
    customers: List[int]   # 1-based customer IDs
    cost: float           # Route distance
    load: float           # Total demand


class SolutionConverter:
    """Convert RL4CO solutions to Cordeau format"""
    
    @staticmethod
    def convert_rl4co_to_cordeau(
        actions: torch.Tensor,
        depot_id: int,
        customer_mapping: Dict[int, int],
        depot_coords: np.ndarray,
        customer_coords: np.ndarray,
        demands: np.ndarray,
        capacity: float) -> List[Route]:
        """
        Convert RL4CO action sequence to Cordeau route format
        
        Args:
            actions: RL4CO action tensor [seq_len]
            depot_id: Depot ID (0-based, will be converted to 1-based)
            customer_mapping: Maps local customer index to global customer ID (0-based)
            depot_coords: Depot coordinates [2]
            customer_coords: Customer coordinates [N, 2]
            demands: Customer demands [N]
            capacity: Vehicle capacity
            
        Returns:
            List of routes in Cordeau format
        """
        # Convert actions to numpy
        if isinstance(actions, torch.Tensor):
            actions = actions.cpu().numpy()
        
        # Parse action sequence to extract customer visit order
        # RL4CO actions: 0 = depot, 1+ = customers
        customer_sequence = []
        for action in actions:
            action_int = int(action)
            if action_int > 0:  # Customer (not depot)
                # Convert from RL4CO index (1-based in action) to local index (0-based)
                local_idx = action_int - 1
                if local_idx < len(customer_mapping):
                    customer_sequence.append(local_idx)
        
        # Split into routes based on capacity constraints
        routes = []
        current_route = []
        current_load = 0.0
        vehicle_id = 1
        
        for local_idx in customer_sequence:
            demand = demands[local_idx]
            
            # Check if adding this customer exceeds capacity
            if current_load + demand > capacity and len(current_route) > 0:
                # Finish current route
                route = SolutionConverter._create_route(
                    depot_id=depot_id + 1,  # Convert to 1-based
                    vehicle_id=vehicle_id,
                    local_customers=current_route,
                    customer_mapping=customer_mapping,
                    depot_coords=depot_coords,
                    customer_coords=customer_coords,
                    demands=demands
                )
                routes.append(route)
                
                # Start new route
                current_route = []
                current_load = 0.0
                vehicle_id += 1
            
            # Add customer to current route
            current_route.append(local_idx)
            current_load += demand
        
        # Add final route if not empty
        if len(current_route) > 0:
            route = SolutionConverter._create_route(
                depot_id=depot_id + 1,  # Convert to 1-based
                vehicle_id=vehicle_id,
                local_customers=current_route,
                customer_mapping=customer_mapping,
                depot_coords=depot_coords,
                customer_coords=customer_coords,
                demands=demands
            )
            routes.append(route)
        
        return routes
    
    @staticmethod
    def _create_route(
        depot_id: int,
        vehicle_id: int,
        local_customers: List[int],
        customer_mapping: Dict[int, int],
        depot_coords: np.ndarray,
        customer_coords: np.ndarray,
        demands: np.ndarray) -> Route:
        """Create a Route object with cost and load calculation"""
        
        # Convert local indices to global 1-based customer IDs
        global_customers = [customer_mapping[local_idx] + 1 for local_idx in local_customers]
        
        # Calculate route cost (distance)
        cost = 0.0
        prev_coords = depot_coords
        
        for local_idx in local_customers:
            curr_coords = customer_coords[local_idx]
            cost += np.linalg.norm(curr_coords - prev_coords)
            prev_coords = curr_coords
        
        # Return to depot
        cost += np.linalg.norm(depot_coords - prev_coords)
        
        # Calculate total load
        load = sum(demands[local_idx] for local_idx in local_customers)
        
        return Route(
            depot_id=depot_id,
            vehicle_id=vehicle_id,
            customers=global_customers,
            cost=float(cost),
            load=float(load)
        )
    
    @staticmethod
    def validate_route(
        route: Route,
        capacity: float,
        distance_limit: float) -> Tuple[bool, str]:
        """
        Validate route against constraints
        
        Args:
            route: Route to validate
            capacity: Vehicle capacity
            distance_limit: Maximum route distance
            
        Returns:
            (is_valid, error_message)
        """
        # Check capacity constraint
        if route.load > capacity:
            return False, f"Capacity exceeded: {route.load:.2f} > {capacity:.2f}"
        
        # Check distance constraint (if specified)
        if distance_limit > 0 and route.cost > distance_limit:
            return False, f"Distance exceeded: {route.cost:.2f} > {distance_limit:.2f}"
        
        # Check route is not empty
        if len(route.customers) == 0:
            return False, "Empty route"
        
        return True, ""
    
    @staticmethod
    def write_initial_solution_file(
        routes: List[Route],
        filepath: str,
        instance_name: str) -> None:
        """
        Write initial solutions to file for GA_Java
        
        Args:
            routes: List of routes
            filepath: Output file path
            instance_name: Instance name for reference
        """
        with open(filepath, 'w') as f:
            # Write header
            f.write("# Initial solutions for GA-MDVRP\n")
            f.write(f"# Instance: {instance_name}\n")
            f.write("# Generated by: VPRL_Sampler\n")
            f.write(f"# Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Number of routes: {len(routes)}\n")
            f.write("\n")
            
            # Calculate total cost
            total_cost = sum(route.cost for route in routes)
            
            # Write solution
            f.write("SOLUTION 1\n")
            f.write(f"COST {total_cost:.2f}\n")
            
            # Group routes by depot
            routes_by_depot = {}
            for route in routes:
                if route.depot_id not in routes_by_depot:
                    routes_by_depot[route.depot_id] = []
                routes_by_depot[route.depot_id].append(route)
            
            # Write routes
            for depot_id in sorted(routes_by_depot.keys()):
                depot_routes = routes_by_depot[depot_id]
                for route in depot_routes:
                    # Format: ROUTE depot_id vehicle_id: 0 customer1 customer2 ... 0
                    customers_str = " ".join(str(c) for c in route.customers)
                    f.write(f"ROUTE {route.depot_id} {route.vehicle_id}: 0 {customers_str} 0\n")
            
            f.write("\n")
