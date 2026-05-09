"""
GA-MDVRP + RouteFinder 混合求解器
实现完整的工作流：前端数据 → Java GA → RL初始化 → GA优化

工作流程:
1. 前端数据通过 ga_mdvrp_java.py 解析
2. Java GA 进行仓库分割（depot assignment）
3. 生成初始种群：80% 随机 + 20% RL生成
4. RL部分：将分割后的子问题转换为npz → RouteFinder推理 → 转回GA格式
5. 合并初始种群并运行GA优化
"""

import os
import sys
import json
import time
import tempfile
import subprocess
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple

# 添加RL4CO路径
RL4CO_PATH = Path(__file__).parent.parent.parent.parent / "RL4CO_Integration"
sys.path.insert(0, str(RL4CO_PATH / "routefinder"))


class GAMDVRPRLHybrid:
    def __init__(self, rl_seed_ratio=0.2, num_rl_samples=20, use_gpu=True, model_type='auto'):

        self.rl_seed_ratio = rl_seed_ratio
        self.num_rl_samples = num_rl_samples
        self.use_gpu = use_gpu
        self.model_type = model_type
        
        # 路径配置
        self.rl4co_path = RL4CO_PATH
        self.ga_mdvrp_path = Path(__file__).parent.parent.parent / "ga_mdvrp_reproduction" / "GA-MDVRP"
        
        print(f"[Hybrid Solver] 初始化完成")
        print(f"  RL种子比例: {rl_seed_ratio*100:.0f}%")
        print(f"  RL采样数: {num_rl_samples}")
        print(f"  使用GPU: {use_gpu}")
        print(f"  模型选择: {model_type}")
    
    def solve(self, instance_data: Dict) -> Dict:
        """
        求解MDVRP实例（混合方法）
        
        Args:
            instance_data: 包含depots和customers的字典
            
        Returns:
            求解结果字典
        """
        start_time = time.time()
        
        print(f"\n{'='*70}")
        print(f"GA-MDVRP + RouteFinder 混合求解器")
        print(f"{'='*70}\n")
        
        # 步骤1: 数据预处理和仓库分割
        print(f"[步骤1/5] 数据预处理和仓库分割...")
        depot_assignments = self._assign_customers_to_depots(instance_data)
        
        # 步骤2: 生成RL种子解
        print(f"\n[步骤2/5] 使用RouteFinder生成种子解...")
        rl_seeds = self._generate_rl_seeds(instance_data, depot_assignments)
        
        # 步骤3: 转换为GA格式的JSON
        print(f"\n[步骤3/5] 转换为GA初始种群格式...")
        seed_json_path = self._convert_to_ga_format(rl_seeds, instance_data, depot_assignments)
        
        # 步骤4: 运行Java GA（使用混合初始化）
        print(f"\n[步骤4/5] 运行GA优化...")
        result = self._run_ga_with_seeds(instance_data, seed_json_path)
        
        # 步骤5: 清理临时文件
        print(f"\n[步骤5/5] 清理临时文件...")
        self._cleanup(seed_json_path)
        
        compute_time = time.time() - start_time
        result['compute_time'] = compute_time
        result['algorithm'] = 'GA-MDVRP + RouteFinder Hybrid'
        
        print(f"\n{'='*70}")
        print(f"混合求解完成")
        print(f"  总成本: {result['total_cost']:.2f}")
        print(f"  计算时间: {compute_time:.2f}秒")
        print(f"{'='*70}\n")
        
        return result
    
    def _assign_customers_to_depots(self, instance_data: Dict) -> Dict:
        """
        将客户分配到最近的仓库（贪心策略）
        
        Returns:
            depot_assignments: {depot_idx: [customer_indices]}
        """
        depots = instance_data['depots']
        customers = instance_data['customers']
        
        depot_assignments = {i: [] for i in range(len(depots))}
        
        for cust_idx, customer in enumerate(customers):
            cx, cy = customer['x'], customer['y']
            
            # 找最近的depot
            min_dist = float('inf')
            best_depot = 0
            
            for depot_idx, depot in enumerate(depots):
                dx, dy = depot['x'], depot['y']
                dist = np.sqrt((cx - dx)**2 + (cy - dy)**2)
                
                if dist < min_dist:
                    min_dist = dist
                    best_depot = depot_idx
            
            depot_assignments[best_depot].append(cust_idx)
        
        # 打印分配结果
        print(f"  仓库分配结果:")
        for depot_idx, customers_list in depot_assignments.items():
            print(f"    Depot {depot_idx+1}: {len(customers_list)} customers")
        
        return depot_assignments
    
    def _select_model(self, instance_data: Dict, depot_assignments: Dict) -> Tuple[str, str]:
        """
        根据问题特征自动选择合适的模型
        
        【重要】参照官方文档和成功的P21代码：
        - 模型规模：根据平均客户数选择50或100
        - 模型类型：根据约束类型选择
          * 只有容量约束：rf-pomo
          * 只有距离约束：rf-pomo
          * **同时有容量和距离约束：rf-moe（多任务模型）**
        
        关键修复：正确识别同时有两种约束的情况
        
        Returns:
            (model_size, model_type): 例如 ('100', 'rf-pomo')
        """
        # 计算平均每个depot的客户数
        avg_customers_per_depot = sum(len(custs) for custs in depot_assignments.values()) / len(depot_assignments)
        
        # 检查约束类型（关键修复）
        max_distance = instance_data.get('max_distance', 0)
        has_distance_constraint = max_distance > 0
        
        # 检查容量约束：所有depot都有有限容量
        has_capacity_constraint = all(
            d.get('capacity', float('inf')) < float('inf') and d.get('capacity', 0) > 0 
            for d in instance_data['depots']
        )
        
        # 选择模型规模
        if avg_customers_per_depot <= 30:
            model_size = '50'
        else:
            model_size = '100'
        
        # 选择模型类型
        if self.model_type != 'auto':
            model_type = self.model_type
        else:
            # 自动选择策略（参照官方文档，关键修复）
            if has_distance_constraint and has_capacity_constraint:
                # 两种约束都有：使用MoE模型（多任务学习）
                model_type = 'rf-moe'
                print(f"  [模型选择] 检测到同时有距离约束(max_distance={max_distance})和容量约束 → 使用rf-moe")
            elif has_distance_constraint:
                # 只有距离约束：使用POMO
                model_type = 'rf-pomo'
                print(f"  [模型选择] 只有距离约束(max_distance={max_distance}) → 使用rf-pomo")
            elif has_capacity_constraint:
                # 只有容量约束：使用标准POMO
                model_type = 'rf-pomo'
                print(f"  [模型选择] 只有容量约束 → 使用rf-pomo")
            else:
                # 无约束或约束不明确：使用标准POMO
                model_type = 'rf-pomo'
                print(f"  [模型选择] 无明确约束 → 使用rf-pomo")
        
        print(f"  问题特征分析:")
        print(f"    平均客户数/depot: {avg_customers_per_depot:.1f}")
        print(f"    距离约束: {'是' if has_distance_constraint else '否'} (max_distance={max_distance})")
        print(f"    容量约束: {'是' if has_capacity_constraint else '否'}")
        print(f"  最终选择模型: {model_size}/{model_type}")
        
        return model_size, model_type
    
    def _generate_rl_seeds(self, instance_data: Dict, depot_assignments: Dict) -> List[Dict]:
        """
        使用RouteFinder为每个depot生成种子解
        
        Returns:
            List of solutions, each containing depot-wise routes
        """
        import torch
        from routefinder.envs import MTVRPEnv
        from routefinder.models import RouteFinderBase, RouteFinderMoE
        from routefinder.models.baselines.mtpomo import MTPOMO
        from routefinder.models.baselines.mvmoe import MVMoE
        
        # TorchRL兼容性修复
        import torchrl.data.tensor_specs as specs
        if not hasattr(specs, 'CompositeSpec'):
            specs.CompositeSpec = specs.Composite
        if not hasattr(specs, 'BoundedTensorSpec'):
            specs.BoundedTensorSpec = specs.Bounded
        if not hasattr(specs, 'UnboundedContinuousTensorSpec'):
            specs.UnboundedContinuousTensorSpec = specs.UnboundedContinuous
        if not hasattr(specs, 'UnboundedDiscreteTensorSpec'):
            specs.UnboundedDiscreteTensorSpec = specs.UnboundedDiscrete
        
        device = torch.device('cuda' if self.use_gpu and torch.cuda.is_available() else 'cpu')
        print(f"  使用设备: {device}")
        
        # 自动选择模型
        model_size, model_type = self._select_model(instance_data, depot_assignments)
        
        # 构建checkpoint路径
        checkpoint_path = self.rl4co_path / "routefinder" / "checkpoints" / model_size / f"{model_type}.ckpt"
        if not checkpoint_path.exists():
            print(f"  [WARNING] 模型未找到: {checkpoint_path}")
            # 回退到默认模型
            checkpoint_path = self.rl4co_path / "routefinder" / "checkpoints" / "100" / "rf-pomo.ckpt"
            print(f"  使用默认模型: {checkpoint_path}")
        
        if not checkpoint_path.exists():
            raise RuntimeError(f"RouteFinder checkpoint未找到: {checkpoint_path}")
        
        # 根据模型类型选择正确的类
        if 'mvmoe' in model_type:
            BaseLitModule = MVMoE
        elif 'mtpomo' in model_type:
            BaseLitModule = MTPOMO
        elif 'moe' in model_type:
            BaseLitModule = RouteFinderMoE
        else:
            BaseLitModule = RouteFinderBase
        
        print(f"  加载模型: {checkpoint_path.name} (类型: {BaseLitModule.__name__})")
        model = BaseLitModule.load_from_checkpoint(str(checkpoint_path), map_location='cpu', strict=False)
        policy = model.policy.to(device)
        policy.eval()
        
        # 验证policy在正确的设备上
        print(f"  Policy设备验证:")
        for name, param in list(policy.named_parameters())[:3]:
            print(f"    {name}: {param.device}")
        
        print(f"  [INFO] 模型加载完成，开始为每个depot生成解...")
        
        # 为每个depot生成解
        all_depot_solutions = []
        
        for depot_idx, customer_indices in depot_assignments.items():
            if not customer_indices:
                continue
            
            print(f"\n  处理 Depot {depot_idx+1} ({len(customer_indices)} customers)...")
            
            # 创建npz文件
            npz_path = self._create_depot_npz(
                instance_data, 
                depot_idx, 
                customer_indices
            )
            
            # 使用RouteFinder采样
            depot_solutions = self._sample_depot_solutions(
                policy, 
                npz_path, 
                device,
                num_samples=self.num_rl_samples
            )
            
            all_depot_solutions.append({
                'depot_idx': depot_idx,
                'customer_indices': customer_indices,
                'solutions': depot_solutions
            })
            
            # 清理npz
            os.unlink(npz_path)
        
        return all_depot_solutions
    
    def _create_depot_npz(self, instance_data: Dict, depot_idx: int, customer_indices: List[int]) -> str:
        """
        为单个depot创建npz文件（MTVRPEnv格式）
        
        关键修复：参照solve_p21_fixed.py的正确格式
        - 正确归一化坐标（先归一化再构建locs）
        - vehicle_capacity是单车容量（归一化后），不是总容量
        - 需求也要归一化
        """
        depot = instance_data['depots'][depot_idx]
        customers = instance_data['customers']
        
        # 提取该depot的客户
        depot_customers = [customers[i] for i in customer_indices]
        n_customers = len(depot_customers)
        
        # 收集所有坐标用于归一化
        all_x = [c['x'] for c in depot_customers] + [depot['x']]
        all_y = [c['y'] for c in depot_customers] + [depot['y']]
        x_min, x_max = min(all_x), max(all_x)
        y_min, y_max = min(all_y), max(all_y)
        x_range = max(x_max - x_min, 1)
        y_range = max(y_max - y_min, 1)
        
        # 构建坐标矩阵: shape = (1, n_customers+1, 2)
        # depot在第一个位置
        locs = np.zeros((1, n_customers + 1, 2), dtype=np.float32)
        
        # Depot坐标（归一化）
        locs[0, 0, 0] = (depot['x'] - x_min) / x_range
        locs[0, 0, 1] = (depot['y'] - y_min) / y_range
        
        # 客户坐标（归一化）
        for i, customer in enumerate(depot_customers):
            locs[0, i+1, 0] = (customer['x'] - x_min) / x_range
            locs[0, i+1, 1] = (customer['y'] - y_min) / y_range
        
        # 需求 (只包含客户，不包含depot), shape = (1, n_customers)
        demands = np.array([c['demand'] for c in depot_customers], dtype=np.float32).reshape(1, n_customers)
        
        # 归一化需求和容量
        # 关键：vehicle_capacity是单车容量，不是所有车的总容量
        max_demand = demands.max()
        if max_demand > 0:
            demands_normalized = demands / max_demand
            capacity_normalized = depot.get('capacity', 60) / max_demand  # 单车容量归一化
        else:
            demands_normalized = demands
            capacity_normalized = depot.get('capacity', 60)
        
        # 其他必需字段
        vehicle_capacity = np.array([[capacity_normalized]], dtype=np.float32)
        speed = np.ones((1, 1), dtype=np.float32)
        num_depots = np.ones((1, 1), dtype=np.int32)
        
        # 保存npz
        with tempfile.NamedTemporaryFile(suffix='.npz', delete=False) as f:
            npz_path = f.name
        
        np.savez(
            npz_path,
            locs=locs,
            demand_linehaul=demands_normalized,
            vehicle_capacity=vehicle_capacity,
            speed=speed,
            num_depots=num_depots
        )
        
        return npz_path
    
    def _sample_depot_solutions(self, policy, npz_path: str, device, num_samples: int) -> List[Dict]:
        """
        对单个depot使用RouteFinder采样
        
        关键修复：参照solve_p21_fixed.py和test.py的正确推理方式
        - 使用 policy(td_reset, env, phase="test", num_starts=1, return_actions=True, decode_type="sampling")
        - 不要循环调用policy，一次调用就完成整个解码过程
        """
        import torch
        from routefinder.envs import MTVRPEnv
        
        print(f"    开始采样，设备: {device}, 采样数量: {num_samples}")
        
        env = MTVRPEnv()
        td_original = env.load_data(npz_path)
        td_original = td_original.to(device)
        
        solutions = []
        
        with torch.inference_mode():
            for i in range(num_samples):
                if i % 5 == 0:
                    print(f"    采样进度: {i}/{num_samples}")
                
                # 每次都从原始td创建一个新的副本
                td = td_original.clone()
                td_reset = env.reset(td)
                
                # 关键修复：使用官方推理方式，一次调用完成整个解码
                # 参照 solve_p21_fixed.py 和 test.py
                out = policy(
                    td_reset, 
                    env, 
                    phase="test", 
                    num_starts=1, 
                    return_actions=True, 
                    decode_type="sampling"
                )
                
                # 提取结果
                cost = -out['reward'].item()
                actions = out['actions'].cpu().numpy()[0]  # 转换为numpy数组
                
                # 统计返回depot的次数（车辆数）
                num_vehicles = (actions == 0).sum()
                
                solutions.append({
                    'actions': actions.tolist(),
                    'cost': cost,
                    'num_vehicles': int(num_vehicles)
                })
        
        # 按成本排序
        solutions.sort(key=lambda x: x['cost'])
        
        print(f"    生成 {len(solutions)} 个解，最佳成本: {solutions[0]['cost']:.2f}, 车辆数: {solutions[0]['num_vehicles']}")
        
        return solutions
    
    def _convert_to_ga_format(self, rl_seeds: List[Dict], instance_data: Dict, depot_assignments: Dict) -> str:
        """
        将RL种子解转换为GA格式的JSON
        """
        num_seeds = int(100 * self.rl_seed_ratio)  # 假设种群大小为100
        
        ga_individuals = []
        
        for sol_idx in range(num_seeds):
            chromosome = {}
            total_fitness = 0.0
            
            for depot_data in rl_seeds:
                depot_idx = depot_data['depot_idx']
                customer_indices = depot_data['customer_indices']
                solutions = depot_data['solutions']
                
                # 获取第sol_idx个解（循环使用）
                solution = solutions[sol_idx % len(solutions)]
                actions = solution['actions']
                cost = solution['cost']
                
                # 转换actions为routes
                routes = self._actions_to_routes(actions, customer_indices, instance_data)
                
                # 添加到chromosome（depot_id是1-indexed）
                chromosome[depot_idx + 1] = routes
                total_fitness += cost
            
            ga_individuals.append({
                'chromosome': chromosome,
                'fitness': total_fitness,
                'isFeasible': True
            })
        
        # 保存JSON
        output_data = {
            'population': ga_individuals,
            'metadata': {
                'source': 'RouteFinder',
                'num_individuals': len(ga_individuals),
                'best_fitness': ga_individuals[0]['fitness'] if ga_individuals else 0
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(output_data, f, indent=2)
            json_path = f.name
        
        print(f"  生成 {len(ga_individuals)} 个种子Individual")
        print(f"  最佳fitness: {ga_individuals[0]['fitness']:.2f}")
        
        return json_path
    
    def _actions_to_routes(self, actions: List[int], customer_indices: List[int], instance_data: Dict) -> List[Dict]:
        """
        将RouteFinder的actions转换为GA的route格式
        """
        routes = []
        current_route = []
        
        for action in actions:
            if action == 0:
                # 返回depot
                if current_route:
                    # 转换为全局客户ID（1-indexed）
                    global_ids = [customer_indices[cid] + 1 for cid in current_route]
                    demand = sum(instance_data['customers'][customer_indices[cid]]['demand'] 
                                for cid in current_route)
                    
                    routes.append({
                        'route': global_ids,
                        'demand': int(demand),
                        'distance': 0.0  # GA会重新计算
                    })
                    current_route = []
            else:
                # 添加客户（action是1-indexed，转为0-indexed）
                current_route.append(action - 1)
        
        # 处理最后一条路线
        if current_route:
            global_ids = [customer_indices[cid] + 1 for cid in current_route]
            demand = sum(instance_data['customers'][customer_indices[cid]]['demand'] 
                        for cid in current_route)
            routes.append({
                'route': global_ids,
                'demand': int(demand),
                'distance': 0.0
            })
        
        return routes
    
    def _run_ga_with_seeds(self, instance_data: Dict, seed_json_path: str) -> Dict:
        """
        运行Java GA（使用种子初始化）
        """
        # 创建临时问题文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dat', delete=False, 
                                        dir=self.ga_mdvrp_path / "data" / "problems") as f:
            problem_file = f.name
            self._write_cordeau_format(f, instance_data)
        
        problem_name = os.path.relpath(problem_file, self.ga_mdvrp_path)
        solution_file = self.ga_mdvrp_path / "data" / "solutions" / f"{problem_name}.res"
        
        try:
            # 运行Java GA
            cmd = [
                'java', '-cp', 'bin;lib/*', 'MainCLI',
                problem_name,
                str(solution_file),
                os.path.abspath(seed_json_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600,
                cwd=str(self.ga_mdvrp_path)
            )
            
            if result.returncode != 0:
                print(f"[WARNING] Java返回非零状态码: {result.returncode}")
                print(f"错误: {result.stderr}")
            
            # 解析结果
            total_cost = self._extract_cost_from_output(result.stdout)
            routes = self._extract_routes_from_output(result.stdout)
            
        finally:
            # 清理问题文件
            if os.path.exists(problem_file):
                os.unlink(problem_file)
        
        return {
            'total_cost': total_cost,
            'routes': routes,
            'num_vehicles': len(routes)
        }
    
    def _write_cordeau_format(self, f, instance_data: Dict):
        """写入Cordeau格式"""
        depots = instance_data['depots']
        customers = instance_data['customers']
        
        num_depots = len(depots)
        num_customers = len(customers)
        vehicles_per_depot = depots[0].get('vehicle_count', 5)
        
        # 第一行
        f.write(f"2 {vehicles_per_depot} {num_customers} {num_depots}\n")
        
        # Depot信息
        max_distance = int(instance_data.get('max_distance', 0))
        for depot in depots:
            capacity = int(depot['capacity'])
            f.write(f"{max_distance} {capacity}\n")
        
        # 客户信息
        for i, customer in enumerate(customers, 1):
            x = int(round(customer['x']))
            y = int(round(customer['y']))
            demand = int(customer['demand'])
            service_time = 0
            f.write(f"{i} {x} {y} {service_time} {demand}\n")
        
        # Depot坐标
        for i, depot in enumerate(depots, 1):
            x = int(round(depot['x']))
            y = int(round(depot['y']))
            f.write(f"{i} {x} {y}\n")
    
    def _extract_cost_from_output(self, output: str) -> float:
        """从输出提取成本"""
        import re
        pattern = r'Total distance best solution:\s*([\d.]+)'
        match = re.search(pattern, output)
        if match:
            return float(match.group(1))
        return 0.0
    
    def _extract_routes_from_output(self, output: str) -> List[Dict]:
        """
        从标准输出中提取路径信息
        使用与ga_mdvrp_java.py相同的逻辑
        """
        import re
        routes = []
        
        try:
            # 使用与ga_mdvrp_java.py相同的模式
            # 格式: "Depot1: [4, 18, 25] - [42, 19, 40]"
            pattern_depot_routes = r'Depot(\d+):\s*(.+?)(?=\s*Depot|\Z)'
            depot_matches = re.findall(pattern_depot_routes, output, re.DOTALL)
            
            if depot_matches:
                for depot_id_str, routes_str in depot_matches:
                    depot_id = int(depot_id_str) - 1  # 转换为0索引
                    # 清理路径字符串（去掉 | 和多余空白）
                    routes_str_clean = routes_str.replace('|', '').strip()
                    
                    # 提取所有方括号中的内容（每个方括号是一辆车）
                    route_pattern = r'\[([^\]]+)\]'
                    route_matches = re.findall(route_pattern, routes_str_clean)
                    
                    for vehicle_idx, route_str in enumerate(route_matches):
                        customer_ids = [int(c.strip()) for c in route_str.split(',') if c.strip()]
                        customers_0indexed = [c - 1 for c in customer_ids]
                        
                        if customers_0indexed:
                            routes.append({
                                'depot_id': depot_id,
                                'vehicle_id': len(routes) + 1,
                                'customers': customers_0indexed,
                                'cost': 0
                            })
                
                print(f"[INFO] 从标准输出提取到 {len(routes)} 条路径")
            else:
                # 备用方案: 尝试 "Depot 1 has customers: [2, 1, 3]" 格式
                pattern_depot_customers = r'Depot\s+(\d+)\s+has\s+customers:\s*\[([^\]]+)\]'
                matches = re.findall(pattern_depot_customers, output)
                
                if matches:
                    print(f"[WARNING] 使用备用格式提取路径（不区分车辆）")
                    for depot_id_str, customers_str in matches:
                        depot_id = int(depot_id_str) - 1
                        customer_ids = [int(c.strip()) for c in customers_str.split(',') if c.strip()]
                        customers_0indexed = [c - 1 for c in customer_ids]
                        
                        if customers_0indexed:
                            routes.append({
                                'depot_id': depot_id,
                                'vehicle_id': len(routes) + 1,
                                'customers': customers_0indexed,
                                'cost': 0
                            })
                    
                    print(f"[INFO] 使用备用模式提取到 {len(routes)} 条路径")
                else:
                    print(f"[ERROR] 无法从标准输出提取路径")
                    
        except Exception as e:
            print(f"[ERROR] 提取路径时出错: {e}")
            import traceback
            traceback.print_exc()
        
        return routes
    
    def _cleanup(self, *paths):
        """清理临时文件"""
        for path in paths:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except:
                    pass


