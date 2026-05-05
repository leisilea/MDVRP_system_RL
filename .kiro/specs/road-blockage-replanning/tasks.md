# 实现计划：道路阻塞动态重规划

## 概述

本实现计划将道路阻塞动态重规划功能分解为可执行的编码任务。核心思路是将车辆当前位置转换为临时仓库，修改距离矩阵以反映道路阻塞，然后使用现有MDVRP求解器重新规划未完成的配送任务。

实现将分为数据模型、核心组件、服务层、API层和前端集成五个阶段。

## 任务列表

- [x] 1. 创建数据模型和异常类
  - 在 `system_test/algorithm-service/` 目录下创建 `replanning/` 模块
  - 创建 `replanning/models.py` 定义所有数据类（VehicleState, TemporaryDepot, BlockedEdge等）
  - 创建 `replanning/exceptions.py` 定义异常类（CapacityConstraintViolation, BlockedEdgeInSolution等）
  - 使用 dataclass 装饰器定义数据模型
  - _需求: 1.3, 2.4, 2.5, 2.6, 3.2, 3.3, 3.4, 6.1, 7.2_

- [ ]* 1.1 为数据模型编写单元测试
  - 创建 `replanning/tests/test_models.py`
  - 测试数据类的实例化和字段验证
  - _需求: 1.3, 2.4, 2.5, 2.6_

- [x] 2. 实现车辆状态解析器 (VehicleStateParser)
  - [x] 2.1 创建 VehicleStateParser 类
    - 在 `replanning/vehicle_state_parser.py` 中实现
    - 实现 `parse_vehicle_states()` 方法：解析所有车辆的当前状态
    - 实现 `_determine_position()` 方法：确定车辆当前位置（支持指定位置或随机选择）
    - 实现 `_calculate_remaining_capacity()` 方法：计算剩余容量并验证非负
    - _需求: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

  - [ ]* 2.2 为 VehicleStateParser 编写单元测试
    - 创建 `replanning/tests/test_vehicle_state_parser.py`
    - 测试正常的车辆状态解析
    - 测试随机位置选择
    - 测试指定位置解析
    - 测试容量计算
    - 测试容量为负的错误情况
    - _需求: 2.2, 2.3, 2.6, 2.7_

- [x] 3. 实现临时仓库转换器 (TemporaryDepotConverter)
  - [x] 3.1 创建 TemporaryDepotConverter 类
    - 在 `replanning/temporary_depot_converter.py` 中实现
    - 实现 `convert_to_temporary_depots()` 方法：将车辆位置转换为临时仓库
    - 实现 `_create_temporary_depot()` 方法：创建单个临时仓库
    - 处理车辆在原始仓库的情况
    - _需求: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [ ]* 3.2 为 TemporaryDepotConverter 编写单元测试
    - 创建 `replanning/tests/test_temporary_depot_converter.py`
    - 测试临时仓库创建
    - 测试车辆在原始仓库的情况
    - 测试坐标和容量的正确转换
    - _需求: 3.2, 3.3, 3.4, 3.5_

- [x] 4. 实现距离矩阵修改器 (DistanceMatrixModifier)
  - [x] 4.1 创建 DistanceMatrixModifier 类
    - 在 `replanning/distance_matrix_modifier.py` 中实现
    - 实现 `modify_distance_matrix()` 方法：修改距离矩阵以反映道路阻塞
    - 实现 `_validate_edge()` 方法：验证路段有效性
    - 使用 NumPy 进行高效的矩阵操作
    - 确保 O(N) 时间复杂度，N为阻塞路段数量
    - _需求: 1.1, 1.2, 1.3, 1.4, 11.1, 11.2, 11.3, 11.4_

  - [ ]* 4.2 为 DistanceMatrixModifier 编写单元测试
    - 创建 `replanning/tests/test_distance_matrix_modifier.py`
    - 测试单个阻塞路段修改
    - 测试多个阻塞路段修改
    - 测试空阻塞列表
    - 测试原始矩阵不被修改
    - 测试性能（O(N)复杂度）
    - _需求: 1.2, 1.4, 11.2, 11.3, 11.4_

- [x] 5. 实现重规划结果验证器 (ReplanningValidator)
  - [x] 5.1 创建 ReplanningValidator 类
    - 在 `replanning/validator.py` 中实现
    - 实现 `validate_solution()` 方法：验证重规划解决方案
    - 实现 `_check_capacity_constraints()` 方法：检查容量约束
    - 实现 `_check_blocked_edges()` 方法：检查路径是否包含阻塞路段
    - 实现 `_check_customer_coverage()` 方法：检查客户覆盖
    - _需求: 6.1, 6.2, 6.3, 6.4, 7.1, 7.2, 7.3_

  - [ ]* 5.2 为 ReplanningValidator 编写单元测试
    - 创建 `replanning/tests/test_validator.py`
    - 测试容量约束验证
    - 测试阻塞路段验证
    - 测试客户覆盖验证
    - 测试多种错误组合
    - _需求: 6.1, 6.2, 6.3, 6.4, 7.1, 7.2, 7.3_

- [x] 6. 检查点 - 核心组件完成
  - 确保所有核心组件的单元测试通过
  - 验证各组件接口符合设计文档
  - 如有问题请向用户询问

- [x] 7. 实现重规划服务 (ReplanningService)
  - [x] 7.1 创建 ReplanningService 主类
    - 在 `replanning/service.py` 中实现
    - 实现 `replan()` 方法：执行完整的重规划流程
    - 集成所有核心组件（Parser, Converter, Modifier, Validator）
    - 调用现有的 MDVRP 求解器
    - 实现 `_calculate_cost_comparison()` 方法：计算成本对比
    - _需求: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

  - [ ]* 7.2 为 ReplanningService 编写集成测试
    - 创建 `replanning/tests/test_service.py`
    - 测试完整的重规划流程
    - 测试成本计算
    - 测试错误处理
    - 测试多次重规划
    - 使用 MDVRP-Instances 中的 p01 数据
    - _需求: 4.1, 4.2, 4.3, 4.4, 4.5, 5.3, 5.4, 5.5, 8.1, 8.2, 8.3, 8.4_

- [x] 8. 实现 API 端点
  - [x] 8.1 在 app.py 中添加 /api/replan 端点（增量添加，不修改现有端点）
    - 创建 POST 端点处理重规划请求
    - 实现请求参数验证和解析
    - 调用 ReplanningService 执行重规划
    - 实现响应格式化（成功和错误响应）
    - 实现错误处理和HTTP状态码映射
    - **注意：只添加新端点，不修改 /api/solve 等现有端点**
    - _需求: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

  - [x] 8.2 支持所有算法类型
    - 验证算法参数（PSO, ACO, GA, GA-MP, GA-RL）
    - 将算法参数传递给求解器
    - 处理不支持的算法错误
    - _需求: 4.4, 4.5, 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_

  - [ ]* 8.3 为 API 端点编写测试
    - 创建 `replanning/tests/test_api.py`
    - 测试正常的重规划请求
    - 测试各种错误情况（400, 500）
    - 测试不同算法的兼容性
    - 测试响应格式
    - 使用 Flask test client
    - _需求: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 12.1, 12.2, 12.3, 12.4, 12.5_

- [x] 9. 检查点 - 后端实现完成
  - 运行所有测试确保通过
  - 使用 Postman 或 curl 手动测试 API
  - 验证与现有求解器的集成
  - 如有问题请向用户询问

- [x] 10. 实现前端重规划功能
  - [x] 10.1 创建重规划 UI 组件（新建组件，不修改现有页面）
    - 在算法计算页面添加"重规划"按钮（增量添加）
    - 创建重规划模态对话框或侧边栏（新组件）
    - 实现阻塞路段选择界面（地图点击交互）
    - 显示当前选中的阻塞路段列表
    - **注意：不修改现有的 AlgorithmCompute.vue 核心逻辑，只添加新功能**
    - _需求: 10.1, 10.2_

  - [x] 10.2 实现地图交互功能
    - 在地图上启用路段选择模式
    - 高亮显示可选择的路段
    - 支持点击选择/取消选择阻塞路段
    - 在地图上标记已选择的阻塞路段
    - _需求: 10.2_

  - [x] 10.3 实现重规划请求和结果展示
    - 调用 /api/replan 端点发送重规划请求
    - 在地图上以不同颜色显示原始路径和新路径
    - 显示成本对比信息（重规划前、后、差异、百分比）
    - 显示算法名称和求解时间
    - 显示临时仓库位置
    - _需求: 10.3, 10.4, 10.5_

  - [x] 10.4 支持多次重规划
    - 允许在重规划结果上继续进行新的重规划
    - 累积显示所有阻塞路段
    - 保持历史重规划记录
    - _需求: 10.6, 8.1, 8.2, 8.3, 8.4_

  - [ ]* 10.5 为前端组件编写测试
    - 创建前端单元测试
    - 测试组件渲染
    - 测试用户交互
    - 测试 API 调用

- [ ] 11. 端到端测试和性能优化
  - [ ]* 11.1 编写端到端测试
    - 使用真实数据测试完整流程
    - 测试小规模场景（p01: 2仓库, 50客户）
    - 测试中规模场景（p07: 4仓库, 100客户）
    - 测试大规模场景（p21: 8仓库, 360客户）
    - 验证响应时间目标（小规模<5s, 中规模<15s, 大规模<60s）
    - _需求: 所有需求的综合验证_

  - [ ] 11.2 性能优化
    - 分析性能瓶颈
    - 优化距离矩阵操作
    - 优化数据结构和算法
    - 添加必要的缓存
    - _需求: 11.1, 11.2, 11.3_

- [ ] 12. 文档和部署准备
  - 更新 README.md 添加重规划功能说明
  - 编写 API 文档（请求/响应格式、错误码）
  - 添加使用示例和代码注释
  - 准备演示数据和场景
  - _需求: 所有需求_

- [ ] 13. 最终检查点
  - 确保所有测试通过
  - 验证所有需求已实现
  - 代码审查和重构
  - 向用户演示功能
  - 收集反馈并进行必要调整

## 注意事项

- **【重要约束】只做增量修改，不改动现有文件**
  - 所有新功能代码放在新的 `replanning/` 模块中
  - 只在 `app.py` 中添加新的 `/api/replan` 端点，不修改现有端点
  - 前端只添加新的重规划组件，不修改现有算法计算页面的核心逻辑
  - 复用现有的求解器和数据结构，通过导入使用，不修改它们的代码
- 标记 `*` 的任务为可选测试任务，可以跳过以加快MVP开发
- 每个任务都引用了具体的需求编号，确保可追溯性
- 检查点任务用于确保增量验证和及时发现问题
- 实现过程中应参考设计文档中的详细接口定义
- 使用现有的 MDVRP 求解器和数据结构，避免重复开发
- 前端实现需要与现有的算法计算页面集成

## 技术栈

- 后端：Python, Flask, NumPy
- 前端：JavaScript/TypeScript, React（根据现有前端技术栈）
- 测试：pytest, Flask test client
- 数据：MDVRP-Instances 标准测试数据集
