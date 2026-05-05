# Requirements Document

## Introduction

本文档定义了P01数据集分割和RouteFinder VRPL模型采样求解功能的需求。该功能将Cordeau格式的MDVRP实例(P01)分解为多个单仓库CVRP子问题,使用RouteFinder预训练模型进行多次采样求解,并输出详细的统计结果和最优解路径信息。

## Glossary

- **P01_Instance**: Cordeau MDVRP数据集中的p01实例,包含50个客户和4个仓库
- **MDVRP**: Multi-Depot Vehicle Routing Problem,多仓库车辆路径问题
- **CVRP**: Capacitated Vehicle Routing Problem,带容量约束的车辆路径问题
- **VRPL**: VRP with Limits,支持容量和距离约束的VRP变体
- **RouteFinder**: 基于深度学习的VRP求解器,提供预训练模型
- **Sampling**: 采样求解方法,生成多个解并选择最优
- **Depot_Splitter**: 仓库分割器,将MDVRP分解为多个CVRP子问题
- **Solution_Aggregator**: 解聚合器,合并各仓库的子问题解
- **BKS**: Best Known Solution,最优已知解,p01的BKS为576.87
- **Gap**: 算法解与BKS的相对差距百分比
- **Cordeau_Format**: Cordeau MDVRP数据格式,包含节点坐标、需求、容量等信息

## Requirements

### Requirement 1: 加载P01实例数据

**User Story:** 作为系统用户,我希望能够加载P01数据文件,以便获取MDVRP问题的完整信息

#### Acceptance Criteria

1. WHEN P01数据文件路径被提供, THE P01_Loader SHALL 解析文件并提取问题规模参数(客户数、仓库数、车辆数)
2. WHEN P01数据文件被解析, THE P01_Loader SHALL 提取所有客户节点的坐标和需求量
3. WHEN P01数据文件被解析, THE P01_Loader SHALL 提取所有仓库节点的坐标
4. WHEN P01数据文件被解析, THE P01_Loader SHALL 提取每个仓库的容量约束和距离约束
5. WHEN 数据加载完成, THE P01_Loader SHALL 返回包含customers、depots、depots_info的结构化数据

### Requirement 2: 客户分配到仓库

**User Story:** 作为系统用户,我希望将客户分配到最近的仓库,以便将MDVRP分解为多个CVRP子问题

#### Acceptance Criteria

1. WHEN 客户列表和仓库列表被提供, THE Depot_Splitter SHALL 计算每个客户到所有仓库的欧几里得距离
2. WHEN 客户到仓库的距离被计算, THE Depot_Splitter SHALL 将每个客户分配到距离最近的仓库
3. WHEN 客户分配完成, THE Depot_Splitter SHALL 返回每个仓库对应的客户列表
4. WHEN 客户分配完成, THE Depot_Splitter SHALL 输出每个仓库分配到的客户数量

### Requirement 3: 转换为RouteFinder格式

**User Story:** 作为系统用户,我希望将CVRP子问题转换为RouteFinder TensorDict格式,以便使用预训练模型求解

#### Acceptance Criteria

1. WHEN 单个仓库的客户列表被提供, THE Format_Converter SHALL 创建位置张量,包含仓库坐标和所有客户坐标
2. WHEN 单个仓库的客户列表被提供, THE Format_Converter SHALL 创建需求张量,仓库需求为0,客户需求为实际值
3. WHEN 格式转换执行, THE Format_Converter SHALL 创建TensorDict对象,包含locs和demand字段
4. WHEN TensorDict创建完成, THE Format_Converter SHALL 添加batch维度,batch_size为1

### Requirement 4: 加载RouteFinder VRPL模型

**User Story:** 作为系统用户,我希望加载RouteFinder预训练模型,以便进行CVRP求解

#### Acceptance Criteria

1. WHEN 模型加载开始, THE Model_Loader SHALL 应用TorchRL兼容性补丁
2. WHEN 模型加载开始, THE Model_Loader SHALL 应用Checkpoint兼容性补丁
3. WHEN checkpoint路径被提供, THE Model_Loader SHALL 加载pomo-vrpl.ckpt预训练模型
4. WHEN 模型加载成功, THE Model_Loader SHALL 设置模型为评估模式
5. WHEN 模型加载成功, THE Model_Loader SHALL 将模型移动到可用设备(GPU或CPU)
6. IF checkpoint文件不存在, THEN THE Model_Loader SHALL 输出错误信息并列出可用的checkpoint文件

### Requirement 5: 执行采样求解

**User Story:** 作为系统用户,我希望对每个CVRP子问题执行多次采样求解,以便获得高质量的解

#### Acceptance Criteria

1. WHEN 采样次数被指定, THE Sampling_Solver SHALL 对每个仓库的CVRP子问题执行指定次数的采样
2. WHEN 单次采样执行, THE Sampling_Solver SHALL 使用sampling解码类型调用模型
3. WHEN 模型返回actions, THE Sampling_Solver SHALL 解码actions为路径列表
4. WHEN 路径被解码, THE Sampling_Solver SHALL 计算每条路径的欧几里得距离成本
5. WHEN 单次采样完成, THE Sampling_Solver SHALL 记录该样本的总成本
6. WHEN 所有采样完成, THE Sampling_Solver SHALL 选择成本最低的解作为最优解

### Requirement 6: 解码路径

**User Story:** 作为系统用户,我希望将模型输出的actions解码为可读的路径信息,以便理解解的结构

#### Acceptance Criteria

1. WHEN actions张量被提供, THE Route_Decoder SHALL 将张量转换为numpy数组
2. WHEN action值为0, THE Route_Decoder SHALL 识别为返回仓库标记,结束当前路径
3. WHEN action值大于0, THE Route_Decoder SHALL 将其解码为客户索引,添加到当前路径
4. WHEN 所有actions处理完成, THE Route_Decoder SHALL 返回路径列表,每条路径包含depot_id、customers和depot信息

### Requirement 7: 计算路径成本

**User Story:** 作为系统用户,我希望准确计算每条路径的成本,以便评估解的质量

#### Acceptance Criteria

1. WHEN 路径包含客户列表, THE Cost_Calculator SHALL 计算仓库到第一个客户的欧几里得距离
2. WHEN 路径包含多个客户, THE Cost_Calculator SHALL 计算相邻客户之间的欧几里得距离
3. WHEN 路径计算完成, THE Cost_Calculator SHALL 计算最后一个客户返回仓库的欧几里得距离
4. WHEN 单条路径成本计算完成, THE Cost_Calculator SHALL 返回总距离,不包含服务时间

### Requirement 8: 输出采样统计

**User Story:** 作为系统用户,我希望查看所有采样的统计信息,以便评估采样方法的稳定性

#### Acceptance Criteria

1. WHEN 所有采样完成, THE Statistics_Reporter SHALL 输出最优成本(所有样本中的最小值)
2. WHEN 所有采样完成, THE Statistics_Reporter SHALL 输出最差成本(所有样本中的最大值)
3. WHEN 所有采样完成, THE Statistics_Reporter SHALL 输出平均成本
4. WHEN 所有采样完成, THE Statistics_Reporter SHALL 输出成本标准差
5. WHEN 统计信息输出, THE Statistics_Reporter SHALL 显示每个样本的成本和是否为新最优

### Requirement 9: 输出最终结果

**User Story:** 作为系统用户,我希望查看最终求解结果和与BKS的对比,以便评估算法性能

#### Acceptance Criteria

1. WHEN 求解完成, THE Result_Reporter SHALL 输出总路径数
2. WHEN 求解完成, THE Result_Reporter SHALL 输出最优成本
3. WHEN 求解完成, THE Result_Reporter SHALL 输出P01的BKS值(576.87)
4. WHEN 求解完成, THE Result_Reporter SHALL 计算并输出Gap百分比
5. WHEN 求解完成, THE Result_Reporter SHALL 输出总求解时间和平均每样本时间
6. IF Gap小于0, THEN THE Result_Reporter SHALL 输出警告信息,提示可能的错误原因
7. IF Gap小于5%, THEN THE Result_Reporter SHALL 输出"解质量优秀"提示
8. IF Gap在5%到10%之间, THEN THE Result_Reporter SHALL 输出"解质量良好"提示
9. IF Gap在10%到20%之间, THEN THE Result_Reporter SHALL 输出"解质量一般"提示
10. IF Gap大于20%, THEN THE Result_Reporter SHALL 输出"解质量较差"提示

### Requirement 10: 输出最优解路径详情

**User Story:** 作为系统用户,我希望查看最优解的详细路径信息,以便验证解的正确性

#### Acceptance Criteria

1. WHEN 最优解被确定, THE Route_Reporter SHALL 输出每条路径的仓库编号
2. WHEN 最优解被确定, THE Route_Reporter SHALL 输出每条路径访问的客户ID列表
3. WHEN 最优解被确定, THE Route_Reporter SHALL 按仓库分组显示路径信息

### Requirement 11: 命令行参数支持

**User Story:** 作为系统用户,我希望通过命令行参数控制采样次数,以便灵活调整求解配置

#### Acceptance Criteria

1. THE Script SHALL 接受--samples参数,指定采样次数
2. WHEN --samples参数未提供, THE Script SHALL 使用默认值10
3. WHEN --samples参数被提供, THE Script SHALL 使用指定的采样次数执行求解

### Requirement 12: 错误处理

**User Story:** 作为系统用户,我希望系统能够妥善处理错误情况,以便快速定位问题

#### Acceptance Criteria

1. IF 模型加载失败, THEN THE System SHALL 输出详细错误信息和堆栈跟踪
2. IF checkpoint文件不存在, THEN THE System SHALL 列出可用的checkpoint文件
3. IF 求解过程发生异常, THEN THE System SHALL 捕获异常并输出错误信息
4. IF 求解失败, THEN THE System SHALL 返回非零退出码

