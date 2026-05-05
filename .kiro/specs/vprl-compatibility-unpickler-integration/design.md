# VPRL CompatibilityUnpickler 集成 Bugfix 设计

## Overview

本 bugfix 解决 VPRL sampler 在加载包含旧版 TorchRL API 类名的 RouteFinder checkpoint 时失败的问题。虽然项目中已经实现了 CompatibilityUnpickler 补丁来处理 TorchRL API 重命名(CompositeSpec → Composite 等),但 VPRL sampler 的 `_load_model()` 方法没有应用该补丁,导致 PyTorch Lightning 的 `load_from_checkpoint()` 使用标准 pickle 反序列化时失败。

修复策略是在 VPRL sampler 调用 `load_from_checkpoint()` 前,通过 monkey-patch `torch.serialization._load` 函数注入 CompatibilityUnpickler 的类名映射逻辑,确保旧版 checkpoint 能够成功加载。这是一个最小化、非侵入式的修复,不影响新版 checkpoint 的加载,也不改变现有的错误处理和回退逻辑。

## Glossary

- **Bug_Condition (C)**: 当 VPRL sampler 尝试加载包含旧版 TorchRL API 类名(CompositeSpec、BoundedTensorSpec 等)的 RouteFinder checkpoint 时触发
- **Property (P)**: 补丁应用后,旧版 checkpoint 能够成功加载,类名自动映射到新版 API
- **Preservation**: 新版 checkpoint 加载、错误处理、POMO 回退、设备映射等现有行为保持不变
- **CompatibilityUnpickler**: 位于 `RL4CO_Integration/routefinder/fix_checkpoint_loader.py` 的自定义 Unpickler,实现 TorchRL API 类名映射
- **torch.serialization._load**: PyTorch 内部函数,负责从 zip 文件中反序列化 checkpoint 数据
- **RouteFinderBase.load_from_checkpoint()**: PyTorch Lightning 提供的类方法,内部调用 `torch.load()` 加载 checkpoint

## Bug Details

### Bug Condition

当 VPRL sampler 调用 `RouteFinderBase.load_from_checkpoint()` 加载使用旧版 TorchRL API 保存的 checkpoint 时,PyTorch Lightning 内部使用标准 `torch.load()` 进行反序列化。在反序列化过程中,pickle 尝试查找 `torchrl.data.tensor_specs.CompositeSpec` 等类,但这些类在新版 TorchRL 中已被重命名,导致 AttributeError。

**Formal Specification:**
```
FUNCTION isBugCondition(checkpoint_path, loading_context)
  INPUT: 
    checkpoint_path: str - 模型 checkpoint 文件路径
    loading_context: dict - 加载上下文,包含 {is_routefinder: bool, has_old_api_classes: bool}
  OUTPUT: boolean
  
  RETURN os.path.exists(checkpoint_path)
         AND loading_context.is_routefinder == True
         AND loading_context.has_old_api_classes == True
         AND NOT compatibilityPatchApplied()
END FUNCTION

FUNCTION compatibilityPatchApplied()
  OUTPUT: boolean
  RETURN torch.serialization._load has been monkey-patched 
         to inject CompatibilityUnpickler logic
END FUNCTION
```

### Examples

- **Example 1**: 加载 `epoch=19-step=1140.ckpt` (包含 CompositeSpec)
  - 预期: 成功加载,CompositeSpec 映射到 Composite
  - 实际(未修复): AttributeError: module 'torchrl.data.tensor_specs' has no attribute 'CompositeSpec'

- **Example 2**: 加载包含 BoundedTensorSpec 的 checkpoint
  - 预期: 成功加载,BoundedTensorSpec 映射到 Bounded
  - 实际(未修复): AttributeError

- **Example 3**: 加载使用新版 API 保存的 checkpoint (包含 Composite)
  - 预期: 正常加载,不受补丁影响
  - 实际(未修复): 正常加载(无 bug)

- **Edge Case**: 加载不存在的文件路径
  - 预期: 返回 False,记录错误日志
  - 实际(未修复): 返回 False(现有错误处理正常)

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- 加载使用新版 TorchRL API 的 checkpoint 必须继续正常工作
- 文件不存在或路径错误时的错误处理逻辑必须保持不变
- POMO 模型的回退加载逻辑必须保持不变
- 模型加载后的 eval 模式设置和设备映射必须保持不变
- 重复加载同一模型的跳过逻辑必须保持不变
- 所有日志记录行为必须保持不变

**Scope:**
所有不涉及加载包含旧版 TorchRL API 类名的 RouteFinder checkpoint 的输入都应完全不受此修复影响。这包括:
- 新版 checkpoint 的加载
- POMO 模型的加载
- 错误路径的处理
- 设备映射和模型初始化
- 日志记录

## Hypothesized Root Cause

基于 bug 描述和代码分析,最可能的原因是:

1. **缺少补丁应用**: VPRL sampler 的 `_load_model()` 方法直接调用 `RouteFinderBase.load_from_checkpoint()`,没有应用 CompatibilityUnpickler 补丁
   - PyTorch Lightning 的 `load_from_checkpoint()` 内部使用标准 `torch.load()`
   - 标准 pickle.Unpickler 无法处理 TorchRL API 重命名

2. **Monkey-patch 时机错误**: 现有的 `fix_checkpoint_loader.py` 提供了 `load_checkpoint_compatible()` 函数,但该函数只在直接调用时有效
   - VPRL sampler 使用 PyTorch Lightning 的高层 API,无法直接使用该函数
   - 需要在调用 `load_from_checkpoint()` 前全局应用补丁

3. **补丁作用域问题**: 即使应用了补丁,也需要确保在 PyTorch Lightning 内部调用 `torch.load()` 时生效
   - 需要 monkey-patch `torch.serialization._load` 而不是 `torch.load`
   - 补丁必须在整个加载过程中保持有效

## Correctness Properties

Property 1: Bug Condition - 旧版 Checkpoint 成功加载

_For any_ RouteFinder checkpoint 文件,如果该文件包含旧版 TorchRL API 类名(CompositeSpec、BoundedTensorSpec、UnboundedContinuousTensorSpec、UnboundedDiscreteTensorSpec),当 VPRL sampler 调用 `_load_model()` 时,修复后的代码 SHALL 成功加载该 checkpoint,自动将旧版类名映射到新版类名(Composite、Bounded、UnboundedContinuous、UnboundedDiscrete),并返回 True。

**Validates: Requirements 2.1, 2.2, 2.3**

Property 2: Preservation - 新版 Checkpoint 和其他行为不变

_For any_ 输入场景,如果该场景不涉及加载包含旧版 TorchRL API 类名的 RouteFinder checkpoint(包括新版 checkpoint、POMO 模型、错误路径、重复加载等),修复后的代码 SHALL 产生与原始代码完全相同的行为,保持所有现有功能不变,包括错误处理、日志记录、设备映射和模型初始化。

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

## Fix Implementation

### Changes Required

假设我们的根因分析正确:

**File**: `VPRL/vprl_sampler.py`

**Function**: `_load_model()`

**Specific Changes**:
1. **导入 CompatibilityUnpickler**: 在函数开始处导入必要的模块
   - `from RL4CO_Integration.routefinder.fix_checkpoint_loader import CompatibilityUnpickler`
   - 或使用相对导入(取决于项目结构)

2. **Monkey-patch torch.serialization._load**: 在调用 `load_from_checkpoint()` 前应用补丁
   - 保存原始 `torch.serialization._load` 函数
   - 创建包装函数,注入 CompatibilityUnpickler 的 find_class 逻辑
   - 临时替换 `torch.serialization._load`

3. **在 try-finally 块中恢复原始函数**: 确保补丁不会影响其他代码
   - 在 finally 块中恢复 `torch.serialization._load`
   - 即使加载失败也要恢复

4. **应用补丁到 RouteFinder 加载**: 只在加载 RouteFinder 模型时应用补丁
   - POMO 模型加载不需要补丁(保持现有行为)

5. **保持所有现有逻辑不变**: 不修改错误处理、日志记录、设备映射等
   - 补丁应该是透明的,不影响其他代码路径

### Implementation Pseudocode

```python
def _load_model(self, model_path: str) -> bool:
    try:
        # ... existing checks (file exists, already loaded) ...
        
        # Try to load as RouteFinder model with compatibility patch
        try:
            from routefinder.models import RouteFinderBase
            import torch.serialization
            import pickle
            
            # Save original _load function
            _original_load = torch.serialization._load
            
            # Create patched version with CompatibilityUnpickler logic
            def _patched_load(zip_file, map_location, pickle_module, 
                            pickle_file='data.pkl', overall_storage=None, 
                            **pickle_load_args):
                original_unpickler = pickle_module.Unpickler
                
                class PatchedUnpickler(original_unpickler):
                    def find_class(self, mod_name, name):
                        # TorchRL API remappings
                        if mod_name == 'torchrl.data.tensor_specs':
                            if name == 'CompositeSpec':
                                from torchrl.data.tensor_specs import Composite
                                return Composite
                            elif name == 'BoundedTensorSpec':
                                from torchrl.data.tensor_specs import Bounded
                                return Bounded
                            # ... other mappings ...
                        return super().find_class(mod_name, name)
                
                try:
                    pickle_module.Unpickler = PatchedUnpickler
                    return _original_load(zip_file, map_location, pickle_module, 
                                        pickle_file, overall_storage, **pickle_load_args)
                finally:
                    pickle_module.Unpickler = original_unpickler
            
            # Apply patch
            try:
                torch.serialization._load = _patched_load
                self.model = RouteFinderBase.load_from_checkpoint(
                    model_path,
                    map_location=map_location
                )
                self.logger.info("Loaded as RouteFinder model")
            finally:
                # Restore original function
                torch.serialization._load = _original_load
                
        except (ImportError, Exception) as e:
            # ... existing POMO fallback logic (unchanged) ...
        
        # ... existing model.eval(), device mapping, logging (unchanged) ...
        
    except Exception as e:
        # ... existing error handling (unchanged) ...
```

## Testing Strategy

### Validation Approach

测试策略遵循两阶段方法:首先在未修复的代码上运行探索性测试,观察 bug 的具体表现并确认根因分析;然后验证修复后的代码能够正确处理旧版 checkpoint,同时保持所有其他行为不变。

### Exploratory Bug Condition Checking

**Goal**: 在实施修复前,在未修复的代码上运行测试,观察 bug 的具体失败模式,确认或反驳根因分析。如果反驳,需要重新假设根因。

**Test Plan**: 编写测试用例,使用包含旧版 TorchRL API 类名的真实 checkpoint 文件调用 `_load_model()`,在未修复的代码上运行,观察 AttributeError 的具体堆栈跟踪和失败点。

**Test Cases**:
1. **旧版 CompositeSpec Checkpoint**: 使用 `epoch=19-step=1140.ckpt` 调用 `_load_model()` (将在未修复代码上失败)
2. **旧版 BoundedTensorSpec Checkpoint**: 如果有包含 BoundedTensorSpec 的 checkpoint,测试加载 (将在未修复代码上失败)
3. **新版 Checkpoint**: 使用新版 API 保存的 checkpoint 测试加载 (应该在未修复代码上成功)
4. **不存在的文件**: 测试错误处理逻辑 (应该在未修复代码上正常返回 False)

**Expected Counterexamples**:
- AttributeError: module 'torchrl.data.tensor_specs' has no attribute 'CompositeSpec'
- 堆栈跟踪应该显示错误发生在 PyTorch Lightning 的 `load_from_checkpoint()` 内部调用 `torch.load()` 时
- 可能的根因: 缺少 CompatibilityUnpickler 补丁,标准 pickle.Unpickler 无法处理类名重命名

### Fix Checking

**Goal**: 验证对于所有满足 bug condition 的输入(包含旧版 TorchRL API 类名的 RouteFinder checkpoint),修复后的函数能够成功加载模型。

**Pseudocode:**
```
FOR ALL checkpoint_path WHERE isBugCondition(checkpoint_path, loading_context) DO
  result := _load_model_fixed(checkpoint_path)
  ASSERT result == True
  ASSERT self.model is not None
  ASSERT self.model is in eval mode
  ASSERT self.model is on correct device
END FOR
```

**Test Cases**:
1. 使用包含 CompositeSpec 的真实 checkpoint 测试
2. 使用包含 BoundedTensorSpec 的 checkpoint 测试(如果有)
3. 使用包含多种旧版类名的 checkpoint 测试
4. 验证加载后模型可以正常进行推理

### Preservation Checking

**Goal**: 验证对于所有不满足 bug condition 的输入(新版 checkpoint、POMO 模型、错误路径等),修复后的函数产生与原始函数完全相同的结果。

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT _load_model_original(input) == _load_model_fixed(input)
END FOR
```

**Testing Approach**: 推荐使用 property-based testing 进行 preservation checking,因为:
- 它可以自动生成大量测试用例覆盖输入域
- 它可以捕获手动单元测试可能遗漏的边界情况
- 它提供强有力的保证,确保所有非 buggy 输入的行为保持不变

**Test Plan**: 首先在未修复的代码上观察各种输入的行为(新版 checkpoint、POMO 模型、错误路径等),然后编写 property-based tests 捕获这些行为,验证修复后行为一致。

**Test Cases**:
1. **新版 Checkpoint Preservation**: 观察未修复代码加载新版 checkpoint 的行为,验证修复后行为相同
2. **POMO 模型 Preservation**: 观察未修复代码的 POMO 回退逻辑,验证修复后逻辑不变
3. **错误处理 Preservation**: 测试文件不存在、路径错误等场景,验证错误处理逻辑不变
4. **重复加载 Preservation**: 测试加载同一模型两次,验证跳过逻辑不变
5. **设备映射 Preservation**: 验证模型加载到正确设备的逻辑不变
6. **日志记录 Preservation**: 验证所有日志消息保持不变

### Unit Tests

- 测试 monkey-patch 的应用和恢复逻辑
- 测试每种旧版类名的映射(CompositeSpec、BoundedTensorSpec 等)
- 测试补丁在异常情况下的恢复(加载失败时 finally 块执行)
- 测试新版 checkpoint 不受补丁影响
- 测试 POMO 回退逻辑不受影响

### Property-Based Tests

- 生成随机的 checkpoint 路径和加载场景,验证错误处理的一致性
- 生成随机的设备配置,验证设备映射逻辑的一致性
- 测试补丁应用和恢复在各种场景下的正确性
- 验证日志记录在所有场景下的一致性

### Integration Tests

- 测试完整的 VPRL sampler 工作流:加载旧版 checkpoint → 生成解 → 验证解的质量
- 测试在真实 MDVRP 实例上使用旧版 checkpoint 的端到端流程
- 测试混合使用新旧版 checkpoint 的场景
- 测试补丁不影响其他使用 torch.load 的代码
