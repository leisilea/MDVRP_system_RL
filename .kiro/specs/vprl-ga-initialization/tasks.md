# Implementation Plan: VPRL-GA Initialization

## Overview

本实现计划将RL4CO的VRPL模型集成到GA_Java求解器中，通过文件通信机制提供高质量初始解。核心特性包括：1.2倍过采样策略（生成24个样本保留最优20个）、基于实例规模的自动模型选择、GA收敛曲线监控（每10代报告）、完整的错误处理和优雅降级。

## Tasks

- [x] 1. 实现Instance_Decomposer组件
  - [x] 1.1 实现MDVRP到CVRP的分解逻辑
    - 创建`VPRL/instance_decomposer.py`文件
    - 实现`decompose_mdvrp()`方法，将MDVRP实例分解为每个仓库对应的CVRP子问题
    - 实现三种客户分配策略：nearest（最近仓库）、balanced（均衡分配）、kmeans（聚类分配）
    - 实现`assign_customers_to_depots()`方法，支持策略选择
    - _Requirements: 2.1, 2.2_

  - [x] 1.2 实现TensorDict格式转换
    - 实现`convert_to_tensordict()`方法，将CVRP子问题转换为RL4CO兼容的TensorDict格式
    - 确保包含所有必需字段：locs（坐标）、demand_linehaul（需求）、capacity（容量）、distance_limit（距离限制）
    - 处理坐标归一化和张量类型转换
    - _Requirements: 2.3, 2.4, 2.5_

  - [ ]* 1.3 编写Instance_Decomposer单元测试
    - 测试三种客户分配策略的正确性
    - 测试TensorDict格式的完整性和类型正确性
    - 测试边界情况：单仓库、单客户、空仓库
    - _Requirements: 2.1, 2.2, 2.3_

- [x] 2. 实现Solution_Converter组件
  - [x] 2.1 实现RL4CO到Cordeau格式的转换
    - 创建`VPRL/solution_converter.py`文件
    - 定义`Route`数据类（depot_id、vehicle_id、customers、cost、load）
    - 实现`convert_rl4co_to_cordeau()`方法，将RL4CO动作序列转换为Cordeau路径格式
    - 实现索引转换：0-based（RL4CO）→ 1-based（Cordeau）
    - 确保每条路径以仓库ID开始和结束
    - _Requirements: 3.2, 3.4_

  - [x] 2.2 实现路径验证逻辑
    - 实现`validate_route()`方法，验证容量约束和距离约束
    - 计算路径总需求和总距离
    - 返回验证结果和错误信息
    - _Requirements: 3.3_

  - [x] 2.3 实现初始解文件写入
    - 实现`write_initial_solution_file()`方法，生成GA_Java可读取的初始解文件
    - 文件格式：包含实例名、时间戳、解数量、每个解的路径和成本
    - 文件位置：`system_test/ga_mdvrp_reproduction/GA-MDVRP/data/initial_solutions/<instance_name>.init`
    - _Requirements: 4.1, 4.2_

  - [ ]* 2.4 编写Solution_Converter单元测试
    - 测试索引转换的正确性（0-based ↔ 1-based）
    - 测试路径验证逻辑（容量、距离约束）
    - 测试文件格式生成的正确性
    - 测试无效解的处理
    - _Requirements: 3.2, 3.3, 3.4_

- [x] 3. 实现自动模型选择和过采样策略
  - [x] 3.1 实现自动模型选择逻辑
    - 在`VPRL/vprl_sampler.py`中实现`_select_model_by_size()`方法
    - 根据客户数量选择合适的模型：≤30客户用20模型，≤60用50模型，≤150用100模型，>150用200模型
    - 支持配置文件中的`model_size_thresholds`参数
    - 记录选择的模型到日志和性能指标
    - _Requirements: 1.2, 新增需求_

  - [x] 3.2 实现1.2倍过采样策略
    - 在`_generate_vrpl_solutions()`方法中实现过采样逻辑
    - 计算采样数量：`num_samples = int(num_solutions_needed * oversampling_ratio)`
    - 生成指定数量的样本（默认24个，当需要20个时）
    - 实现`_select_best_solutions()`方法，按成本排序选择最优的num_solutions_needed个解
    - 计算过采样改进指标：`(avg_all_samples - avg_kept_solutions) / avg_all_samples * 100`
    - _Requirements: 1.1, 1.3, 新增需求_

  - [ ]* 3.3 编写过采样策略单元测试
    - 测试采样数量计算的正确性
    - 测试解选择逻辑（确保选择最优解）
    - 测试过采样改进指标的计算
    - _Requirements: 1.1, 1.3_

- [x] 4. 实现GA_Java收敛曲线监控
  - [x] 4.1 增强GA_Java_Wrapper支持收敛跟踪
    - 在`VPRL/ga_java_wrapper.py`中添加`convergence_interval`参数（默认10）
    - 修改`solve_with_initial_solutions()`方法，传递收敛跟踪参数给GA_Java
    - 定义`ConvergencePoint`数据类（generation、best_cost、timestamp）
    - _Requirements: 6.3, 新增需求_

  - [x] 4.2 实现收敛数据解析
    - 实现`_parse_convergence_output()`方法，从GA_Java标准输出解析收敛数据
    - 解析格式：`Generation 10: Best cost = 589.23`
    - 提取每个报告点的代数、最优成本和时间戳
    - 将解析结果存储到`PerformanceMetrics.convergence_curve`
    - _Requirements: 6.3, 新增需求_

  - [ ]* 4.3 编写收敛跟踪单元测试
    - 测试收敛数据解析的正确性
    - 测试不同报告间隔的处理
    - 测试解析错误的处理
    - _Requirements: 6.3_

- [x] 5. 实现VPRL_Sampler主协调器
  - [x] 5.1 实现核心初始化和配置管理
    - 创建`VPRL/vprl_sampler.py`文件
    - 实现`VPRLSampler.__init__()`方法，加载配置和模型
    - 实现`_load_model()`方法，加载RL4CO模型检查点
    - 集成自动模型选择逻辑
    - 支持GPU/CPU设备选择
    - _Requirements: 1.1, 1.2, 5.1_

  - [x] 5.2 实现端到端solve方法
    - 实现`solve()`方法，接受Cordeau实例和配置参数
    - 协调整个工作流：实例分解 → 解生成（含过采样）→ 解选择 → 格式转换 → GA_Java调用
    - 支持enable_vrpl开关控制是否使用VRPL初始化
    - 支持vrpl_ratio参数控制初始种群中VRPL解的占比
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 5.3 实现性能指标收集
    - 实现`_collect_metrics()`方法，收集所有性能数据
    - 记录VRPL生成时间、采样数量、过采样改进、使用的模型
    - 记录转换时间、有效/无效解数量
    - 记录GA计算时间、迭代代数、最终成本、收敛曲线
    - 计算改进指标：vs随机初始化、VRPL贡献度
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 6. Checkpoint - 核心功能验证
  - 确保所有核心组件正常工作，运行单元测试
  - 使用小实例（p01）测试端到端流程
  - 验证过采样策略、自动模型选择、收敛跟踪功能
  - 如有问题请向用户报告

- [x] 7. 实现错误处理和优雅降级
  - [x] 7.1 实现错误处理器
    - 创建`VPRL/error_handler.py`文件
    - 实现`handle_model_loading_error()`：模型加载失败时禁用VRPL，使用纯GA_Java
    - 实现`handle_generation_error()`：解生成失败时重试一次，失败后回退
    - 实现`handle_validation_error()`：路径验证失败时跳过该解，记录警告
    - _Requirements: 7.1, 7.2, 7.3_

  - [x] 7.2 集成错误处理到VPRL_Sampler
    - 在solve()方法中添加try-except块处理各类错误
    - 模型加载失败：记录警告，禁用VRPL，继续使用纯GA_Java
    - 解生成失败：记录错误，回退到纯GA_Java
    - 部分解有效：使用部分初始化，记录有效解数量
    - 确保所有错误情况下GA_Java都能正常运行
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [x] 7.3 实现日志记录策略
    - 配置日志级别：DEBUG（详细流程）、INFO（主要步骤）、WARNING（可恢复错误）、ERROR（严重错误）
    - 记录关键步骤：配置加载、模型选择、采样过程、过采样改进、转换结果、GA执行
    - 记录性能数据：时间、成本、改进百分比
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [ ]* 7.4 编写错误处理单元测试
    - 测试每种错误类型的处理逻辑
    - 测试重试机制
    - 测试回退行为
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 8. 实现配置管理
  - [x] 8.1 实现配置数据类和管理器
    - 创建`VPRL/config.py`文件
    - 定义`VPRLConfig`数据类，包含所有配置参数
    - 模型设置：model_path、model_selection_strategy、model_size_thresholds
    - 采样设置：num_solutions_needed、oversampling_ratio、sampling_temperature
    - GA集成设置：vrpl_ratio、enable_vrpl、convergence_report_interval
    - 实现`from_file()`和`to_file()`方法用于配置文件读写
    - 为所有参数提供合理的默认值
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [x] 8.2 创建默认配置文件
    - 创建`VPRL/config.json`文件
    - 包含所有默认参数值
    - 添加注释说明每个参数的作用
    - _Requirements: 8.3, 8.4_

  - [x] 8.3 集成配置管理到VPRL_Sampler
    - 在初始化时加载配置文件
    - 支持配置文件不存在时使用默认值
    - 在启动时打印当前使用的配置参数
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [ ]* 8.4 编写配置管理单元测试
    - 测试配置文件加载
    - 测试默认值应用
    - 测试配置验证
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [x] 9. 集成测试和验证
  - [x] 9.1 端到端集成测试
    - 创建`VPRL/tests/test_integration.py`文件
    - 测试完整工作流：使用p01实例测试端到端流程
    - 测试启用/禁用VRPL的两种模式
    - 测试不同vrpl_ratio值的效果
    - 验证过采样策略：确认生成24个样本，保留20个最优解
    - 验证自动模型选择：测试不同规模实例选择正确模型
    - 验证收敛跟踪：确认每10代报告一次最优成本
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 9.2 性能基准测试
    - 创建`VPRL/examples/benchmark.py`文件
    - 在标准实例（p01、p03、p04）上运行性能测试
    - 测量VRPL生成时间、转换时间、GA时间、总时间
    - 验证过采样开销：确认1.2倍采样只增加约20%时间
    - 验证质量改进：确认过采样带来5-10%质量提升
    - 比较使用/不使用VRPL的性能差异
    - 记录收敛曲线数据
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [ ]* 9.3 手动GA_Java集成验证
    - 手动验证GA_Java能检测并加载.init文件
    - 验证vrpl_ratio在初始种群中的实际占比
    - 验证.init文件缺失时GA_Java正常运行
    - 验证收敛曲线输出格式正确
    - _Requirements: 4.3, 4.4, 4.5_

- [x] 10. 文档和示例
  - [x] 10.1 创建使用示例
    - 创建`VPRL/examples/basic_usage.py`：基本使用示例
    - 创建`VPRL/examples/custom_config.py`：自定义配置示例
    - 展示过采样策略的使用
    - 展示自动模型选择的配置
    - 展示收敛曲线的访问和可视化
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 10.2 创建README文档
    - 创建`VPRL/README.md`文件
    - 说明功能概述和核心特性（过采样、自动模型选择、收敛跟踪）
    - 说明安装依赖和配置步骤
    - 提供快速开始指南
    - 说明配置参数和默认值
    - 提供故障排除指南
    - _Requirements: 所有需求_

- [x] 11. Final Checkpoint - 完整性验证
  - 运行所有测试确保通过
  - 验证所有核心功能：过采样策略、自动模型选择、收敛跟踪
  - 验证错误处理和优雅降级
  - 检查文档完整性
  - 如有问题请向用户报告

## Notes

- 任务标记`*`的为可选任务，可跳过以加快MVP开发
- 每个任务都引用了具体的需求编号以保证可追溯性
- Checkpoint任务确保增量验证
- 核心实现要点：
  - 1.2倍过采样：生成24个样本，保留最优20个，带来5-10%质量提升
  - 自动模型选择：根据客户数量自动选择20/50/100/200客户模型
  - 收敛跟踪：每10代报告一次最优成本，用于分析优化效果
  - 文件通信：通过.init文件与GA_Java通信，不修改源代码
  - 优雅降级：任何错误都不会导致崩溃，自动回退到纯GA_Java
