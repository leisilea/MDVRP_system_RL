"""
道路阻塞动态重规划模块

该模块提供MDVRP问题的动态重规划功能，当道路被阻塞时，
可以快速生成新的路径规划方案。

简化版重规划：只处理被堵车辆的绕路，不重新分配任务。
"""

from .exceptions import (
    ReplanningError,
    CapacityConstraintViolation,
    BlockedEdgeInSolution,
    InvalidVehiclePosition,
    NoFeasibleSolution,
    UnsupportedAlgorithm,
    InvalidBlockedEdge
)

from .simple_replanner import SimpleReplanner
from .api_simple import handle_simple_replan, validate_replan_request

__all__ = [
    # Exceptions
    'ReplanningError',
    'CapacityConstraintViolation',
    'BlockedEdgeInSolution',
    'InvalidVehiclePosition',
    'NoFeasibleSolution',
    'UnsupportedAlgorithm',
    'InvalidBlockedEdge',
    # Simple Replanner
    'SimpleReplanner',
    'handle_simple_replan',
    'validate_replan_request',
]
