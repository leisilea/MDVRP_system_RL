import subprocess
import os
import tempfile
import time
import re
from typing import Dict, List, Tuple
import numpy as np


class GAMDVRPJava:

    def __init__(self, java_home=None, **kwargs):
        self.java_home = java_home
        self.java_cmd = self._find_java()
        self.ga_mdvrp_path = self._find_ga_mdvrp_path()
    
    def _find_java(self):
        if self.java_home:
            java_cmd = os.path.join(self.java_home, 'bin', 'java')
            if os.path.exists(java_cmd):
                return java_cmd
        
        # 使用系统 PATH 中的 java
        return 'java'
    
    def _find_ga_mdvrp_path(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ga_mdvrp_path = os.path.join(
            current_dir,
            '../../ga_mdvrp_reproduction/GA-MDVRP'
        )
        return os.path.abspath(ga_mdvrp_path)
    
    def _convert_from_mdvrp_instance(self, instance):

        # 构建 depots 列表
        depots = []
        for i in range(instance.num_depots):
            depot = {
                'x': float(instance.depots_coords[i, 0]),
                'y': float(instance.depots_coords[i, 1]),
                'vehicle_count': int(instance.depot_vehicles[i]),
                'capacity': int(instance.depot_capacities[i])
            }
            depots.append(depot)
        
        # 构建 customers 列表
        customers = []
        for i in range(instance.num_customers):
            customer = {
                'x': float(instance.customers_coords[i, 0]),
                'y': float(instance.customers_coords[i, 1]),
                'demand': int(instance.demands[i]),
                'service_time': 0  # Cordeau 格式需要，默认为 0
            }
            customers.append(customer)
        
        # 获取最大距离约束
        max_distance = 0
        if instance.max_route_distances is not None:
            max_distance = float(instance.max_route_distances[0])
        
        print(f"[INFO] MDVRPInstance转换: {len(depots)}个仓库, {len(customers)}个客户")
        
        return {
            'depots': depots,
            'customers': customers,
            'max_distance': max_distance
        }
    
    def solve(self, instance_data: Dict, dataset_file: str = None) -> Dict:
        start_time = time.time()
        
        # 类型检查：如果是 MDVRPInstance 对象，转换为字典
        if hasattr(instance_data, 'depots_coords'):
            print("[INFO] 检测到 MDVRPInstance 对象，正在转换...")
            instance_data = self._convert_from_mdvrp_instance(instance_data)
        
        print(f"\n{'='*60}")
        print(f"GA-MDVRP (Java) 求解器")
        print(f"{'='*60}")
        
        # 如果提供了数据集文件路径，直接使用
        if dataset_file and os.path.exists(dataset_file):
            print(f"使用原始数据集文件: {dataset_file}")
            problem_file = dataset_file
            problem_name = dataset_file  
            temp_file_created = False
        else:
            # 1. 将数据写入临时文件（Cordeau 格式）
            problems_dir = os.path.join(self.ga_mdvrp_path, 'data', 'problems')
            os.makedirs(problems_dir, exist_ok=True)
            
            with tempfile.NamedTemporaryFile(
                mode='w', 
                suffix='.dat', 
                delete=False,
                dir=problems_dir
            ) as f:
                problem_file = f.name
                self._write_cordeau_format(f, instance_data)
            
            # 使用相对于 GA-MDVRP 根目录的路径
            problem_name = os.path.relpath(problem_file, self.ga_mdvrp_path)
            temp_file_created = True
        
        # 2. 创建临时输出文件路径
        solution_file = os.path.join(
            self.ga_mdvrp_path,
            'data',
            'solutions',
            f'{problem_name}.res'
        )
        
        try:
            # 3. 调用 Java 程序
            print(f"问题文件: {problem_name}")
            print(f"输出文件: {solution_file}")
            print(f"开始求解...")
            
            # 运行 Java 程序
            result = self._run_java_solver(problem_name)
            
            print(f"\nJava 程序输出:")
            print(result.stdout)
            
            if result.returncode != 0:
                print(f"[WARNING] Java 程序返回非零状态码: {result.returncode}")
                print(f"错误输出: {result.stderr}")
            
            # 4. 解析结果
            print(f"\n{'='*60}")
            print(f"开始解析结果")
            print(f"{'='*60}")
            
            if os.path.exists(solution_file):
                routes, total_cost = self._parse_solution_file(solution_file, instance_data)
            else:
                print(f"[WARNING] 未找到输出文件: {solution_file}")
                # 尝试从标准输出解析成本和路径
                total_cost = self._extract_cost_from_output(result.stdout)
                routes = self._extract_routes_from_output(result.stdout, instance_data)
            
            # 验证客户覆盖
            all_visited_customers = set()
            for route in routes:
                all_visited_customers.update(route['customers'])
            
            total_customers = len(instance_data['customers'])
            if len(all_visited_customers) < total_customers:
                unvisited = set(range(total_customers)) - all_visited_customers
                print(f"[WARNING] 有 {len(unvisited)} 个客户未被访问: {sorted(unvisited)}")
            
            print(f"{'='*60}\n")
            
        except subprocess.TimeoutExpired:
            print(f"[WARNING] Java 程序执行超时（60分钟）")
            total_cost = float('inf')
            routes = []
        except Exception as e:
            print(f"[WARNING] 执行过程中出错: {e}")
            import traceback
            traceback.print_exc()
            total_cost = float('inf')
            routes = []
        finally:
            # 清理临时文件（仅当创建了临时文件时）
            if temp_file_created and os.path.exists(problem_file):
                try:
                    os.unlink(problem_file)
                except:
                    pass
        
        compute_time = time.time() - start_time
        
        # 检查结果合理性
        if total_cost == 0.0 and len(routes) > 0:
            print(f"\n[WARNING] 总成本为 0，这可能表示：")
            print(f"  1. 所有客户坐标都是 (0, 0)")
            print(f"  2. 客户坐标与仓库坐标相同")
            print(f"  3. 输入数据格式不正确")
            print(f"  请检查输入数据！")
        
        result_dict = {
            'algorithm': 'GA-MDVRP (Ombuki-Berman 2009)',
            'total_cost': total_cost,
            'compute_time': compute_time,
            'routes': routes,
            'num_vehicles': len(routes),
            'convergence_data': []  # Java 版本不提供收敛数据
        }
        
        print(f"\n{'='*60}")
        print(f"求解完成")
        print(f"  总成本: {total_cost:.2f}")
        print(f"  路径数: {len(routes)}")
        print(f"  计算时间: {compute_time:.2f}秒")
        print(f"{'='*60}\n")
        
        return result_dict
    
    def _run_java_solver(self, problem_name):
        """运行 Java 求解器"""
        # 方法1: 尝试使用编译好的 class 文件
        out_dir = os.path.join(self.ga_mdvrp_path, 'out')
        
        if os.path.exists(out_dir):
            # 使用编译好的类（CLI版本，无需JavaFX）
            cmd = [
                self.java_cmd,
                '-cp', out_dir,
                'MainCLI',
                problem_name
            ]
        else:
            # 方法2: 尝试直接编译并运行
            src_dir = os.path.join(self.ga_mdvrp_path, 'src')
            cmd = [
                self.java_cmd,
                '-cp', src_dir,
                'MainCLI',
                problem_name
            ]
        
        # 设置工作目录为 GA-MDVRP 根目录
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 60分钟超时（允许大规模实例运行）
            cwd=self.ga_mdvrp_path
        )
        
        return result
    
    def _write_cordeau_format(self, f, instance_data):
        """将数据写入 Cordeau 格式文件"""
        depots = instance_data['depots']
        customers = instance_data['customers']
        
        num_depots = len(depots)
        num_customers = len(customers)
        vehicles_per_depot = int(depots[0].get('vehicle_count', 5))
        
        # 第一行：类型 车辆数 客户数 仓库数
        f.write(f"2 {vehicles_per_depot} {num_customers} {num_depots}\n")
        
        # 仓库信息：最大距离 容量（必须是整数）
        max_distance = int(instance_data.get('max_distance', 0))
        for depot in depots:
            capacity = int(depot['capacity'])
            f.write(f"{max_distance} {capacity}\n")
        
        # 客户信息：ID x y 服务时间 需求
        # 注意：Java 使用 Integer.parseInt() 读取坐标，必须写成整数格式
        for i, customer in enumerate(customers, 1):
            x = int(round(customer['x']))  # 转换为整数
            y = int(round(customer['y']))  # 转换为整数
            demand = int(customer['demand'])
            service_time = int(customer.get('service_time', 0))
            f.write(f"{i} {x} {y} {service_time} {demand}\n")
        
        # 仓库坐标：ID x y
        # 注意：Java 使用 Integer.parseInt() 读取坐标，必须写成整数格式
        for i, depot in enumerate(depots, 1):
            x = int(round(depot['x']))  # 转换为整数
            y = int(round(depot['y']))  # 转换为整数
            f.write(f"{i} {x} {y}\n")
    
    def _parse_solution_file(self, filepath, instance_data):
        """
        解析 Java 程序输出的解决方案文件
        修复：计算每条路径的实际成本
        """
        routes = []
        total_cost = 0
        
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            
            # 解析路径信息
            route_pattern = r'Route\s+(\d+)\s+(\d+):\s+([\d\s]+)'
            matches = re.findall(route_pattern, content)
            
            for match in matches:
                depot_id = int(match[0]) - 1  # Java是1-indexed，转为0-indexed
                vehicle_id = int(match[1])
                nodes = [int(x) for x in match[2].split()]
                
                # 提取客户（去掉仓库节点，Java是1-indexed）
                customers = [n - 1 for n in nodes if n > 0]
                
                if customers:
                    # 计算路径成本
                    cost = self._calculate_route_cost(
                        depot_id, 
                        customers, 
                        instance_data
                    )
                    
                    routes.append({
                        'depot_id': depot_id,
                        'vehicle_id': vehicle_id,
                        'customers': customers,
                        'cost': cost
                    })
            
            # 提取总成本
            cost_pattern = r'(?:Total distance|Cost):\s*([\d.]+)'
            cost_match = re.search(cost_pattern, content)
            if cost_match:
                total_cost = float(cost_match.group(1))
            
            print(f"[INFO] 从文件解析到 {len(routes)} 条路径，总成本: {total_cost:.2f}")
            
        except Exception as e:
            print(f"[ERROR] 解析解决方案文件失败: {e}")
        
        return routes, total_cost
    
    def _extract_cost_from_output(self, output):
        """从标准输出中提取成本"""
        try:
            # 主模式
            pattern = r'Total distance best solution:\s*([\d.]+)'
            match = re.search(pattern, output)
            if match:
                return float(match.group(1))
            
            # 备用模式
            pattern2 = r'Total distance.*?:\s*([\d.]+)'
            match2 = re.search(pattern2, output)
            if match2:
                return float(match2.group(1))
        except Exception as e:
            print(f"[WARNING] 提取成本时出错: {e}")
        
        return 0.0
    
    def _extract_routes_from_output(self, output, instance_data):
        """
        从标准输出中提取路径信息
        修复：计算每条路径的实际成本
        """
        routes = []
        
        try:
            # 优先使用详细格式: "Depot1: [4, 18, 25] - [42, 19, 40]"
            # 这种格式表示每个depot有多条路径（每个方括号是一辆车的路径）
            # 修复：使用 (?=Depot|\Z) 来匹配到下一个Depot或字符串结尾
            pattern_depot_routes = r'Depot(\d+):\s*(.+?)(?=\s*Depot|\Z)'
            depot_matches = re.findall(pattern_depot_routes, output, re.DOTALL)
            
            if depot_matches:
                for depot_id_str, routes_str in depot_matches:
                    depot_id = int(depot_id_str) - 1  # Java是1-indexed，转为0-indexed
                    # 清理路径字符串（去掉 | 和多余空白）
                    routes_str_clean = routes_str.replace('|', '').strip()
                    
                    # 提取所有方括号中的内容（每个方括号是一辆车）
                    route_pattern = r'\[([^\]]+)\]'
                    route_matches = re.findall(route_pattern, routes_str_clean)
                    
                    for vehicle_idx, route_str in enumerate(route_matches):
                        # Java输出的是1-indexed客户ID
                        customer_ids = [int(c.strip()) for c in route_str.split(',') if c.strip()]
                        # 转换为0-indexed
                        customers_0indexed = [c - 1 for c in customer_ids]
                        
                        if customers_0indexed:
                            # 计算路径成本
                            cost = self._calculate_route_cost(
                                depot_id, 
                                customers_0indexed, 
                                instance_data
                            )
                            
                            routes.append({
                                'depot_id': depot_id,  # 0-indexed
                                'vehicle_id': len(routes) + 1,
                                'customers': customers_0indexed,  # 0-indexed
                                'cost': cost
                            })
                
                print(f"[INFO] 从标准输出提取到 {len(routes)} 条路径")
            else:
                # 备用方案: 尝试 "Depot 1 has customers: [2, 1, 3]" 格式
                # 注意：这种格式把所有客户放在一起，不区分车辆
                pattern_depot_customers = r'Depot\s+(\d+)\s+has\s+customers:\s*\[([^\]]+)\]'
                matches = re.findall(pattern_depot_customers, output)
                
                if matches:
                    print(f"[WARNING] 使用备用格式提取路径（不区分车辆）")
                    for depot_id_str, customers_str in matches:
                        depot_id = int(depot_id_str) - 1
                        customer_ids = [int(c.strip()) for c in customers_str.split(',') if c.strip()]
                        customers_0indexed = [c - 1 for c in customer_ids]
                        
                        if customers_0indexed:
                            # 计算路径成本
                            cost = self._calculate_route_cost(
                                depot_id, 
                                customers_0indexed, 
                                instance_data
                            )
                            
                            routes.append({
                                'depot_id': depot_id,
                                'vehicle_id': len(routes) + 1,
                                'customers': customers_0indexed,
                                'cost': cost
                            })
                    
                    print(f"[INFO] 使用备用模式提取到 {len(routes)} 条路径")
                else:
                    print(f"[ERROR] 无法从标准输出提取路径")
                    
        except Exception as e:
            print(f"[ERROR] 提取路径时出错: {e}")
            import traceback
            traceback.print_exc()
        
        return routes
    
    def _calculate_route_cost(self, depot_id, customers, instance_data):
        """
        计算单条路径的成本（欧几里得距离）
        
        Args:
            depot_id: 仓库索引（0-indexed）
            customers: 客户索引列表（0-indexed）
            instance_data: 问题实例数据
        
        Returns:
            路径总成本
        """
        if not customers:
            return 0.0
        
        depot = instance_data['depots'][depot_id]
        depot_x, depot_y = depot['x'], depot['y']
        
        total_cost = 0.0
        prev_x, prev_y = depot_x, depot_y
        
        # 从仓库到第一个客户，然后依次访问每个客户
        for cust_idx in customers:
            customer = instance_data['customers'][cust_idx]
            cust_x, cust_y = customer['x'], customer['y']
            
            # 计算距离
            dist = np.sqrt((cust_x - prev_x)**2 + (cust_y - prev_y)**2)
            total_cost += dist
            
            prev_x, prev_y = cust_x, cust_y
        
        # 从最后一个客户返回仓库
        dist = np.sqrt((depot_x - prev_x)**2 + (depot_y - prev_y)**2)
        total_cost += dist
        
        return total_cost


