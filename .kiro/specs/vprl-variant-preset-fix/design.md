# Bugfix Design Document

## Root Cause Analysis

### Bug Condition C(X)

**C(X) = model.env.generator.subsample=True AND 手动创建的TensorDict缺少必需字段**

当满足此条件时,`model.env.reset(td)`调用失败并抛出"Cannot use subsample if variant_preset is not specified"错误。

### Detailed Analysis

通过check_model_env.py诊断,我们发现:
- 模型的MTVRPGenerator配置: `variant_preset='all'`, `subsample=True`
- 当`subsample=True`时,generator的`subsample_problems()`方法会被调用
- `subsample_problems()`期望TensorDict包含所有MTVRP特征字段
- 当前`convert_to_tensordict()`只创建了部分字段,缺少:
  - `vehicle_capacity` (应该是scaled capacity)
  - `capacity_original` (未scaled的原始capacity)
  - `backhaul_class` (backhaul类型)

### Error Flow

1. `_generate_vrpl_solutions()` 调用 `model.env.reset(td)`
2. `MTVRPEnv.reset()` 调用 `generator._generate()` 或直接使用传入的td
3. 如果`generator.subsample=True`,调用`subsample_problems(td)`
4. `subsample_problems()`尝试访问缺失的字段,导致错误

## Solution Design

### Approach: 补全TensorDict必需字段

修改`VPRL/instance_decomposer.py`的`convert_to_tensordict()`方法,添加所有MTVRPGenerator期望的字段。

### Required Fields for MTVRP

根据`MTVRPGenerator._generate()`方法,完整的TensorDict应包含:

```python
{
    'locs': [B, N+1, 2],                    # ✓ 已有
    'demand_linehaul': [B, N+1],            # ✓ 已有
    'demand_backhaul': [B, N+1],            # ✓ 已有
    'backhaul_class': [B, 1],               # ✗ 缺失
    'distance_limit': [B, 1],               # ✓ 已有
    'time_windows': [B, N+1, 2],            # ✓ 已有
    'service_time': [B, N+1],               # ✓ 已有
    'vehicle_capacity': [B, 1],             # ✗ 缺失 (scaled)
    'capacity_original': [B, 1],            # ✗ 缺失 (unscaled)
    'open_route': [B, 1],                   # ✓ 已有
    'speed': [B, 1],                        # ✓ 已有
}
```

### Implementation Details

#### 1. 添加缺失字段

在`convert_to_tensordict()`中添加:

```python
# Backhaul class (1 = classic backhaul)
backhaul_class = torch.tensor([1.0], dtype=torch.float32).unsqueeze(0)

# Vehicle capacity (scaled and unscaled)
capacity_original = torch.tensor([capacity], dtype=torch.float32).unsqueeze(0)
vehicle_capacity = torch.tensor([1.0], dtype=torch.float32).unsqueeze(0)  # Scaled to 1.0
```

#### 2. Demand Scaling

MTVRPGenerator在`scale_demand=True`时会将demands除以capacity。我们需要预先进行scaling:

```python
# Scale demands by capacity
demand_linehaul_scaled = demand_linehaul / capacity
```

#### 3. 字段顺序

确保TensorDict字段顺序与generator生成的一致,虽然这不是必需的,但有助于调试。

### Alternative Approach (Not Chosen)

**方案B: 禁用subsample**

可以通过修改模型的generator配置来禁用subsample:
```python
model.env.generator.subsample = False
```

**不选择此方案的原因:**
- 改变模型训练时的配置可能影响推理行为
- 模型可能依赖subsample逻辑来处理不同variant
- 补全字段是更安全的方案,保持模型原始行为

## Correctness Properties

### Property 1: TensorDict完整性
```python
@given(sub_problem=valid_cvrp_subproblem())
def test_tensordict_has_all_required_fields(sub_problem):
    td = convert_to_tensordict(...)
    
    required_fields = [
        'locs', 'demand_linehaul', 'demand_backhaul', 
        'backhaul_class', 'distance_limit', 'time_windows',
        'service_time', 'vehicle_capacity', 'capacity_original',
        'open_route', 'speed'
    ]
    
    for field in required_fields:
        assert field in td.keys()
```

### Property 2: 环境reset成功
```python
@given(sub_problem=valid_cvrp_subproblem())
def test_env_reset_succeeds_with_subsample(sub_problem):
    td = convert_to_tensordict(...)
    
    # 应该不抛出异常
    td_reset = model.env.reset(td)
    assert td_reset is not None
```

### Property 3: Demand scaling正确性
```python
@given(sub_problem=valid_cvrp_subproblem())
def test_demand_scaling_preserves_feasibility(sub_problem):
    td = convert_to_tensordict(...)
    
    # Scaled demands应该 <= 1.0 (scaled capacity)
    assert torch.all(td['demand_linehaul'] <= td['vehicle_capacity'])
```

## Testing Strategy

### Unit Tests

1. **test_convert_to_tensordict_fields**: 验证所有必需字段存在
2. **test_demand_scaling**: 验证demand正确scaling
3. **test_capacity_fields**: 验证capacity_original和vehicle_capacity正确

### Integration Tests

1. **test_env_reset_with_subsample**: 验证model.env.reset()成功
2. **test_solution_generation_all_depots**: 验证所有depot都能生成解
3. **test_no_fallback_to_ga**: 验证不会回退到纯GA_Java

### Property-Based Tests

使用Hypothesis生成随机CVRP sub-problems,验证:
- TensorDict字段完整性
- 环境reset成功
- Demand scaling正确性

## Implementation Plan

### Phase 1: 修复convert_to_tensordict()
- 添加缺失的字段
- 实现demand scaling
- 更新字段注释

### Phase 2: 测试验证
- 编写单元测试
- 编写集成测试
- 运行test_vprl_solution_generation.py验证

### Phase 3: 回归测试
- 验证subsample=False的模型仍然工作
- 验证不同variant_preset的模型工作
- 验证解转换逻辑不受影响

## Files to Modify

1. **VPRL/instance_decomposer.py**
   - `convert_to_tensordict()` 方法
   - 添加缺失字段
   - 实现demand scaling

## Risk Assessment

### Low Risk
- 只修改TensorDict创建逻辑
- 不改变模型或环境代码
- 向后兼容(添加字段不影响现有功能)

### Mitigation
- 完整的单元测试覆盖
- 集成测试验证端到端流程
- 保留原有回退机制(fallback to GA_Java)
