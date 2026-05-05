# Requirements Document

## Introduction

本功能使用强化学习模型（RL4CO的VRPL变体）通过Sampling采样方式为GA_Java算法提供高质量的初始路径。VRPL模型可以处理同时具有容量和距离约束的CVRP问题，这与GA_Java在分配完仓库车辆后的运算步骤本质相同。通过使用RL4CO生成的初始解，可以提高GA_Java的初始种群质量，从而减少计算代数，提高运算速度。

## Glossary

- **VPRL_Sampler**: 使用RL4CO的VRPL模型通过采样方式生成CVRP解的组件
- **GA_Java**: 基于遗传算法的MDVRP求解器，通过subprocess调用Java程序
- **Solution_Converter**: 将RL4CO生成的路径格式转换为GA_Java初始种群格式的转换器
- **CVRP**: 带容量约束的车辆路径问题（Capacitated Vehicle Routing Problem）
- **VRPL**: RL4CO中的MTVRP变体，支持容量和距离双重约束
- **Initial_Population**: GA_Java算法的初始种群，包含多个候选解
- **Cordeau_Instance**: Cordeau格式的MDVRP问题实例
- **RL4CO_Model**: 训练好的RL4CO强化学习模型检查点文件

## Requirements

### Requirement 1: VRPL模型采样

**User Story:** 作为算法开发者，我希望使用VRPL模型生成多个不同的CVRP解，以便为GA_Java提供多样化的初始种群。

#### Acceptance Criteria

1. WHEN提供RL4CO_Model路径和问题实例，THE VPRL_Sampler SHALL加载模型并生成指定数量的解
2. THE VPRL_Sampler SHALL支持配置每个实例生成的解数量（默认20个）
3. THE VPRL_Sampler SHALL使用sampling解码方式以获得多样性
4. THE VPRL_Sampler SHALL支持配置采样温度参数（默认1.0）
5. WHEN生成解时，THE VPRL_Sampler SHALL返回每个解的路径序列和对应成本

### Requirement 2: Cordeau实例转换

**User Story:** 作为算法开发者，我希望将Cordeau格式的MDVRP实例转换为RL4CO格式，以便VRPL模型可以处理。

#### Acceptance Criteria

1. WHEN提供Cordeau_Instance，THE Solution_Converter SHALL提取仓库坐标、客户坐标、需求、容量和距离限制
2. THE Solution_Converter SHALL为每个仓库创建独立的CVRP子问题
3. THE Solution_Converter SHALL将坐标、需求、容量转换为PyTorch张量格式
4. THE Solution_Converter SHALL设置distance_limit为Cordeau实例中的最大路径距离
5. WHEN转换完成，THE Solution_Converter SHALL返回RL4CO兼容的TensorDict对象

### Requirement 3: 解格式转换

**User Story:** 作为算法开发者，我希望将RL4CO生成的路径转换为GA_Java可接受的格式，以便作为初始种群使用。

#### Acceptance Criteria

1. WHEN提供RL4CO生成的动作序列，THE Solution_Converter SHALL解析出访问的客户顺序
2. THE Solution_Converter SHALL将客户索引从0-based转换为1-based（Cordeau格式要求）
3. THE Solution_Converter SHALL按容量约束将客户序列分割为多条路径
4. THE Solution_Converter SHALL为每条路径添加仓库起点和终点
5. WHEN转换完成，THE Solution_Converter SHALL返回GA_Java兼容的路径列表格式

### Requirement 4: GA_Java初始种群注入

**User Story:** 作为算法开发者，我希望将RL4CO生成的解注入到GA_Java的初始种群中，以便提高初始解质量而不修改GA_Java源代码。

#### Acceptance Criteria

1. THE Solution_Converter SHALL生成Cordeau格式的初始解文件
2. THE Solution_Converter SHALL将初始解文件保存到GA_Java可读取的位置
3. WHEN GA_Java启动时，THE GA_Java SHALL检测并加载初始解文件
4. THE GA_Java SHALL将加载的初始解作为种群的一部分（占比可配置，默认50%）
5. IF初始解文件不存在，THEN THE GA_Java SHALL使用随机生成的初始种群

### Requirement 5: 端到端集成

**User Story:** 作为算法开发者，我希望有一个统一的接口来使用VRPL增强的GA_Java求解器，以便简化使用流程。

#### Acceptance Criteria

1. THE VPRL_Sampler SHALL提供统一的solve方法接受Cordeau_Instance作为输入
2. WHEN调用solve方法时，THE VPRL_Sampler SHALL自动执行实例转换、解生成、格式转换和GA_Java调用
3. THE VPRL_Sampler SHALL支持配置是否启用VRPL初始化（默认启用）
4. THE VPRL_Sampler SHALL支持配置VRPL生成的解在初始种群中的占比（默认50%）
5. WHEN求解完成，THE VPRL_Sampler SHALL返回与GA_Java相同格式的结果字典

### Requirement 6: 性能监控

**User Story:** 作为算法开发者，我希望监控VRPL初始化对GA_Java性能的影响，以便评估优化效果。

#### Acceptance Criteria

1. THE VPRL_Sampler SHALL记录VRPL解生成的时间
2. THE VPRL_Sampler SHALL记录解格式转换的时间
3. THE VPRL_Sampler SHALL记录GA_Java的计算时间和迭代代数
4. THE VPRL_Sampler SHALL记录使用VRPL初始化前后的最优成本对比
5. WHEN求解完成，THE VPRL_Sampler SHALL在结果中包含性能统计信息

### Requirement 7: 错误处理

**User Story:** 作为算法开发者，我希望系统能够优雅地处理错误情况，以便保证求解器的鲁棒性。

#### Acceptance Criteria

1. IF RL4CO_Model文件不存在，THEN THE VPRL_Sampler SHALL记录警告并禁用VRPL初始化
2. IF VRPL解生成失败，THEN THE VPRL_Sampler SHALL记录错误并回退到纯GA_Java求解
3. IF解格式转换失败，THEN THE Solution_Converter SHALL记录错误并跳过该解
4. IF至少有一个有效的VRPL解，THEN THE VPRL_Sampler SHALL继续使用部分初始化
5. THE VPRL_Sampler SHALL在所有错误情况下确保GA_Java能够正常运行

### Requirement 8: 配置管理

**User Story:** 作为算法开发者，我希望通过配置文件管理VRPL参数，以便灵活调整系统行为。

#### Acceptance Criteria

1. THE VPRL_Sampler SHALL支持从配置文件读取模型路径
2. THE VPRL_Sampler SHALL支持配置采样数量、温度、初始种群占比等参数
3. THE VPRL_Sampler SHALL为所有参数提供合理的默认值
4. WHEN配置文件不存在，THEN THE VPRL_Sampler SHALL使用默认配置
5. THE VPRL_Sampler SHALL在启动时打印当前使用的配置参数

