from flask import Flask, request, jsonify
from flask_cors import CORS
import time
import logging
import traceback
from config import Config

# 导入算法求解器
from solver.mdvrp_solver import create_solver

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)  # 允许跨域请求

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==================== 异常处理器 ====================

def handle_exceptions(f):
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            logger.error(f"参数错误: {str(e)}")
            return jsonify({
                'success': False,
                'error': '参数错误',
                'message': str(e),
                'error_type': 'ValueError'
            }), 400
        except KeyError as e:
            logger.error(f"缺少必要字段: {str(e)}")
            return jsonify({
                'success': False,
                'error': '缺少必要字段',
                'message': f'缺少字段: {str(e)}',
                'error_type': 'KeyError'
            }), 400
        except NotImplementedError as e:
            logger.error(f"功能未实现: {str(e)}")
            return jsonify({
                'success': False,
                'error': '功能未实现',
                'message': str(e),
                'error_type': 'NotImplementedError'
            }), 501
        except Exception as e:
            logger.error(f"服务器内部错误: {str(e)}", exc_info=True)
            return jsonify({
                'success': False,
                'error': '服务器内部错误',
                'message': str(e),
                'error_type': type(e).__name__,
                'traceback': traceback.format_exc() if Config.DEBUG else None
            }), 500
    wrapper.__name__ = f.__name__
    return wrapper


# ==================== 输入验证 ====================

def validate_depot(depot, index):
    #验证仓库数据
    required_fields = ['id', 'x', 'y', 'vehicles', 'capacity']
    for field in required_fields:
        if field not in depot:
            raise ValueError(f"仓库 {index} 缺少必要字段: {field}")
    
    if not isinstance(depot['vehicles'], (int, float)) or depot['vehicles'] <= 0:
        raise ValueError(f"仓库 {index} 的车辆数必须为正数")
    
    if not isinstance(depot['capacity'], (int, float)) or depot['capacity'] <= 0:
        raise ValueError(f"仓库 {index} 的容量必须为正数")

    # 车辆最大行驶距离是可选字段，0或缺省表示不限制
    if 'maxDistance' in depot:
        if not isinstance(depot['maxDistance'], (int, float)) or depot['maxDistance'] < 0:
            raise ValueError(f"仓库 {index} 的最大行驶距离必须为非负数")
    
    return True


def validate_customer(customer, index):
    #验证客户数据
    required_fields = ['id', 'x', 'y', 'demand']
    for field in required_fields:
        if field not in customer:
            raise ValueError(f"客户 {index} 缺少必要字段: {field}")
    
    if not isinstance(customer['demand'], (int, float)) or customer['demand'] < 0:
        raise ValueError(f"客户 {index} 的需求必须为非负数")
    
    return True


def validate_request_data(data):
    #验证请求数据

    # 检查基本结构
    if not data:
        raise ValueError("请求体不能为空")
    
    if 'depots' not in data:
        raise ValueError("缺少 'depots' 字段")
    
    if 'customers' not in data:
        raise ValueError("缺少 'customers' 字段")
    
    depots = data['depots']
    customers = data['customers']
    
    # 检查数据类型
    if not isinstance(depots, list):
        raise ValueError("'depots' 必须是数组")
    
    if not isinstance(customers, list):
        raise ValueError("'customers' 必须是数组")
    
    # 检查数量
    if len(depots) == 0:
        raise ValueError("至少需要一个仓库")
    
    if len(customers) == 0:
        raise ValueError("至少需要一个客户")
    
    # 验证每个仓库
    for i, depot in enumerate(depots):
        validate_depot(depot, i + 1)
    
    # 验证每个客户
    for i, customer in enumerate(customers):
        validate_customer(customer, i + 1)
    
    # 验证算法参数
    params = data.get('params', {})
    if not isinstance(params, dict):
        raise ValueError("'params' 必须是对象")
    
    algorithm = params.get('algorithm', 'genetic')
    valid_algorithms = ['genetic', 'ga_multiprogramming', 'GA_RL_HYBRID', 'ACO', 'PSO']
    if algorithm not in valid_algorithms:
        raise ValueError(f"不支持的算法: {algorithm}，支持的算法: {', '.join(valid_algorithms)}")
    
    return True


# ==================== 接口 ====================

@app.route('/health', methods=['GET'])
def health_check():
    # 检查接口
    logger.info("健康检查请求")
    return jsonify({
        'success': True,
        'status': 'ok',
        'service': 'MDVRP Algorithm Service',
        'version': '1.0.0',
        'timestamp': time.time()
    })


@app.route('/api/solve', methods=['POST'])
@handle_exceptions
def solve_mdvrp():
    """
    求解 MDVRP 问题的主接口
    
    请求格式：
    {
        "depots": [
            {"id": 1, "x": 0, "y": 0, "vehicles": 5, "capacity": 100}
        ],
        "customers": [
            {"id": 1, "x": 10, "y": 20, "demand": 15},
            {"id": 2, "x": 30, "y": 40, "demand": 20}
        ],
        "params": {
            "algorithm": "genetic",
            "max_iterations": 1000,
            "population_size": 50
        }
    }
    
    返回格式：
    {
        "success": true,
        "data": {
            "routes": [
                {
                    "vehicle_id": 1,
                    "depot_id": 1,
                    "path": [1, 3, 5, 7],
                    "cost": 150.5
                }
            ],
            "total_cost": 270.8,
            "compute_time": 2.34,
            "num_routes": 1,
            "algorithm": "genetic"
        },
        "timestamp": 1234567890.123
    }
    """
    start_time = time.time()
    data = request.json
    
    # 验证处理输入数据
    validate_request_data(data)
    
    depots = data['depots']
    customers = data['customers']
    params = data.get('params', {})
    
    logger.info(f"收到求解请求 - 仓库数: {len(depots)}, 客户数: {len(customers)}, 算法: {params.get('algorithm', 'genetic')}")
    
    # 使用数据调用求解器 接受solution
    solver = create_solver(depots, customers, params)
    result = solver.solve()
    
    solution = {
        'routes': result.get('routes', []),
        'totalCost': result.get('totalCost', result.get('total_cost', 0)),
        'computeTime': result.get('computeTime', result.get('compute_time', 0)),
        'numRoutes': result.get('numRoutes', result.get('num_routes', 0)),
        'algorithm': result.get('algorithm', params.get('algorithm', 'unknown')),
        'convergence': result.get('convergence', [])
    }
    
    # 记录错误+时间+日志
    if 'error' in result:
        solution['error'] = result['error']
    solution['timestamp'] = time.time()
    
    logger.info(f"求解完成 - 总成本: {solution['totalCost']:.2f}, "
               f"耗时: {solution['computeTime']:.3f}s, "
               f"路径数: {solution['numRoutes']}")
    
    return jsonify({
        'success': True,
        'data': solution,
        'timestamp': time.time()
    })

 #目前算法是写在前端,未使用此接口
# @app.route('/api/algorithms', methods=['GET'])
# def list_algorithms():
#     # 列出可用的算法列表
#     return jsonify({
#         'success': True,
#         'data': {
#             'algorithms': [
#                 {
#                     'id': 'genetic',
#                     'name': '遗传算法 (GA-MDVRP)',
#                     'description': '基于 Ombuki-Berman 2009 论文的遗传算法 Java 实现',
#                     'status': 'available',
#                     'aliases': ['GA'],
#                     'paper': 'Ombuki-Berman & Hanshar (2009)',
#                     'source': 'markusmkim/GA-MDVRP',
#                     'requires': 'Java 11+'
#                 },
#                 {
#                     'id': 'ga_multiprogramming',
#                     'name': '多进程遗传算法 (GA Multiprocessing)',
#                     'description': '使用多进程加速的遗传算法 Python 实现',
#                     'status': 'available',
#                     'aliases': []
#                 },
#                 {
#                     'id': 'ACO',
#                     'name': '蚁群算法 (ACO)',
#                     'description': '模拟蚂蚁觅食行为的优化算法',
#                     'status': 'available',
#                     'aliases': []
#                 },
#                 {
#                     'id': 'PSO',
#                     'name': '粒子群算法 (PSO)',
#                     'description': '基于群体智能的优化算法',
#                     'status': 'available',
#                     'aliases': []
#                 },
#                 {
#                     'id': 'GA_RL_HYBRID',
#                     'name': 'GA + RouteFinder 混合求解器',
#                     'description': '结合遗传算法和强化学习(RouteFinder)的混合求解器，使用RL生成高质量初始种群',
#                     'status': 'available',
#                     'aliases': ['ga_rl_hybrid', 'hybrid'],
#                     'paper': 'RouteFinder (2024)',
#                     'requires': 'PyTorch, TorchRL, CUDA (optional)'
#                 }
#             ]
#         },
#         'timestamp': time.time()
#     })


# 测试连接接口 - 未使用,已注释
# @app.route('/api/test', methods=['POST'])
# @handle_exceptions
# def test_connection():
#     """测试连接的简单接口"""
#     data = request.json
#     logger.info(f"测试接口收到数据: {data}")
#     return jsonify({
#         'success': True,
#         'message': '连接成功！',
#         'received': data,
#         'timestamp': time.time()
#     })


@app.route('/api/replan', methods=['POST'])
@handle_exceptions
def replan_routes():
    """
    重规划API端点
    
    当道路被阻塞时，对现有路径进行动态重规划。
    
    请求格式：
    {
        "depots": [
            {"id": 1, "x": 0, "y": 0, "vehicles": 5, "capacity": 100}
        ],
        "customers": [
            {"id": 1, "x": 10, "y": 20, "demand": 15}
        ],
        "routes": [
            {"vehicleId": 1, "depotId": 1, "path": [1, 3, 5], "cost": 150.5}
        ],
        "blocked_edges": [
            {"from": 1, "to": 3}
        ],
        "vehicle_positions": {
            "1": 3
        },
        "algorithm": "GA",
        "params": {
            "max_iterations": 1000
        }
    }
    
    返回格式：
    {
        "success": true,
        "data": {
            "new_routes": [...],
            "replanned_route_ids": [1],
            "cost_before": 450.5,
            "cost_after": 480.3,
            "cost_difference": 29.8,
            "cost_change_percent": 6.62,
            "algorithm": "GA",
            "solve_time": 2.34,
            "num_routes": 3,
            "temporary_depots": [...]
        },
        "timestamp": 1234567890.123
    }
    """
    start_time = time.time()
    data = request.json
    
    # 验证输入数据
    _validate_replan_request(data)
    
    # 解析请求参数
    depots = data['depots']
    customers = data['customers']
    routes = data['routes']
    blocked_edges = data['blocked_edges']
    vehicle_positions = data.get('vehicle_positions')
    algorithm = data.get('algorithm', 'GA')
    params = data.get('params')
    
    logger.info(f"收到重规划请求 - 仓库数: {len(depots)}, 客户数: {len(customers)}, "
               f"路径数: {len(routes)}, 阻塞路段数: {len(blocked_edges)}, 算法: {algorithm}")
    
    try:
        # 导入简化版重规划服务
        from replanning.service_simple import SimpleReplanningService
        from replanning.models import (
            DepotInput, CustomerInput, RouteInput, BlockedEdgeInput
        )
        from replanning.exceptions import (
            ReplanningError,
            CapacityConstraintViolation,
            BlockedEdgeInSolution,
            InvalidVehiclePosition,
            NoFeasibleSolution,
            UnsupportedAlgorithm
        )
        
        # 转换输入数据为数据类
        depot_inputs = [DepotInput(**depot) for depot in depots]
        customer_inputs = [CustomerInput(**customer) for customer in customers]
        route_inputs = [RouteInput(**route) for route in routes]
        blocked_edge_inputs = [BlockedEdgeInput.from_dict(edge) for edge in blocked_edges]
        
        # 创建简化版重规划服务实例
        service = SimpleReplanningService()
        
        # 执行重规划
        result = service.replan(
            depots=depot_inputs,
            customers=customer_inputs,
            routes=route_inputs,
            blocked_edges=blocked_edge_inputs,
            vehicle_positions=vehicle_positions,
            algorithm=algorithm,
            params=params
        )
        
        # 转换响应为字典格式
        response_data = result.to_dict()
        
        logger.info(f"重规划完成 - 新路径数: {result.num_routes}, "
                   f"成本变化: {result.cost_difference:.2f} ({result.cost_change_percent:.2f}%), "
                   f"耗时: {result.solve_time:.3f}s")
        
        return jsonify({
            'success': True,
            'data': response_data,
            'timestamp': time.time()
        })
        
    except UnsupportedAlgorithm as e:
        logger.error(f"不支持的算法: {str(e)}")
        return jsonify({
            'success': False,
            'error': '不支持的算法',
            'message': str(e),
            'error_type': 'UnsupportedAlgorithm',
            'details': {
                'algorithm': e.algorithm,
                'supported_algorithms': e.supported_algorithms
            }
        }), 400
        
    except CapacityConstraintViolation as e:
        logger.error(f"容量约束违反: {str(e)}")
        return jsonify({
            'success': False,
            'error': '容量约束违反',
            'message': str(e),
            'error_type': 'CapacityConstraintViolation',
            'details': {
                'vehicle_id': e.vehicle_id,
                'remaining_capacity': e.remaining,
                'required_capacity': e.required
            }
        }), 400
        
    except BlockedEdgeInSolution as e:
        logger.error(f"解决方案包含阻塞路段: {str(e)}")
        return jsonify({
            'success': False,
            'error': '解决方案包含阻塞路段',
            'message': str(e),
            'error_type': 'BlockedEdgeInSolution',
            'details': {
                'vehicle_id': e.vehicle_id,
                'from_node': e.from_node,
                'to_node': e.to_node
            }
        }), 400
        
    except InvalidVehiclePosition as e:
        logger.error(f"无效的车辆位置: {str(e)}")
        return jsonify({
            'success': False,
            'error': '无效的车辆位置',
            'message': str(e),
            'error_type': 'InvalidVehiclePosition',
            'details': {
                'vehicle_id': e.vehicle_id,
                'position': e.position,
                'valid_positions': e.valid_positions
            }
        }), 400
        
    except NoFeasibleSolution as e:
        logger.error(f"无可行解: {str(e)}")
        return jsonify({
            'success': False,
            'error': '无可行解',
            'message': str(e),
            'error_type': 'NoFeasibleSolution',
            'details': {
                'reason': e.reason
            }
        }), 500
        
    except ReplanningError as e:
        logger.error(f"重规划错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': '重规划错误',
            'message': str(e),
            'error_type': 'ReplanningError'
        }), 500


def _validate_replan_request(data):
    """验证重规划请求数据"""
    # 检查基本结构
    if not data:
        raise ValueError("请求体不能为空")
    
    # 检查必要字段
    required_fields = ['depots', 'customers', 'routes', 'blocked_edges']
    for field in required_fields:
        if field not in data:
            raise ValueError(f"缺少必要字段: {field}")
    
    depots = data['depots']
    customers = data['customers']
    routes = data['routes']
    blocked_edges = data['blocked_edges']
    
    # 检查数据类型
    if not isinstance(depots, list):
        raise ValueError("'depots' 必须是数组")
    
    if not isinstance(customers, list):
        raise ValueError("'customers' 必须是数组")
    
    if not isinstance(routes, list):
        raise ValueError("'routes' 必须是数组")
    
    if not isinstance(blocked_edges, list):
        raise ValueError("'blocked_edges' 必须是数组")
    
    # 检查数量
    if len(depots) == 0:
        raise ValueError("至少需要一个仓库")
    
    if len(customers) == 0:
        raise ValueError("至少需要一个客户")
    
    if len(routes) == 0:
        raise ValueError("至少需要一个路径")
    
    # 验证每个仓库
    for i, depot in enumerate(depots):
        validate_depot(depot, i + 1)
    
    # 验证每个客户
    for i, customer in enumerate(customers):
        validate_customer(customer, i + 1)
    
    # 验证每个路径
    for i, route in enumerate(routes):
        _validate_route(route, i + 1)
    
    # 验证每个阻塞路段
    for i, edge in enumerate(blocked_edges):
        _validate_blocked_edge(edge, i + 1)
    
    # 验证车辆位置（可选）
    if 'vehicle_positions' in data and data['vehicle_positions'] is not None:
        vehicle_positions = data['vehicle_positions']
        if not isinstance(vehicle_positions, dict):
            raise ValueError("'vehicle_positions' 必须是对象")
        
        # 验证每个车辆位置
        for vehicle_id, position in vehicle_positions.items():
            if not isinstance(position, (int, float)):
                raise ValueError(f"车辆 {vehicle_id} 的位置必须是数字")
    
    # 验证算法（可选）
    if 'algorithm' in data:
        algorithm = data['algorithm']
        valid_algorithms = ['genetic', 'ga_multiprogramming', 'GA_RL_HYBRID', 'ACO', 'PSO']
        if algorithm not in valid_algorithms:
            raise ValueError(f"不支持的算法: {algorithm}，支持的算法: {', '.join(valid_algorithms)}")
    
    # 验证参数（可选）
    if 'params' in data and data['params'] is not None:
        params = data['params']
        if not isinstance(params, dict):
            raise ValueError("'params' 必须是对象")
    
    return True


def _validate_route(route, index):
    """验证路径数据"""
    required_fields = ['vehicleId', 'depotId', 'path', 'cost']
    for field in required_fields:
        if field not in route:
            raise ValueError(f"路径 {index} 缺少必要字段: {field}")
    
    if not isinstance(route['vehicleId'], (int, float)):
        raise ValueError(f"路径 {index} 的 vehicleId 必须是数字")
    
    if not isinstance(route['depotId'], (int, float)):
        raise ValueError(f"路径 {index} 的 depotId 必须是数字")
    
    if not isinstance(route['path'], list):
        raise ValueError(f"路径 {index} 的 path 必须是数组")
    
    if not isinstance(route['cost'], (int, float)):
        raise ValueError(f"路径 {index} 的 cost 必须是数字")
    
    return True


def _validate_blocked_edge(edge, index):
    """验证阻塞路段数据"""
    # 支持两种字段名格式: from/to 或 from_node/to_node
    has_from = 'from' in edge or 'from_node' in edge
    has_to = 'to' in edge or 'to_node' in edge
    
    if not has_from:
        raise ValueError(f"阻塞路段 {index} 缺少必要字段: from 或 from_node")
    
    if not has_to:
        raise ValueError(f"阻塞路段 {index} 缺少必要字段: to 或 to_node")
    
    from_node = edge.get('from') or edge.get('from_node')
    to_node = edge.get('to') or edge.get('to_node')
    
    if not isinstance(from_node, (int, float)):
        raise ValueError(f"阻塞路段 {index} 的起点必须是数字")
    
    if not isinstance(to_node, (int, float)):
        raise ValueError(f"阻塞路段 {index} 的终点必须是数字")
    
    return True


# ==================== 错误处理 ====================

@app.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return jsonify({
        'success': False,
        'error': '接口不存在',
        'message': '请求的接口不存在',
        'error_type': 'NotFound'
    }), 404


@app.errorhandler(405)
def method_not_allowed(error):
    """405错误处理"""
    return jsonify({
        'success': False,
        'error': '方法不允许',
        'message': '该接口不支持此HTTP方法',
        'error_type': 'MethodNotAllowed'
    }), 405


@app.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    logger.error(f"服务器内部错误: {str(error)}", exc_info=True)
    return jsonify({
        'success': False,
        'error': '服务器内部错误',
        'message': str(error),
        'error_type': 'InternalServerError'
    }), 500


if __name__ == '__main__':
    logger.info(f"启动 Flask 服务 - 端口: {Config.PORT}")
    logger.info(f"调试模式: {Config.DEBUG}")
    logger.info(f"监听地址: {Config.HOST}:{Config.PORT}")
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )
