"""
异常类定义

定义重规划功能所需的所有异常类。
"""


class ReplanningError(Exception):
    """
    重规划基础异常
    
    所有重规划相关的异常都继承自此类。
    """
    pass


class CapacityConstraintViolation(ReplanningError):
    """
    容量约束违反异常
    
    当车辆的剩余容量不足以服务分配的客户时抛出。
    """
    
    def __init__(self, vehicle_id: int, remaining: float, required: float):
        """
        Args:
            vehicle_id: 车辆ID
            remaining: 剩余容量
            required: 需要的容量
        """
        self.vehicle_id = vehicle_id
        self.remaining = remaining
        self.required = required
        super().__init__(
            f"车辆{vehicle_id}的剩余容量({remaining:.2f})不足以服务分配的客户(需要{required:.2f})"
        )


class BlockedEdgeInSolution(ReplanningError):
    """
    解决方案包含阻塞路段异常
    
    当重规划结果中的路径包含阻塞路段时抛出。
    """
    
    def __init__(self, vehicle_id: int, from_node: int, to_node: int):
        """
        Args:
            vehicle_id: 车辆ID
            from_node: 起点节点ID
            to_node: 终点节点ID
        """
        self.vehicle_id = vehicle_id
        self.from_node = from_node
        self.to_node = to_node
        super().__init__(
            f"车辆{vehicle_id}的路径包含阻塞路段: {from_node} -> {to_node}"
        )


class InvalidVehiclePosition(ReplanningError):
    """
    无效的车辆位置异常
    
    当指定的车辆位置不在其路径上时抛出。
    """
    
    def __init__(self, vehicle_id: int, position: int, valid_positions: list = None):
        """
        Args:
            vehicle_id: 车辆ID
            position: 指定的位置
            valid_positions: 有效位置列表（可选）
        """
        self.vehicle_id = vehicle_id
        self.position = position
        self.valid_positions = valid_positions
        
        msg = f"车辆{vehicle_id}的位置{position}无效"
        if valid_positions:
            msg += f"，有效位置为: {valid_positions}"
        
        super().__init__(msg)


class NoFeasibleSolution(ReplanningError):
    """
    无可行解异常
    
    当求解器无法找到满足所有约束的解决方案时抛出。
    """
    
    def __init__(self, reason: str):
        """
        Args:
            reason: 无法找到可行解的原因
        """
        self.reason = reason
        super().__init__(f"无法找到可行解: {reason}")


class InvalidBlockedEdge(ReplanningError):
    """
    无效的阻塞路段异常
    
    当阻塞路段的节点ID无效时抛出。
    """
    
    def __init__(self, from_node: int, to_node: int, reason: str):
        """
        Args:
            from_node: 起点节点ID
            to_node: 终点节点ID
            reason: 无效的原因
        """
        self.from_node = from_node
        self.to_node = to_node
        self.reason = reason
        super().__init__(
            f"阻塞路段 {from_node} -> {to_node} 无效: {reason}"
        )


class UnsupportedAlgorithm(ReplanningError):
    """
    不支持的算法异常
    
    当指定的算法不被支持时抛出。
    """
    
    def __init__(self, algorithm: str, supported_algorithms: list):
        """
        Args:
            algorithm: 指定的算法名称
            supported_algorithms: 支持的算法列表
        """
        self.algorithm = algorithm
        self.supported_algorithms = supported_algorithms
        super().__init__(
            f"不支持的算法: {algorithm}。支持的算法: {', '.join(supported_algorithms)}"
        )
