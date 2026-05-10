"""
增强的 GA_Java 包装器,支持初始解和收敛跟踪
"""

import os
import re
import time
import subprocess
import tempfile
from typing import Dict, List, Optional, Union
from dataclasses import dataclass

from .solution_converter import Route, SolutionConverter


@dataclass
class ConvergencePoint:
    """收敛跟踪数据点"""
    generation: int
    best_cost: float
    timestamp: float  # 自开始以来的秒数


class GAJavaWrapper:
    """增强的 GA_Java 包装器,集成 VRPL"""
    
    def __init__(self, java_home: Optional[str] = None):
        """
        初始化 GA_Java 包装器
        
        参数:
            java_home: Java 安装路径(可选)
        """
        self.java_home = java_home
        self.java_cmd = self._find_java()
        self.ga_mdvrp_path = self._find_ga_mdvrp_path()
        
        # 检查 Java 环境
        self._check_java()
    
    def _find_java(self) -> str:
        """查找 Java 可执行文件"""
        if self.java_home:
            java_cmd = os.path.join(self.java_home, 'bin', 'java')
            if os.path.exists(java_cmd):
                return java_cmd
        return 'java'
    
    def _find_ga_mdvrp_path(self) -> str:
        """查找 GA-MDVRP 项目路径"""
        # 假设 VPRL 在项目根目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ga_mdvrp_path = os.path.join(
            current_dir,
            '../system_test/ga_mdvrp_reproduction/GA-MDVRP'
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
            print(f"[OK] Java 环境: {version_info}")
        except FileNotFoundError:
            raise RuntimeError(
                "未找到 Java!请安装 JDK 11 或更高版本\n"
                "下载地址: https://www.oracle.com/java/technologies/downloads/"
            )
        except Exception as e:
            raise RuntimeError(f"Java 检查失败: {e}")
    
    def solve_with_initial_solutions(
        self,
        instance_data,
        initial_solutions: Optional[List[Route]] = None,
        vrpl_ratio: float = 0.5,
        convergence_interval: int = 10) -> Dict:
        """
        使用可选的初始解和收敛跟踪求解 MDVRP
        
        参数:
            instance_data: MDVRP 实例(MDVRPInstance 对象或文件路径)
            initial_solutions: 来自 VRPL 的初始路径(可选)
            vrpl_ratio: 初始解在种群中的比例
            convergence_interval: 每 N 代报告一次最佳成本
            
        返回:
            包含 convergence_data 的解字典
        """
        start_time = time.time()
        
        print(f"\n{'='*60}")
        print(f"GA-MDVRP (Java) 增强版(集成 VRPL)")
        print(f"{'='*60}")
        
        # 确定实例文件
        if isinstance(instance_data, str) and os.path.exists(instance_data):
            problem_file = instance_data
            instance_name = os.path.basename(problem_file)
            temp_file_created = False
        else:
            # 创建临时 Cordeau 文件
            problems_dir = os.path.join(self.ga_mdvrp_path, 'data', 'problems')
            os.makedirs(problems_dir, exist_ok=True)
            
            # 创建临时文件并写入数据
            fd, problem_file = tempfile.mkstemp(
                suffix='.dat',
                dir=problems_dir
            )
            
            try:
                with os.fdopen(fd, 'w') as f:
                    self._write_cordeau_format(f, instance_data)
            except Exception as e:
                os.close(fd)
                raise RuntimeError(f"写入 Cordeau 格式失败: {e}")
            
            instance_name = os.path.basename(problem_file)
            temp_file_created = True
        
        # 如果提供了初始解,则写入文件
        init_file_path = None
        if initial_solutions and len(initial_solutions) > 0:
            init_file_path = self._write_initial_solution_file(
                routes=initial_solutions,
                instance_name=instance_name
            )
            print(f"初始解: {len(initial_solutions)} 条路径")
            print(f"VRPL 比例: {vrpl_ratio * 100:.1f}%")
        else:
            print("未提供初始解,使用随机初始化")
        
        try:
            # 运行 GA_Java
            print(f"启动 GA_Java...")
            result = self._run_java_solver(
                problem_name=os.path.relpath(problem_file, self.ga_mdvrp_path)
            )
            
            # 注意:输出已由 _run_java_solver 实时打印
            
            if result.returncode != 0:
                print(f"\n[警告] GA_Java 返回非零状态: {result.returncode}")
                if result.stderr:
                    print(f"错误输出: {result.stderr}")
            
            # 解析结果
            total_cost = self._extract_cost_from_output(result.stdout)
            routes = self._extract_routes_from_output(result.stdout)
            convergence_curve = self._parse_convergence_output(
                result.stdout,
                interval=convergence_interval,
                start_time=start_time
            )
            
        except subprocess.TimeoutExpired:
            print(f"[警告] GA_Java 执行超时(60 分钟)")
            total_cost = float('inf')
            routes = []
            convergence_curve = []
        except Exception as e:
            print(f"[警告] 执行错误: {e}")
            import traceback
            traceback.print_exc()
            total_cost = float('inf')
            routes = []
            convergence_curve = []
        finally:
            # 清理
            if temp_file_created and os.path.exists(problem_file):
                try:
                    os.unlink(problem_file)
                except:
                    pass
            if init_file_path and os.path.exists(init_file_path):
                try:
                    os.unlink(init_file_path)
                except:
                    pass
        
        compute_time = time.time() - start_time
        
        result_dict = {
            'algorithm': 'VPRL-增强 GA-MDVRP',
            'total_cost': total_cost,
            'compute_time': compute_time,
            'routes': routes,
            'num_vehicles': len(routes),
            'convergence_curve': convergence_curve,
            'ga_iterations': len(convergence_curve) * convergence_interval if convergence_curve else 0
        }
        
        print(f"\n{'='*60}")
        print(f"求解完成")
        print(f"  总成本: {total_cost:.2f}")
        print(f"  路径数: {len(routes)}")
        print(f"  计算时间: {compute_time:.2f}秒")
        print(f"  收敛点数: {len(convergence_curve)}")
        print(f"{'='*60}\n")
        
        return result_dict
    
    def _write_initial_solution_file(
        self,
        routes: List[Route],
        instance_name: str) -> str:
        """
        为 GA_Java 写入初始解文件
        
        参数:
            routes: 路径列表
            instance_name: 实例名称
            
        返回:
            初始解文件路径
        """
        # 创建 initial_solutions 目录
        init_dir = os.path.join(self.ga_mdvrp_path, 'data', 'initial_solutions')
        os.makedirs(init_dir, exist_ok=True)
        
        # 生成文件名
        filepath = os.path.join(init_dir, f"{instance_name}.init")
        
        # 写入文件
        SolutionConverter.write_initial_solution_file(
            routes=routes,
            filepath=filepath,
            instance_name=instance_name
        )
        
        print(f"初始解文件已写入: {filepath}")
        return filepath
    
    def _run_java_solver(self, problem_name: str):
        """运行 Java 求解器并实时输出"""
        out_dir = os.path.join(self.ga_mdvrp_path, 'out')
        
        if os.path.exists(out_dir):
            cmd = [
                self.java_cmd,
                '-cp', out_dir,
                'MainCLI',
                problem_name
            ]
        else:
            src_dir = os.path.join(self.ga_mdvrp_path, 'src')
            cmd = [
                self.java_cmd,
                '-cp', src_dir,
                'MainCLI',
                problem_name
            ]
        
        # 使用 Popen 实现实时输出
        print(f"[信息] 启动 Java 进程并实时输出...")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # 行缓冲
            universal_newlines=True,
            cwd=self.ga_mdvrp_path
        )
        
        # 收集输出的同时实时打印
        stdout_lines = []
        stderr_lines = []
        
        try:
            # 实时读取 stdout
            for line in process.stdout:
                print(line, end='')  # 立即打印
                stdout_lines.append(line)
            
            # 等待进程完成
            process.wait(timeout=3600)  # 60 分钟
            
            # 读取剩余的 stderr
            stderr_output = process.stderr.read()
            if stderr_output:
                stderr_lines.append(stderr_output)
                if process.returncode != 0:
                    print(f"\n[STDERR] {stderr_output}")
            
        except subprocess.TimeoutExpired:
            process.kill()
            raise
        
        # 创建与 subprocess.run 兼容的结果对象
        class Result:
            def __init__(self, returncode, stdout, stderr):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr
        
        return Result(
            returncode=process.returncode,
            stdout=''.join(stdout_lines),
            stderr=''.join(stderr_lines)
        )
    
    def _parse_convergence_output(
        self,
        output: str,
        interval: int = 10,
        start_time: float = None) -> List[ConvergencePoint]:
        """
        从 GA_Java 输出中解析收敛数据
        
        参数:
            output: GA_Java 标准输出
            interval: 报告间隔
            start_time: 开始时间戳
            
        返回:
            ConvergencePoint 对象列表
        """
        convergence_curve = []
        
        try:
            # 模式: "Generation: 10  |  Best distance: 589.23"
            pattern = r'Generation:\s*(\d+)\s*\|.*?Best.*?distance[:\s]+([\d.]+)'
            matches = re.findall(pattern, output, re.IGNORECASE)
            
            for match in matches:
                generation = int(match[0])
                best_cost = float(match[1])
                timestamp = time.time() - start_time if start_time else 0.0
                
                convergence_curve.append(ConvergencePoint(
                    generation=generation,
                    best_cost=best_cost,
                    timestamp=timestamp
                ))
            
            if convergence_curve:
                print(f"[信息] 解析了 {len(convergence_curve)} 个收敛点")
            else:
                print(f"[警告] 输出中未找到收敛数据")
                
        except Exception as e:
            print(f"[警告] 解析收敛数据失败: {e}")
        
        return convergence_curve
    
    def _extract_cost_from_output(self, output: str) -> float:
        """从输出中提取总成本"""
        try:
            pattern = r'Total distance best solution:\s*([\d.]+)'
            match = re.search(pattern, output)
            if match:
                cost = float(match.group(1))
                print(f"[信息] 提取的成本: {cost}")
                return cost
            else:
                pattern2 = r'Total distance.*?:\s*([\d.]+)'
                match2 = re.search(pattern2, output)
                if match2:
                    cost = float(match2.group(1))
                    print(f"[信息] 提取的成本(备用模式): {cost}")
                    return cost
        except Exception as e:
            print(f"[警告] 提取成本失败: {e}")
        
        print(f"[警告] 无法提取成本,返回 0")
        return 0.0
    
    def _extract_routes_from_output(self, output: str) -> List[Dict]:
        """从输出中提取路径"""
        routes = []
        try:
            pattern1 = r'Depot(\d+):\s*\[([^\]]+)\]'
            matches1 = re.findall(pattern1, output)
            
            if matches1:
                for depot_id_str, customers_str in matches1:
                    depot_id = int(depot_id_str) - 1
                    customers = [int(c.strip()) - 1 for c in customers_str.split(',') if c.strip()]
                    
                    if customers:
                        routes.append({
                            'depot_id': depot_id,
                            'vehicle_id': len(routes) + 1,
                            'customers': customers,
                            'cost': 0
                        })
                print(f"[信息] 提取了 {len(routes)} 条路径")
            else:
                print(f"[警告] 输出中未找到路径")
                
        except Exception as e:
            print(f"[警告] 提取路径失败: {e}")
        
        return routes
    
    def _write_cordeau_format(self, f, instance_data):
        """
        写入 Cordeau 格式文件
        
        参数:
            f: 文件句柄
            instance_data: MDVRPInstance 对象
        """
        # 头部: type vehicles_per_depot num_customers num_depots
        vehicles_per_depot = int(instance_data.depot_vehicles[0])  # 假设所有仓库相同
        f.write(f"2 {vehicles_per_depot} {instance_data.num_customers} {instance_data.num_depots}\n")
        
        # D/Q 参数(每个仓库的 max_distance 和 capacity)
        # Java 期望整数,因此将浮点数转换为整数
        for i in range(instance_data.num_depots):
            max_dist = int(instance_data.max_route_distances[i])
            capacity = int(instance_data.depot_capacities[i])
            f.write(f"{max_dist} {capacity}\n")
        
        # 客户(id, x, y, service_duration, demand)
        # Java 期望所有整数
        for i in range(instance_data.num_customers):
            customer_id = i + 1
            x = int(instance_data.customers_coords[i, 0])
            y = int(instance_data.customers_coords[i, 1])
            demand = int(instance_data.demands[i])
            f.write(f"{customer_id} {x} {y} 0 {demand}\n")
        
        # 仓库(id, x, y)
        # Java 期望所有整数
        for i in range(instance_data.num_depots):
            depot_id = instance_data.num_customers + i + 1
            x = int(instance_data.depots_coords[i, 0])
            y = int(instance_data.depots_coords[i, 1])
            f.write(f"{depot_id} {x} {y}\n")
