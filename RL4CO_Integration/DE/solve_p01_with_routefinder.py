"""
P01 RouteFinder Sampling Solver

This script solves the P01 MDVRP instance using RouteFinder VRPL pretrained model
with sampling-based approach. It splits the MDVRP into multiple CVRP subproblems,
solves each using sampling, and aggregates the results.

Usage:
    python solve_p01_with_routefinder.py [--samples N]
    
Arguments:
    --samples: Number of samples per depot (default: 10)
"""

import argparse
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
from tensordict import TensorDict


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class Customer:
    """Customer node data model"""
    id: int
    x: float
    y: float
    demand: float
    service_time: float = 0.0


@dataclass
class Depot:
    """Depot node data model"""
    id: int
    x: float
    y: float


@dataclass
class DepotInfo:
    """Depot constraint information"""
    capacity: float
    max_distance: float


@dataclass
class Route:
    """Route data model"""
    depot_id: int
    customers: List[int]
    cost: float


@dataclass
class Solution:
    """Solution data model"""
    routes: List[Route]
    total_cost: float
    depot_costs: Dict[int, float]
    n_routes: int


@dataclass
class SamplingSolution:
    """Sampling solution result"""
    routes: List[Route]
    cost: float
    all_costs: List[float]
    best_sample_idx: int


# ============================================================================
# P01 Data Loader
# ============================================================================

class P01Loader:
    """Loader for Cordeau format MDVRP instances"""
    
    @staticmethod
    def load_instance(filepath: str) -> Dict[str, Any]:
        """
        Load P01 instance from Cordeau format file
        
        Args:
            filepath: Path to P01 data file
            
        Returns:
            Dictionary containing:
                - n_customers: int
                - n_depots: int
                - n_vehicles: int
                - customers: List[Dict]
                - depots: List[Dict]
                - depots_info: List[Dict]
        """
        with open(filepath, 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
        
        # Line 1: type m n t
        parts = lines[0].split()
        type_id = int(parts[0])
        m = int(parts[1])  # number of vehicles
        n = int(parts[2])  # number of customers
        t = int(parts[3])  # number of depots
        
        # Lines 2 to t+1: D Q (vehicle constraints)
        depots_info = []
        for i in range(1, t + 1):
            parts = lines[i].split()
            D = float(parts[0])  # max distance
            Q = float(parts[1])  # capacity
            depots_info.append({
                'max_distance': D,
                'capacity': Q
            })
        
        # Lines t+2 to n+t+1: customer nodes
        # Lines n+t+2 to n+2t+1: depot nodes
        customers = []
        depots = []
        
        for i in range(t + 1, len(lines)):
            parts = lines[i].split()
            node_id = int(parts[0])
            x = float(parts[1])
            y = float(parts[2])
            service_time = float(parts[3])
            demand = float(parts[4])
            
            # Last t nodes are depots
            if i >= t + 1 + n:
                depots.append({
                    'id': node_id,
                    'x': x,
                    'y': y
                })
            else:
                customers.append({
                    'id': node_id,
                    'x': x,
                    'y': y,
                    'demand': demand,
                    'service_time': service_time
                })
        
        return {
            'n_customers': n,
            'n_depots': t,
            'n_vehicles': m,
            'customers': customers,
            'depots': depots,
            'depots_info': depots_info
        }


# ============================================================================
# Depot Splitter
# ============================================================================

class DepotSplitter:
    """Split MDVRP into multiple CVRP subproblems by assigning customers to nearest depot"""
    
    @staticmethod
    def euclidean_distance(x1: float, y1: float, x2: float, y2: float) -> float:
        """Calculate Euclidean distance between two points"""
        return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)
    
    @staticmethod
    def assign_customers_to_nearest_depot(
        customers: List[Dict],
        depots: List[Dict]
    ) -> Dict[int, List[Dict]]:
        """
        Assign each customer to the nearest depot
        
        Args:
            customers: List of customer dictionaries
            depots: List of depot dictionaries
            
        Returns:
            Dictionary mapping depot_id to list of assigned customers
        """
        depot_customers = {depot['id']: [] for depot in depots}
        
        for customer in customers:
            # Calculate distance to all depots
            min_distance = float('inf')
            nearest_depot_id = None
            
            for depot in depots:
                dist = DepotSplitter.euclidean_distance(
                    customer['x'], customer['y'],
                    depot['x'], depot['y']
                )
                if dist < min_distance:
                    min_distance = dist
                    nearest_depot_id = depot['id']
            
            # Assign customer to nearest depot
            depot_customers[nearest_depot_id].append(customer)
        
        # Print assignment statistics
        print("\n客户分配统计:")
        for depot_id, assigned_customers in depot_customers.items():
            print(f"  仓库 {depot_id}: {len(assigned_customers)} 个客户")
        
        return depot_customers


# ============================================================================
# Format Converter
# ============================================================================

class FormatConverter:
    """Convert CVRP subproblem to RouteFinder TensorDict format"""
    
    @staticmethod
    def convert_to_tensordict(
        depot: Dict,
        customers: List[Dict],
        capacity: float,
        max_distance: float,
        device: str = 'cpu'
    ) -> TensorDict:
        """
        Convert CVRP subproblem to TensorDict format for RouteFinder VRPL model
        
        Args:
            depot: Depot information {'x', 'y'}
            customers: List of customers [{'x', 'y', 'demand'}, ...]
            capacity: Vehicle capacity
            max_distance: Maximum distance limit
            device: Device to place tensors on
            
        Returns:
            TensorDict with fields required by RouteFinder VRPL:
                - locs: [1+n_customers, 2]
                - demand_linehaul: [1+n_customers] (delivery demand)
                - demand_backhaul: [1+n_customers] (pickup demand, all zeros for CVRP)
                - vehicle_capacity: scalar
                - distance_limit: scalar
                - time_windows: [1+n_customers, 2] (all [0, inf] for CVRP)
                - backhaul_class: [1+n_customers] (all 1 for CVRP)
                - open_route: [1] (False for CVRP)
        """
        n_customers = len(customers)
        
        # Create location tensor: [depot, customer1, customer2, ...]
        locs = torch.zeros((1 + n_customers, 2), dtype=torch.float32, device=device)
        locs[0, 0] = depot['x']
        locs[0, 1] = depot['y']
        
        for i, customer in enumerate(customers):
            locs[i + 1, 0] = customer['x']
            locs[i + 1, 1] = customer['y']
        
        # Create demand tensors for VRPL format
        # demand_linehaul: delivery demand (our CVRP demand)
        # demand_backhaul: pickup demand (all zeros for CVRP)
        demand_linehaul = torch.zeros(1 + n_customers, dtype=torch.float32, device=device)
        demand_backhaul = torch.zeros(1 + n_customers, dtype=torch.float32, device=device)
        
        for i, customer in enumerate(customers):
            demand_linehaul[i + 1] = customer['demand']
        
        # Time windows: [0, inf] for all nodes (no time window constraints)
        time_windows = torch.zeros((1 + n_customers, 2), dtype=torch.float32, device=device)
        time_windows[:, 1] = float('inf')
        
        # Service time: all zeros for CVRP (no service time)
        service_time = torch.zeros(1 + n_customers, dtype=torch.float32, device=device)
        
        # Backhaul class: 1 for all (classical backhaul, but we have no backhaul)
        backhaul_class = torch.ones(1 + n_customers, dtype=torch.long, device=device)
        
        # Open route: False (closed routes)
        open_route = torch.tensor([False], dtype=torch.bool, device=device)
        
        # Distance limit
        distance_limit_tensor = torch.tensor([max_distance if max_distance > 0 else float('inf')], 
                                            dtype=torch.float32, device=device)
        
        # Vehicle capacity
        vehicle_capacity_tensor = torch.tensor([capacity], dtype=torch.float32, device=device)
        
        # Create TensorDict with all required fields
        td = TensorDict({
            'locs': locs.unsqueeze(0),  # [1, n+1, 2]
            'demand_linehaul': demand_linehaul.unsqueeze(0),  # [1, n+1]
            'demand_backhaul': demand_backhaul.unsqueeze(0),  # [1, n+1]
            'time_windows': time_windows.unsqueeze(0),  # [1, n+1, 2]
            'service_time': service_time.unsqueeze(0),  # [1, n+1]
            'backhaul_class': backhaul_class.unsqueeze(0),  # [1, n+1]
            'open_route': open_route.unsqueeze(0),  # [1, 1]
            'distance_limit': distance_limit_tensor.unsqueeze(0),  # [1, 1]
            'vehicle_capacity': vehicle_capacity_tensor.unsqueeze(0),  # [1, 1]
            'capacity_original': vehicle_capacity_tensor.unsqueeze(0),  # [1, 1]
        }, batch_size=[1])
        
        return td


# ============================================================================
# Model Loader
# ============================================================================

class ModelLoader:
    """Load RouteFinder VRPL pretrained model"""
    
    @staticmethod
    def load_vrpl_model(checkpoint_path: str, device: str = 'auto') -> torch.nn.Module:
        """
        Load VRPL model from checkpoint (following official RouteFinder test.py)
        
        Args:
            checkpoint_path: Path to checkpoint file
            device: 'auto', 'cuda', or 'cpu'
            
        Returns:
            Loaded model in eval mode
            
        Raises:
            FileNotFoundError: If checkpoint file doesn't exist
        """
        # Apply TorchRL compatibility patch
        try:
            from fix_routefinder_compatibility import add_compatibility_alias
            add_compatibility_alias()
            print("✓ TorchRL兼容性补丁已应用")
        except Exception as e:
            print(f"⚠️  无法应用TorchRL兼容性补丁: {e}")
        
        # Check if checkpoint exists
        checkpoint_file = Path(checkpoint_path)
        if not checkpoint_file.exists():
            print(f"✗ Checkpoint文件不存在: {checkpoint_path}")
            print("\n可用的checkpoint文件:")
            checkpoint_dir = checkpoint_file.parent
            if checkpoint_dir.exists():
                for f in checkpoint_dir.glob('*.ckpt'):
                    print(f"  - {f}")
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")
        
        # Auto-detect device
        if device == 'auto':
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        print(f"✓ 使用设备: {device}")
        
        # Load using RouteFinder's RouteFinderBase model
        # Following official test.py: load to CPU first, then move to device
        try:
            # Import RouteFinder from local routefinder package
            import sys
            sys.path.insert(0, 'RL4CO_Integration/routefinder')
            from routefinder.models.model import RouteFinderBase
            
            print(f"✓ 从checkpoint加载RouteFinder模型...")
            
            # Load to CPU first (avoids RNG state issues)
            model = RouteFinderBase.load_from_checkpoint(
                checkpoint_path,
                map_location="cpu",  # Always load to CPU first
                strict=False
            )
            print(f"✓ 模型加载成功: {checkpoint_path}")
            
            # Set to eval mode
            model.eval()
            
            # Move to target device
            model = model.to(device)
            print(f"✓ 模型已移动到设备: {device}")
            
            return model
            
        except Exception as e:
            print(f"✗ 加载失败: {e}")
            import traceback
            traceback.print_exc()
            raise


# ============================================================================
# Route Decoder
# ============================================================================

class RouteDecoder:
    """Decode model actions to route lists"""
    
    @staticmethod
    def decode_actions(
        actions: torch.Tensor,
        depot_id: int
    ) -> List[Dict[str, Any]]:
        """
        Decode actions tensor to route list
        
        Args:
            actions: Model output actions tensor [batch, seq_len]
            depot_id: Depot ID
            
        Returns:
            List of routes, each containing:
                - depot_id: int
                - customers: List[int]
                - depot: int
        """
        # Convert to numpy
        if isinstance(actions, torch.Tensor):
            actions = actions.cpu().numpy()
        
        # Handle batch dimension
        if len(actions.shape) > 1:
            actions = actions[0]  # Take first batch
        
        routes = []
        current_route = []
        
        for action in actions:
            action_val = int(action)
            
            if action_val == 0:
                # Return to depot - end current route
                if current_route:
                    routes.append({
                        'depot_id': depot_id,
                        'customers': current_route.copy(),
                        'depot': depot_id
                    })
                    current_route = []
            else:
                # Visit customer
                current_route.append(action_val)
        
        # Add last route if exists
        if current_route:
            routes.append({
                'depot_id': depot_id,
                'customers': current_route,
                'depot': depot_id
            })
        
        return routes


# ============================================================================
# Cost Calculator
# ============================================================================

class CostCalculator:
    """Calculate route costs using Euclidean distance"""
    
    @staticmethod
    def calculate_route_cost(
        route: Dict[str, Any],
        nodes: Dict[int, Dict[str, float]]
    ) -> float:
        """
        Calculate single route cost
        
        Args:
            route: Route information {'depot_id', 'customers', 'depot'}
            nodes: All node coordinates {node_id: {'x', 'y'}, ...}
            
        Returns:
            Total route distance (excluding service time)
        """
        if not route['customers']:
            return 0.0
        
        cost = 0.0
        depot_id = route['depot_id']
        customers = route['customers']
        
        # Depot to first customer
        depot_node = nodes[depot_id]
        first_customer = nodes[customers[0]]
        cost += DepotSplitter.euclidean_distance(
            depot_node['x'], depot_node['y'],
            first_customer['x'], first_customer['y']
        )
        
        # Between customers
        for i in range(len(customers) - 1):
            node1 = nodes[customers[i]]
            node2 = nodes[customers[i + 1]]
            cost += DepotSplitter.euclidean_distance(
                node1['x'], node1['y'],
                node2['x'], node2['y']
            )
        
        # Last customer to depot
        last_customer = nodes[customers[-1]]
        cost += DepotSplitter.euclidean_distance(
            last_customer['x'], last_customer['y'],
            depot_node['x'], depot_node['y']
        )
        
        return cost
    
    @staticmethod
    def calculate_solution_cost(
        routes: List[Dict],
        nodes: Dict[int, Dict[str, float]]
    ) -> float:
        """Calculate total solution cost"""
        total_cost = 0.0
        for route in routes:
            total_cost += CostCalculator.calculate_route_cost(route, nodes)
        return total_cost


# ============================================================================
# Sampling Solver
# ============================================================================

class SamplingSolver:
    """Execute sampling-based solving"""
    
    def __init__(self, model: torch.nn.Module, num_samples: int = 10):
        """
        Initialize sampling solver
        
        Args:
            model: VRPL model
            num_samples: Number of samples
        """
        self.model = model
        self.num_samples = num_samples
        self.device = next(model.parameters()).device
    
    def solve(
        self,
        td: TensorDict,
        depot_id: int,
        nodes: Dict[int, Dict[str, float]]
    ) -> Dict[str, Any]:
        """
        Solve single CVRP subproblem
        
        Args:
            td: TensorDict format instance
            depot_id: Depot ID
            nodes: All node coordinates
            
        Returns:
            Dictionary containing:
                - routes: List[Dict]
                - cost: float
                - all_costs: List[float]
                - best_sample_idx: int
        """
        all_costs = []
        all_routes = []
        best_cost = float('inf')
        best_routes = None
        best_idx = -1
        
        print(f"\n仓库 {depot_id} 采样求解:")
        
        # Get environment from model
        env = self.model.env
        
        with torch.no_grad():
            for sample_idx in range(self.num_samples):
                # Reset environment with the TensorDict to initialize all required fields
                # Move to device first
                td_reset = env.reset(td.clone().to(self.device))
                
                # Sample solution
                out = self.model.policy(td_reset, env, decode_type="sampling", return_actions=True)
                
                # Decode actions
                actions = out.get('actions', out.get('action', None))
                if actions is None:
                    print(f"  样本 {sample_idx + 1}: ✗ 无法获取actions")
                    continue
                
                routes = RouteDecoder.decode_actions(actions, depot_id)
                
                # Calculate cost
                cost = CostCalculator.calculate_solution_cost(routes, nodes)
                all_costs.append(cost)
                all_routes.append(routes)
                
                # Check if new best
                is_new_best = cost < best_cost
                if is_new_best:
                    best_cost = cost
                    best_routes = routes
                    best_idx = sample_idx
                
                status = "✓ 新最优" if is_new_best else ""
                print(f"  样本 {sample_idx + 1}: 成本 = {cost:.2f} {status}")
        
        return {
            'routes': best_routes,
            'cost': best_cost,
            'all_costs': all_costs,
            'best_sample_idx': best_idx
        }


# ============================================================================
# Solution Aggregator
# ============================================================================

class SolutionAggregator:
    """Aggregate solutions from all depots"""
    
    @staticmethod
    def aggregate_solutions(
        depot_solutions: Dict[int, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Aggregate all depot solutions
        
        Args:
            depot_solutions: {depot_id: solution, ...}
            
        Returns:
            Dictionary containing:
                - routes: List[Dict]
                - total_cost: float
                - depot_costs: Dict[int, float]
                - n_routes: int
        """
        all_routes = []
        depot_costs = {}
        total_cost = 0.0
        
        for depot_id, solution in depot_solutions.items():
            all_routes.extend(solution['routes'])
            depot_costs[depot_id] = solution['cost']
            total_cost += solution['cost']
        
        return {
            'routes': all_routes,
            'total_cost': total_cost,
            'depot_costs': depot_costs,
            'n_routes': len(all_routes)
        }


# ============================================================================
# Statistics Reporter
# ============================================================================

class StatisticsReporter:
    """Report sampling statistics"""
    
    @staticmethod
    def report_sampling_statistics(
        all_costs: List[float],
        depot_id: int
    ) -> None:
        """
        Report sampling statistics
        
        Args:
            all_costs: List of all sample costs
            depot_id: Depot ID
        """
        if not all_costs:
            return
        
        min_cost = min(all_costs)
        max_cost = max(all_costs)
        avg_cost = sum(all_costs) / len(all_costs)
        std_cost = (sum((c - avg_cost) ** 2 for c in all_costs) / len(all_costs)) ** 0.5
        
        print(f"\n仓库 {depot_id} 采样统计:")
        print(f"  最优成本: {min_cost:.2f}")
        print(f"  最差成本: {max_cost:.2f}")
        print(f"  平均成本: {avg_cost:.2f}")
        print(f"  标准差: {std_cost:.2f}")


# ============================================================================
# Result Reporter
# ============================================================================

class ResultReporter:
    """Report final results"""
    
    @staticmethod
    def report_final_results(
        solution: Dict[str, Any],
        bks: float,
        total_time: float,
        num_samples: int
    ) -> None:
        """
        Report final results
        
        Args:
            solution: Complete solution
            bks: Best Known Solution
            total_time: Total solving time
            num_samples: Number of samples
        """
        total_cost = solution['total_cost']
        n_routes = solution['n_routes']
        gap = ((total_cost - bks) / bks) * 100
        avg_time = total_time / num_samples if num_samples > 0 else 0
        
        print("\n" + "=" * 80)
        print("最终结果")
        print("=" * 80)
        print(f"总路径数: {n_routes}")
        print(f"最优成本: {total_cost:.2f}")
        print(f"BKS: {bks:.2f}")
        print(f"Gap: {gap:.2f}%")
        print(f"总求解时间: {total_time:.2f}秒")
        print(f"平均每样本时间: {avg_time:.2f}秒")
        
        # Quality assessment
        if gap < 0:
            print("\n⚠️  警告: 负Gap!")
            print("可能的错误原因:")
            print("  - 约束违反(容量或距离)")
            print("  - 距离计算错误")
            print("  - BKS读取错误")
            print("  - 节点编号混淆")
        elif gap < 5:
            print("\n✓ 解质量: 优秀")
        elif gap < 10:
            print("\n✓ 解质量: 良好")
        elif gap < 20:
            print("\n✓ 解质量: 一般")
        else:
            print("\n✓ 解质量: 较差")
        
        print("=" * 80)


# ============================================================================
# Route Reporter
# ============================================================================

class RouteReporter:
    """Report route details"""
    
    @staticmethod
    def report_routes(solution: Dict[str, Any]) -> None:
        """
        Report route details
        
        Args:
            solution: Complete solution
        """
        print("\n最优解路径详情:")
        print("-" * 80)
        
        # Group routes by depot
        depot_routes = {}
        for route in solution['routes']:
            depot_id = route['depot_id']
            if depot_id not in depot_routes:
                depot_routes[depot_id] = []
            depot_routes[depot_id].append(route)
        
        # Print routes by depot
        for depot_id in sorted(depot_routes.keys()):
            routes = depot_routes[depot_id]
            print(f"\n仓库 {depot_id} ({len(routes)} 条路径):")
            for i, route in enumerate(routes, 1):
                customers_str = " -> ".join(map(str, route['customers']))
                print(f"  路径 {i}: {depot_id} -> {customers_str} -> {depot_id}")


# ============================================================================
# Main Function
# ============================================================================

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Solve P01 with RouteFinder sampling')
    parser.add_argument('--samples', type=int, default=10, help='Number of samples per depot')
    args = parser.parse_args()
    
    print("=" * 80)
    print("P01 RouteFinder Sampling Solver")
    print("=" * 80)
    print(f"采样次数: {args.samples}")
    print()
    
    try:
        start_time = time.time()
        
        # Load P01 instance
        print("加载P01实例...")
        instance_path = "MDVRP-Instances/dat/p01"
        instance = P01Loader.load_instance(instance_path)
        print(f"✓ 加载完成: {instance['n_customers']} 客户, {instance['n_depots']} 仓库")
        
        # Assign customers to nearest depot
        print("\n分配客户到最近仓库...")
        depot_customers = DepotSplitter.assign_customers_to_nearest_depot(
            instance['customers'],
            instance['depots']
        )
        
        # Load VRPL model
        print("\n加载VRPL模型...")
        checkpoint_path = "RL4CO_Integration/routefinder/checkpoints/100/pomo/pomo-vrpl.ckpt"
        model = ModelLoader.load_vrpl_model(checkpoint_path)
        device = next(model.parameters()).device
        
        # Create node coordinate dictionary
        nodes = {}
        for customer in instance['customers']:
            nodes[customer['id']] = customer
        for depot in instance['depots']:
            nodes[depot['id']] = depot
        
        # Solve each depot subproblem
        depot_solutions = {}
        
        for depot_idx, depot in enumerate(instance['depots']):
            depot_id = depot['id']
            assigned_customers = depot_customers[depot_id]
            
            if not assigned_customers:
                print(f"\n仓库 {depot_id}: 无分配客户,跳过")
                continue
            
            print(f"\n处理仓库 {depot_id} ({len(assigned_customers)} 客户)...")
            
            # Convert to TensorDict
            depot_info = instance['depots_info'][depot_idx]
            td = FormatConverter.convert_to_tensordict(
                depot,
                assigned_customers,
                depot_info['capacity'],
                depot_info['max_distance'],
                device=str(device)
            )
            
            # Solve with sampling
            solver = SamplingSolver(model, num_samples=args.samples)
            solution = solver.solve(td, depot_id, nodes)
            depot_solutions[depot_id] = solution
            
            # Report statistics
            StatisticsReporter.report_sampling_statistics(
                solution['all_costs'],
                depot_id
            )
        
        # Aggregate solutions
        print("\n聚合所有仓库的解...")
        final_solution = SolutionAggregator.aggregate_solutions(depot_solutions)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Report final results
        bks = 576.87  # P01 BKS
        ResultReporter.report_final_results(
            final_solution,
            bks,
            total_time,
            args.samples * instance['n_depots']
        )
        
        # Report route details
        RouteReporter.report_routes(final_solution)
        
        return 0
        
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
