"""
VPRL-GA 集成的错误处理工具模块

此模块为 VPRL-GA 初始化工作流中的各种失败场景提供错误处理函数,确保优雅降级
"""

import logging
from typing import Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ErrorContext:
    """错误处理的上下文信息"""
    error_type: str
    error_message: str
    retry_count: int = 0
    can_continue: bool = True
    fallback_action: Optional[str] = None


class ErrorHandler:
    """处理 VPRL-GA 工作流中的错误,实现优雅降级"""
    
    @staticmethod
    def handle_model_loading_error(error: Exception) -> Tuple[bool, str]:
        """
        处理模型加载失败
        
        参数:
            error: 发生的异常
            
        返回:
            元组 (should_continue, fallback_action)
            - should_continue: 是否应该继续使用回退方案
            - fallback_action: 回退操作的描述
        """
        logger.warning(f"Failed to load RL4CO model: {error}")
        logger.warning("Disabling VRPL initialization, using pure GA_Java")
        
        return True, "disable_vrpl"
    
    @staticmethod
    def handle_generation_error(
        error: Exception, 
        retry_count: int,
        max_retries: int = 1
    ) -> Tuple[bool, str]:
        """
        处理解生成失败
        
        参数:
            error: 发生的异常
            retry_count: 当前重试次数
            max_retries: 最大重试次数
            
        返回:
            元组 (should_retry, action)
            - should_retry: 是否应该重试,False 表示应该回退
            - action: "retry" 或 "fallback"
        """
        if retry_count < max_retries:
            logger.warning(
                f"Solution generation failed: {error}. "
                f"Retrying... (attempt {retry_count + 1}/{max_retries})"
            )
            return True, "retry"
        else:
            logger.error(
                f"Solution generation failed after {max_retries} retries: {error}"
            )
            logger.error("Falling back to pure GA_Java")
            return False, "fallback"
    
    @staticmethod
    def handle_validation_error(
        route_info: str,
        error_message: str
    ) -> None:
        """
        处理路径验证失败
        
        参数:
            route_info: 路径信息(仓库、车辆等)
            error_message: 验证错误消息
        """
        logger.warning(f"Invalid route ({route_info}): {error_message}")
        logger.warning("Skipping this solution")
    
    @staticmethod
    def handle_conversion_error(
        error: Exception,
        solution_index: int
    ) -> None:
        """
        处理解转换失败
        
        参数:
            error: 发生的异常
            solution_index: 失败的解的索引
        """
        logger.warning(
            f"Failed to convert solution {solution_index}: {error}"
        )
        logger.warning("Skipping this solution")
    
    @staticmethod
    def handle_file_io_error(
        error: Exception,
        filepath: str
    ) -> Tuple[bool, str]:
        """
        处理文件 I/O 失败
        
        参数:
            error: 发生的异常
            filepath: 失败的文件路径
            
        返回:
            元组 (should_continue, fallback_action)
        """
        logger.error(f"Failed to write file {filepath}: {error}")
        logger.error("Continuing without initial solution file")
        logger.error("GA_Java will use random initialization")
        
        return True, "skip_file"
    
    @staticmethod
    def handle_ga_java_error(
        error: Exception
    ) -> Tuple[bool, str]:
        """
        处理 GA_Java 执行失败
        
        参数:
            error: 发生的异常
            
        返回:
            元组 (should_continue, error_type)
        """
        logger.error(f"GA_Java execution failed: {error}")
        logger.error("Solve operation cannot continue")
        
        return False, "ga_java_failure"
    
    @staticmethod
    def log_partial_success(
        valid_solutions: int,
        total_solutions: int
    ) -> None:
        """
        当部分解有效时记录部分成功
        
        参数:
            valid_solutions: 有效解的数量
            total_solutions: 尝试的总解数
        """
        if valid_solutions == 0:
            logger.warning(
                "No valid VRPL solutions generated. "
                "Falling back to pure GA_Java"
            )
        elif valid_solutions < total_solutions:
            logger.warning(
                f"Only {valid_solutions}/{total_solutions} solutions are valid. "
                f"Using partial initialization"
            )
        else:
            logger.info(
                f"All {valid_solutions} solutions are valid"
            )
    
    @staticmethod
    def create_error_context(
        error_type: str,
        error: Exception,
        retry_count: int = 0
    ) -> ErrorContext:
        """
        创建用于跟踪的错误上下文
        
        参数:
            error_type: 错误类型
            error: 异常对象
            retry_count: 当前重试次数
            
        返回:
            ErrorContext 对象
        """
        return ErrorContext(
            error_type=error_type,
            error_message=str(error),
            retry_count=retry_count,
            can_continue=True,
            fallback_action=None
        )


def configure_logging(
    level: str = "INFO",
    log_file: Optional[str] = None
) -> None:
    """
    配置 VPRL 模块的日志记录
    
    参数:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 可选的日志文件路径
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # 配置格式
    log_format = (
        "[%(levelname)s] %(asctime)s - %(name)s - %(message)s"
    )
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # 配置处理器
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    # 配置根日志记录器
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=handlers,
        force=True
    )
    
    # 设置 VPRL 日志记录器级别
    vprl_logger = logging.getLogger("VPRL")
    vprl_logger.setLevel(log_level)
