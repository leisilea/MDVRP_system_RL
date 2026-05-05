"""
GA-MDVRP Java 包装类
通过 subprocess 调用 Java 程序求解 MDVRP

基于: markusmkim/GA-MDVRP
论文: Ombuki-Berman & Hanshar (2009) - Springer
"""

import subprocess
import os
import tempfile
import time
import re
from typing import Dict, List, Tuple
import numpy as np


class GAMDVRPJava:
    """
    GA-MDVRP Java 版本包装类
    通过 subprocess 调用编译好的 Java 程序
    """
    
    def __init__(self, java_home=None, **kwargs):
        """
        初始化包装类
        
        Args:
            java_home: Java 安装路径（可选）
        """
        self.java_home = java_home
        self.java_cmd = self._find_java()
        self.ga_mdvrp_path = self._find_ga_mdvrp_path()
        
        # 检查 Java 环境
        self._check_java()
        
        # 检查 GA-MDVRP 是否已编译
        self._check_compiled()
    
    def _find_java(self):
        """查找 Java 可执行文件"""
        if self.java_home:
            java_cmd = os.path.join(self.java_home, 'bin', 'java')
            if os.path.exists(java_cmd):
                return java_cmd
        
        # 使用系统 PATH 中的 java
        return 'java'
    
    def _find_ga_mdvrp_path(self):
        """查找 GA-MDVRP 项目路径"""
        # 从当前文件位置推算
        # 当前: system_test/algorithm-service/solver/ga_mdvrp_java.py
        # 目标: system_test/ga_mdvrp_reproduction/GA-MDVRP
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ga_mdvrp_path = os.path.join(
            current_dir,
            '../../ga_mdvrp_reproduction/GA-MDVRP'
        )
        return os.path.abspath(ga_mdvrp_path)
    
    def _check_java(self):
        """检查 Java 环境"""
        try:
            result = subprocess.run(
                [self.java_cmd, '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            version_info = result.stderr.split('\n')[0]
            print(f"[OK] Java 环境检查通过: {version_info}")
        except FileNotFoundError:
            raise RuntimeError(
                "未找到 Java！请安装 JDK 11 或更高版本\n"
                "下载地址: https://www.oracle.com/java/technologies/downloads/"
            )
        except Exception as e:
            raise RuntimeError(f"Java 环境检查失败: {e}")
    
    def _check_compiled(self):
        """检查 GA-MDVRP 是否已编译"""
        out_dir = os.path.join(self.ga_mdvrp_path, 'out')
        
        if not os.path.exists(out_dir):
            print(f"[WARNING] GA-MDVRP 尚未编译")
            print(f"  项目路径: {self.ga_mdvrp_path}")
            print(f"  请先编译 Java 代码")
            # 不抛出异常，允许继续（可能使用其他方式运行）
    
    def _convert_from_mdvrp_instance(self, instance):
        """
        将 MDVRPInstance 对象转换为字典格式
        
        Args:
            instance: MDVRPInstance 对象
            
        Returns:
            dict: 包含 depots, customers, max_distance 的字典
        """
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
        
        # 调试：打印转换后的数据
        print(f"[DEBUG] MDVRPInstance 转换结果:")
        print(f"  仓库: {depots}")
        print(f"  客户: {customers}")
        print(f"  最大距离: {max_distance}")
        
        return {
            'depots': depots,
            'customers': customers,
            'max_distance': max_distance
        }
    
    def solve(self, instance_data: Dict, dataset_file: str = None) -> Dict:
        """
        求解 MDVRP 实例
        
        Args:
            instance_data: MDVRPInstance 对象或包含以下字段的字典
                - depots: 仓库列表 [{x, y, vehicle_count, capacity}, ...]
                - customers: 客户列表 [{x, y, demand}, ...]
                - max_distance: 最大行驶距离（可选）
            dataset_file: 可选，直接使用原始数据集文件路径（如 MDVRP-Instances/dat/p01）
                
        Returns:
            包含求解结果的字典
        """
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
            problem_name = dataset_file  # 使用绝对路径
            temp_file_created = False
        else:
            # 1. 将数据写入临时文件（Cordeau 格式）
            # 确保 data/problems 目录存在
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
                print(f"[INFO] 找到输出文件: {solution_file}")
                routes, total_cost = self._parse_solution_file(solution_file)
                print(f"[INFO] 从文件解析到 {len(routes)} 条路径，总成本: {total_cost}")
            else:
                print(f"[WARNING] 未找到输出文件: {solution_file}")
                # 尝试从标准输出解析成本和路径
                total_cost = self._extract_cost_from_output(result.stdout)
                routes = self._extract_routes_from_output(result.stdout)
                print(f"[INFO] 从标准输出解析到 {len(routes)} 条路径，总成本: {total_cost}")
            
            # 详细打印每条路径
            print(f"\n解析到的路径详情:")
            for i, route in enumerate(routes):
                print(f"  路径 {i+1}:")
                print(f"    仓库ID: {route['depot_id']}")
                print(f"    车辆ID: {route['vehicle_id']}")
                print(f"    客户列表: {route['customers']}")
                print(f"    客户数量: {len(route['customers'])}")
            
            # 统计覆盖的客户
            all_visited_customers = set()
            for route in routes:
                all_visited_customers.update(route['customers'])
            
            total_customers = len(instance_data['customers'])
            print(f"\n客户覆盖统计:")
            print(f"  总客户数: {total_customers}")
            print(f"  已访问客户数: {len(all_visited_customers)}")
            print(f"  已访问客户ID: {sorted(all_visited_customers)}")
            
            if len(all_visited_customers) < total_customers:
                unvisited = set(range(total_customers)) - all_visited_customers
                print(f"  ⚠️ 未访问客户数: {len(unvisited)}")
                print(f"  ⚠️ 未访问客户ID: {sorted(unvisited)}")
                print(f"\n[ERROR] 有客户未被访问！这是一个严重的问题！")
            else:
                print(f"  ✓ 所有客户都已访问")
            
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
            timeout=3600,  # 60分钟超时（允许大规模实例运行）
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
        
        # 调试：打印输入数据
        print(f"[DEBUG] 写入 Cordeau 格式:")
        print(f"  仓库数: {num_depots}, 客户数: {num_customers}, 每仓库车辆数: {vehicles_per_depot}")
        print(f"  仓库坐标: {[(d['x'], d['y']) for d in depots]}")
        print(f"  客户坐标: {[(c['x'], c['y']) for c in customers]}")
        print(f"  客户需求: {[c['demand'] for c in customers]}")
        
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
            line = f"{i} {x} {y} {service_time} {demand}\n"
            f.write(line)
            if i <= 3:  # 只打印前3个客户
                print(f"  客户 {i}: {line.strip()}")
        
        # 仓库坐标：ID x y
        # 注意：Java 使用 Integer.parseInt() 读取坐标，必须写成整数格式
        for i, depot in enumerate(depots, 1):
            x = int(round(depot['x']))  # 转换为整数
            y = int(round(depot['y']))  # 转换为整数
            line = f"{i} {x} {y}\n"
            f.write(line)
            print(f"  仓库 {i}: {line.strip()}")
    
    def _parse_solution_file(self, filepath):
        """解析 Java 程序输出的解决方案文件"""
        routes = []
        total_cost = 0
        
        print(f"\n[DEBUG] 开始解析解决方案文件: {filepath}")
        
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            
            print(f"[DEBUG] 文件内容长度: {len(content)} 字符")
            print(f"[DEBUG] 文件内容前500字符:")
            print(content[:500])
            print(f"[DEBUG] 文件内容后500字符:")
            print(content[-500:])
            
            # 尝试解析路径信息
            # 格式可能是: Route X Y: depot customer1 customer2 ... depot
            route_pattern = r'Route\s+(\d+)\s+(\d+):\s+([\d\s]+)'
            matches = re.findall(route_pattern, content)
            
            print(f"[DEBUG] 使用模式 '{route_pattern}' 找到 {len(matches)} 个匹配")
            
            for idx, match in enumerate(matches):
                depot_id = int(match[0]) - 1  # 转换为0索引
                vehicle_id = int(match[1])
                nodes = [int(x) for x in match[2].split()]
                
                print(f"[DEBUG] 路径 {idx+1}: depot_id={depot_id}, vehicle_id={vehicle_id}, nodes={nodes}")
                
                # 提取客户（去掉仓库节点）
                customers = [n - 1 for n in nodes if n > 0]  # 转换为0索引
                
                print(f"[DEBUG] 提取的客户 (0索引): {customers}")
                
                routes.append({
                    'depot_id': depot_id,
                    'vehicle_id': vehicle_id,
                    'customers': customers,
                    'cost': 0  # 成本需要单独计算
                })
            
            # 尝试提取总成本
            cost_pattern = r'(?:Total distance|Cost):\s*([\d.]+)'
            cost_match = re.search(cost_pattern, content)
            if cost_match:
                total_cost = float(cost_match.group(1))
                print(f"[DEBUG] 提取到总成本: {total_cost}")
            else:
                print(f"[DEBUG] 未能提取总成本")
            
        except Exception as e:
            print(f"[ERROR] 解析解决方案文件失败: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"[DEBUG] 解析完成: {len(routes)} 条路径, 总成本: {total_cost}")
        return routes, total_cost
    
    def _extract_cost_from_output(self, output):
        """从标准输出中提取成本"""
        try:
            # 查找类似 "Total distance best solution: 66.57" 的行
            pattern = r'Total distance best solution:\s*([\d.]+)'
            match = re.search(pattern, output)
            if match:
                cost = float(match.group(1))
                print(f"[INFO] 从输出中提取到成本: {cost}")
                return cost
            else:
                print(f"[WARNING] 未能从输出中提取成本，使用备用模式")
                # 备用模式
                pattern2 = r'Total distance.*?:\s*([\d.]+)'
                match2 = re.search(pattern2, output)
                if match2:
                    cost = float(match2.group(1))
                    print(f"[INFO] 使用备用模式提取到成本: {cost}")
                    return cost
        except Exception as e:
            print(f"[WARNING] 提取成本时出错: {e}")
        
        print(f"[WARNING] 无法提取成本，返回 0")
        return 0.0  # 改为返回 0 而不是 inf，因为 Java 程序成功运行了
    
    def _extract_routes_from_output(self, output):
        """从标准输出中提取路径信息"""
        routes = []
        
        print(f"\n[DEBUG] 开始从标准输出提取路径")
        print(f"[DEBUG] 输出长度: {len(output)} 字符")
        
        try:
            # 优先使用详细格式: "Depot1: [4, 18, 25] - [42, 19, 40]"
            # 这种格式表示每个depot有多条路径（每个方括号是一辆车的路径）
            # 修复：使用 (?=Depot|\Z) 来匹配到下一个Depot或字符串结尾
            pattern_depot_routes = r'Depot(\d+):\s*(.+?)(?=\s*Depot|\Z)'
            depot_matches = re.findall(pattern_depot_routes, output, re.DOTALL)
            
            print(f"[DEBUG] 使用模式 '{pattern_depot_routes}' 找到 {len(depot_matches)} 个depot")
            
            if depot_matches:
                for depot_id_str, routes_str in depot_matches:
                    depot_id = int(depot_id_str) - 1  # 转换为0索引
                    # 清理路径字符串（去掉 | 和多余空白）
                    routes_str_clean = routes_str.replace('|', '').strip()
                    print(f"[DEBUG] Depot {depot_id_str} 的路径字符串: '{routes_str_clean}'")
                    
                    # 提取所有方括号中的内容（每个方括号是一辆车）
                    route_pattern = r'\[([^\]]+)\]'
                    route_matches = re.findall(route_pattern, routes_str_clean)
                    
                    print(f"[DEBUG] 找到 {len(route_matches)} 辆车的路径")
                    
                    for vehicle_idx, route_str in enumerate(route_matches):
                        customer_ids = [int(c.strip()) for c in route_str.split(',') if c.strip()]
                        customers_0indexed = [c - 1 for c in customer_ids]
                        
                        print(f"[DEBUG] 车辆 {vehicle_idx+1}: 原始ID={customer_ids}, 0-based={customers_0indexed}")
                        
                        if customers_0indexed:
                            routes.append({
                                'depot_id': depot_id,
                                'vehicle_id': len(routes) + 1,
                                'customers': customers_0indexed,
                                'cost': 0
                            })
                
                print(f"[INFO] 成功提取到 {len(routes)} 条路径（{len(depot_matches)} 个depot）")
            else:
                print(f"[WARNING] 未能匹配到 'Depot X: [...]' 格式")
                
                # 备用方案: 尝试 "Depot 1 has customers: [2, 1, 3]" 格式
                # 注意：这种格式把所有客户放在一起，不区分车辆
                pattern_depot_customers = r'Depot\s+(\d+)\s+has\s+customers:\s*\[([^\]]+)\]'
                matches = re.findall(pattern_depot_customers, output)
                
                print(f"[DEBUG] 尝试备用模式，找到 {len(matches)} 个匹配")
                
                if matches:
                    print(f"[WARNING] 使用备用格式，将所有客户作为一条路径")
                    for depot_id_str, customers_str in matches:
                        depot_id = int(depot_id_str) - 1
                        customer_ids = [int(c.strip()) for c in customers_str.split(',') if c.strip()]
                        customers_0indexed = [c - 1 for c in customer_ids]
                        
                        print(f"[DEBUG] Depot {depot_id_str}: {len(customer_ids)} 个客户")
                        
                        if customers_0indexed:
                            routes.append({
                                'depot_id': depot_id,
                                'vehicle_id': len(routes) + 1,
                                'customers': customers_0indexed,
                                'cost': 0
                            })
                    
                    print(f"[INFO] 使用备用模式提取到 {len(routes)} 条路径")
                else:
                    print(f"[ERROR] 所有模式都未能提取到路径！")
                    
        except Exception as e:
            print(f"[ERROR] 提取路径时出错: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"[DEBUG] 路径提取完成: 共 {len(routes)} 条路径")
        return routes


# 测试代码
if __name__ == '__main__':
    print("测试 GA-MDVRP Java 包装类\n")
    
    # 创建测试实例
    instance_data = {
        'depots': [
            {'x': 20, 'y': 20, 'vehicle_count': 5, 'capacity': 80},
            {'x': 30, 'y': 40, 'vehicle_count': 5, 'capacity': 80},
        ],
        'customers': [
            {'x': 10, 'y': 10, 'demand': 10},
            {'x': 15, 'y': 15, 'demand': 15},
            {'x': 25, 'y': 25, 'demand': 20},
            {'x': 35, 'y': 35, 'demand': 12},
            {'x': 40, 'y': 40, 'demand': 18},
        ]
    }
    
    try:
        # 创建求解器
        solver = GAMDVRPJava()
        
        # 求解
        result = solver.solve(instance_data)
        
        print("\n最终结果:")
        print(f"  算法: {result['algorithm']}")
        print(f"  总成本: {result['total_cost']:.2f}")
        print(f"  路径数: {result['num_vehicles']}")
        print(f"  计算时间: {result['compute_time']:.2f}秒")
        
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
