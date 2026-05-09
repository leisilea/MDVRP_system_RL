"""
数据模型定义

定义重规划功能所需的所有数据类。
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict


# ============================================================================
# 内部数据模型（用于业务逻辑）
# ============================================================================

@dataclass
class VehicleState:
    """
    车辆状态（内部使用）
    
    表示车辆在重规划时刻的完整状态，包括位置、已服务客户、
    未服务客户和剩余容量等信息。
    """
    vehicle_id: int  # 车辆ID
    depot_id: int  # 所属仓库ID
    current_position: int  # 当前位置（客户ID或仓库ID）
    served_customers: List[int]  # 已服务客户ID列表
    unserved_customers: List[int]  # 未服务客户ID列表
    remaining_capacity: float  # 剩余容量
    original_capacity: float  # 初始容量
    is_at_depot: bool = False  # 是否在仓库位置


@dataclass
class TemporaryDepot:
    """
    临时仓库（内部使用）
    
    将车辆当前位置转换为临时仓库，用于重新求解。
    """
    id: int  # 新的仓库ID
    x: float  # X坐标
    y: float  # Y坐标
    vehicles: int  # 车辆数（固定为1）
    capacity: float  # 容量（车辆剩余容量）
    original_customer_id: int  # 原始客户ID（如果不在仓库）
    vehicle_id: int  # 对应的车辆ID


@dataclass
class BlockedEdge:
    """
    阻塞路段
    
    表示一条不可通行的道路，由起点和终点节点定义。
    """
    from_node: int  # 起点节点ID
    to_node: int  # 终点节点ID


# ============================================================================
# API 请求数据模型
# ============================================================================

@dataclass
class DepotInput:
    """仓库输入"""
    id: int
    x: float
    y: float
    vehicles: int
    capacity: float
    maxDistance: Optional[float] = None


@dataclass
class CustomerInput:
    """客户输入"""
    id: int
    x: float
    y: float
    demand: float


@dataclass
class RouteInput:
    """路径输入"""
    vehicleId: int
    depotId: int
    path: List[int]  # 客户ID列表
    cost: float


@dataclass
class BlockedEdgeInput:
    """
    阻塞路段输入
    
    支持两种字段名格式：
    - from/to (前端常用)
    - from_node/to_node (后端常用)
    """
    from_node: int
    to_node: int
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'BlockedEdgeInput':
        """
        从字典创建实例，支持多种字段名格式
        
        Args:
            data: 包含阻塞路段信息的字典
            
        Returns:
            BlockedEdgeInput 实例
        """
        # 支持 'from'/'to' 或 'from_node'/'to_node'
        from_node = data.get('from_node') or data.get('from')
        to_node = data.get('to_node') or data.get('to')
        
        if from_node is None or to_node is None:
            raise ValueError("阻塞路段必须包含 from_node/from 和 to_node/to 字段")
        
        return cls(from_node=int(from_node), to_node=int(to_node))


@dataclass
class ReplanRequest:
    """重规划请求"""
    depots: List[DepotInput]
    customers: List[CustomerInput]
    routes: List[RouteInput]
    blocked_edges: List[BlockedEdgeInput]
    vehicle_positions: Optional[Dict[int, int]] = None  # {vehicle_id: customer_id}
    algorithm: str = "genetic"
    params: Optional[Dict] = None


# ============================================================================
# API 响应数据模型
# ============================================================================

@dataclass
class RouteOutput:
    """路径输出"""
    vehicleId: int
    depotId: int
    path: List[int]  # 客户ID列表
    cost: float
    temporary_depot_info: Optional[Dict] = None  # 临时仓库信息


@dataclass
class TemporaryDepotInfo:
    """临时仓库信息（用于响应）"""
    original_customer_id: int  # 原始客户ID（-1表示在原始仓库）
    x: float
    y: float
    remaining_capacity: float
    vehicle_id: int


@dataclass
class ReplanResponse:
    """重规划响应"""
    new_routes: List[RouteOutput]  # 新的路径列表
    replanned_route_ids: List[int]  # 被重规划的路径ID列表
    cost_before: float  # 重规划前的总成本
    cost_after: float  # 重规划后的总成本
    cost_difference: float  # 成本差异
    cost_change_percent: float  # 成本变化百分比
    algorithm: str  # 使用的算法
    solve_time: float  # 求解时间（秒）
    num_routes: int  # 路径总数
    temporary_depots: List[TemporaryDepotInfo]  # 临时仓库信息
    vehicle_positions: Optional[Dict[int, int]] = None  # 车辆当前位置 {vehicle_id: customer_id}
    
    def to_dict(self) -> Dict:
        """转换为字典格式（用于JSON响应）"""
        result = {
            'new_routes': [
                {
                    'vehicleId': r.vehicleId,
                    'depotId': r.depotId,
                    'path': r.path,
                    'cost': r.cost,
                    'temporary_depot_info': r.temporary_depot_info
                }
                for r in self.new_routes
            ],
            'replanned_route_ids': self.replanned_route_ids,
            'cost_before': self.cost_before,
            'cost_after': self.cost_after,
            'cost_difference': self.cost_difference,
            'cost_change_percent': self.cost_change_percent,
            'algorithm': self.algorithm,
            'solve_time': self.solve_time,
            'num_routes': self.num_routes,
            'temporary_depots': [
                {
                    'original_customer_id': td.original_customer_id,
                    'x': td.x,
                    'y': td.y,
                    'remaining_capacity': td.remaining_capacity,
                    'vehicle_id': td.vehicle_id
                }
                for td in self.temporary_depots
            ]
        }
        
        # 添加车辆位置信息（如果有）
        if self.vehicle_positions:
            result['vehicle_positions'] = self.vehicle_positions
        
        return result
