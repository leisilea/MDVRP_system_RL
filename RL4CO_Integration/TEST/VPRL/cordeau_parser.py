"""
Cordeau MDVRP 实例解析器

将 Cordeau 格式的 MDVRP 实例文件解析为 MDVRPInstance 对象
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Tuple
import numpy as np


@dataclass
class MDVRPInstance:
    """MDVRP 实例数据容器"""
    name: str
    num_depots: int
    num_customers: int
    depots_coords: np.ndarray
    customers_coords: np.ndarray
    demands: np.ndarray
    depot_capacities: np.ndarray
    depot_vehicles: np.ndarray
    max_route_distances: np.ndarray
    distance_matrix: np.ndarray = None


def parse_cordeau_mdvrp(file_path: Path) -> Tuple[List[Dict], List[Dict], int, List[float], List[float]]:
    """
    解析 Cordeau MDVRP 文件格式
    
    参数:
        file_path: Cordeau 格式文件路径
        
    返回:
        元组 (depots, customers, vehicles_per_depot, d_vals, q_vals)
    """
    lines = [line.strip() for line in file_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        raise ValueError(f"Empty file: {file_path}")

    header = lines[0].split()
    if len(header) < 4:
        raise ValueError(f"Invalid header format: {file_path}")

    problem_type = int(header[0])
    if problem_type != 2:
        raise ValueError(f"Not MDVRP (type=2): {file_path}, type={problem_type}")

    vehicles_per_depot = int(header[1])
    num_customers = int(header[2])
    num_depots = int(header[3])

    # D/Q 参数
    dq_rows = [lines[i].split() for i in range(1, 1 + num_depots)]
    d_vals = [float(parts[0]) for parts in dq_rows]
    q_vals = [float(parts[1]) for parts in dq_rows]

    # 客户数据
    customer_start = 1 + num_depots
    customer_end = customer_start + num_customers
    customers: List[Dict] = []
    for i in range(customer_start, customer_end):
        parts = lines[i].split()
        if len(parts) < 5:
            raise ValueError(f"Invalid customer line: {file_path} line {i+1}")
        customers.append({
            "id": int(parts[0]),
            "x": float(parts[1]),
            "y": float(parts[2]),
            "demand": float(parts[4]),
        })

    # 仓库数据
    depots: List[Dict] = []
    depot_start = customer_end
    for idx, i in enumerate(range(depot_start, depot_start + num_depots)):
        parts = lines[i].split()
        if len(parts) < 3:
            raise ValueError(f"Invalid depot line: {file_path} line {i+1}")
        max_distance = d_vals[idx]
        depots.append({
            "id": int(parts[0]),
            "x": float(parts[1]),
            "y": float(parts[2]),
            "vehicles": vehicles_per_depot,
            "capacity": float(q_vals[idx]),
            "maxDistance": 0.0 if max_distance < 0 else max_distance,
        })

    return depots, customers, vehicles_per_depot, d_vals, q_vals


def load_cordeau_instance(file_path: str) -> MDVRPInstance:
    """
    加载 Cordeau 格式的 MDVRP 实例
    
    参数:
        file_path: Cordeau 格式文件路径
        
    返回:
        MDVRPInstance 对象
    """
    path = Path(file_path)
    depots, customers, vehicles_per_depot, d_vals, q_vals = parse_cordeau_mdvrp(path)
    
    num_depots = len(depots)
    num_customers = len(customers)
    
    # 转换为 numpy 数组
    depots_coords = np.array([[d['x'], d['y']] for d in depots])
    customers_coords = np.array([[c['x'], c['y']] for c in customers])
    demands = np.array([c['demand'] for c in customers])
    depot_capacities = np.array([d['capacity'] for d in depots])
    depot_vehicles = np.array([d['vehicles'] for d in depots])
    max_route_distances = np.array([d['maxDistance'] for d in depots])
    
    # 计算距离矩阵
    all_coords = np.vstack([depots_coords, customers_coords])
    diff = all_coords[:, np.newaxis, :] - all_coords[np.newaxis, :, :]
    distance_matrix = np.sqrt(np.sum(diff**2, axis=-1))
    
    instance = MDVRPInstance(
        name=path.stem,
        num_depots=num_depots,
        num_customers=num_customers,
        depots_coords=depots_coords,
        customers_coords=customers_coords,
        demands=demands,
        depot_capacities=depot_capacities,
        depot_vehicles=depot_vehicles,
        max_route_distances=max_route_distances,
        distance_matrix=distance_matrix
    )
    
    return instance
