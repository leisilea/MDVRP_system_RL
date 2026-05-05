# Design Document - Vehicle Maximum Distance Constraint

## Overview

本设计文档详细说明了为MDVRP仿真系统添加车辆最大行驶距离约束功能的技术实现方案。该功能允许用户为每个仓库配置车辆的最大行驶距离限制,并在算法求解过程中强制执行此约束,确保生成的路径方案符合实际运营限制。

### 功能目标

- 在数据库层面支持存储每个仓库的最大行驶距离配置
- 在后端API层面提供maxDistance字段的CRUD操作和验证
- 在前端界面提供maxDistance的输入、编辑和显示功能
- 在算法服务层面实现距离约束的计算和强制执行
- 提供清晰的错误提示和约束违反反馈机制

### 技术栈

- **Database**: MySQL 8.0+
- **Backend**: Spring Boot 2.7+, MyBatis-Plus 3.5+, Java 11+
- **Frontend**: Vue 3, Element Plus, Axios
- **Algorithm Service**: Python 3.8+, Flask 2.0+, NumPy

### 设计原则

1. **向后兼容**: 现有数据和功能不受影响,maxDistance为NULL时表示无限制
2. **数据一致性**: 在数据库、后端、前端和算法服务之间保持数据格式一致
3. **用户友好**: 提供清晰的输入验证和错误提示
4. **性能优化**: 距离计算结果缓存,避免重复计算
5. **可扩展性**: 设计支持未来添加更多约束类型

## Architecture

### 系统架构图

```
┌─────────────┐
│   Frontend  │
│  (Vue 3)    │
└──────┬──────┘
       │ HTTP/REST
       ↓
┌─────────────┐
│   Backend   │
│ (Spring     │
│  Boot)      │
└──────┬──────┘
       │ JDBC
       ↓
┌─────────────┐      ┌──────────────┐
│   Database  │      │  Algorithm   │
│   (MySQL)   │      │   Service    │
└─────────────┘      │  (Python)    │
                     └──────────────┘
                            ↑
                            │ HTTP/REST
                            │
                     ┌──────┴──────┐
                     │   Backend   │
                     └─────────────┘
```


### 数据流图

```
用户输入maxDistance
       ↓
前端验证 (0.01 ~ 999999.99)
       ↓
发送到后端API
       ↓
后端验证和持久化
       ↓
存储到MySQL数据库
       ↓
算法求解时读取
       ↓
传递给算法服务
       ↓
算法服务解析并应用约束
       ↓
路径生成时检查距离
       ↓
返回结果或约束违反错误
       ↓
前端显示结果或错误提示
```

### 模块交互

1. **数据管理流程**: Frontend → Backend API → Database
2. **算法求解流程**: Frontend → Backend API → Algorithm Service → Backend → Frontend
3. **约束验证流程**: Algorithm Service (距离计算) → 约束检查 → 路径调整或错误返回

## Components and Interfaces

### 1. Database Layer

#### 1.1 Schema Changes

**Migration Script**: `add_max_distance_column.sql`

```sql
-- 添加max_distance列到depot表
ALTER TABLE depot 
ADD COLUMN max_distance DECIMAL(10,2) DEFAULT NULL 
COMMENT '车辆最大行驶距离(km),NULL表示无限制';

-- 添加检查约束确保max_distance为正数或NULL
ALTER TABLE depot 
ADD CONSTRAINT chk_max_distance_positive 
CHECK (max_distance IS NULL OR max_distance > 0);

-- 为max_distance列添加索引以优化查询性能
CREATE INDEX idx_depot_max_distance ON depot(max_distance);

-- 验证现有数据
SELECT COUNT(*) as total_depots, 
       COUNT(max_distance) as depots_with_limit,
       COUNT(*) - COUNT(max_distance) as depots_unlimited
FROM depot;
```



#### 1.2 Column Specifications

| 字段名 | 类型 | 约束 | 默认值 | 说明 |
|--------|------|------|--------|------|
| max_distance | DECIMAL(10,2) | NULL, CHECK > 0 | NULL | 车辆最大行驶距离(km) |

**设计说明**:
- **DECIMAL(10,2)**: 支持最大999999.99km的距离,精度为0.01km(10米)
- **DEFAULT NULL**: 现有数据自动设置为NULL,表示无距离限制
- **CHECK约束**: 确保如果设置了值,必须大于0
- **索引**: 优化按距离限制查询的性能

#### 1.3 Backward Compatibility

- 所有现有depot记录的max_distance将自动设置为NULL
- NULL值在业务逻辑中解释为"无距离限制"
- 现有的查询和操作不受影响
- 迁移脚本可以安全地在生产环境执行

### 2. Backend Layer

#### 2.1 Entity Model

**File**: `system_test/backend/src/main/java/com/gz/gd/backend/entity/Depot.java`

```java
package com.gz.gd.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import javax.validation.constraints.DecimalMin;
import javax.validation.constraints.DecimalMax;
import javax.validation.constraints.Digits;
import java.math.BigDecimal;

@Data
@TableName("depot")
public class Depot {
    @TableId(type = IdType.AUTO)
    private Long id;
    
    private Long scenarioId;
    
    private String name;
    
    private String address;
    
    private BigDecimal longitude;
    
    private BigDecimal latitude;
    
    private Integer vehicleCount;
    
    private Integer vehicleCapacity;
    
    /**
     * 车辆最大行驶距离(km)
     * NULL表示无距离限制
     */
    @DecimalMin(value = "0.01", message = "最大行驶距离必须大于0")
    @DecimalMax(value = "999999.99", message = "最大行驶距离不能超过999999.99")
    @Digits(integer = 8, fraction = 2, message = "最大行驶距离格式不正确")
    private BigDecimal maxDistance;
}
```



**设计说明**:
- 使用`BigDecimal`类型确保精确的小数计算
- 使用JSR-303验证注解进行输入验证
- `@DecimalMin`和`@DecimalMax`确保值在合理范围内
- `@Digits`确保小数位数正确
- 字段可以为NULL,表示无限制

#### 2.2 Service Layer Validation

**File**: `system_test/backend/src/main/java/com/gz/gd/backend/service/impl/DepotServiceImpl.java`

```java
@Service
public class DepotServiceImpl extends ServiceImpl<DepotMapper, Depot> implements DepotService {
    
    private static final Logger logger = LoggerFactory.getLogger(DepotServiceImpl.class);
    
    @Override
    public Depot createDepot(Depot depot) {
        // 验证maxDistance
        validateMaxDistance(depot);
        
        // 保存到数据库
        boolean success = this.save(depot);
        if (!success) {
            throw new RuntimeException("创建仓库失败");
        }
        
        logger.info("创建仓库成功: id={}, name={}, maxDistance={}", 
                   depot.getId(), depot.getName(), depot.getMaxDistance());
        return depot;
    }
    
    @Override
    public Depot updateDepot(Long id, Depot depot) {
        // 验证仓库是否存在
        Depot existing = this.getById(id);
        if (existing == null) {
            throw new RuntimeException("仓库不存在: id=" + id);
        }
        
        // 验证maxDistance
        validateMaxDistance(depot);
        
        // 更新
        depot.setId(id);
        boolean success = this.updateById(depot);
        if (!success) {
            throw new RuntimeException("更新仓库失败");
        }
        
        logger.info("更新仓库成功: id={}, name={}, maxDistance={}", 
                   depot.getId(), depot.getName(), depot.getMaxDistance());
        return depot;
    }
    
    /**
     * 验证maxDistance字段
     */
    private void validateMaxDistance(Depot depot) {
        BigDecimal maxDistance = depot.getMaxDistance();
        
        // NULL是允许的,表示无限制
        if (maxDistance == null) {
            return;
        }
        
        // 检查是否为正数
        if (maxDistance.compareTo(BigDecimal.ZERO) <= 0) {
            logger.warn("maxDistance验证失败: 值必须大于0, 实际值={}", maxDistance);
            throw new IllegalArgumentException("最大行驶距离必须大于0");
        }
        
        // 检查是否超出范围
        BigDecimal maxLimit = new BigDecimal("999999.99");
        if (maxDistance.compareTo(maxLimit) > 0) {
            logger.warn("maxDistance验证失败: 值超出范围, 实际值={}", maxDistance);
            throw new IllegalArgumentException("最大行驶距离超出允许范围");
        }
        
        logger.debug("maxDistance验证通过: {}", maxDistance);
    }
}
```



#### 2.3 Controller Layer

**File**: `system_test/backend/src/main/java/com/gz/gd/backend/controller/DepotController.java`

现有的Controller不需要修改,因为:
1. MyBatis-Plus自动处理新增的字段
2. JSON序列化/反序列化自动包含maxDistance字段
3. 验证逻辑在Service层处理

#### 2.4 Error Response Format

```json
{
  "success": false,
  "message": "最大行驶距离必须大于0",
  "code": 400,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 3. Frontend Layer

#### 3.1 DataManagement Component Changes

**File**: `system_test/frontend/src/views/DataManagement.vue`

**3.1.1 Table Column Addition**

在仓库表格中添加maxDistance列:

```vue
<el-table-column prop="vehicleCapacity" label="车辆载重" width="100" />
<!-- 新增列 -->
<el-table-column label="最大行驶距离(km)" width="150">
  <template #default="{ row }">
    <span v-if="row.maxDistance === null || row.maxDistance === undefined">
      无限制
    </span>
    <span v-else>
      {{ Number(row.maxDistance).toFixed(2) }}
    </span>
  </template>
</el-table-column>
<el-table-column label="操作" width="150" fixed="right">
```

**3.1.2 Form Field Addition**

在仓库对话框表单中添加maxDistance输入:

```vue
<el-form-item label="车辆载重" required>
  <el-input-number v-model="depotForm.vehicleCapacity" :min="1" style="width: 100%" />
</el-form-item>
<!-- 新增表单项 -->
<el-form-item label="最大行驶距离(km)">
  <el-input-number 
    v-model="depotForm.maxDistance" 
    :min="0.01" 
    :max="999999.99"
    :precision="2"
    :controls="true"
    clearable
    placeholder="留空表示无限制"
    style="width: 100%" 
  />
  <div style="color: #909399; font-size: 12px; margin-top: 5px;">
    设置车辆单次行驶的最大距离限制,留空表示无限制
  </div>
</el-form-item>
```



**3.1.3 Form Data Model Update**

```javascript
const depotForm = ref({
  id: null,
  scenarioId: null,
  name: '',
  address: '',
  longitude: 113.9987,
  latitude: 22.5975,
  vehicleCount: 1,
  vehicleCapacity: 100,
  maxDistance: null  // 新增字段,默认为null表示无限制
})
```

**3.1.4 Validation Rules**

```javascript
const depotFormRules = {
  name: [
    { required: true, message: '请输入仓库名称', trigger: 'blur' }
  ],
  vehicleCount: [
    { required: true, message: '请输入车辆数', trigger: 'blur' },
    { type: 'number', min: 1, message: '车辆数必须大于0', trigger: 'blur' }
  ],
  vehicleCapacity: [
    { required: true, message: '请输入车辆载重', trigger: 'blur' },
    { type: 'number', min: 1, message: '车辆载重必须大于0', trigger: 'blur' }
  ],
  maxDistance: [
    { 
      validator: (rule, value, callback) => {
        if (value === null || value === undefined || value === '') {
          // NULL是允许的
          callback()
          return
        }
        if (value <= 0) {
          callback(new Error('最大行驶距离必须大于0'))
          return
        }
        if (value > 999999.99) {
          callback(new Error('最大行驶距离不能超过999999.99'))
          return
        }
        callback()
      }, 
      trigger: 'blur' 
    }
  ]
}
```

#### 3.2 UI/UX Considerations

**显示逻辑**:
- NULL值显示为"无限制"
- 数值显示保留2位小数
- 使用灰色文字提示用户留空表示无限制

**输入体验**:
- 使用`el-input-number`组件提供数字输入
- 设置`clearable`属性允许用户清空输入
- 提供`+/-`按钮方便调整数值
- 设置合理的步长(默认1km)

**错误提示**:
- 实时验证输入范围
- 提交前验证所有字段
- 后端错误通过`ElMessage.error()`显示



### 4. Algorithm Service Layer

#### 4.1 Data Model Changes

**File**: `system_test/algorithm-service/solver/mdvrp_solver.py`

```python
class MDVRPInstance:
    """MDVRP问题实例"""
    
    def __init__(self, depots, customers):
        """
        初始化MDVRP实例
        
        Args:
            depots: 仓库列表,每个仓库包含:
                - id: 仓库ID
                - x, y: 坐标
                - vehicles: 车辆数量
                - capacity: 车辆容量
                - maxDistance: 最大行驶距离(可选,None表示无限制)
            customers: 客户列表
        """
        self.depots = []
        for depot in depots:
            self.depots.append({
                'id': depot['id'],
                'x': depot['x'],
                'y': depot['y'],
                'vehicles': depot['vehicles'],
                'capacity': depot['capacity'],
                'maxDistance': depot.get('maxDistance', None)  # 新增字段
            })
        
        self.customers = customers
        self.num_depots = len(depots)
        self.num_customers = len(customers)
        
        # 计算距离矩阵
        self.distance_matrix = self._calculate_distance_matrix()
    
    def _calculate_distance_matrix(self):
        """计算所有点之间的欧几里得距离"""
        all_points = self.depots + self.customers
        n = len(all_points)
        distance_matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    dx = all_points[i]['x'] - all_points[j]['x']
                    dy = all_points[i]['y'] - all_points[j]['y']
                    distance_matrix[i][j] = np.sqrt(dx * dx + dy * dy)
        
        return distance_matrix
    
    def get_depot_max_distance(self, depot_id):
        """
        获取指定仓库的最大行驶距离限制
        
        Args:
            depot_id: 仓库ID
            
        Returns:
            float or None: 最大距离,None表示无限制
        """
        for depot in self.depots:
            if depot['id'] == depot_id:
                return depot.get('maxDistance', None)
        return None
```



#### 4.2 Distance Calculation Functions

**File**: `system_test/algorithm-service/solver/mdvrp_solver.py`

```python
def calculate_route_distance(route, depot_idx, instance):
    """
    计算路径的总距离
    
    Args:
        route: 客户ID列表 [c1, c2, c3, ...]
        depot_idx: 仓库在depots列表中的索引
        instance: MDVRPInstance实例
        
    Returns:
        float: 路径总距离
    """
    if len(route) == 0:
        return 0.0
    
    distance = 0.0
    distance_matrix = instance.distance_matrix
    
    # 从仓库到第一个客户
    distance += distance_matrix[depot_idx][route[0]]
    
    # 客户之间的距离
    for i in range(len(route) - 1):
        distance += distance_matrix[route[i]][route[i + 1]]
    
    # 从最后一个客户返回仓库
    distance += distance_matrix[route[-1]][depot_idx]
    
    return distance


def check_distance_constraint(route, depot_idx, instance):
    """
    检查路径是否满足距离约束
    
    Args:
        route: 客户ID列表
        depot_idx: 仓库索引
        instance: MDVRPInstance实例
        
    Returns:
        tuple: (is_valid, actual_distance, max_distance)
    """
    actual_distance = calculate_route_distance(route, depot_idx, instance)
    depot_id = instance.depots[depot_idx]['id']
    max_distance = instance.get_depot_max_distance(depot_id)
    
    # 如果没有设置最大距离,则总是满足约束
    if max_distance is None:
        return True, actual_distance, None
    
    # 检查是否超过限制
    is_valid = actual_distance <= max_distance
    return is_valid, actual_distance, max_distance


def split_route_by_distance(route, depot_idx, instance):
    """
    根据距离约束分割路径
    
    Args:
        route: 客户ID列表
        depot_idx: 仓库索引
        instance: MDVRPInstance实例
        
    Returns:
        list: 分割后的路径列表
    """
    depot_id = instance.depots[depot_idx]['id']
    max_distance = instance.get_depot_max_distance(depot_id)
    
    # 如果没有距离限制,返回原路径
    if max_distance is None:
        return [route]
    
    result_routes = []
    current_route = []
    
    for customer in route:
        # 尝试将客户添加到当前路径
        test_route = current_route + [customer]
        test_distance = calculate_route_distance(test_route, depot_idx, instance)
        
        if test_distance <= max_distance:
            # 可以添加
            current_route.append(customer)
        else:
            # 超过限制,开始新路径
            if current_route:
                result_routes.append(current_route)
            current_route = [customer]
    
    # 添加最后一条路径
    if current_route:
        result_routes.append(current_route)
    
    return result_routes
```



#### 4.3 Genetic Algorithm (GA) Integration

**File**: `system_test/algorithm-service/solver/ga.py`

```python
class GeneticAlgorithm:
    def __init__(self, instance, params):
        self.instance = instance
        self.params = params
        # ... 其他初始化代码
    
    def split_into_routes(self, chromosome, depot_idx):
        """
        将染色体分割成多条路径,同时考虑容量和距离约束
        
        Args:
            chromosome: 客户序列
            depot_idx: 仓库索引
            
        Returns:
            list: 路径列表
        """
        depot = self.instance.depots[depot_idx]
        capacity = depot['capacity']
        max_distance = depot.get('maxDistance', None)
        
        routes = []
        current_route = []
        current_load = 0
        
        for customer_idx in chromosome:
            customer = self.instance.customers[customer_idx]
            demand = customer['demand']
            
            # 尝试添加客户到当前路径
            test_route = current_route + [customer_idx]
            test_load = current_load + demand
            
            # 检查容量约束
            if test_load > capacity:
                # 容量超限,开始新路径
                if current_route:
                    routes.append(current_route)
                current_route = [customer_idx]
                current_load = demand
                continue
            
            # 检查距离约束(如果设置了)
            if max_distance is not None:
                test_distance = calculate_route_distance(
                    test_route, depot_idx, self.instance
                )
                if test_distance > max_distance:
                    # 距离超限,开始新路径
                    if current_route:
                        routes.append(current_route)
                    current_route = [customer_idx]
                    current_load = demand
                    continue
            
            # 可以添加
            current_route.append(customer_idx)
            current_load = test_load
        
        # 添加最后一条路径
        if current_route:
            routes.append(current_route)
        
        return routes
    
    def validate_solution(self, solution):
        """
        验证解决方案是否满足所有约束
        
        Returns:
            tuple: (is_valid, error_message)
        """
        for route_info in solution['routes']:
            depot_idx = route_info['depot_idx']
            route = route_info['path']
            
            # 检查距离约束
            is_valid, actual_distance, max_distance = check_distance_constraint(
                route, depot_idx, self.instance
            )
            
            if not is_valid:
                depot_id = self.instance.depots[depot_idx]['id']
                error_msg = (
                    f"路径违反距离约束: 仓库ID={depot_id}, "
                    f"实际距离={actual_distance:.2f}km, "
                    f"最大限制={max_distance:.2f}km"
                )
                return False, error_msg
        
        return True, None
```



#### 4.4 PSO Algorithm Integration

**File**: `system_test/algorithm-service/solver/pso.py`

```python
class ParticleSwarmOptimization:
    def __init__(self, instance, params):
        self.instance = instance
        self.params = params
        # ... 其他初始化代码
    
    def decode_particle(self, particle, depot_idx):
        """
        将粒子解码为路径,应用距离约束
        
        Args:
            particle: 粒子位置向量
            depot_idx: 仓库索引
            
        Returns:
            list: 路径列表
        """
        # 根据粒子值排序客户
        customer_order = np.argsort(particle)
        
        # 使用split_route_by_distance分割路径
        routes = []
        depot = self.instance.depots[depot_idx]
        capacity = depot['capacity']
        max_distance = depot.get('maxDistance', None)
        
        current_route = []
        current_load = 0
        
        for customer_idx in customer_order:
            customer = self.instance.customers[customer_idx]
            demand = customer['demand']
            
            # 检查容量
            if current_load + demand > capacity:
                if current_route:
                    routes.append(current_route)
                current_route = [customer_idx]
                current_load = demand
                continue
            
            # 检查距离
            test_route = current_route + [customer_idx]
            if max_distance is not None:
                test_distance = calculate_route_distance(
                    test_route, depot_idx, self.instance
                )
                if test_distance > max_distance:
                    if current_route:
                        routes.append(current_route)
                    current_route = [customer_idx]
                    current_load = demand
                    continue
            
            current_route.append(customer_idx)
            current_load += demand
        
        if current_route:
            routes.append(current_route)
        
        return routes
    
    def calculate_fitness(self, particle, depot_idx):
        """
        计算粒子适应度,对违反约束的粒子进行惩罚
        """
        routes = self.decode_particle(particle, depot_idx)
        total_cost = 0
        penalty = 0
        
        for route in routes:
            route_cost = calculate_route_distance(route, depot_idx, self.instance)
            total_cost += route_cost
            
            # 检查距离约束
            is_valid, actual_distance, max_distance = check_distance_constraint(
                route, depot_idx, self.instance
            )
            
            if not is_valid:
                # 添加惩罚项
                excess = actual_distance - max_distance
                penalty += excess * 1000  # 大惩罚系数
        
        return total_cost + penalty
```



#### 4.5 ACO Algorithm Integration

**File**: `system_test/algorithm-service/solver/liziqun.py`

```python
class AntColonyOptimization:
    def __init__(self, instance, params):
        self.instance = instance
        self.params = params
        # ... 其他初始化代码
    
    def construct_solution(self, depot_idx):
        """
        蚂蚁构造解决方案,考虑距离约束
        """
        depot = self.instance.depots[depot_idx]
        capacity = depot['capacity']
        max_distance = depot.get('maxDistance', None)
        
        unvisited = set(range(self.instance.num_customers))
        routes = []
        
        while unvisited:
            current_route = []
            current_load = 0
            current_pos = depot_idx  # 从仓库开始
            
            while unvisited:
                # 计算可行的下一个客户
                feasible_customers = []
                
                for customer_idx in unvisited:
                    customer = self.instance.customers[customer_idx]
                    demand = customer['demand']
                    
                    # 检查容量约束
                    if current_load + demand > capacity:
                        continue
                    
                    # 检查距离约束
                    test_route = current_route + [customer_idx]
                    if max_distance is not None:
                        test_distance = calculate_route_distance(
                            test_route, depot_idx, self.instance
                        )
                        if test_distance > max_distance:
                            continue  # 不可行
                    
                    feasible_customers.append(customer_idx)
                
                # 如果没有可行客户,结束当前路径
                if not feasible_customers:
                    break
                
                # 根据信息素和启发式信息选择下一个客户
                next_customer = self.select_next_customer(
                    current_pos, feasible_customers
                )
                
                current_route.append(next_customer)
                current_load += self.instance.customers[next_customer]['demand']
                current_pos = next_customer
                unvisited.remove(next_customer)
            
            if current_route:
                routes.append(current_route)
        
        return routes
    
    def update_pheromones(self, all_solutions):
        """
        只对满足约束的解更新信息素
        """
        for solution in all_solutions:
            # 验证解是否满足所有约束
            is_valid = True
            for route_info in solution['routes']:
                depot_idx = route_info['depot_idx']
                route = route_info['path']
                
                valid, _, _ = check_distance_constraint(
                    route, depot_idx, self.instance
                )
                if not valid:
                    is_valid = False
                    break
            
            # 只对可行解更新信息素
            if is_valid:
                self._update_pheromone_for_solution(solution)
```



#### 4.6 API Request/Response Format

**Request Format** (from Backend to Algorithm Service):

```json
{
  "depots": [
    {
      "id": 1,
      "x": 113.9987,
      "y": 22.5975,
      "vehicles": 5,
      "capacity": 100,
      "maxDistance": 50.5
    },
    {
      "id": 2,
      "x": 114.0123,
      "y": 22.6012,
      "vehicles": 3,
      "capacity": 80,
      "maxDistance": null
    }
  ],
  "customers": [
    {
      "id": 1,
      "x": 114.0234,
      "y": 22.6123,
      "demand": 15
    }
  ],
  "params": {
    "algorithm": "genetic",
    "max_iterations": 1000,
    "population_size": 50
  }
}
```

**Success Response**:

```json
{
  "success": true,
  "data": {
    "routes": [
      {
        "vehicle_id": 1,
        "depot_id": 1,
        "path": [1, 3, 5],
        "cost": 45.8,
        "distance": 48.2,
        "load": 85
      }
    ],
    "totalCost": 270.5,
    "computeTime": 2.34,
    "numRoutes": 3,
    "algorithm": "genetic",
    "validation": {
      "allConstraintsSatisfied": true,
      "distanceViolations": []
    }
  },
  "timestamp": 1705312345.123
}
```

**Error Response** (Constraint Violation):

```json
{
  "success": false,
  "error": "约束违反",
  "message": "无法找到满足最大行驶距离约束的可行解",
  "details": {
    "violations": [
      {
        "depot_id": 1,
        "max_distance": 50.0,
        "required_distance": 65.3,
        "excess": 15.3
      }
    ],
    "suggestions": [
      "增加仓库1的最大行驶距离限制",
      "增加仓库1的车辆数量",
      "减少客户需求或重新分配客户"
    ]
  },
  "timestamp": 1705312345.123
}
```



#### 4.7 Input Validation

**File**: `system_test/algorithm-service/app.py`

更新`validate_depot`函数:

```python
def validate_depot(depot, index):
    """验证仓库数据"""
    required_fields = ['id', 'x', 'y', 'vehicles', 'capacity']
    for field in required_fields:
        if field not in depot:
            raise ValueError(f"仓库 {index} 缺少必要字段: {field}")
    
    if not isinstance(depot['vehicles'], (int, float)) or depot['vehicles'] <= 0:
        raise ValueError(f"仓库 {index} 的车辆数必须为正数")
    
    if not isinstance(depot['capacity'], (int, float)) or depot['capacity'] <= 0:
        raise ValueError(f"仓库 {index} 的容量必须为正数")
    
    # 验证maxDistance(可选字段)
    if 'maxDistance' in depot and depot['maxDistance'] is not None:
        max_distance = depot['maxDistance']
        if not isinstance(max_distance, (int, float)):
            raise ValueError(f"仓库 {index} 的maxDistance必须是数字")
        if max_distance <= 0:
            raise ValueError(f"仓库 {index} 的maxDistance必须大于0")
        if max_distance > 999999.99:
            raise ValueError(f"仓库 {index} 的maxDistance超出允许范围")
    
    return True
```

## Data Models

### Database Schema

```sql
CREATE TABLE depot (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    scenario_id BIGINT NOT NULL,
    name VARCHAR(50) NOT NULL,
    address VARCHAR(255),
    longitude DECIMAL(10, 6) NOT NULL,
    latitude DECIMAL(10, 6) NOT NULL,
    vehicle_count INT DEFAULT 5 COMMENT '车辆数量',
    vehicle_capacity INT DEFAULT 100 COMMENT '车辆载重',
    max_distance DECIMAL(10,2) DEFAULT NULL COMMENT '车辆最大行驶距离(km)',
    FOREIGN KEY (scenario_id) REFERENCES scenario(id) ON DELETE CASCADE,
    CONSTRAINT chk_max_distance_positive CHECK (max_distance IS NULL OR max_distance > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='仓库表';
```

### Java Entity

```java
public class Depot {
    private Long id;
    private Long scenarioId;
    private String name;
    private String address;
    private BigDecimal longitude;
    private BigDecimal latitude;
    private Integer vehicleCount;
    private Integer vehicleCapacity;
    private BigDecimal maxDistance;  // 新增
}
```

### Python Data Model

```python
depot = {
    'id': 1,
    'x': 113.9987,
    'y': 22.5975,
    'vehicles': 5,
    'capacity': 100,
    'maxDistance': 50.5  # 新增,None表示无限制
}
```

### Frontend Data Model

```javascript
const depot = {
  id: 1,
  scenarioId: 1,
  name: '仓库A',
  address: '广州市天河区',
  longitude: 113.9987,
  latitude: 22.5975,
  vehicleCount: 5,
  vehicleCapacity: 100,
  maxDistance: 50.5  // 新增,null表示无限制
}
```



## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

在编写正确性属性之前,我对需求进行了分析以识别和消除冗余:

**识别的冗余**:
1. Requirements 7.3, 8.3, 9.3 都要求"当max_distance为NULL时只应用容量约束" - 可以合并为一个通用属性
2. Requirements 7.4, 8.5, 9.5 都要求"验证最终解满足距离约束" - 可以合并为一个通用属性
3. Requirements 11.5 和 15.4 都要求"记录约束违反详情" - 是重复的
4. Requirements 2.4 和整体的序列化/反序列化可以用一个round-trip属性覆盖
5. 多个算法的路径分割逻辑(7.1-7.2, 8.1-8.2, 9.1-9.2)可以抽象为通用的约束执行属性

**合并后的属性**:
- 将算法特定的约束检查合并为通用的"算法必须遵守距离约束"属性
- 将多个验证需求合并为"解决方案验证"属性
- 将日志需求合并为更少的综合属性

### Core Properties



### Property 1: NULL maxDistance表示无限制

*For any* depot with maxDistance set to NULL, the system SHALL NOT apply any distance constraint when generating routes for that depot, only capacity constraints SHALL be enforced.

**Validates: Requirements 1.3, 7.3, 8.3, 9.3**

### Property 2: maxDistance验证

*For any* input value for maxDistance, if the value is not NULL, then it MUST be a positive number greater than 0 and less than or equal to 999999.99, otherwise the system SHALL reject the input with an appropriate error message.

**Validates: Requirements 1.4, 3.1, 3.4**

### Property 3: 数据持久化完整性

*For any* depot record, when updating the maxDistance field, all other fields (id, scenarioId, name, address, longitude, latitude, vehicleCount, vehicleCapacity) SHALL remain unchanged.

**Validates: Requirements 1.5**

### Property 4: JSON序列化Round-Trip

*For any* Depot object, serializing it to JSON and then deserializing back SHALL produce an equivalent Depot object with the same maxDistance value (including NULL).

**Validates: Requirements 2.3, 2.4, 2.5**

### Property 5: 前端显示格式化

*For any* depot with a numeric maxDistance value, the frontend display function SHALL format it with exactly 2 decimal places; for any depot with NULL maxDistance, the display SHALL show "无限制".

**Validates: Requirements 4.4, 4.5**

### Property 6: 前端验证阻止提交

*For any* form state with validation errors (negative maxDistance, zero maxDistance, or maxDistance > 999999.99), the form submission SHALL be prevented.

**Validates: Requirements 5.4**

### Property 7: 路径距离计算公式

*For any* route with n customers (n ≥ 1), the calculated distance SHALL equal: distance(depot, customer[0]) + sum(distance(customer[i], customer[i+1]) for i in 0..n-2) + distance(customer[n-1], depot).

**Validates: Requirements 6.1, 6.2**

### Property 8: 距离计算一致性

*For any* route, the distance used for constraint checking SHALL be identical to the distance used for cost calculation, both derived from the same distance_matrix.

**Validates: Requirements 6.2**

### Property 9: 算法路径生成遵守距离约束

*For any* algorithm (GA, PSO, ACO) and any depot with maxDistance set, when constructing or splitting routes, adding a customer that would cause the route distance to exceed maxDistance SHALL trigger the start of a new route.

**Validates: Requirements 7.1, 7.2, 8.1, 8.2, 9.1, 9.2**

### Property 10: 解决方案验证

*For any* solution returned by any algorithm, every route SHALL satisfy its depot's distance constraint (if maxDistance is set), otherwise the solution SHALL be rejected with a constraint violation error.

**Validates: Requirements 7.4, 8.5, 9.5, 13.1, 13.2**

### Property 11: PSO适应度惩罚

*For any* PSO particle that generates routes violating distance constraints, the fitness value SHALL include a penalty term proportional to the constraint violation amount.

**Validates: Requirements 8.4**

### Property 12: ACO信息素更新

*For any* ACO solution, pheromone trails SHALL only be updated if all routes in the solution satisfy their respective distance constraints.

**Validates: Requirements 9.4**

### Property 13: API数据传递

*For any* depot object sent from backend to algorithm service, the maxDistance field SHALL be correctly parsed as either a float (if set) or None (if NULL), and SHALL be stored in the MDVRPInstance for use by all algorithms.

**Validates: Requirements 10.1, 10.2, 10.3, 10.4**

### Property 14: 约束违反错误响应

*For any* algorithm execution that fails due to distance constraint violations, the error response SHALL include detailed violation information: depot_id, max_distance, actual_distance, and excess amount.

**Validates: Requirements 10.5, 11.2, 11.5, 15.4**

### Property 15: 向后兼容性

*For any* existing depot record with NULL max_distance (created before the feature), all CRUD operations, algorithm executions, and frontend displays SHALL function correctly without errors.

**Validates: Requirements 12.5**

### Property 16: 解决方案响应包含距离信息

*For any* successful solution, the response SHALL include the calculated distance for each route, enabling frontend display and validation reporting.

**Validates: Requirements 13.3, 13.4, 13.5**

### Property 17: 日志记录完整性

*For any* depot CRUD operation, constraint checking, route splitting, or constraint violation, the system SHALL log the event with appropriate details (depot_id, maxDistance, actual_distance) at the correct log level (INFO for normal operations, WARN for violations).

**Validates: Requirements 3.5, 15.1, 15.2, 15.3, 15.5**



## Error Handling

### 1. Input Validation Errors

#### 1.1 Frontend Validation

**场景**: 用户输入无效的maxDistance值

**错误类型**:
- 负数或零: "最大行驶距离必须大于0"
- 超出范围: "最大行驶距离不能超过999999.99"
- 非数字: "请输入有效的数字"

**处理方式**:
- 实时显示错误提示在输入框下方
- 禁用提交按钮直到错误修正
- 使用红色边框标识错误字段

#### 1.2 Backend Validation

**场景**: API接收到无效的maxDistance值

**错误响应**:
```json
{
  "success": false,
  "message": "最大行驶距离必须大于0",
  "code": 400,
  "field": "maxDistance",
  "value": -10.5,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**HTTP状态码**: 400 Bad Request

**日志级别**: WARN

### 2. Constraint Violation Errors

#### 2.1 算法无法找到可行解

**场景**: 距离约束过于严格,无法生成满足所有约束的解

**错误响应**:
```json
{
  "success": false,
  "error": "约束违反",
  "message": "无法找到满足最大行驶距离约束的可行解",
  "details": {
    "violations": [
      {
        "depot_id": 1,
        "depot_name": "仓库A",
        "max_distance": 30.0,
        "min_required_distance": 45.5,
        "reason": "最近的客户组合仍需要45.5km,超过30.0km限制"
      }
    ],
    "suggestions": [
      "将仓库1的最大行驶距离从30.0km增加到至少45.5km",
      "增加仓库1的车辆数量以分配更多路径",
      "减少客户需求或重新分配客户到其他仓库"
    ]
  },
  "timestamp": 1705312345.123
}
```

**前端处理**:
- 显示醒目的错误对话框
- 列出所有违反的约束
- 提供可操作的建议
- 允许用户直接跳转到编辑仓库页面

#### 2.2 解决方案验证失败

**场景**: 算法返回的解包含违反距离约束的路径

**错误响应**:
```json
{
  "success": false,
  "error": "解决方案验证失败",
  "message": "生成的解决方案包含违反距离约束的路径",
  "details": {
    "invalid_routes": [
      {
        "route_id": 3,
        "vehicle_id": 2,
        "depot_id": 1,
        "max_distance": 50.0,
        "actual_distance": 62.3,
        "excess": 12.3,
        "path": [1, 5, 8, 12]
      }
    ]
  },
  "timestamp": 1705312345.123
}
```

**处理方式**:
- 拒绝该解决方案
- 记录详细的验证失败信息
- 触发算法重试或返回错误给用户



### 3. Database Errors

#### 3.1 迁移脚本执行失败

**场景**: 添加max_distance列时数据库错误

**错误处理**:
- 回滚事务
- 记录详细错误日志
- 通知管理员
- 提供手动修复指南

#### 3.2 CHECK约束违反

**场景**: 尝试插入负数或零的max_distance

**错误响应**:
```
ERROR 3819 (HY000): Check constraint 'chk_max_distance_positive' is violated.
```

**处理方式**:
- 在应用层捕获该错误
- 转换为用户友好的错误消息
- 返回HTTP 400

### 4. Algorithm Service Errors

#### 4.1 解析错误

**场景**: maxDistance字段格式错误

**错误响应**:
```json
{
  "success": false,
  "error": "参数错误",
  "message": "仓库 1 的maxDistance必须是数字",
  "error_type": "ValueError",
  "timestamp": 1705312345.123
}
```

**HTTP状态码**: 400 Bad Request

#### 4.2 超时错误

**场景**: 算法在30秒内无法找到可行解

**错误响应**:
```json
{
  "success": false,
  "error": "超时",
  "message": "算法执行超时,可能是约束过于严格导致无可行解",
  "execution_time": 30.0,
  "timestamp": 1705312345.123
}
```

**HTTP状态码**: 408 Request Timeout

### 5. Error Recovery Strategies

#### 5.1 自动重试

- 算法服务临时故障: 最多重试3次,间隔1秒
- 数据库连接失败: 最多重试3次,间隔2秒

#### 5.2 降级策略

- 如果距离约束导致无解,建议用户:
  1. 临时移除距离约束(设为NULL)
  2. 查看无约束情况下的最优解
  3. 根据实际距离调整约束值

#### 5.3 用户通知

- 所有错误都通过`ElMessage.error()`显示
- 关键错误使用`ElMessageBox.alert()`模态对话框
- 提供"查看详情"按钮展开完整错误信息

## Testing Strategy

### 测试方法论

本功能采用**双重测试方法**:
1. **Unit Tests**: 验证特定示例、边界情况和错误条件
2. **Property-Based Tests**: 验证跨所有输入的通用属性

两种测试方法是互补的,共同确保全面覆盖:
- Unit tests捕获具体的bug和边界情况
- Property tests通过随机化验证通用正确性

### 1. Database Layer Testing

#### 1.1 Unit Tests

**测试框架**: JUnit 5 + H2 Database

**测试用例**:

```java
@Test
void testAddMaxDistanceColumn() {
    // 验证列存在且类型正确
    DatabaseMetaData metaData = connection.getMetaData();
    ResultSet columns = metaData.getColumns(null, null, "depot", "max_distance");
    assertTrue(columns.next());
    assertEquals("DECIMAL", columns.getString("TYPE_NAME"));
    assertEquals(10, columns.getInt("COLUMN_SIZE"));
    assertEquals(2, columns.getInt("DECIMAL_DIGITS"));
}

@Test
void testDefaultValueIsNull() {
    // 创建depot不指定max_distance
    Depot depot = new Depot();
    depot.setName("Test Depot");
    depot.setScenarioId(1L);
    depotMapper.insert(depot);
    
    // 验证max_distance为NULL
    Depot saved = depotMapper.selectById(depot.getId());
    assertNull(saved.getMaxDistance());
}

@Test
void testCheckConstraintRejectsNegative() {
    // 尝试插入负数
    Depot depot = new Depot();
    depot.setMaxDistance(new BigDecimal("-10.5"));
    
    assertThrows(DataIntegrityViolationException.class, () -> {
        depotMapper.insert(depot);
    });
}

@Test
void testCheckConstraintRejectsZero() {
    // 尝试插入零
    Depot depot = new Depot();
    depot.setMaxDistance(BigDecimal.ZERO);
    
    assertThrows(DataIntegrityViolationException.class, () -> {
        depotMapper.insert(depot);
    });
}
```



#### 1.2 Property-Based Tests

**测试框架**: jqwik

**测试配置**: 每个属性测试运行100次迭代

```java
@Property
@Label("Feature: vehicle-max-distance-constraint, Property 3: 数据持久化完整性")
void updateMaxDistancePreservesOtherFields(
    @ForAll @BigRange(min = "0.01", max = "999999.99") BigDecimal maxDistance) {
    
    // 创建初始depot
    Depot original = createTestDepot();
    depotMapper.insert(original);
    
    // 只更新maxDistance
    original.setMaxDistance(maxDistance);
    depotMapper.updateById(original);
    
    // 验证其他字段未变
    Depot updated = depotMapper.selectById(original.getId());
    assertEquals(original.getName(), updated.getName());
    assertEquals(original.getScenarioId(), updated.getScenarioId());
    assertEquals(original.getVehicleCount(), updated.getVehicleCount());
    assertEquals(original.getVehicleCapacity(), updated.getVehicleCapacity());
    assertEquals(maxDistance, updated.getMaxDistance());
}
```

### 2. Backend Layer Testing

#### 2.1 Unit Tests

**测试框架**: JUnit 5 + Mockito + Spring Boot Test

**测试用例**:

```java
@SpringBootTest
class DepotServiceTest {
    
    @Autowired
    private DepotService depotService;
    
    @Test
    void testCreateDepotWithValidMaxDistance() {
        Depot depot = new Depot();
        depot.setName("Test Depot");
        depot.setMaxDistance(new BigDecimal("50.5"));
        
        Depot saved = depotService.createDepot(depot);
        
        assertNotNull(saved.getId());
        assertEquals(new BigDecimal("50.5"), saved.getMaxDistance());
    }
    
    @Test
    void testCreateDepotWithNullMaxDistance() {
        Depot depot = new Depot();
        depot.setName("Test Depot");
        depot.setMaxDistance(null);
        
        Depot saved = depotService.createDepot(depot);
        
        assertNull(saved.getMaxDistance());
    }
    
    @Test
    void testValidationRejectsNegativeMaxDistance() {
        Depot depot = new Depot();
        depot.setMaxDistance(new BigDecimal("-10.5"));
        
        IllegalArgumentException ex = assertThrows(
            IllegalArgumentException.class,
            () -> depotService.createDepot(depot)
        );
        
        assertEquals("最大行驶距离必须大于0", ex.getMessage());
    }
    
    @Test
    void testValidationRejectsZeroMaxDistance() {
        Depot depot = new Depot();
        depot.setMaxDistance(BigDecimal.ZERO);
        
        IllegalArgumentException ex = assertThrows(
            IllegalArgumentException.class,
            () -> depotService.createDepot(depot)
        );
        
        assertEquals("最大行驶距离必须大于0", ex.getMessage());
    }
    
    @Test
    void testValidationRejectsExcessiveMaxDistance() {
        Depot depot = new Depot();
        depot.setMaxDistance(new BigDecimal("1000000.00"));
        
        IllegalArgumentException ex = assertThrows(
            IllegalArgumentException.class,
            () -> depotService.createDepot(depot)
        );
        
        assertEquals("最大行驶距离超出允许范围", ex.getMessage());
    }
}
```

#### 2.2 Property-Based Tests

```java
@Property
@Label("Feature: vehicle-max-distance-constraint, Property 2: maxDistance验证")
void validMaxDistanceAccepted(
    @ForAll @BigRange(min = "0.01", max = "999999.99") BigDecimal maxDistance) {
    
    Depot depot = createTestDepot();
    depot.setMaxDistance(maxDistance);
    
    // 应该成功创建
    assertDoesNotThrow(() -> depotService.createDepot(depot));
}

@Property
@Label("Feature: vehicle-max-distance-constraint, Property 2: maxDistance验证")
void invalidMaxDistanceRejected(
    @ForAll @BigRange(min = "-1000", max = "0") BigDecimal invalidMaxDistance) {
    
    Depot depot = createTestDepot();
    depot.setMaxDistance(invalidMaxDistance);
    
    // 应该抛出异常
    assertThrows(IllegalArgumentException.class, 
                () -> depotService.createDepot(depot));
}

@Property
@Label("Feature: vehicle-max-distance-constraint, Property 4: JSON序列化Round-Trip")
void jsonSerializationRoundTrip(
    @ForAll @BigRange(min = "0.01", max = "999999.99") BigDecimal maxDistance) {
    
    Depot original = createTestDepot();
    original.setMaxDistance(maxDistance);
    
    // 序列化
    String json = objectMapper.writeValueAsString(original);
    
    // 反序列化
    Depot deserialized = objectMapper.readValue(json, Depot.class);
    
    // 验证maxDistance相等
    assertEquals(original.getMaxDistance(), deserialized.getMaxDistance());
}
```



### 3. Frontend Layer Testing

#### 3.1 Unit Tests

**测试框架**: Vitest + Vue Test Utils

**测试用例**:

```javascript
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DataManagement from '@/views/DataManagement.vue'

describe('DataManagement - maxDistance', () => {
  it('displays "无限制" for NULL maxDistance', () => {
    const depot = { id: 1, name: 'Depot A', maxDistance: null }
    const wrapper = mount(DataManagement, {
      props: { depots: [depot] }
    })
    
    expect(wrapper.text()).toContain('无限制')
  })
  
  it('displays numeric maxDistance with 2 decimal places', () => {
    const depot = { id: 1, name: 'Depot A', maxDistance: 50.5 }
    const wrapper = mount(DataManagement, {
      props: { depots: [depot] }
    })
    
    expect(wrapper.text()).toContain('50.50')
  })
  
  it('shows error for negative maxDistance', async () => {
    const wrapper = mount(DataManagement)
    const input = wrapper.find('input[name="maxDistance"]')
    
    await input.setValue(-10)
    await input.trigger('blur')
    
    expect(wrapper.text()).toContain('最大行驶距离必须大于0')
  })
  
  it('shows error for zero maxDistance', async () => {
    const wrapper = mount(DataManagement)
    const input = wrapper.find('input[name="maxDistance"]')
    
    await input.setValue(0)
    await input.trigger('blur')
    
    expect(wrapper.text()).toContain('最大行驶距离必须大于0')
  })
  
  it('shows error for excessive maxDistance', async () => {
    const wrapper = mount(DataManagement)
    const input = wrapper.find('input[name="maxDistance"]')
    
    await input.setValue(1000000)
    await input.trigger('blur')
    
    expect(wrapper.text()).toContain('最大行驶距离不能超过999999.99')
  })
  
  it('prevents form submission with validation errors', async () => {
    const wrapper = mount(DataManagement)
    const input = wrapper.find('input[name="maxDistance"]')
    const submitButton = wrapper.find('button[type="submit"]')
    
    await input.setValue(-10)
    
    expect(submitButton.attributes('disabled')).toBeDefined()
  })
})
```

#### 3.2 Property-Based Tests

**测试框架**: fast-check

```javascript
import fc from 'fast-check'

describe('DataManagement - Property Tests', () => {
  it('Property 5: 前端显示格式化', () => {
    fc.assert(
      fc.property(
        fc.float({ min: 0.01, max: 999999.99 }),
        (maxDistance) => {
          const formatted = formatMaxDistance(maxDistance)
          const parts = formatted.split('.')
          
          // 验证有2位小数
          expect(parts[1]).toHaveLength(2)
        }
      ),
      { numRuns: 100 }
    )
  })
  
  it('Property 6: 前端验证阻止提交', () => {
    fc.assert(
      fc.property(
        fc.oneof(
          fc.float({ max: 0 }),           // 负数或零
          fc.float({ min: 1000000 })      // 超出范围
        ),
        (invalidValue) => {
          const hasError = validateMaxDistance(invalidValue)
          expect(hasError).toBe(true)
        }
      ),
      { numRuns: 100 }
    )
  })
})
```

### 4. Algorithm Service Testing

#### 4.1 Unit Tests

**测试框架**: pytest

**测试用例**:

```python
import pytest
from solver.mdvrp_solver import (
    calculate_route_distance,
    check_distance_constraint,
    split_route_by_distance
)

def test_calculate_route_distance_single_customer():
    """测试单客户路径距离计算"""
    instance = create_test_instance()
    route = [0]  # 一个客户
    depot_idx = 0
    
    distance = calculate_route_distance(route, depot_idx, instance)
    
    # 应该是 depot->customer + customer->depot
    expected = (instance.distance_matrix[depot_idx][route[0]] + 
                instance.distance_matrix[route[0]][depot_idx])
    assert abs(distance - expected) < 0.001

def test_calculate_route_distance_empty_route():
    """测试空路径距离为0"""
    instance = create_test_instance()
    route = []
    depot_idx = 0
    
    distance = calculate_route_distance(route, depot_idx, instance)
    
    assert distance == 0.0

def test_check_distance_constraint_null_max_distance():
    """测试NULL maxDistance总是满足约束"""
    instance = create_test_instance_with_null_max_distance()
    route = [0, 1, 2, 3, 4]  # 很长的路径
    depot_idx = 0
    
    is_valid, actual, max_dist = check_distance_constraint(
        route, depot_idx, instance
    )
    
    assert is_valid is True
    assert max_dist is None

def test_check_distance_constraint_violation():
    """测试距离约束违反检测"""
    instance = create_test_instance_with_max_distance(30.0)
    route = [0, 1, 2, 3, 4]  # 超过30km的路径
    depot_idx = 0
    
    is_valid, actual, max_dist = check_distance_constraint(
        route, depot_idx, instance
    )
    
    assert is_valid is False
    assert actual > 30.0
    assert max_dist == 30.0

def test_split_route_by_distance():
    """测试路径按距离分割"""
    instance = create_test_instance_with_max_distance(20.0)
    long_route = [0, 1, 2, 3, 4, 5]
    depot_idx = 0
    
    split_routes = split_route_by_distance(long_route, depot_idx, instance)
    
    # 验证每条路径都满足约束
    for route in split_routes:
        is_valid, _, _ = check_distance_constraint(route, depot_idx, instance)
        assert is_valid is True
```



#### 4.2 Property-Based Tests

**测试框架**: Hypothesis

**测试配置**: 每个属性测试运行100次迭代

```python
from hypothesis import given, strategies as st, settings

@given(
    max_distance=st.floats(min_value=0.01, max_value=999999.99),
    num_customers=st.integers(min_value=1, max_value=20)
)
@settings(max_examples=100)
def test_property_7_route_distance_calculation(max_distance, num_customers):
    """
    Feature: vehicle-max-distance-constraint
    Property 7: 路径距离计算公式
    
    For any route with n customers, the calculated distance SHALL equal:
    distance(depot, customer[0]) + sum(distance(customer[i], customer[i+1])) 
    + distance(customer[n-1], depot)
    """
    instance = create_random_instance(num_customers)
    depot_idx = 0
    route = list(range(num_customers))
    
    # 使用函数计算
    calculated = calculate_route_distance(route, depot_idx, instance)
    
    # 手动计算验证
    expected = instance.distance_matrix[depot_idx][route[0]]
    for i in range(len(route) - 1):
        expected += instance.distance_matrix[route[i]][route[i + 1]]
    expected += instance.distance_matrix[route[-1]][depot_idx]
    
    assert abs(calculated - expected) < 0.001

@given(
    max_distance=st.floats(min_value=10.0, max_value=100.0),
    num_customers=st.integers(min_value=5, max_value=15)
)
@settings(max_examples=100)
def test_property_9_algorithm_respects_distance_constraint(max_distance, num_customers):
    """
    Feature: vehicle-max-distance-constraint
    Property 9: 算法路径生成遵守距离约束
    
    For any algorithm and any depot with maxDistance set, routes SHALL NOT
    exceed the maxDistance limit.
    """
    instance = create_random_instance_with_max_distance(
        num_customers, max_distance
    )
    
    # 测试GA
    ga_solver = GeneticAlgorithm(instance, {'max_iterations': 100})
    ga_solution = ga_solver.solve()
    
    for route_info in ga_solution['routes']:
        depot_idx = route_info['depot_idx']
        route = route_info['path']
        
        is_valid, actual, max_dist = check_distance_constraint(
            route, depot_idx, instance
        )
        
        assert is_valid, f"GA violated constraint: {actual} > {max_dist}"

@given(
    num_depots=st.integers(min_value=1, max_value=3),
    num_customers=st.integers(min_value=5, max_value=20)
)
@settings(max_examples=100)
def test_property_10_solution_validation(num_depots, num_customers):
    """
    Feature: vehicle-max-distance-constraint
    Property 10: 解决方案验证
    
    For any solution, every route SHALL satisfy its depot's distance constraint.
    """
    instance = create_random_instance(num_depots, num_customers)
    solver = create_solver(instance.depots, instance.customers, {})
    
    solution = solver.solve()
    
    # 验证所有路径
    for route_info in solution['routes']:
        depot_idx = route_info['depot_idx']
        route = route_info['path']
        
        is_valid, actual, max_dist = check_distance_constraint(
            route, depot_idx, instance
        )
        
        if max_dist is not None:
            assert is_valid, (
                f"Route violated constraint: depot={depot_idx}, "
                f"actual={actual}, max={max_dist}"
            )

@given(
    max_distance=st.one_of(st.none(), st.floats(min_value=0.01, max_value=999999.99))
)
@settings(max_examples=100)
def test_property_13_api_data_passing(max_distance):
    """
    Feature: vehicle-max-distance-constraint
    Property 13: API数据传递
    
    For any depot with maxDistance, it SHALL be correctly parsed and stored.
    """
    depot_data = {
        'id': 1,
        'x': 0.0,
        'y': 0.0,
        'vehicles': 5,
        'capacity': 100,
        'maxDistance': max_distance
    }
    
    instance = MDVRPInstance([depot_data], [])
    
    stored_max_distance = instance.get_depot_max_distance(1)
    
    assert stored_max_distance == max_distance

@given(
    st.lists(
        st.floats(min_value=0.01, max_value=999999.99),
        min_size=1,
        max_size=5
    )
)
@settings(max_examples=100)
def test_property_1_null_means_unlimited(max_distances):
    """
    Feature: vehicle-max-distance-constraint
    Property 1: NULL maxDistance表示无限制
    
    For any depot with NULL maxDistance, no distance constraint SHALL be applied.
    """
    # 创建一个有NULL maxDistance的depot
    depot_with_null = {
        'id': 1,
        'x': 0.0,
        'y': 0.0,
        'vehicles': 10,
        'capacity': 1000,
        'maxDistance': None
    }
    
    customers = create_random_customers(20)
    instance = MDVRPInstance([depot_with_null], customers)
    
    # 创建一个非常长的路径
    long_route = list(range(len(customers)))
    
    # 应该总是满足约束(因为是NULL)
    is_valid, actual, max_dist = check_distance_constraint(
        long_route, 0, instance
    )
    
    assert is_valid is True
    assert max_dist is None
```



### 5. Integration Testing

#### 5.1 End-to-End Tests

**测试框架**: Cypress (Frontend) + TestContainers (Backend)

**测试场景**:

```javascript
describe('Vehicle Max Distance Constraint - E2E', () => {
  it('完整流程: 创建带距离限制的仓库并求解', () => {
    // 1. 登录系统
    cy.login()
    
    // 2. 创建场景
    cy.visit('/data-management')
    cy.get('[data-test="add-scenario"]').click()
    cy.get('[data-test="scenario-name"]').type('测试场景')
    cy.get('[data-test="save-scenario"]').click()
    
    // 3. 添加仓库(带maxDistance)
    cy.get('[data-test="add-depot"]').click()
    cy.get('[data-test="depot-name"]').type('仓库A')
    cy.get('[data-test="depot-max-distance"]').type('50.5')
    cy.get('[data-test="save-depot"]').click()
    
    // 4. 验证显示
    cy.get('[data-test="depot-table"]')
      .should('contain', '50.50')
    
    // 5. 添加客户
    cy.get('[data-test="customer-tab"]').click()
    cy.addMultipleCustomers(10)
    
    // 6. 运行算法
    cy.visit('/algorithm')
    cy.selectScenario('测试场景')
    cy.selectAlgorithm('GA')
    cy.get('[data-test="run-algorithm"]').click()
    
    // 7. 验证结果
    cy.get('[data-test="solution-result"]', { timeout: 30000 })
      .should('be.visible')
    
    // 8. 验证所有路径满足距离约束
    cy.get('[data-test="route-distance"]').each(($el) => {
      const distance = parseFloat($el.text())
      expect(distance).to.be.lessThan(50.5)
    })
  })
  
  it('约束违反场景: 距离限制过严', () => {
    // 1. 创建距离限制很小的仓库
    cy.createDepot({ name: '仓库B', maxDistance: 5.0 })
    
    // 2. 添加距离较远的客户
    cy.addCustomersAtDistance(30)
    
    // 3. 运行算法
    cy.runAlgorithm('GA')
    
    // 4. 应该显示错误
    cy.get('[data-test="error-dialog"]')
      .should('be.visible')
      .and('contain', '无法找到满足最大行驶距离约束的可行解')
    
    // 5. 应该显示建议
    cy.get('[data-test="suggestions"]')
      .should('contain', '增加最大行驶距离')
  })
})
```

#### 5.2 Performance Tests

**测试框架**: JMeter + Python locust

**测试场景**:

```python
from locust import HttpUser, task, between

class MDVRPUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def solve_with_distance_constraint(self):
        """测试带距离约束的求解性能"""
        payload = {
            'depots': [
                {
                    'id': 1,
                    'x': 0, 'y': 0,
                    'vehicles': 5,
                    'capacity': 100,
                    'maxDistance': 50.0
                }
            ],
            'customers': self.generate_customers(20),
            'params': {
                'algorithm': 'genetic',
                'max_iterations': 1000
            }
        }
        
        with self.client.post(
            '/api/solve',
            json=payload,
            catch_response=True
        ) as response:
            if response.elapsed.total_seconds() > 45:  # 150% of 30s baseline
                response.failure(f"Too slow: {response.elapsed.total_seconds()}s")
            elif response.status_code == 200:
                response.success()
```

### 6. Test Coverage Goals

**目标覆盖率**:
- **Backend代码覆盖率**: ≥ 85%
  - Service层: ≥ 90%
  - Controller层: ≥ 80%
  - Entity层: 100%

- **Frontend代码覆盖率**: ≥ 80%
  - 组件逻辑: ≥ 85%
  - 验证函数: 100%
  - 显示函数: ≥ 90%

- **Algorithm Service覆盖率**: ≥ 85%
  - 距离计算函数: 100%
  - 约束检查函数: 100%
  - 算法核心逻辑: ≥ 80%

**Property-Based Test配置**:
- 每个属性测试最少100次迭代
- 使用随机种子确保可重现性
- 失败时自动缩小(shrinking)到最小反例

### 7. Continuous Integration

**CI Pipeline配置**:

```yaml
# .github/workflows/ci.yml
name: CI - Vehicle Max Distance Constraint

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up JDK 11
        uses: actions/setup-java@v2
        with:
          java-version: '11'
      - name: Run Unit Tests
        run: mvn test
      - name: Run Property Tests
        run: mvn test -Dtest=*PropertyTest
      - name: Generate Coverage Report
        run: mvn jacoco:report
      - name: Upload Coverage
        uses: codecov/codecov-action@v2
  
  algorithm-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.8'
      - name: Install Dependencies
        run: pip install -r requirements.txt
      - name: Run Unit Tests
        run: pytest tests/unit
      - name: Run Property Tests
        run: pytest tests/property --hypothesis-profile=ci
      - name: Generate Coverage Report
        run: pytest --cov=solver --cov-report=xml
  
  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Node.js
        uses: actions/setup-node@v2
        with:
          node-version: '16'
      - name: Install Dependencies
        run: npm install
      - name: Run Unit Tests
        run: npm run test:unit
      - name: Run E2E Tests
        run: npm run test:e2e
      - name: Generate Coverage Report
        run: npm run test:coverage
```

## Implementation Roadmap

### Phase 1: Database and Backend (Week 1)

**Day 1-2: Database Layer**
- 编写并测试SQL迁移脚本
- 在开发环境执行迁移
- 验证现有数据完整性

**Day 3-4: Backend Entity and Service**
- 更新Depot实体类
- 实现Service层验证逻辑
- 编写单元测试和属性测试

**Day 5: Backend Integration**
- 测试API端点
- 验证JSON序列化/反序列化
- 集成测试

### Phase 2: Frontend (Week 2)

**Day 1-2: UI Components**
- 添加表格列显示
- 实现表单输入字段
- 添加验证规则

**Day 3-4: Frontend Logic**
- 实现显示格式化逻辑
- 添加客户端验证
- 错误处理和用户反馈

**Day 5: Frontend Testing**
- 单元测试
- 集成测试
- E2E测试

### Phase 3: Algorithm Service (Week 3)

**Day 1-2: Core Functions**
- 实现距离计算函数
- 实现约束检查函数
- 实现路径分割函数

**Day 3: GA Integration**
- 更新GA算法
- 添加距离约束检查
- 测试

**Day 4: PSO and ACO Integration**
- 更新PSO算法
- 更新ACO算法
- 测试

**Day 5: Algorithm Service Testing**
- 单元测试
- 属性测试
- 性能测试

### Phase 4: Integration and Testing (Week 4)

**Day 1-2: System Integration**
- 端到端集成测试
- 性能测试
- 压力测试

**Day 3-4: Bug Fixes and Optimization**
- 修复发现的问题
- 性能优化
- 代码审查

**Day 5: Documentation and Deployment**
- 更新用户文档
- 准备部署脚本
- 生产环境部署

## Appendix

### A. SQL Migration Script

完整的迁移脚本位于: `system_test/database/add_max_distance_column.sql`

### B. API Examples

详细的API请求/响应示例见本文档"Components and Interfaces"章节。

### C. Configuration Files

**Backend application.yml**:
```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/mdvrp_db
    username: root
    password: password
  jpa:
    hibernate:
      ddl-auto: none  # 使用手动迁移脚本
```

**Algorithm Service config.py**:
```python
class Config:
    HOST = '0.0.0.0'
    PORT = 5000
    DEBUG = False
    MAX_DISTANCE_DEFAULT = None  # NULL表示无限制
```

### D. References

- MDVRP问题定义: Cordeau, J. F., et al. (1997)
- 遗传算法实现: Goldberg, D. E. (1989)
- 粒子群算法: Kennedy, J., & Eberhart, R. (1995)
- 蚁群算法: Dorigo, M., & Gambardella, L. M. (1997)
- Property-Based Testing: Claessen, K., & Hughes, J. (2000)

---

**Document Version**: 1.0  
**Last Updated**: 2024-01-15  
**Author**: System Design Team  
**Status**: Ready for Review
