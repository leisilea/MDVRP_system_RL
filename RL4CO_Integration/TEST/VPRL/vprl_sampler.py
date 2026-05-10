import os
import time
import logging
import numpy as np
import torch
from typing import Dict, List, Optional, Union
from dataclasses import dataclass

from .config import VPRLConfig
from .instance_decomposer import InstanceDecomposer, CVRPSubProblem
from .solution_converter import SolutionConverter, Route
from .error_handler import ErrorHandler


@dataclass
class ConvergencePoint:
    # 记录当前代数+数据 用来绘制收敛曲线
    generation: int
    best_cost: float
    timestamp: float  


@dataclass
class PerformanceMetrics:
    """VPRL-GA 集成的性能指标"""
    # VRPL 指标
    vrpl_generation_time: float
    vrpl_num_samples_generated: int
    vrpl_num_solutions_kept: int
    vrpl_avg_cost: float
    vrpl_best_cost: float
    vrpl_kept_avg_cost: float
    oversampling_improvement: float
    model_used: str
    
    # 转换指标
    conversion_time: float
    num_valid_solutions: int
    num_invalid_solutions: int
    
    # GA_Java 指标
    ga_computation_time: float
    ga_iterations: int
    ga_final_cost: float
    convergence_curve: List[ConvergencePoint]
    
    # 对比
    improvement_vs_random: float
    vrpl_contribution: float


class VPRLSampler:
    
    def __init__(self, model_path: Optional[str] = None, config: Optional[VPRLConfig] = None):
        """
        初始化 VPRL 采样器
        
        Args:
            model_path: RL4CO 模型检查点路径 (覆盖配置)
            config: VPRLConfig 实例或 None 使用默认值
        """
        # 加载配置
        if config is None:
            config_file = os.path.join(os.path.dirname(__file__), "config.json")
            if os.path.exists(config_file):
                self.config = VPRLConfig.from_file(config_file)
            else:
                self.config = VPRLConfig()
        else:
            self.config = config
        
        # 如果提供了模型路径则覆盖
        if model_path is not None:
            self.config.model_path = model_path
        
        # 设置日志
        self._setup_logging()
        
        # 模型将按需加载
        self.model = None
        self.current_model_path = None
        
        self.logger.info("VPRL_Sampler initialized")
        self.logger.info(f"Configuration:\n{self.config}")
    
    def _setup_logging(self):
        """设置日志配置"""
        self.logger = logging.getLogger("VPRL")
        self.logger.setLevel(getattr(logging, self.config.log_level))
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, self.config.log_level))
        formatter = logging.Formatter('[%(levelname)s] %(message)s')
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # 文件处理器 (如果指定)
        if self.config.log_file:
            os.makedirs(os.path.dirname(self.config.log_file), exist_ok=True)
            file_handler = logging.FileHandler(self.config.log_file)
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
    
    def _select_model_by_size(self, num_customers: int) -> str:
        """
        根据实例规模选择合适的模型
        
        Args:
            num_customers: 客户数量
            
        Returns:
            模型路径
        """
        model_path = self.config.get_model_for_size(num_customers)
        self.logger.info(f"Auto-selected model for {num_customers} customers: {model_path}")
        return model_path
    
    def _load_model(self, model_path: str) -> bool:
        """
        加载 RL4CO 模型并进行错误处理
        
        Args:
            model_path: 模型检查点路径
            
        Returns:
            成功返回 True,否则返回 False
        """
        try:
            # 检查是否已加载
            if self.model is not None and self.current_model_path == model_path:
                self.logger.debug(f"Model already loaded: {model_path}")
                return True
            
            self.logger.info(f"Loading RL4CO model from: {model_path}")
            
            if not os.path.exists(model_path):
                self.logger.error(f"Model file not found: {model_path}")
                return False
            


            import torch
            import torch.serialization
            import pickle
            
            # TorchRL 兼容性修复: 映射旧版API名称到新版
            # 因为RouteFinder中的RL4CO版本和RouteFinder本身版本中的torchrl版本不兼容(很奇怪)
            try:
                import torchrl.data.tensor_specs as specs
                if not hasattr(specs, 'CompositeSpec'):
                    from torchrl.data.tensor_specs import Composite, Bounded, UnboundedContinuous, UnboundedDiscrete
                    specs.CompositeSpec = Composite
                    specs.BoundedTensorSpec = Bounded
                    specs.UnboundedContinuousTensorSpec = UnboundedContinuous
                    specs.UnboundedDiscreteTensorSpec = UnboundedDiscrete
                    self.logger.debug("Applied TorchRL compatibility aliases")
            except Exception as e:
                self.logger.debug(f"Could not apply TorchRL aliases: {e}")
            
            # 加载 RouteFinder 模型
            from routefinder.models import RouteFinderBase
            
            # 应用 CompatibilityUnpickler 补丁以兼容旧 TorchRL API
            _original_load = torch.serialization._load
            
            def _patched_load(zip_file, map_location, pickle_module, 
                            pickle_file='data.pkl', overall_storage=None, 
                            **pickle_load_args):
                """注入 CompatibilityUnpickler 的 find_class 逻辑的补丁 _load"""
                original_unpickler = pickle_module.Unpickler
                
                class PatchedUnpickler(original_unpickler):
                    def find_class(self, mod_name, name):
                        # 旧检查点的 TorchRL API 重映射
                        if mod_name == 'torchrl.data.tensor_specs':
                            if name == 'CompositeSpec':
                                from torchrl.data.tensor_specs import Composite
                                return Composite
                            elif name == 'BoundedTensorSpec':
                                from torchrl.data.tensor_specs import Bounded
                                return Bounded
                            elif name == 'UnboundedContinuousTensorSpec':
                                from torchrl.data.tensor_specs import UnboundedContinuous
                                return UnboundedContinuous
                            elif name == 'UnboundedDiscreteTensorSpec':
                                from torchrl.data.tensor_specs import UnboundedDiscrete
                                return UnboundedDiscrete
                        return super().find_class(mod_name, name)
                
                try:
                    pickle_module.Unpickler = PatchedUnpickler
                    return _original_load(zip_file, map_location, pickle_module, 
                                        pickle_file, overall_storage, **pickle_load_args)
                finally:
                    pickle_module.Unpickler = original_unpickler
            
            # 应用补丁并加载模型
            try:
                torch.serialization._load = _patched_load
                
                # RNG 状态 CUDA 加载错误的修复:
                # 首先将检查点加载到 CPU 以避免 RNG 状态设备映射问题
                checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
                
                # 删除 RNG 状态 (推理不需要,且会导致GPU推理失败)
                if 'rng_states' in checkpoint:
                    self.logger.debug("Removing RNG states from checkpoint (not needed for inference)")
                    del checkpoint['rng_states']
                
                # 删除导致加载错误的仅训练超参数
                if 'hyper_parameters' in checkpoint:
                    training_only_params = ['normalize_reward', 'alpha', 'epsilon', 'norm_operation']
                    for param in training_only_params:
                        if param in checkpoint['hyper_parameters']:
                            self.logger.debug(f"Removing training-only parameter: {param}={checkpoint['hyper_parameters'][param]}")
                            checkpoint['hyper_parameters'].pop(param)
                
                # 手动加载以避免 Lightning 的参数验证
                if 'hyper_parameters' in checkpoint and 'state_dict' in checkpoint:
                    hparams = checkpoint['hyper_parameters'].copy()
                    self.model = RouteFinderBase(**hparams)
                    self.model.load_state_dict(checkpoint['state_dict'], strict=False)
                    self.logger.info("Loaded as RouteFinder model")
                else:
                    raise ValueError("Checkpoint missing required keys: hyper_parameters or state_dict")
            finally:
                # 始终恢复原始函数
                torch.serialization._load = _original_load
            
            self.model.eval()
            self.model = self.model.to(self.config.device)
            self.current_model_path = model_path
            
            self.logger.info(f"Model loaded successfully on device: {self.config.device}")
            return True
            
        except Exception as e:
            # 使用错误处理器
            should_continue, action = ErrorHandler.handle_model_loading_error(e)
            return False
    
    def _generate_vrpl_solutions(
        self,
        sub_problem: CVRPSubProblem,
        num_solutions_needed: int,
        retry_count: int = 0) -> tuple:
        """
        使用 RL4CO 生成解,支持过采样和错误处理
        
        Args:
            sub_problem: CVRP 子问题
            num_solutions_needed: 需要的解数量
            retry_count: 当前重试次数
            
        Returns:
            (best_solutions, all_costs, improvement) 元组,失败时返回 (None, None, 0.0)
        """
        try:
            # 计算要生成的样本数 (过采样)
            num_samples = int(num_solutions_needed * self.config.oversampling_ratio)
            
            self.logger.info(
                f"Oversampling: generating {num_samples} samples, will keep best {num_solutions_needed}"
            )
            
            # 生成样本
            # 使用模型的环境来正确初始化问题
            # 这确保所有环境参数都正确设置
            all_solutions = []
            all_costs = []
            
            with torch.no_grad():
                for i in range(num_samples):
                    # 为每个样本创建一个新的 TensorDict
                    td = sub_problem.tensordict.clone().to(self.config.device)
                    
                    # 使用问题数据重置环境
                    # 这正确初始化所有环境状态
                    td_reset = self.model.env.reset(td)
                    
                    out = self.model.policy(
                        td_reset,
                        decode_type=self.config.decode_type,
                        temperature=self.config.sampling_temperature,
                        return_actions=True
                    )
                    
                    # 获取成本
                    cost = self.model.env.get_reward(td_reset, out['actions'])
                    
                    all_solutions.append(out['actions'].cpu())
                    all_costs.append(cost.cpu().item())
            
            # 选择最佳解
            best_solutions, improvement = self._select_best_solutions(
                all_solutions, all_costs, num_solutions_needed
            )
            
            self.logger.info(
                f"Oversampling improvement: {improvement:.1f}% "
                f"(avg cost: {np.mean(all_costs):.2f} → {np.mean([all_costs[i] for i in range(num_solutions_needed)]):.2f})"
            )
            
            return best_solutions, all_costs, improvement
            
        except Exception as e:
            # 使用错误处理器
            should_retry, action = ErrorHandler.handle_generation_error(e, retry_count)
            
            if should_retry:
                # 重试一次
                return self._generate_vrpl_solutions(
                    sub_problem, num_solutions_needed, retry_count + 1
                )
            else:
                # 返回空结果以触发回退
                return None, None, 0.0
    
    def _select_best_solutions(
        self,
        solutions: List[torch.Tensor],
        costs: List[float],
        num_to_keep: int) -> tuple:
        """
        从过采样池中选择最佳解
        
        Args:
            solutions: 解张量列表
            costs: 成本列表
            num_to_keep: 要保留的解数量
            
        Returns:
            (best_solutions, oversampling_improvement_percentage)
        """
        # 按成本排序
        sorted_indices = np.argsort(costs)
        best_indices = sorted_indices[:num_to_keep]
        
        # 选择最佳解
        best_solutions = [solutions[i] for i in best_indices]
        
        # 计算改进
        avg_all = np.mean(costs)
        avg_kept = np.mean([costs[i] for i in best_indices])
        improvement = (avg_all - avg_kept) / avg_all * 100 if avg_all > 0 else 0.0
        
        return best_solutions, improvement
    
    def solve(
        self,
        instance_data,
        enable_vrpl: Optional[bool] = None,
        num_solutions_needed: Optional[int] = None,
        oversampling_ratio: Optional[float] = None,
        temperature: Optional[float] = None,
        vrpl_ratio: Optional[float] = None) -> Dict:
        """
        使用 VRPL 增强的 GA 求解 MDVRP 实例
        
        Args:
            instance_data: MDVRPInstance 对象或 Cordeau 文件路径
            enable_vrpl: 是否使用 VRPL 初始化 (覆盖配置)
            num_solutions_needed: 需要的解数量 (覆盖配置)
            oversampling_ratio: 过采样比率 (覆盖配置)
            temperature: 采样温度 (覆盖配置)
            vrpl_ratio: 种群中的 VRPL 比率 (覆盖配置)
            
        Returns:
            包含路径、成本和性能指标的解字典
        """
        start_time = time.time()
        
        # 如果是文件路径则加载实例
        if isinstance(instance_data, str):
            self.logger.info(f"Loading Cordeau instance from: {instance_data}")
            from .cordeau_parser import load_cordeau_instance
            instance_data = load_cordeau_instance(instance_data)
            self.logger.info(f"Instance loaded: {instance_data.num_depots} depots, {instance_data.num_customers} customers")
        
        # 应用参数覆盖
        enable_vrpl = enable_vrpl if enable_vrpl is not None else self.config.enable_vrpl
        num_solutions_needed = num_solutions_needed if num_solutions_needed is not None else self.config.num_solutions_needed
        vrpl_ratio = vrpl_ratio if vrpl_ratio is not None else self.config.vrpl_ratio
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"VPRL-Enhanced GA Solver")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"VRPL enabled: {enable_vrpl}")
        self.logger.info(f"Solutions needed: {num_solutions_needed}")
        
        # 初始化指标
        vrpl_time = 0.0
        conversion_time = 0.0
        all_routes = []
        num_samples_generated = 0
        num_solutions_kept = 0
        all_costs_list = []
        kept_costs_list = []
        oversampling_improvement = 0.0
        model_used = "None"
        num_valid = 0
        num_invalid = 0
        
        # 步骤 1: 如果启用 VRPL 则分解 MDVRP
        if enable_vrpl:
            try:
                self.logger.info(f"Decomposing MDVRP instance...")
                
                # 获取客户数量以选择模型
                num_customers = instance_data.num_customers
                
                # 选择并加载模型
                model_path = self._select_model_by_size(num_customers)
                model_used = model_path
                
                if not self._load_model(model_path):
                    self.logger.warning("Model loading failed, disabling VRPL")
                    enable_vrpl = False
                else:
                    # 分解 MDVRP
                    sub_problems = InstanceDecomposer.decompose_mdvrp(
                        instance=instance_data,
                        strategy=self.config.assignment_strategy
                    )
                    
                    self.logger.info(
                        f"Decomposed into {len(sub_problems)} CVRP sub-problems"
                    )
                    
                    # 步骤 2: 为每个仓库生成解
                    vrpl_start = time.time()
                    
                    for sub_problem in sub_problems:
                        self.logger.info(
                            f"Generating solutions for depot {sub_problem.depot_id + 1} "
                            f"({len(sub_problem.customer_indices)} customers)"
                        )
                        
                        # 使用过采样生成解
                        result = self._generate_vrpl_solutions(
                            sub_problem=sub_problem,
                            num_solutions_needed=num_solutions_needed
                        )
                        
                        # 检查生成是否失败
                        if result[0] is None:
                            self.logger.warning(
                                f"Failed to generate solutions for depot {sub_problem.depot_id + 1}"
                            )
                            continue
                        
                        best_solutions, all_costs, improvement = result
                        
                        num_samples_generated += len(all_costs)
                        num_solutions_kept += len(best_solutions)
                        all_costs_list.extend(all_costs)
                        kept_costs_list.extend(all_costs[:len(best_solutions)])
                        oversampling_improvement += improvement
                        
                        # 步骤 3: 将解转换为 Cordeau 格式
                        conversion_start = time.time()
                        
                        for idx, solution_tensor in enumerate(best_solutions):
                            try:
                                # 创建客户映射
                                customer_mapping = {
                                    i: sub_problem.customer_indices[i]
                                    for i in range(len(sub_problem.customer_indices))
                                }
                                
                                # 转换为路径
                                routes = SolutionConverter.convert_rl4co_to_cordeau(
                                    actions=solution_tensor,
                                    depot_id=sub_problem.depot_id,
                                    customer_mapping=customer_mapping,
                                    depot_coords=sub_problem.depot_coords,
                                    customer_coords=sub_problem.customer_coords,
                                    demands=sub_problem.demands,
                                    capacity=sub_problem.capacity
                                )
                                
                                # 验证路径
                                for route in routes:
                                    is_valid, error_msg = SolutionConverter.validate_route(
                                        route=route,
                                        capacity=sub_problem.capacity,
                                        distance_limit=sub_problem.distance_limit
                                    )
                                    
                                    if is_valid:
                                        all_routes.append(route)
                                        num_valid += 1
                                    else:
                                        if self.config.skip_invalid_solutions:
                                            ErrorHandler.handle_validation_error(
                                                route_info=f"depot {route.depot_id}, vehicle {route.vehicle_id}",
                                                error_message=error_msg
                                            )
                                            num_invalid += 1
                                        else:
                                            all_routes.append(route)
                                            num_valid += 1
                            
                            except Exception as e:
                                ErrorHandler.handle_conversion_error(e, idx)
                                num_invalid += 1
                        
                        conversion_time += time.time() - conversion_start
                    
                    vrpl_time = time.time() - vrpl_start
                    oversampling_improvement /= len(sub_problems) if len(sub_problems) > 0 else 1  # 平均值
                    
                    self.logger.info(f"VRPL generation completed in {vrpl_time:.2f}s")
                    self.logger.info(f"Generated {num_samples_generated} samples, kept {num_solutions_kept}")
                    
                    # 记录部分成功
                    ErrorHandler.log_partial_success(num_valid, num_valid + num_invalid)
                    
                    # 检查是否有任何有效解
                    if num_valid == 0:
                        self.logger.warning("No valid VRPL solutions, falling back to pure GA_Java")
                        enable_vrpl = False
                        all_routes = []
                    
            except Exception as e:
                self.logger.error(f"VRPL generation failed: {e}")
                if self.config.fallback_on_error:
                    self.logger.warning("Falling back to pure GA_Java")
                    enable_vrpl = False
                    all_routes = []
                else:
                    raise
        
        # 步骤 4: 调用 GA_Java
        from .ga_java_wrapper import GAJavaWrapper
        
        ga_wrapper = GAJavaWrapper()
        ga_result = ga_wrapper.solve_with_initial_solutions(
            instance_data=instance_data,
            initial_solutions=all_routes if enable_vrpl and len(all_routes) > 0 else None,
            vrpl_ratio=vrpl_ratio,
            convergence_interval=self.config.convergence_report_interval
        )
        
        # 步骤 5: 收集指标
        total_time = time.time() - start_time
        
        metrics = PerformanceMetrics(
            vrpl_generation_time=vrpl_time,
            vrpl_num_samples_generated=num_samples_generated,
            vrpl_num_solutions_kept=num_solutions_kept,
            vrpl_avg_cost=np.mean(all_costs_list) if all_costs_list else 0.0,
            vrpl_best_cost=min(all_costs_list) if all_costs_list else 0.0,
            vrpl_kept_avg_cost=np.mean(kept_costs_list) if kept_costs_list else 0.0,
            oversampling_improvement=oversampling_improvement,
            model_used=model_used,
            conversion_time=conversion_time,
            num_valid_solutions=num_valid,
            num_invalid_solutions=num_invalid,
            ga_computation_time=ga_result['compute_time'],
            ga_iterations=ga_result.get('ga_iterations', 0),
            ga_final_cost=ga_result['total_cost'],
            convergence_curve=ga_result.get('convergence_curve', []),
            improvement_vs_random=0.0,  # TODO: 如果有基线则计算
            vrpl_contribution=oversampling_improvement
        )
        
        result = {
            'algorithm': 'VPRL-Enhanced GA-MDVRP',
            'total_cost': ga_result['total_cost'],
            'compute_time': total_time,
            'routes': ga_result['routes'],
            'num_vehicles': ga_result['num_vehicles'],
            'performance_metrics': metrics
        }
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"Solving completed")
        self.logger.info(f"  Total cost: {result['total_cost']:.2f}")
        self.logger.info(f"  Total time: {total_time:.2f}s")
        self.logger.info(f"  VRPL time: {vrpl_time:.2f}s ({vrpl_time/total_time*100:.1f}%)")
        self.logger.info(f"  GA time: {metrics.ga_computation_time:.2f}s")
        self.logger.info(f"  Oversampling improvement: {oversampling_improvement:.1f}%")
        self.logger.info(f"{'='*60}\n")
        
        return result
