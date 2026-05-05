"""
Configuration Management for VPRL
"""

import json
import torch
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional


@dataclass
class VPRLConfig:
    """Configuration for VPRL Sampler"""
    
    # Model settings
    model_path: str = "models/vrpl_cvrp100.ckpt"
    model_selection_strategy: str = "auto"  # "auto", "fixed", "custom"
    model_size_thresholds: Dict[int, str] = field(default_factory=lambda: {
        60: "models/vrpl_cvrp50.ckpt",
        150: "models/vrpl_cvrp100.ckpt",
        999999: "models/vrpl_cvrp200.ckpt"
    })
    
    # Sampling settings
    num_solutions_needed: int = 20  # Number of solutions needed for GA
    oversampling_ratio: float = 1.2  # Generate 1.2x samples, keep best
    sampling_temperature: float = 1.0
    decode_type: str = "sampling"
    
    # GA integration settings
    vrpl_ratio: float = 0.5  # 50% of initial population from VRPL
    enable_vrpl: bool = True
    
    # GA convergence monitoring
    convergence_report_interval: int = 10  # Report every N generations
    enable_convergence_tracking: bool = True
    
    # Customer assignment
    assignment_strategy: str = "nearest"  # "nearest", "balanced", "kmeans"
    
    # Performance settings
    batch_size: int = 1
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    
    # Error handling
    fallback_on_error: bool = True
    skip_invalid_solutions: bool = True
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = "logs/vprl_sampler.log"
    
    @classmethod
    def from_file(cls, filepath: str) -> 'VPRLConfig':
        """
        Load configuration from JSON file
        
        Args:
            filepath: Path to JSON config file
            
        Returns:
            VPRLConfig instance
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Handle model_size_thresholds conversion (JSON keys are strings)
        if 'model_size_thresholds' in data:
            thresholds = {}
            for k, v in data['model_size_thresholds'].items():
                # Convert string keys to int, handle "inf"
                if k == "inf":
                    thresholds[999999] = v
                else:
                    thresholds[int(k)] = v
            data['model_size_thresholds'] = thresholds
        
        return cls(**data)
    
    def to_file(self, filepath: str) -> None:
        """
        Save configuration to JSON file
        
        Args:
            filepath: Path to output JSON file
        """
        data = asdict(self)
        
        # Convert model_size_thresholds keys to strings for JSON
        if 'model_size_thresholds' in data:
            thresholds = {}
            for k, v in data['model_size_thresholds'].items():
                if k >= 999999:
                    thresholds["inf"] = v
                else:
                    thresholds[str(k)] = v
            data['model_size_thresholds'] = thresholds
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_model_for_size(self, num_customers: int) -> str:
        """
        Get appropriate model path based on instance size
        
        Args:
            num_customers: Number of customers in instance
            
        Returns:
            Model path
        """
        if self.model_selection_strategy == "fixed":
            return self.model_path
        
        elif self.model_selection_strategy == "auto":
            # Find the smallest threshold that accommodates this instance
            sorted_thresholds = sorted(self.model_size_thresholds.keys())
            for threshold in sorted_thresholds:
                if num_customers <= threshold:
                    return self.model_size_thresholds[threshold]
            # Fallback to largest model
            return self.model_size_thresholds[sorted_thresholds[-1]]
        
        else:  # custom
            return self.model_path
    
    def __str__(self) -> str:
        """String representation for logging"""
        return (
            f"VPRLConfig(\n"
            f"  model_path={self.model_path},\n"
            f"  model_selection_strategy={self.model_selection_strategy},\n"
            f"  num_solutions_needed={self.num_solutions_needed},\n"
            f"  oversampling_ratio={self.oversampling_ratio},\n"
            f"  sampling_temperature={self.sampling_temperature},\n"
            f"  vrpl_ratio={self.vrpl_ratio},\n"
            f"  enable_vrpl={self.enable_vrpl},\n"
            f"  convergence_report_interval={self.convergence_report_interval},\n"
            f"  assignment_strategy={self.assignment_strategy},\n"
            f"  device={self.device}\n"
            f")"
        )
