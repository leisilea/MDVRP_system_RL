"""
道路阻塞动态重规划模块

该模块提供MDVRP问题的动态重规划功能，当道路被阻塞时，
可以快速生成新的路径规划方案。
"""

from .models import (
    VehicleState,
    TemporaryDepot,
    BlockedEdge,
    DepotInput,
    CustomerInput,
    RouteInput,
    BlockedEdgeInput,
    ReplanRequest,
    RouteOutput,
    TemporaryDepotInfo,
    ReplanResponse
)

from .exceptions import (
    ReplanningError,
    CapacityConstraintViolation,
    BlockedEdgeInSolution,
    InvalidVehiclePosition,
    NoFeasibleSolution,
    UnsupportedAlgorithm
)

from .service import ReplanningService

__all__ = [
    # Models
    'VehicleState',
    'TemporaryDepot',
    'BlockedEdge',
    'DepotInput',
    'CustomerInput',
    'RouteInput',
    'BlockedEdgeInput',
    'ReplanRequest',
    'RouteOutput',
    'TemporaryDepotInfo',
    'ReplanResponse',
    # Exceptions
    'ReplanningError',
    'CapacityConstraintViolation',
    'BlockedEdgeInSolution',
    'InvalidVehiclePosition',
    'NoFeasibleSolution',
    'UnsupportedAlgorithm',
    # Service
    'ReplanningService',
]
