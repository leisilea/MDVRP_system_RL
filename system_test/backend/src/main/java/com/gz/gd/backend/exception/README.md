# 全局异常处理使用指南

## 📋 文件说明

### 1. GlobalExceptionHandler.java
全局异常处理器，自动捕获所有Controller抛出的异常并返回统一的Result格式。

### 2. BusinessException.java
自定义业务异常类，用于业务逻辑中主动抛出异常。

---

## 🎯 使用方式

### 方式1：在Service层抛出BusinessException（推荐）

```java
@Service
public class ScenarioService {
    
    public Scenario getById(Long id) {
        Scenario scenario = scenarioMapper.selectById(id);
        
        // ✅ 推荐：抛出BusinessException
        if (scenario == null) {
            throw new BusinessException(404, "场景不存在，ID: " + id);
        }
        
        return scenario;
    }
    
    public void deleteById(Long id) {
        // 检查是否存在
        Scenario scenario = getById(id);  // 如果不存在会自动抛出异常
        
        // 检查业务规则
        if (scenario.getStatus().equals("RUNNING")) {
            throw new BusinessException(400, "场景正在运行中，无法删除");
        }
        
        scenarioMapper.deleteById(id);
    }
}
```

### 方式2：在Controller层简化异常处理

**之前的写法**（可以简化）：
```java
@GetMapping("/{id}")
public Result<Scenario> getById(@PathVariable Long id) {
    try {
        Scenario scenario = scenarioService.getById(id);
        if (scenario != null) {
            return Result.success(scenario);
        } else {
            return Result.error(404, "场景不存在");
        }
    } catch (Exception e) {
        log.error("查询场景异常", e);
        return Result.error("查询场景异常: " + e.getMessage());
    }
}
```

**现在的写法**（更简洁）：
```java
@GetMapping("/{id}")
public Result<Scenario> getById(@PathVariable Long id) {
    // Service层会抛出BusinessException，GlobalExceptionHandler会自动处理
    Scenario scenario = scenarioService.getById(id);
    return Result.success(scenario);
}
```

---

## 📝 异常处理清单

GlobalExceptionHandler 会自动处理以下异常：

| 异常类型 | HTTP状态码 | 返回错误码 | 说明 |
|---------|-----------|-----------|------|
| BusinessException | 200 | 自定义 | 业务异常（推荐使用） |
| MethodArgumentNotValidException | 400 | 400 | @Valid参数验证失败 |
| BindException | 400 | 400 | 参数绑定失败 |
| MethodArgumentTypeMismatchException | 400 | 400 | 参数类型不匹配 |
| NumberFormatException | 400 | 400 | 数字格式错误 |
| ClassCastException | 400 | 400 | 类型转换错误 |
| IllegalArgumentException | 400 | 400 | 非法参数 |
| IllegalStateException | 400 | 400 | 非法状态 |
| NullPointerException | 500 | 500 | 空指针（需要修复代码） |
| RuntimeException | 500 | 500 | 其他运行时异常 |
| Exception | 500 | 500 | 所有未捕获异常（兜底） |

---

## 🔍 测试示例

### 测试1：参数验证异常

**请求**：
```
POST /api/scenario
Content-Type: application/json

{
  "name": "",
  "description": "测试"
}
```

**响应**（如果name字段有@NotBlank验证）：
```json
{
  "code": 400,
  "message": "参数验证失败: 场景名称不能为空",
  "data": null
}
```

### 测试2：参数类型错误

**请求**：
```
GET /api/scenario/abc
```

**响应**：
```json
{
  "code": 400,
  "message": "参数 'id' 类型错误，期望类型: Long",
  "data": null
}
```

### 测试3：业务异常

**请求**：
```
GET /api/scenario/999
```

**响应**（如果ID不存在）：
```json
{
  "code": 404,
  "message": "场景不存在，ID: 999",
  "data": null
}
```

### 测试4：系统异常

**请求**：
```
POST /api/algorithm/solve
Content-Type: application/json

{
  "scenarioId": 1,
  "params": {}
}
```

**响应**（如果算法服务不可用）：
```json
{
  "code": 500,
  "message": "系统异常: Connection refused",
  "data": null
}
```

---

## 💡 最佳实践

### 1. Service层使用BusinessException

```java
@Service
public class DepotService {
    
    public Depot getById(Long id) {
        Depot depot = depotMapper.selectById(id);
        if (depot == null) {
            throw new BusinessException(404, "仓库不存在");
        }
        return depot;
    }
    
    public void updateDepot(Depot depot) {
        // 检查是否存在
        Depot existing = getById(depot.getId());
        
        // 检查业务规则
        if (depot.getVehicleCount() <= 0) {
            throw new BusinessException(400, "车辆数量必须大于0");
        }
        
        if (depot.getVehicleCapacity() <= 0) {
            throw new BusinessException(400, "车辆载重必须大于0");
        }
        
        depotMapper.updateById(depot);
    }
}
```

### 2. Controller层简化代码

```java
@RestController
@RequestMapping("/api/depot")
public class DepotController {
    
    @Autowired
    private DepotService depotService;
    
    // ✅ 简洁的写法
    @GetMapping("/{id}")
    public Result<Depot> getById(@PathVariable Long id) {
        return Result.success(depotService.getById(id));
    }
    
    // ✅ 简洁的写法
    @PutMapping("/{id}")
    public Result<Void> updateDepot(@PathVariable Long id, @RequestBody Depot depot) {
        depot.setId(id);
        depotService.updateDepot(depot);
        return Result.success();
    }
}
```

### 3. 添加参数验证注解

```java
import jakarta.validation.constraints.*;

@Data
public class Scenario {
    
    @NotBlank(message = "场景名称不能为空")
    @Size(max = 100, message = "场景名称长度不能超过100")
    private String name;
    
    @Size(max = 500, message = "描述长度不能超过500")
    private String description;
}
```

```java
@PostMapping
public Result<Scenario> createScenario(@Valid @RequestBody Scenario scenario) {
    // @Valid会自动触发验证，失败时GlobalExceptionHandler会处理
    return Result.success(scenarioService.createScenario(scenario));
}
```

---

## ⚠️ 注意事项

1. **不要在Controller层捕获所有异常**
   - ❌ 错误：`catch (Exception e) { return Result.error(...); }`
   - ✅ 正确：让异常传播到GlobalExceptionHandler

2. **使用BusinessException传递业务错误**
   - ❌ 错误：`return Result.error(404, "不存在");`
   - ✅ 正确：`throw new BusinessException(404, "不存在");`

3. **日志记录已由GlobalExceptionHandler处理**
   - Controller层不需要再写 `log.error(...)`
   - Service层可以记录业务日志 `log.info(...)`

4. **空指针异常应该修复代码**
   - NullPointerException通常是代码bug
   - 不应该依赖GlobalExceptionHandler来处理

---

## 🚀 迁移指南

如果你的Controller已经写了try-catch，可以逐步迁移：

### 步骤1：Service层添加BusinessException

```java
// 修改前
public Scenario getById(Long id) {
    return scenarioMapper.selectById(id);
}

// 修改后
public Scenario getById(Long id) {
    Scenario scenario = scenarioMapper.selectById(id);
    if (scenario == null) {
        throw new BusinessException(404, "场景不存在");
    }
    return scenario;
}
```

### 步骤2：Controller层简化代码

```java
// 修改前
@GetMapping("/{id}")
public Result<Scenario> getById(@PathVariable Long id) {
    try {
        Scenario scenario = scenarioService.getById(id);
        if (scenario != null) {
            return Result.success(scenario);
        } else {
            return Result.error(404, "场景不存在");
        }
    } catch (Exception e) {
        log.error("查询场景异常", e);
        return Result.error("查询场景异常: " + e.getMessage());
    }
}

// 修改后
@GetMapping("/{id}")
public Result<Scenario> getById(@PathVariable Long id) {
    return Result.success(scenarioService.getById(id));
}
```

---

**创建时间**: 2026年2月24日  
**版本**: v1.0
