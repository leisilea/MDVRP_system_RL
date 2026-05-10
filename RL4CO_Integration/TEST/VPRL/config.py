"""
VPRL 配置管理模块
"""

import json
import torch
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional


@dataclass
class VPRLConfig:
    """VPRL 采样器配置类"""
    
    # 模型设置
    model_path: str = "models/vrpl_cvrp100.ckpt"
    model_selection_strategy: str = "auto"  # "auto", "fixed", "custom"
    model_size_thresholds: Dict[int, str] = field(default_factory=lambda: {
        60: "models/vrpl_cvrp50.ckpt",
        150: "models/vrpl_cvrp100.ckpt",
        999999: "models/vrpl_cvrp200.ckpt"
    })
    
    # 采样设置
    num_solutions_needed: int = 20  # GA 需要的解数量
    oversampling_ratio: float = 1.2  # 生成 1.2 倍样本,保留最优的
    sampling_temperature: float = 1.0
    decode_type: str = "sampling"
    
    # GA 集成设置
    vrpl_ratio: float = 0.5  # 初始种群中 VRPL 解的占比(50%)
    enable_vrpl: bool = True
    
    # GA 收敛监控
    convergence_report_interval: int = 10  # 每 N 代报告一次
    enable_convergence_tracking: bool = True
    
    # 客户分配策略
    assignment_strategy: str = "nearest"  # "nearest", "balanced", "kmeans"
    
    # 性能设置
    batch_size: int = 1
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    
    # 错误处理
    fallback_on_error: bool = True
    skip_invalid_solutions: bool = True
    
    # 日志设置
    log_level: str = "INFO"
    log_file: Optional[str] = "logs/vprl_sampler.log"
    
    @classmethod
    def from_file(cls, filepath: str) -> 'VPRLConfig':
        """
        从 JSON 文件加载配置
        
        参数:
            filepath: JSON 配置文件路径
            
        返回:
            VPRLConfig 实例
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # 处理 model_size_thresholds 转换(JSON 键是字符串)
        if 'model_size_thresholds' in data:
            thresholds = {}
            for k, v in data['model_size_thresholds'].items():
                # 将字符串键转换为整数,处理 "inf"
                if k == "inf":
                    thresholds[999999] = v
                else:
                    thresholds[int(k)] = v
            data['model_size_thresholds'] = thresholds
        
        return cls(**data)
    
    def to_file(self, filepath: str) -> None:
        """
        将配置保存到 JSON 文件
        
        参数:
            filepath: 输出 JSON 文件路径
        """
        data = asdict(self)
        
        # 将 model_size_thresholds 键转换为字符串以便 JSON 序列化
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
        根据实例规模获取合适的模型路径
        
        参数:
            num_customers: 实例中的客户数量
            
        返回:
            模型路径
        """
        if self.model_selection_strategy == "fixed":
            return self.model_path
        
        elif self.model_selection_strategy == "auto":
            # 找到能容纳此实例的最小阈值
            sorted_thresholds = sorted(self.model_size_thresholds.keys())
            for threshold in sorted_thresholds:
                if num_customers <= threshold:
                    return self.model_size_thresholds[threshold]
            # 回退到最大模型
            return self.model_size_thresholds[sorted_thresholds[-1]]
        
        else:  # custom
            return self.model_path
    
    def __str__(self) -> str:
        """用于日志记录的字符串表示"""
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
