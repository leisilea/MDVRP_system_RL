# Requirements Document - Vehicle Maximum Distance Constraint

## Introduction

本文档定义了为 MDVRP (Multi-Depot Vehicle Routing Problem) 仿真系统添加车辆最大行驶距离约束功能的需求。该功能允许用户为每个仓库配置车辆的最大行驶距离限制,并在算法求解过程中强制执行此约束,确保生成的路径方案符合实际运营限制。

## Glossary

- **System**: MDVRP仿真系统,包含数据库、Java后端、Vue.js前端和Python算法服务
- **Database**: MySQL数据库,存储场景、仓库、客户和解决方案数据
- **Backend**: Spring Boot Java后端服务,提供RESTful API
- **Frontend**: Vue.js前端应用,提供用户界面
- **Algorithm_Service**: Python算法服务,实现GA、PSO、ACO等优化算法
- **Depot**: 仓库实体,包含位置、车辆数量、车辆容量等属性
- **Vehicle**: 车辆,从仓库出发访问客户后返回仓库
- **Route**: 路径,车辆从仓库出发经过一系列客户后返回仓库的完整行程
- **Route_Distance**: 路径距离,车辆从仓库出发到所有客户再返回仓库的总距离
- **Max_Distance**: 最大行驶距离,单辆车辆允许行驶的最大距离限制
- **Distance_Constraint**: 距离约束,要求每条路径的总距离不超过max_distance的约束条件
- **Constraint_Violation**: 约束违反,当路径距离超过max_distance时发生的错误状态

## Requirements

### Requirement 1: 数据库架构扩展

**User Story:** 作为系统管理员,我需要在数据库中存储每个仓库的最大行驶距离限制,以便系统能够持久化这一配置。

#### Acceptance Criteria

1. THE Database SHALL add a column named `max_distance` to the `depot` table with type DECIMAL(10,2)
2. THE Database SHALL set the default value of `max_distance` to NULL to indicate no distance limit
3. WHEN `max_distance` is NULL, THE System SHALL treat it as unlimited distance
4. WHEN `max_distance` is set, THE System SHALL ensure it is a positive number greater than zero
5. THE Database SHALL allow updating existing depot records with `max_distance` values without data loss

### Requirement 2: 后端实体模型更新

**User Story:** 作为后端开发者,我需要更新Depot实体类以包含maxDistance字段,以便Java代码能够处理距离限制数据。

#### Acceptance Criteria

1. THE Backend SHALL add a `maxDistance` field of type BigDecimal to the Depot entity class
2. THE Backend SHALL annotate the `maxDistance` field with appropriate JPA annotations
3. WHEN serializing Depot to JSON, THE Backend SHALL include the `maxDistance` field
4. WHEN deserializing JSON to Depot, THE Backend SHALL correctly parse the `maxDistance` field
5. THE Backend SHALL maintain backward compatibility with existing depot records that have NULL `max_distance`

### Requirement 3: 后端API验证

**User Story:** 作为API用户,我需要后端验证maxDistance输入,以便防止无效数据进入系统。

#### Acceptance Criteria

1. WHEN creating or updating a depot with `maxDistance`, THE Backend SHALL validate that it is either NULL or a positive number
2. IF `maxDistance` is negative or zero, THEN THE Backend SHALL return HTTP 400 with error message "最大行驶距离必须大于0"
3. IF `maxDistance` exceeds 999999.99, THEN THE Backend SHALL return HTTP 400 with error message "最大行驶距离超出允许范围"
4. WHEN `maxDistance` is NULL, THE Backend SHALL accept the request without validation errors
5. THE Backend SHALL log validation errors with depot ID and invalid value

### Requirement 4: 前端表单增强

**User Story:** 作为系统用户,我需要在前端界面输入和编辑仓库的最大行驶距离,以便配置车辆运营限制。

#### Acceptance Criteria

1. THE Frontend SHALL add an input field labeled "最大行驶距离(km)" to the depot creation form
2. THE Frontend SHALL add an input field labeled "最大行驶距离(km)" to the depot editing form
3. THE Frontend SHALL display the `maxDistance` value in the depot list table as a new column
4. WHEN `maxDistance` is NULL, THE Frontend SHALL display "无限制" in the table column
5. WHEN `maxDistance` has a value, THE Frontend SHALL display the numeric value with 2 decimal places
6. THE Frontend SHALL use el-input-number component with :min="0.01" and :precision="2" for input
7. THE Frontend SHALL allow users to clear the maxDistance field to set it to NULL (unlimited)

### Requirement 5: 前端输入验证

**User Story:** 作为系统用户,我需要前端验证我的输入,以便在提交前发现错误。

#### Acceptance Criteria

1. WHEN user enters a negative number for maxDistance, THE Frontend SHALL display error message "最大行驶距离必须大于0"
2. WHEN user enters zero for maxDistance, THE Frontend SHALL display error message "最大行驶距离必须大于0"
3. WHEN user enters a value exceeding 999999.99, THE Frontend SHALL display error message "最大行驶距离不能超过999999.99"
4. THE Frontend SHALL prevent form submission when validation errors exist
5. THE Frontend SHALL clear validation errors when user corrects the input

### Requirement 6: 算法距离计算

**User Story:** 作为算法开发者,我需要准确计算每条路径的总距离,以便验证距离约束。

#### Acceptance Criteria

1. THE Algorithm_Service SHALL calculate route distance as: distance(depot, first_customer) + sum(distance(customer_i, customer_i+1)) + distance(last_customer, depot)
2. THE Algorithm_Service SHALL use the same distance_matrix used for cost calculation
3. WHEN a route has only one customer, THE Algorithm_Service SHALL calculate distance as: distance(depot, customer) + distance(customer, depot)
4. WHEN a route has zero customers, THE Algorithm_Service SHALL calculate distance as zero
5. THE Algorithm_Service SHALL store calculated route distances for constraint checking

### Requirement 7: 遗传算法距离约束

**User Story:** 作为算法用户,我需要GA算法遵守最大行驶距离约束,以便生成可行的路径方案。

#### Acceptance Criteria

1. WHEN splitting routes in GA, THE Algorithm_Service SHALL check if adding next customer would exceed max_distance
2. IF adding next customer would exceed max_distance, THEN THE Algorithm_Service SHALL start a new route
3. WHEN max_distance is NULL for a depot, THE Algorithm_Service SHALL only apply capacity constraint
4. THE Algorithm_Service SHALL validate final solution to ensure all routes satisfy distance constraint
5. IF no feasible solution exists, THEN THE Algorithm_Service SHALL return error "无法找到满足距离约束的可行解"

### Requirement 8: PSO算法距离约束

**User Story:** 作为算法用户,我需要PSO算法遵守最大行驶距离约束,以便生成可行的路径方案。

#### Acceptance Criteria

1. WHEN decoding particles in PSO, THE Algorithm_Service SHALL check route distance against max_distance
2. IF route distance exceeds max_distance, THEN THE Algorithm_Service SHALL split the route at appropriate point
3. WHEN max_distance is NULL for a depot, THE Algorithm_Service SHALL only apply capacity constraint
4. THE Algorithm_Service SHALL penalize particles that violate distance constraint in fitness calculation
5. THE Algorithm_Service SHALL validate final solution to ensure all routes satisfy distance constraint

### Requirement 9: ACO算法距离约束

**User Story:** 作为算法用户,我需要ACO算法遵守最大行驶距离约束,以便生成可行的路径方案。

#### Acceptance Criteria

1. WHEN constructing routes in ACO, THE Algorithm_Service SHALL track cumulative route distance
2. IF adding next customer would exceed max_distance, THEN THE Algorithm_Service SHALL mark that customer as infeasible for current route
3. WHEN max_distance is NULL for a depot, THE Algorithm_Service SHALL only apply capacity constraint
4. THE Algorithm_Service SHALL update pheromone trails only for feasible routes
5. THE Algorithm_Service SHALL validate final solution to ensure all routes satisfy distance constraint

### Requirement 10: 算法服务API扩展

**User Story:** 作为后端开发者,我需要算法服务接收max_distance参数,以便将约束传递给算法。

#### Acceptance Criteria

1. THE Algorithm_Service SHALL accept `maxDistance` field in depot objects from API requests
2. THE Algorithm_Service SHALL parse `maxDistance` as float or None (for NULL)
3. WHEN creating MDVRPInstance, THE Algorithm_Service SHALL store max_distance for each depot
4. THE Algorithm_Service SHALL pass max_distance to all algorithm implementations (GA, PSO, ACO)
5. THE Algorithm_Service SHALL include constraint violation information in error responses

### Requirement 11: 错误处理和用户反馈

**User Story:** 作为系统用户,我需要清晰的错误提示,以便理解为什么算法无法找到解决方案。

#### Acceptance Criteria

1. WHEN algorithm fails due to distance constraint, THE System SHALL return error message "无法找到满足最大行驶距离约束的可行解,请增加max_distance或车辆数量"
2. WHEN algorithm fails due to combined constraints, THE System SHALL return error message listing all violated constraints
3. THE Frontend SHALL display algorithm errors in a prominent alert dialog
4. THE Frontend SHALL suggest actions: "增加最大行驶距离" or "增加车辆数量" or "减少客户需求"
5. THE Backend SHALL log constraint violation details including depot_id, max_distance, and actual_route_distance

### Requirement 12: 数据迁移

**User Story:** 作为系统管理员,我需要安全地迁移现有数据,以便不影响已有的仓库配置。

#### Acceptance Criteria

1. THE System SHALL provide a SQL migration script to add the `max_distance` column
2. THE migration script SHALL set `max_distance` to NULL for all existing depot records
3. THE migration script SHALL execute without errors on existing database instances
4. WHEN migration completes, THE System SHALL verify that all existing depot records remain accessible
5. THE System SHALL maintain all existing functionality for depots with NULL `max_distance`

### Requirement 13: 解决方案验证

**User Story:** 作为质量保证人员,我需要系统验证所有返回的解决方案,以便确保约束得到遵守。

#### Acceptance Criteria

1. WHEN algorithm returns a solution, THE System SHALL validate each route's distance against its depot's max_distance
2. IF any route violates distance constraint, THEN THE System SHALL reject the solution and return error
3. THE System SHALL calculate and log the maximum route distance for each depot in the solution
4. THE System SHALL include route distances in the solution response for frontend display
5. THE System SHALL provide a validation report showing: depot_id, max_distance, actual_max_route_distance, status (pass/fail)

### Requirement 14: 性能要求

**User Story:** 作为系统用户,我需要算法在合理时间内完成,即使增加了距离约束。

#### Acceptance Criteria

1. WHEN max_distance constraint is active, THE Algorithm_Service SHALL complete execution within 150% of baseline time (without constraint)
2. THE Algorithm_Service SHALL optimize constraint checking to minimize performance impact
3. THE Algorithm_Service SHALL cache distance calculations to avoid redundant computation
4. WHEN problem is infeasible, THE Algorithm_Service SHALL detect and return error within 30 seconds
5. THE System SHALL log execution time for performance monitoring

### Requirement 15: 文档和日志

**User Story:** 作为开发者,我需要完整的日志记录,以便调试和监控系统行为。

#### Acceptance Criteria

1. THE Backend SHALL log all depot CRUD operations including max_distance changes
2. THE Algorithm_Service SHALL log constraint checking results for each route
3. THE Algorithm_Service SHALL log when routes are split due to distance constraint
4. THE System SHALL log constraint violation details with depot_id, route_id, and distance values
5. THE System SHALL provide INFO level logs for normal operations and WARN level logs for constraint violations

