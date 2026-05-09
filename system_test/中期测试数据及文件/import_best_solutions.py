"""
MDVRP最优解导入工具
将MDVRP-Instances/sol文件夹中的最优解导入到数据库solution表
算法名称统一为 "best_solution"，用于性能对比
"""
import os
import re
import pymysql
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
import json
from datetime import datetime


@dataclass
class DatabaseConfig:
    """数据库配置"""
    host: str = 'localhost'
    port: int = 3306
    user: str = 'root'
    password: str = '1234'
    database: str = 'mdvrp_db'
    charset: str = 'utf8mb4'


class BestSolutionParser:
    """最优解文件解析器"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.instance_name = os.path.splitext(os.path.basename(file_path))[0]
    
    def parse(self) -> Dict[str, Any]:
        """
        解析.res文件格式：
        第1行: 总成本
        后续行: depot_id vehicle_id cost load 0 customer1 customer2 ... 0
        
        Returns:
            Dict: 包含routes和totalCost的字典
        """
        with open(self.file_path, 'r') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        
        if not lines:
            raise ValueError("Empty solution file")
        
        # 第一行是总成本
        total_cost = float(lines[0])
        
        # 解析路径
        routes = []
        for line in lines[1:]:
            parts = line.split()
            if len(parts) < 5:
                continue
            
            depot_id = int(parts[0])
            vehicle_id = int(parts[1])
            route_cost = float(parts[2])
            load = int(float(parts[3]))  # 先转float再转int，处理 "176.00" 这种情况
            
            # 提取客户路径（去掉开头和结尾的0）
            path_parts = parts[4:]
            path = []
            for p in path_parts:
                customer_id = int(float(p))  # 先转float再转int
                if customer_id != 0:  # 0表示仓库
                    path.append(customer_id)
            
            routes.append({
                'vehicleId': vehicle_id,
                'depotId': depot_id,
                'path': path,
                'cost': route_cost,
                'load': load
            })
        
        return {
            'routes': routes,
            'totalCost': total_cost,
            'numRoutes': len(routes),
            'algorithm': 'best_solution'
        }


class BestSolutionImporter:
    """最优解导入器"""
    
    def __init__(self, config: DatabaseConfig = None):
        self.config = config or DatabaseConfig()
        self.connection = None
    
    def connect(self):
        """连接数据库"""
        try:
            self.connection = pymysql.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
                charset=self.config.charset,
                cursorclass=pymysql.cursors.DictCursor
            )
            print(f"✓ 成功连接到数据库: {self.config.database}")
        except Exception as e:
            print(f"✗ 数据库连接失败: {e}")
            raise
    
    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
    
    def get_scenario_by_name(self, instance_name: str) -> Dict:
        """根据实例名称查找对应的场景"""
        with self.connection.cursor() as cursor:
            # 尝试多种命名格式
            possible_names = [
                f"MDVRP-{instance_name}",
                instance_name,
                f"MDVRP-{instance_name}.dat"
            ]
            
            for name in possible_names:
                sql = "SELECT * FROM scenario WHERE name = %s"
                cursor.execute(sql, (name,))
                result = cursor.fetchone()
                if result:
                    return result
            
            return None
    
    def get_depot_customer_mapping(self, scenario_id: int) -> Tuple[Dict, Dict]:
        """
        获取场景的仓库和客户ID映射
        
        Returns:
            Tuple[Dict, Dict]: (depot_mapping, customer_mapping)
            depot_mapping: {原始ID -> 数据库ID}
            customer_mapping: {原始ID -> 数据库ID}
        """
        with self.connection.cursor() as cursor:
            # 获取仓库映射
            sql = "SELECT id, name FROM depot WHERE scenario_id = %s ORDER BY id"
            cursor.execute(sql, (scenario_id,))
            depots = cursor.fetchall()
            
            depot_mapping = {}
            for idx, depot in enumerate(depots, 1):
                # 尝试从name中提取原始ID (格式: "Depot-1")
                match = re.search(r'Depot-(\d+)', depot['name'])
                if match:
                    original_id = int(match.group(1))
                    depot_mapping[original_id] = depot['id']
                else:
                    # 如果没有匹配到，使用顺序索引作为映射
                    depot_mapping[idx] = depot['id']
            
            # 获取客户映射
            sql = "SELECT id, name FROM customer WHERE scenario_id = %s ORDER BY id"
            cursor.execute(sql, (scenario_id,))
            customers = cursor.fetchall()
            
            customer_mapping = {}
            for idx, customer in enumerate(customers, 1):
                # 尝试从name中提取原始ID (格式: "Customer-1")
                match = re.search(r'Customer-(\d+)', customer['name'])
                if match:
                    original_id = int(match.group(1))
                    customer_mapping[original_id] = customer['id']
                else:
                    # 如果没有匹配到，使用顺序索引作为映射
                    customer_mapping[idx] = customer['id']
            
            return depot_mapping, customer_mapping
    
    def import_solution(self, instance_name: str, solution_data: Dict[str, Any], 
                       overwrite: bool = False) -> int:
        """
        导入最优解到数据库
        
        Args:
            instance_name: 实例名称（如 "p01"）
            solution_data: 解数据
            overwrite: 是否覆盖已存在的解
            
        Returns:
            int: 解ID
        """
        if not self.connection:
            self.connect()
        
        try:
            # 查找对应的场景
            scenario = self.get_scenario_by_name(instance_name)
            if not scenario:
                raise ValueError(f"找不到实例 '{instance_name}' 对应的场景")
            
            scenario_id = scenario['id']
            print(f"  找到场景: {scenario['name']} (ID={scenario_id})")
            
            # 获取ID映射
            depot_mapping, customer_mapping = self.get_depot_customer_mapping(scenario_id)
            
            # 检查是否已存在best_solution
            existing_solution = self._get_solution_by_algorithm(scenario_id, 'best_solution')
            
            if existing_solution:
                if overwrite:
                    print(f"  已存在best_solution，删除旧数据...")
                    self._delete_solution(existing_solution['id'])
                else:
                    print(f"  已存在best_solution，跳过导入")
                    return existing_solution['id']
            
            # 转换路径中的ID（从原始ID转换为数据库ID）
            converted_routes = []
            for route in solution_data['routes']:
                # 转换depot_id
                original_depot_id = route['depotId']
                db_depot_id = depot_mapping.get(original_depot_id)
                if not db_depot_id:
                    print(f"  警告: 找不到仓库ID {original_depot_id} 的映射，跳过此路径")
                    continue
                
                # 转换customer_ids
                db_customer_ids = []
                for original_customer_id in route['path']:
                    db_customer_id = customer_mapping.get(original_customer_id)
                    if db_customer_id:
                        db_customer_ids.append(db_customer_id)
                    else:
                        print(f"  警告: 找不到客户ID {original_customer_id} 的映射")
                
                if db_customer_ids:  # 只添加有效的路径
                    converted_routes.append({
                        'vehicleId': route['vehicleId'],
                        'depotId': db_depot_id,
                        'path': db_customer_ids,
                        'cost': route['cost']
                    })
            
            # 创建解记录
            solution_id = self._create_solution(
                scenario_id=scenario_id,
                algorithm='best_solution',
                total_cost=solution_data['totalCost'],
                routes=converted_routes,
                compute_time=0.0  # 最优解没有计算时间
            )
            
            print(f"  ✓ 导入最优解: 总成本={solution_data['totalCost']:.2f}, "
                  f"路径数={len(converted_routes)} (ID={solution_id})")
            
            self.connection.commit()
            return solution_id
            
        except Exception as e:
            self.connection.rollback()
            print(f"  ✗ 导入失败: {e}")
            raise
    
    def _get_solution_by_algorithm(self, scenario_id: int, algorithm: str) -> Dict:
        """查询指定算法的解"""
        with self.connection.cursor() as cursor:
            sql = "SELECT * FROM solution WHERE scenario_id = %s AND algorithm = %s"
            cursor.execute(sql, (scenario_id, algorithm))
            return cursor.fetchone()
    
    def _delete_solution(self, solution_id: int):
        """删除解"""
        with self.connection.cursor() as cursor:
            sql = "DELETE FROM solution WHERE id = %s"
            cursor.execute(sql, (solution_id,))
    
    def _create_solution(self, scenario_id: int, algorithm: str, total_cost: float,
                        routes: List[Dict], compute_time: float) -> int:
        """创建解记录（存储到solution表）"""
        with self.connection.cursor() as cursor:
            # 将routes转换为JSON字符串
            routes_json = json.dumps(routes)
            
            sql = """
                INSERT INTO solution 
                (scenario_id, algorithm, routes, total_cost, compute_time, create_time)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            create_time = datetime.now()
            
            cursor.execute(sql, (
                scenario_id,
                algorithm,
                routes_json,
                total_cost,
                compute_time,
                create_time
            ))
            
            return cursor.lastrowid
    
    def import_from_directory(self, sol_directory: str, pattern: str = None,
                            overwrite: bool = False, limit: int = None):
        """
        从目录批量导入最优解
        
        Args:
            sol_directory: 解文件目录（MDVRP-Instances/sol）
            pattern: 文件名匹配模式（正则表达式）
            overwrite: 是否覆盖已存在的解
            limit: 限制导入数量
        """
        if not os.path.exists(sol_directory):
            print(f"✗ 目录不存在: {sol_directory}")
            return
        
        # 获取所有.res文件
        files = [f for f in os.listdir(sol_directory) 
                if f.endswith('.res') and os.path.isfile(os.path.join(sol_directory, f))]
        
        # 过滤文件
        if pattern:
            regex = re.compile(pattern)
            files = [f for f in files if regex.match(f)]
        
        # 限制数量
        if limit:
            files = files[:limit]
        
        print(f"\n找到 {len(files)} 个解文件")
        print("=" * 60)
        
        success_count = 0
        fail_count = 0
        
        for i, filename in enumerate(files, 1):
            print(f"\n[{i}/{len(files)}] 导入 {filename}...")
            
            try:
                file_path = os.path.join(sol_directory, filename)
                instance_name = os.path.splitext(filename)[0]
                
                # 解析解文件
                parser = BestSolutionParser(file_path)
                solution_data = parser.parse()
                
                # 导入数据库
                solution_id = self.import_solution(instance_name, solution_data, overwrite)
                success_count += 1
                
            except Exception as e:
                print(f"  ✗ 失败: {e}")
                fail_count += 1
                continue
        
        print("\n" + "=" * 60)
        print(f"导入完成: 成功 {success_count}, 失败 {fail_count}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='导入MDVRP最优解到数据库')
    parser.add_argument('directory', help='解文件目录路径（MDVRP-Instances/sol）')
    parser.add_argument('--pattern', help='文件名匹配模式（正则表达式）', default=None)
    parser.add_argument('--overwrite', action='store_true', help='覆盖已存在的解')
    parser.add_argument('--limit', type=int, help='限制导入数量', default=None)
    parser.add_argument('--host', default='localhost', help='数据库主机')
    parser.add_argument('--port', type=int, default=3306, help='数据库端口')
    parser.add_argument('--user', default='root', help='数据库用户名')
    parser.add_argument('--password', default='1234', help='数据库密码')
    parser.add_argument('--database', default='mdvrp_db', help='数据库名称')
    
    args = parser.parse_args()
    
    # 创建数据库配置
    config = DatabaseConfig(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database
    )
    
    # 创建导入器
    importer = BestSolutionImporter(config)
    
    try:
        importer.connect()
        importer.import_from_directory(
            sol_directory=args.directory,
            pattern=args.pattern,
            overwrite=args.overwrite,
            limit=args.limit
        )
    finally:
        importer.close()


if __name__ == "__main__":
    # 如果直接运行，使用默认配置导入所有解
    print("MDVRP最优解导入工具")
    print("=" * 60)
    
    # 默认导入MDVRP-Instances/sol目录下的所有解
    default_dir = "../../MDVRP-Instances/sol"
    
    if os.path.exists(default_dir):
        print(f"使用默认目录: {default_dir}")
        print("导入所有MDVRP最优解...")
        
        importer = BestSolutionImporter()
        try:
            importer.connect()
            importer.import_from_directory(
                sol_directory=default_dir,
                pattern=None,  # 不使用过滤器，导入所有文件
                overwrite=False,
                limit=None  # 不限制数量
            )
        finally:
            importer.close()
    else:
        print(f"默认目录不存在: {default_dir}")
        print("\n使用方法:")
        print("  python import_best_solutions.py <目录路径> [选项]")
        print("\n示例:")
        print("  python import_best_solutions.py ../../MDVRP-Instances/sol")
        print("  python import_best_solutions.py ../../MDVRP-Instances/sol --pattern 'p0[1-5]'")
        print("  python import_best_solutions.py ../../MDVRP-Instances/sol --limit 10 --overwrite")
