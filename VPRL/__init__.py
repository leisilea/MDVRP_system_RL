"""
VPRL: RL4CO VRPL Integration for GA-MDVRP
Provides high-quality initial solutions using reinforcement learning
"""

from .instance_decomposer import InstanceDecomposer, CVRPSubProblem
from .solution_converter import SolutionConverter, Route
from .vprl_sampler import VPRLSampler
from .config import VPRLConfig
from .cordeau_parser import load_cordeau_instance, MDVRPInstance

__version__ = "1.0.0"
__all__ = [
    "InstanceDecomposer",
    "CVRPSubProblem",
    "SolutionConverter",
    "Route",
    "VPRLSampler",
    "VPRLConfig",
    "load_cordeau_instance",
    "MDVRPInstance",
]
