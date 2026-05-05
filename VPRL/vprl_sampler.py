"""
VPRL Sampler: Main orchestrator for RL4CO-GA integration
"""

import os
import time
import logging
import numpy as np
import torch
from typing import Dict, List, Optional, Union
from dataclasses import dataclass

from rl4co.models import POMO

from .config import VPRLConfig
from .instance_decomposer import InstanceDecomposer, CVRPSubProblem
from .solution_converter import SolutionConverter, Route
from .error_handler import ErrorHandler


@dataclass
class ConvergencePoint:
    """Convergence tracking data point"""
    generation: int
    best_cost: float
    timestamp: float  # Seconds since start


@dataclass
class PerformanceMetrics:
    """Performance metrics for VPRL-GA integration"""
    # VRPL metrics
    vrpl_generation_time: float
    vrpl_num_samples_generated: int
    vrpl_num_solutions_kept: int
    vrpl_avg_cost: float
    vrpl_best_cost: float
    vrpl_kept_avg_cost: float
    oversampling_improvement: float
    model_used: str
    
    # Conversion metrics
    conversion_time: float
    num_valid_solutions: int
    num_invalid_solutions: int
    
    # GA_Java metrics
    ga_computation_time: float
    ga_iterations: int
    ga_final_cost: float
    convergence_curve: List[ConvergencePoint]
    
    # Comparison
    improvement_vs_random: float
    vrpl_contribution: float


class VPRLSampler:
    """Main orchestrator for VPRL-enhanced GA solving"""
    
    def __init__(self, model_path: Optional[str] = None, config: Optional[VPRLConfig] = None):
        """
        Initialize VPRL Sampler
        
        Args:
            model_path: Path to RL4CO model checkpoint (overrides config)
            config: VPRLConfig instance or None to use defaults
        """
        # Load configuration
        if config is None:
            config_file = os.path.join(os.path.dirname(__file__), "config.json")
            if os.path.exists(config_file):
                self.config = VPRLConfig.from_file(config_file)
            else:
                self.config = VPRLConfig()
        else:
            self.config = config
        
        # Override model path if provided
        if model_path is not None:
            self.config.model_path = model_path
        
        # Setup logging
        self._setup_logging()
        
        # Model will be loaded on demand
        self.model = None
        self.current_model_path = None
        
        self.logger.info("VPRL_Sampler initialized")
        self.logger.info(f"Configuration:\n{self.config}")
    
    def _setup_logging(self):
        """Setup logging configuration"""
        self.logger = logging.getLogger("VPRL")
        self.logger.setLevel(getattr(logging, self.config.log_level))
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, self.config.log_level))
        formatter = logging.Formatter('[%(levelname)s] %(message)s')
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler (if specified)
        if self.config.log_file:
            os.makedirs(os.path.dirname(self.config.log_file), exist_ok=True)
            file_handler = logging.FileHandler(self.config.log_file)
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
    
    def _select_model_by_size(self, num_customers: int) -> str:
        """
        Select appropriate model based on instance size
        
        Args:
            num_customers: Number of customers
            
        Returns:
            Model path
        """
        model_path = self.config.get_model_for_size(num_customers)
        self.logger.info(f"Auto-selected model for {num_customers} customers: {model_path}")
        return model_path
    
    def _load_model(self, model_path: str) -> bool:
        """
        Load RL4CO model with error handling
        
        Args:
            model_path: Path to model checkpoint
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if already loaded
            if self.model is not None and self.current_model_path == model_path:
                self.logger.debug(f"Model already loaded: {model_path}")
                return True
            
            self.logger.info(f"Loading RL4CO model from: {model_path}")
            
            if not os.path.exists(model_path):
                self.logger.error(f"Model file not found: {model_path}")
                return False
            
            # Load model with device mapping to handle CUDA device mismatch
            # Map all tensors to the configured device (cpu or cuda:0)
            import torch
            import torch.serialization
            import pickle
            import tempfile
            import os as os_module  # Import at function level to avoid scoping issues
            map_location = self.config.device if self.config.device == 'cpu' else 'cuda:0'
            
            # Apply TorchRL compatibility aliases at module level
            # This ensures old API names work during model initialization
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
            
            # Try to load as RouteFinder model first, then fall back to POMO
            try:
                from routefinder.models import RouteFinderBase
                
                # Apply CompatibilityUnpickler patch for old TorchRL API compatibility
                # Save original _load function
                _original_load = torch.serialization._load
                
                def _patched_load(zip_file, map_location, pickle_module, 
                                pickle_file='data.pkl', overall_storage=None, 
                                **pickle_load_args):
                    """Patched _load that injects CompatibilityUnpickler's find_class logic"""
                    original_unpickler = pickle_module.Unpickler
                    
                    class PatchedUnpickler(original_unpickler):
                        def find_class(self, mod_name, name):
                            # TorchRL API remappings for old checkpoints
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
                
                # Apply patch and load model
                try:
                    torch.serialization._load = _patched_load
                    
                    # Fix for RNG state CUDA loading error:
                    # Load checkpoint to CPU first to avoid RNG state device mapping issues
                    checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
                    
                    # Remove RNG states if present (not needed for inference)
                    if 'rng_states' in checkpoint:
                        self.logger.debug("Removing RNG states from checkpoint (not needed for inference)")
                        del checkpoint['rng_states']
                    
                    # Remove training-only hyperparameters that cause loading errors
                    if 'hyper_parameters' in checkpoint:
                        training_only_params = ['normalize_reward', 'alpha', 'epsilon', 'norm_operation']
                        for param in training_only_params:
                            if param in checkpoint['hyper_parameters']:
                                self.logger.debug(f"Removing training-only parameter: {param}={checkpoint['hyper_parameters'][param]}")
                                checkpoint['hyper_parameters'].pop(param)
                    
                    # Always use manual loading to avoid Lightning's parameter validation
                    if 'hyper_parameters' in checkpoint and 'state_dict' in checkpoint:
                        hparams = checkpoint['hyper_parameters'].copy()
                        
                        self.model = RouteFinderBase(**hparams)
                        
                        # Load state dict
                        self.model.load_state_dict(checkpoint['state_dict'], strict=False)
                        
                        self.logger.info("Loaded as RouteFinder model")
                    else:
                        raise ValueError("Checkpoint missing required keys: hyper_parameters or state_dict")
                finally:
                    # Always restore original function
                    torch.serialization._load = _original_load
                    
            except (ImportError, Exception) as e:
                self.logger.warning(f"RouteFinder loading failed: {type(e).__name__}: {e}")
                self.logger.debug(f"Not a RouteFinder model, trying POMO")
                
                # Fix for RNG state CUDA loading error:
                # Load checkpoint to CPU first, remove RNG states, then load model
                checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
                
                # Remove RNG states if present (not needed for inference)
                if 'rng_states' in checkpoint:
                    self.logger.debug("Removing RNG states from checkpoint (not needed for inference)")
                    del checkpoint['rng_states']
                
                # Save cleaned checkpoint to temporary file for load_from_checkpoint
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.ckpt', delete=False) as tmp_file:
                    tmp_path = tmp_file.name
                    torch.save(checkpoint, tmp_path)
                
                try:
                    self.model = POMO.load_from_checkpoint(
                        tmp_path,
                        map_location='cpu'
                    )
                    self.logger.info("Loaded as POMO model")
                finally:
                    # Clean up temporary file
                    if os_module.path.exists(tmp_path):
                        os_module.unlink(tmp_path)
            
            self.model.eval()
            self.model = self.model.to(self.config.device)
            self.current_model_path = model_path
            
            self.logger.info(f"Model loaded successfully on device: {self.config.device}")
            return True
            
        except Exception as e:
            # Use error handler
            should_continue, action = ErrorHandler.handle_model_loading_error(e)
            return False
    
    def _generate_vrpl_solutions(
        self,
        sub_problem: CVRPSubProblem,
        num_solutions_needed: int,
        retry_count: int = 0) -> tuple:
        """
        Generate solutions using RL4CO with oversampling and error handling
        
        Args:
            sub_problem: CVRP sub-problem
            num_solutions_needed: Number of solutions needed
            retry_count: Current retry count
            
        Returns:
            Tuple of (best_solutions, all_costs, improvement) or (None, None, 0.0) on failure
        """
        try:
            # Calculate number of samples to generate (oversampling)
            num_samples = int(num_solutions_needed * self.config.oversampling_ratio)
            
            self.logger.info(
                f"Oversampling: generating {num_samples} samples, will keep best {num_solutions_needed}"
            )
            
            # Generate samples
            # Use model's environment to properly initialize the problem
            # This ensures all environment parameters are correctly set
            all_solutions = []
            all_costs = []
            
            with torch.no_grad():
                for i in range(num_samples):
                    # Create a fresh TensorDict for each sample
                    td = sub_problem.tensordict.clone().to(self.config.device)
                    
                    # Reset environment with the problem data
                    # This properly initializes all environment state
                    td_reset = self.model.env.reset(td)
                    
                    out = self.model.policy(
                        td_reset,
                        decode_type=self.config.decode_type,
                        temperature=self.config.sampling_temperature,
                        return_actions=True
                    )
                    
                    # Get cost
                    cost = self.model.env.get_reward(td_reset, out['actions'])
                    
                    all_solutions.append(out['actions'].cpu())
                    all_costs.append(cost.cpu().item())
            
            # Select best solutions
            best_solutions, improvement = self._select_best_solutions(
                all_solutions, all_costs, num_solutions_needed
            )
            
            self.logger.info(
                f"Oversampling improvement: {improvement:.1f}% "
                f"(avg cost: {np.mean(all_costs):.2f} → {np.mean([all_costs[i] for i in range(num_solutions_needed)]):.2f})"
            )
            
            return best_solutions, all_costs, improvement
            
        except Exception as e:
            # Use error handler
            should_retry, action = ErrorHandler.handle_generation_error(e, retry_count)
            
            if should_retry:
                # Retry once
                return self._generate_vrpl_solutions(
                    sub_problem, num_solutions_needed, retry_count + 1
                )
            else:
                # Return empty results to trigger fallback
                return None, None, 0.0
    
    def _select_best_solutions(
        self,
        solutions: List[torch.Tensor],
        costs: List[float],
        num_to_keep: int) -> tuple:
        """
        Select best solutions from oversampled pool
        
        Args:
            solutions: List of solution tensors
            costs: List of costs
            num_to_keep: Number of solutions to keep
            
        Returns:
            (best_solutions, oversampling_improvement_percentage)
        """
        # Sort by cost
        sorted_indices = np.argsort(costs)
        best_indices = sorted_indices[:num_to_keep]
        
        # Select best solutions
        best_solutions = [solutions[i] for i in best_indices]
        
        # Calculate improvement
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
        Solve MDVRP instance with VRPL-enhanced GA
        
        Args:
            instance_data: MDVRPInstance object or path to Cordeau file
            enable_vrpl: Whether to use VRPL initialization (overrides config)
            num_solutions_needed: Number of solutions needed (overrides config)
            oversampling_ratio: Oversampling ratio (overrides config)
            temperature: Sampling temperature (overrides config)
            vrpl_ratio: VRPL ratio in population (overrides config)
            
        Returns:
            Solution dictionary with routes, cost, and performance metrics
        """
        start_time = time.time()
        
        # Load instance if it's a file path
        if isinstance(instance_data, str):
            self.logger.info(f"Loading Cordeau instance from: {instance_data}")
            from .cordeau_parser import load_cordeau_instance
            instance_data = load_cordeau_instance(instance_data)
            self.logger.info(f"Instance loaded: {instance_data.num_depots} depots, {instance_data.num_customers} customers")
        
        # Apply parameter overrides
        enable_vrpl = enable_vrpl if enable_vrpl is not None else self.config.enable_vrpl
        num_solutions_needed = num_solutions_needed if num_solutions_needed is not None else self.config.num_solutions_needed
        vrpl_ratio = vrpl_ratio if vrpl_ratio is not None else self.config.vrpl_ratio
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"VPRL-Enhanced GA Solver")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"VRPL enabled: {enable_vrpl}")
        self.logger.info(f"Solutions needed: {num_solutions_needed}")
        
        # Initialize metrics
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
        
        # Step 1: Decompose MDVRP if VRPL is enabled
        if enable_vrpl:
            try:
                self.logger.info(f"Decomposing MDVRP instance...")
                
                # Get number of customers for model selection
                num_customers = instance_data.num_customers
                
                # Select and load model
                model_path = self._select_model_by_size(num_customers)
                model_used = model_path
                
                if not self._load_model(model_path):
                    self.logger.warning("Model loading failed, disabling VRPL")
                    enable_vrpl = False
                else:
                    # Decompose MDVRP
                    sub_problems = InstanceDecomposer.decompose_mdvrp(
                        instance=instance_data,
                        strategy=self.config.assignment_strategy
                    )
                    
                    self.logger.info(
                        f"Decomposed into {len(sub_problems)} CVRP sub-problems"
                    )
                    
                    # Step 2: Generate solutions for each depot
                    vrpl_start = time.time()
                    
                    for sub_problem in sub_problems:
                        self.logger.info(
                            f"Generating solutions for depot {sub_problem.depot_id + 1} "
                            f"({len(sub_problem.customer_indices)} customers)"
                        )
                        
                        # Generate solutions with oversampling
                        result = self._generate_vrpl_solutions(
                            sub_problem=sub_problem,
                            num_solutions_needed=num_solutions_needed
                        )
                        
                        # Check if generation failed
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
                        
                        # Step 3: Convert solutions to Cordeau format
                        conversion_start = time.time()
                        
                        for idx, solution_tensor in enumerate(best_solutions):
                            try:
                                # Create customer mapping
                                customer_mapping = {
                                    i: sub_problem.customer_indices[i]
                                    for i in range(len(sub_problem.customer_indices))
                                }
                                
                                # Convert to routes
                                routes = SolutionConverter.convert_rl4co_to_cordeau(
                                    actions=solution_tensor,
                                    depot_id=sub_problem.depot_id,
                                    customer_mapping=customer_mapping,
                                    depot_coords=sub_problem.depot_coords,
                                    customer_coords=sub_problem.customer_coords,
                                    demands=sub_problem.demands,
                                    capacity=sub_problem.capacity
                                )
                                
                                # Validate routes
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
                    oversampling_improvement /= len(sub_problems) if len(sub_problems) > 0 else 1  # Average
                    
                    self.logger.info(f"VRPL generation completed in {vrpl_time:.2f}s")
                    self.logger.info(f"Generated {num_samples_generated} samples, kept {num_solutions_kept}")
                    
                    # Log partial success
                    ErrorHandler.log_partial_success(num_valid, num_valid + num_invalid)
                    
                    # Check if we have any valid solutions
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
        
        # Step 4: Call GA_Java
        from .ga_java_wrapper import GAJavaWrapper
        
        ga_wrapper = GAJavaWrapper()
        ga_result = ga_wrapper.solve_with_initial_solutions(
            instance_data=instance_data,
            initial_solutions=all_routes if enable_vrpl and len(all_routes) > 0 else None,
            vrpl_ratio=vrpl_ratio,
            convergence_interval=self.config.convergence_report_interval
        )
        
        # Step 5: Collect metrics
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
            improvement_vs_random=0.0,  # TODO: Calculate if baseline available
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
