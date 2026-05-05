"""
Error handling utilities for VPRL-GA integration.

This module provides error handling functions for various failure scenarios
in the VPRL-GA initialization workflow, ensuring graceful degradation.
"""

import logging
from typing import Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ErrorContext:
    """Context information for error handling"""
    error_type: str
    error_message: str
    retry_count: int = 0
    can_continue: bool = True
    fallback_action: Optional[str] = None


class ErrorHandler:
    """Handles errors in VPRL-GA workflow with graceful degradation"""
    
    @staticmethod
    def handle_model_loading_error(error: Exception) -> Tuple[bool, str]:
        """
        Handle model loading failure.
        
        Args:
            error: The exception that occurred
            
        Returns:
            Tuple of (should_continue, fallback_action)
            - should_continue: True if should continue with fallback
            - fallback_action: Description of fallback action
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
        Handle solution generation failure.
        
        Args:
            error: The exception that occurred
            retry_count: Current retry count
            max_retries: Maximum number of retries
            
        Returns:
            Tuple of (should_retry, action)
            - should_retry: True if should retry, False if should fallback
            - action: "retry" or "fallback"
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
        Handle route validation failure.
        
        Args:
            route_info: Information about the route (depot, vehicle, etc.)
            error_message: Validation error message
        """
        logger.warning(f"Invalid route ({route_info}): {error_message}")
        logger.warning("Skipping this solution")
    
    @staticmethod
    def handle_conversion_error(
        error: Exception,
        solution_index: int
    ) -> None:
        """
        Handle solution conversion failure.
        
        Args:
            error: The exception that occurred
            solution_index: Index of the solution that failed
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
        Handle file I/O failure.
        
        Args:
            error: The exception that occurred
            filepath: Path to the file that failed
            
        Returns:
            Tuple of (should_continue, fallback_action)
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
        Handle GA_Java execution failure.
        
        Args:
            error: The exception that occurred
            
        Returns:
            Tuple of (should_continue, error_type)
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
        Log partial success when some solutions are valid.
        
        Args:
            valid_solutions: Number of valid solutions
            total_solutions: Total number of solutions attempted
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
        Create error context for tracking.
        
        Args:
            error_type: Type of error
            error: The exception
            retry_count: Current retry count
            
        Returns:
            ErrorContext object
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
    Configure logging for VPRL module.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Configure format
    log_format = (
        "[%(levelname)s] %(asctime)s - %(name)s - %(message)s"
    )
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Configure handlers
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=handlers,
        force=True
    )
    
    # Set VPRL logger level
    vprl_logger = logging.getLogger("VPRL")
    vprl_logger.setLevel(log_level)
