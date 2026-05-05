# Implementation Tasks

## Task 1: 编写bug condition探索测试

编写property-based test验证bug condition存在。

**Acceptance Criteria:**
- 测试在未修复的代码上失败(检测到bug)
- 测试使用Hypothesis生成随机CVRP sub-problems
- 测试验证当subsample=True时,model.env.reset()失败
- 测试输出清晰的失败信息,包含缺失的字段

**Files:**
- 创建 `tests/test_vprl_variant_preset_bug.py`

**Correctness Property:**
```python
# Bug condition exploration test
@given(sub_problem=valid_cvrp_subproblem())
def test_bug_condition_env_reset_fails_with_incomplete_tensordict(sub_problem):
    """
    Bug condition: 当model.env.generator.subsample=True且TensorDict缺少必需字段时,
    model.env.reset(td)应该失败
    """
    # 使用当前(未修复)的convert_to_tensordict
    td = convert_to_tensordict(...)
    
    # 加载配置了subsample=True的模型
    model = load_model_with_subsample_true()
    
    # 应该抛出错误(bug存在)
    with pytest.raises(Exception, match="Cannot use subsample"):
        model.env.reset(td)
```

---

## Task 2: 编写preservation测试

编写测试验证修复不会破坏现有功能。

**Acceptance Criteria:**
- 测试验证subsample=False的模型仍然工作
- 测试验证不同variant_preset的模型工作
- 测试验证解转换逻辑不受影响
- 测试验证回退机制仍然工作

**Files:**
- 更新 `tests/test_vprl_variant_preset_bug.py`

**Correctness Properties:**
```python
# Preservation test 1: subsample=False仍然工作
def test_preservation_subsample_false_still_works():
    """验证当model.env.generator.subsample=False时,系统继续正常工作"""
    # 创建或mock一个subsample=False的模型
    # 验证解生成成功

# Preservation test 2: 不同variant_preset工作
@pytest.mark.parametrize("variant_preset", ["cvrp", "vrpl", "vrptw", "all"])
def test_preservation_different_variant_presets(variant_preset):
    """验证不同variant_preset配置都能工作"""
    # 对每个variant_preset验证解生成

# Preservation test 3: 解转换逻辑不变
def test_preservation_solution_conversion_unchanged():
    """验证解转换为Cordeau格式的逻辑保持不变"""
    # 验证convert_rl4co_to_cordeau()仍然正确工作

# Preservation test 4: 回退机制工作
def test_preservation_fallback_mechanism_works():
    """验证当VPRL失败时,回退到GA_Java机制仍然工作"""
    # Mock VPRL失败场景
    # 验证系统回退到GA_Java
```

---

## Task 3: 修复convert_to_tensordict()添加缺失字段

修改`VPRL/instance_decomposer.py`的`convert_to_tensordict()`方法,添加MTVRPGenerator期望的所有字段。

**Acceptance Criteria:**
- 添加`backhaul_class`字段 [B, 1]
- 添加`vehicle_capacity`字段 [B, 1] (scaled to 1.0)
- 添加`capacity_original`字段 [B, 1] (unscaled)
- 实现demand scaling (demand_linehaul / capacity)
- 所有字段形状正确,包含batch dimension
- 代码注释清晰,说明每个字段的用途

**Files:**
- `VPRL/instance_decomposer.py` - `convert_to_tensordict()` 方法

**Implementation Details:**
```python
@staticmethod
def convert_to_tensordict(
    depot_coords: np.ndarray,
    customer_coords: np.ndarray,
    demands: np.ndarray,
    capacity: float,
    distance_limit: float) -> TensorDict:
    """
    Convert CVRP sub-problem to RL4CO TensorDict format
    
    Creates a complete TensorDict compatible with MTVRPGenerator,
    including all fields required when subsample=True.
    """
    num_customers = len(customer_coords)
    
    # Combine depot and customer coordinates
    locs = np.vstack([depot_coords.reshape(1, 2), customer_coords])
    
    # Demands: depot has 0 demand
    demand_linehaul = np.concatenate([[0.0], demands])
    
    # Scale demands by capacity (MTVRPGenerator expects scaled demands)
    demand_linehaul_scaled = demand_linehaul / capacity
    
    # Convert to tensors and add batch dimension
    td = TensorDict({
        'locs': torch.tensor(locs, dtype=torch.float32).unsqueeze(0),
        'demand_linehaul': torch.tensor(demand_linehaul_scaled, dtype=torch.float32).unsqueeze(0),
        'demand_backhaul': torch.zeros(1, num_customers + 1, dtype=torch.float32),
        'backhaul_class': torch.tensor([1.0], dtype=torch.float32).unsqueeze(0),  # Classic backhaul
        'distance_limit': torch.tensor([distance_limit], dtype=torch.float32).unsqueeze(0),
        'time_windows': torch.tensor(
            [[0.0, float('inf')]] * (num_customers + 1), 
            dtype=torch.float32
        ).unsqueeze(0),
        'service_time': torch.zeros(1, num_customers + 1, dtype=torch.float32),
        'vehicle_capacity': torch.tensor([1.0], dtype=torch.float32).unsqueeze(0),  # Scaled capacity
        'capacity_original': torch.tensor([capacity], dtype=torch.float32).unsqueeze(0),  # Unscaled
        'open_route': torch.tensor([False], dtype=torch.bool).unsqueeze(0),
        'speed': torch.tensor([1.0], dtype=torch.float32).unsqueeze(0),
    }, batch_size=[1])
    
    return td
```

---

## Task 4: 编写fix checking测试

编写测试验证修复后bug condition不再触发。

**Acceptance Criteria:**
- 测试在修复后的代码上通过
- 测试验证model.env.reset()成功(不抛出异常)
- 测试验证生成的解有效
- 测试使用与Task 1相同的test cases

**Files:**
- 更新 `tests/test_vprl_variant_preset_bug.py`

**Correctness Property:**
```python
# Fix checking test
@given(sub_problem=valid_cvrp_subproblem())
def test_fix_env_reset_succeeds_with_complete_tensordict(sub_problem):
    """
    验证修复后,当TensorDict包含所有必需字段时,
    model.env.reset(td)成功
    """
    # 使用修复后的convert_to_tensordict
    td = convert_to_tensordict(...)
    
    # 加载配置了subsample=True的模型
    model = load_model_with_subsample_true()
    
    # 应该成功(不抛出异常)
    td_reset = model.env.reset(td)
    assert td_reset is not None
    assert 'action_mask' in td_reset.keys()
```

---

## Task 5: 运行集成测试验证端到端流程

运行完整的VPRL解生成流程,验证所有depot都能成功生成解。

**Acceptance Criteria:**
- 运行`python test_vprl_solution_generation.py`成功
- 所有9个depot都成功生成解(不失败)
- 没有回退到纯GA_Java
- 生成的解数量符合预期(每个depot 5个解)
- 日志显示"Oversampling improvement"而不是错误

**Test Command:**
```bash
python test_vprl_solution_generation.py
```

**Expected Output:**
```
[INFO] Generating solutions for depot 1 (40 customers)
[INFO] Oversampling: generating 7 samples, will keep best 5
[INFO] Oversampling improvement: X.X%
✓ 成功生成 5 个解
...
[INFO] VRPL generation completed in X.XXs
[INFO] Generated 63 samples, kept 45
```

---

## Task 6: 添加单元测试验证字段完整性

编写单元测试验证convert_to_tensordict()创建的TensorDict包含所有必需字段。

**Acceptance Criteria:**
- 测试验证所有11个必需字段存在
- 测试验证每个字段的形状正确
- 测试验证demand scaling正确
- 测试验证capacity字段值正确

**Files:**
- 创建 `tests/test_instance_decomposer.py`

**Test Cases:**
```python
def test_convert_to_tensordict_has_all_required_fields():
    """验证TensorDict包含所有MTVRPGenerator期望的字段"""
    td = convert_to_tensordict(...)
    
    required_fields = [
        'locs', 'demand_linehaul', 'demand_backhaul',
        'backhaul_class', 'distance_limit', 'time_windows',
        'service_time', 'vehicle_capacity', 'capacity_original',
        'open_route', 'speed'
    ]
    
    for field in required_fields:
        assert field in td.keys(), f"Missing field: {field}"

def test_convert_to_tensordict_field_shapes():
    """验证每个字段的形状正确"""
    num_customers = 40
    td = convert_to_tensordict(...)
    
    assert td['locs'].shape == (1, num_customers + 1, 2)
    assert td['demand_linehaul'].shape == (1, num_customers + 1)
    assert td['vehicle_capacity'].shape == (1, 1)
    # ... 验证其他字段

def test_convert_to_tensordict_demand_scaling():
    """验证demand正确scaling"""
    capacity = 100.0
    demands = np.array([10, 20, 30])
    td = convert_to_tensordict(..., capacity=capacity, ...)
    
    # Scaled demands应该是原始demands除以capacity
    expected_scaled = torch.tensor([0.0, 0.1, 0.2, 0.3])
    assert torch.allclose(td['demand_linehaul'][0], expected_scaled)
    
    # vehicle_capacity应该是1.0 (scaled)
    assert td['vehicle_capacity'][0, 0] == 1.0
    
    # capacity_original应该是原始capacity
    assert td['capacity_original'][0, 0] == capacity
```

---

## Notes

- 所有测试应该使用pytest框架
- Property-based tests使用Hypothesis库
- 测试应该独立运行,不依赖外部状态
- 每个task完成后运行相关测试验证
- Task 3是核心修复,其他tasks是测试验证
