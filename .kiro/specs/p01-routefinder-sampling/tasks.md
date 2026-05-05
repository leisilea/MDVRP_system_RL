# Implementation Plan: P01 RouteFinder Sampling

## Overview

本实现计划将P01 MDVRP实例分解为多个CVRP子问题,使用RouteFinder VRPL预训练模型进行采样求解。实现包括数据加载、仓库分割、格式转换、模型加载、采样求解、结果聚合和统计输出等模块。

## Tasks

- [x] 1. 创建项目结构和核心数据模型
  - 创建RL4CO_Integration/solve_p01_with_routefinder.py文件
  - 定义数据类: Customer, Depot, DepotInfo, Route, Solution, SamplingSolution
  - 添加必要的导入语句(torch, numpy, tensordict, argparse, time等)
  - _Requirements: 1.5, 6.4, 7.4_

- [ ] 2. 实现P01数据加载模块
  - [x] 2.1 实现P01Loader类
    - 实现load_instance静态方法,解析Cordeau格式文件
    - 解析第1行获取问题规模(type, m, n, t)
    - 解析第2到t+1行获取车辆约束(D, Q)
    - 解析客户节点(前n个节点)和仓库节点(最后t个节点)
    - 返回包含customers、depots、depots_info的字典
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
  
  - [ ]* 2.2 编写Property 1属性测试
    - **Property 1: Cordeau格式解析保持数据完整性**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**

- [ ] 3. 实现仓库分割模块
  - [x] 3.1 实现DepotSplitter类
    - 实现euclidean_distance静态方法计算欧几里得距离
    - 实现assign_customers_to_nearest_depot静态方法
    - 对每个客户计算到所有仓库的距离,分配到最近仓库
    - 返回每个仓库对应的客户列表字典
    - 输出每个仓库分配到的客户数量
    - _Requirements: 2.1, 2.2, 2.3, 2.4_
  
  - [ ]* 3.2 编写Property 2属性测试
    - **Property 2: 客户分配到最近仓库**
    - **Validates: Requirements 2.1, 2.2, 2.3_

- [ ] 4. 实现格式转换模块
  - [x] 4.1 实现FormatConverter类
    - 实现convert_to_tensordict静态方法
    - 创建位置张量[depot_coord, customer1_coord, ...]
    - 创建需求张量[0, demand1, demand2, ...]
    - 添加capacity和distance_limit字段
    - 添加batch维度(batch_size=1)
    - _Requirements: 3.1, 3.2, 3.3, 3.4_
  
  - [ ]* 4.2 编写Property 3属性测试
    - **Property 3: 格式转换创建有效TensorDict**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4**

- [ ] 5. 实现模型加载模块
  - [x] 5.1 实现ModelLoader类
    - 实现load_vrpl_model静态方法
    - 使用fix_checkpoint_loader.py的load_checkpoint_compatible()函数
    - 应用TorchRL兼容性补丁
    - 设置模型为评估模式(model.eval())
    - 自动检测可用设备(GPU优先)
    - 处理FileNotFoundError,列出可用checkpoint文件
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 12.2_

- [ ] 6. Checkpoint - 验证数据加载和模型加载
  - 确保所有测试通过,询问用户是否有问题

- [ ] 7. 实现路径解码模块
  - [x] 7.1 实现RouteDecoder类
    - 实现decode_actions静态方法
    - 将actions张量转换为numpy数组
    - action值为0时结束当前路径
    - action值大于0时添加客户到当前路径
    - 返回路径列表,每条路径包含depot_id、customers和depot
    - _Requirements: 6.1, 6.2, 6.3, 6.4_
  
  - [ ]* 7.2 编写Property 6属性测试
    - **Property 6: Action解码产生有效路径**
    - **Validates: Requirements 6.2, 6.3, 6.4**

- [ ] 8. 实现成本计算模块
  - [x] 8.1 实现CostCalculator类
    - 实现calculate_route_cost静态方法
    - 计算仓库到第一个客户的欧几里得距离
    - 计算相邻客户之间的欧几里得距离
    - 计算最后一个客户返回仓库的欧几里得距离
    - 实现calculate_solution_cost静态方法计算解的总成本
    - _Requirements: 7.1, 7.2, 7.3, 7.4_
  
  - [ ]* 8.2 编写Property 4属性测试
    - **Property 4: 路径成本使用欧几里得距离**
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4**

- [ ] 9. 实现采样求解模块
  - [x] 9.1 实现SamplingSolver类
    - 实现__init__方法,接收model和num_samples参数
    - 实现solve方法,对单个CVRP子问题执行采样求解
    - 执行指定次数的采样,使用decode_type="sampling"
    - 调用RouteDecoder解码actions为路径列表
    - 调用CostCalculator计算每个样本的成本
    - 选择成本最低的样本作为最优解
    - 返回包含routes、cost、all_costs、best_sample_idx的字典
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_
  
  - [ ]* 9.2 编写Property 5属性测试
    - **Property 5: 采样选择最小成本解**
    - **Validates: Requirements 5.5, 5.6**

- [ ] 10. 实现解聚合模块
  - [x] 10.1 实现SolutionAggregator类
    - 实现aggregate_solutions静态方法
    - 聚合所有仓库的路径列表
    - 计算总成本(所有仓库成本之和)
    - 记录每个仓库的成本
    - 计算总路径数
    - 返回包含routes、total_cost、depot_costs、n_routes的字典
    - _Requirements: 9.1, 9.2_

- [ ] 11. 实现统计报告模块
  - [x] 11.1 实现StatisticsReporter类
    - 实现report_sampling_statistics静态方法
    - 输出最优成本(最小值)
    - 输出最差成本(最大值)
    - 输出平均成本
    - 输出成本标准差
    - 显示每个样本的成本和是否为新最优
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_
  
  - [ ]* 11.2 编写Property 7属性测试
    - **Property 7: 统计计算正确性**
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.4**

- [ ] 12. 实现结果报告模块
  - [x] 12.1 实现ResultReporter类
    - 实现report_final_results静态方法
    - 输出总路径数
    - 输出最优成本
    - 输出P01的BKS值(576.87)
    - 计算并输出Gap百分比: ((cost - bks) / bks) * 100
    - 输出总求解时间和平均每样本时间
    - 根据Gap输出解质量评价(优秀<5%, 良好5-10%, 一般10-20%, 较差>20%)
    - 如果Gap<0,输出警告信息和可能的错误原因
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9, 9.10_
  
  - [ ]* 12.2 编写Property 8和Property 9属性测试
    - **Property 8: Gap计算公式正确性**
    - **Property 9: 时间计算正确性**
    - **Validates: Requirements 9.4, 9.5**

- [ ] 13. 实现路径报告模块
  - [x] 13.1 实现RouteReporter类
    - 实现report_routes静态方法
    - 按仓库分组显示路径信息
    - 输出每条路径的仓库编号
    - 输出每条路径访问的客户ID列表
    - _Requirements: 10.1, 10.2, 10.3_

- [ ] 14. Checkpoint - 验证所有模块实现
  - 确保所有测试通过,询问用户是否有问题

- [ ] 15. 实现主函数和命令行接口
  - [x] 15.1 实现main函数
    - 解析命令行参数(--samples,默认值10)
    - 加载P01实例数据(MDVRP-Instances/dat/p01)
    - 调用DepotSplitter分配客户到仓库
    - 加载VRPL模型(routefinder/checkpoints/50/pomo-vrpl.ckpt)
    - 对每个仓库执行采样求解
    - 调用StatisticsReporter输出每个仓库的采样统计
    - 调用SolutionAggregator聚合所有仓库的解
    - 调用ResultReporter输出最终结果
    - 调用RouteReporter输出路径详情
    - 添加错误处理和异常捕获
    - _Requirements: 11.1, 11.2, 11.3, 12.1, 12.3, 12.4_
  
  - [x] 15.2 添加if __name__ == "__main__"入口
    - 调用main函数
    - 捕获所有异常并输出错误信息
    - 返回适当的退出码
    - _Requirements: 12.1, 12.2, 12.3, 12.4_

- [ ] 16. 集成测试和验证
  - [ ]* 16.1 编写集成测试
    - 测试完整流程使用真实P01数据
    - 验证输出结果的正确性
    - 验证Gap在合理范围内
    - 验证所有4个仓库都被正确处理
  
  - [ ] 16.2 手动运行脚本验证
    - 运行python RL4CO_Integration/solve_p01_with_routefinder.py
    - 验证输出格式正确
    - 验证统计信息合理
    - 验证路径详情完整

- [ ] 17. Final Checkpoint - 确保所有测试通过
  - 确保所有测试通过,询问用户是否有问题

## Notes

- 任务标记为`*`的为可选任务,可跳过以加快MVP开发
- 每个任务都引用了具体的需求条款以保证可追溯性
- Checkpoint任务确保增量验证
- 属性测试验证通用正确性属性
- 单元测试验证特定示例和边界情况
- P01 BKS值为576.87
- 使用fix_checkpoint_loader.py处理模型加载兼容性
- 距离计算使用欧几里得距离,不包含服务时间
