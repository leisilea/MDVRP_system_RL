# RouteFinder Checkpoint Loader 修复设计文档

## Overview

修复 RouteFinder checkpoint 加载器中缺少 `persistent_load` 方法的问题。当前的 `CompatibilityUnpickler` 只实现了 `find_class` 来处理 TorchRL API 重命名，但 PyTorch checkpoint 使用 persistent ID 机制来存储张量引用，导致加载时抛出 `_pickle.UnpicklingError`。修复方案是在 `CompatibilityUnpickler` 中添加 `persistent_load` 方法，委托给父类的默认实现，同时保持现有的 `find_class` 功能。

## Glossary

- **Bug_Condition (C)**: checkpoint 文件包含 persistent ID 指令（PyTorch 用于存储张量引用的机制）
- **Property (P)**: checkpoint 成功加载并返回包含模型权重和超参数的字典
- **Preservation**: 现有的 `find_class` 方法处理 TorchRL API 重命名的功能必须保持不变
- **CompatibilityUnpickler**: 位于 `RL4CO_Integration/routefinder/fix_checkpoint_loader.py` 的自定义 unpickler 类，用于处理 TorchRL API 变化
- **persistent_load**: pickle 协议中用于处理 persistent ID 的回调方法，PyTorch 使用它来加载张量数据
- **persistent ID**: pickle 中的特殊指令，用于引用外部存储的对象（如大型张量），而不是直接序列化到 pickle 流中

## Bug Details

### Bug Condition

当 checkpoint 文件包含 PyTorch 的 persistent ID 指令时，`CompatibilityUnpickler` 无法处理这些指令。PyTorch 在保存 checkpoint 时使用 persistent ID 机制来高效存储张量数据，但当前的 unpickler 没有实现 `persistent_load` 方法来处理这些指令。

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type (file_handle, checkpoint_path)
  OUTPUT: boolean
  
  RETURN checkpoint_contains_persistent_ids(input.file_handle)
         AND CompatibilityUnpickler.persistent_load is None
         AND unpickler_encounters_PERSID_opcode(input.file_handle)
END FUNCTION
```

### Examples

- **Example 1**: 加载 `routefinder/checkpoints/100/rf-transformer.ckpt` 时，unpickler 遇到 PERSID opcode（persistent ID 指令），但 `CompatibilityUnpickler` 没有 `persistent_load` 方法，抛出 `_pickle.UnpicklingError: A load persistent id instruction was encountered, but no persistent_load function was specified`

- **Example 2**: 加载包含模型权重张量的 PyTorch Lightning checkpoint 时，张量以 persistent ID 形式存储，unpickler 无法解析这些引用，导致加载失败

- **Example 3**: 运行 `python test_checkpoint_fix.py` 时，在 `CompatibilityUnpickler(f).load()` 调用处失败，无法获取 checkpoint 字典

- **Edge Case**: 如果 checkpoint 文件不包含 persistent ID（纯 Python 对象的 pickle），则不会触发此 bug，但这种情况在 PyTorch checkpoint 中极为罕见

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- `find_class` 方法必须继续正确处理 TorchRL API 重命名（CompositeSpec → Composite, BoundedTensorSpec → Bounded 等）
- 加载不包含 persistent ID 的普通 pickle 对象时，行为必须保持不变
- 成功加载后返回的 checkpoint 字典结构（包含 'hyper_parameters', 'state_dict' 等键）必须保持不变

**Scope:**
所有不涉及 persistent ID 处理的输入应完全不受此修复影响。这包括:
- TorchRL 类名重映射逻辑
- 普通 Python 对象的反序列化
- checkpoint 字典的结构和内容

## Hypothesized Root Cause

基于 bug 描述和错误信息，最可能的问题是:

1. **缺少 persistent_load 方法**: `CompatibilityUnpickler` 继承自 `pickle.Unpickler`，但只覆盖了 `find_class` 方法。当 unpickler 遇到 PERSID 或 BINPERSID opcode 时，会调用 `persistent_load` 方法，但该方法在当前实现中未定义

2. **PyTorch checkpoint 格式**: PyTorch 使用 `torch.save()` 保存 checkpoint 时，会使用 persistent ID 机制来存储张量。这些 persistent ID 需要通过 `persistent_load` 方法来解析

3. **pickle 协议要求**: pickle 协议规定，如果 pickle 流中包含 persistent ID 指令，unpickler 必须提供 `persistent_load` 方法来处理这些指令，否则会抛出错误

## Correctness Properties

Property 1: Bug Condition - Persistent ID 处理

_For any_ checkpoint 文件输入，如果该文件包含 persistent ID 指令（isBugCondition 返回 true），修复后的 CompatibilityUnpickler SHALL 成功加载 checkpoint，通过实现 persistent_load 方法来处理这些指令，并返回包含模型权重和超参数的完整 checkpoint 字典。

**Validates: Requirements 2.1, 2.2**

Property 2: Preservation - find_class 功能保持不变

_For any_ checkpoint 文件输入，无论是否包含 persistent ID，修复后的 CompatibilityUnpickler SHALL 继续通过 find_class 方法正确处理 TorchRL API 重命名，保持现有的类名映射功能（CompositeSpec → Composite 等）完全不变。

**Validates: Requirements 3.1, 3.2, 3.3**

## Fix Implementation

### Changes Required

假设我们的根因分析正确:

**File**: `RL4CO_Integration/routefinder/fix_checkpoint_loader.py`

**Class**: `CompatibilityUnpickler`

**Specific Changes**:
1. **添加 persistent_load 方法**: 在 `CompatibilityUnpickler` 类中添加 `persistent_load` 方法
   - 该方法接受一个 persistent ID 参数
   - 委托给父类 `pickle.Unpickler` 的默认 persistent_load 实现
   - 或者直接返回 persistent ID，让 PyTorch 的加载机制处理

2. **实现方式选项 A - 委托给父类**: 
   ```python
   def persistent_load(self, pid):
       return super().persistent_load(pid)
   ```

3. **实现方式选项 B - 直接返回 PID**: 
   ```python
   def persistent_load(self, pid):
       return pid
   ```

4. **验证兼容性**: 确保添加 persistent_load 后，find_class 方法仍然正常工作

5. **测试**: 使用 `test_checkpoint_fix.py` 验证修复后的加载器能成功加载 checkpoint

## Testing Strategy

### Validation Approach

测试策略采用两阶段方法：首先在未修复的代码上运行探索性测试以确认 bug 和根因，然后验证修复后的代码能正确处理 persistent ID 并保持现有功能。

### Exploratory Bug Condition Checking

**Goal**: 在实现修复之前，在未修复的代码上运行测试以确认 bug。验证根因假设（缺少 persistent_load 方法）。如果假设被推翻，需要重新分析根因。

**Test Plan**: 编写测试来加载包含 persistent ID 的 checkpoint 文件，并捕获异常。在未修复的代码上运行这些测试，观察失败模式并确认错误信息。

**Test Cases**:
1. **Basic Checkpoint Load Test**: 尝试加载 `routefinder/checkpoints/100/rf-transformer.ckpt`（将在未修复代码上失败，抛出 UnpicklingError）
2. **Persistent ID Detection Test**: 检查 checkpoint 文件是否包含 PERSID opcode（将确认 persistent ID 的存在）
3. **Method Existence Test**: 验证 `CompatibilityUnpickler` 是否有 `persistent_load` 方法（将在未修复代码上返回 False）
4. **Error Message Verification**: 确认错误信息为 "A load persistent id instruction was encountered, but no persistent_load function was specified"（将在未修复代码上匹配）

**Expected Counterexamples**:
- Checkpoint 加载失败，抛出 `_pickle.UnpicklingError`
- 可能的原因: 缺少 persistent_load 方法，pickle 协议要求该方法存在，PyTorch checkpoint 格式依赖 persistent ID

### Fix Checking

**Goal**: 验证对于所有包含 persistent ID 的 checkpoint 输入，修复后的函数能产生预期行为（成功加载）。

**Pseudocode:**
```
FOR ALL checkpoint_file WHERE isBugCondition(checkpoint_file) DO
  result := load_checkpoint_compatible_fixed(checkpoint_file)
  ASSERT result is dict
  ASSERT 'hyper_parameters' in result OR 'state_dict' in result
  ASSERT no exception raised
END FOR
```

### Preservation Checking

**Goal**: 验证对于所有不涉及 persistent ID 处理的输入，修复后的函数产生与原函数相同的结果。

**Pseudocode:**
```
FOR ALL input WHERE NOT requires_persistent_load_change(input) DO
  ASSERT load_checkpoint_compatible_original(input) = load_checkpoint_compatible_fixed(input)
END FOR
```

**Testing Approach**: 推荐使用基于属性的测试进行保持性检查，因为:
- 它自动生成许多测试用例，覆盖输入域
- 它能捕获手动单元测试可能遗漏的边缘情况
- 它为所有非 bug 输入提供强有力的保证，确保行为不变

**Test Plan**: 首先在未修复的代码上观察 find_class 方法的行为（处理 TorchRL API 重命名），然后编写基于属性的测试来验证修复后该行为保持不变。

**Test Cases**:
1. **TorchRL API Remapping Preservation**: 观察未修复代码能正确处理 CompositeSpec → Composite 映射，然后验证修复后此功能继续工作
2. **Other Class Remapping Preservation**: 观察未修复代码能处理 BoundedTensorSpec, UnboundedContinuousTensorSpec 等映射，验证修复后保持不变
3. **Checkpoint Structure Preservation**: 观察未修复代码（如果能加载不含 persistent ID 的 checkpoint）返回的字典结构，验证修复后结构相同
4. **Non-PyTorch Pickle Preservation**: 测试加载普通 Python 对象的 pickle 文件，验证行为不变

### Unit Tests

- 测试 `persistent_load` 方法能正确处理 persistent ID
- 测试 `find_class` 方法在添加 `persistent_load` 后仍然正确工作
- 测试加载包含 persistent ID 的 checkpoint 文件成功
- 测试加载后的 checkpoint 字典包含预期的键（hyper_parameters, state_dict 等）
- 测试边缘情况：空 persistent ID, 无效 persistent ID

### Property-Based Tests

- 生成随机的 TorchRL 类名，验证 find_class 映射在修复后保持一致
- 生成不同结构的 checkpoint 文件，验证加载行为的一致性
- 测试在多种场景下 persistent_load 和 find_class 的交互

### Integration Tests

- 完整流程测试：加载真实的 RouteFinder checkpoint 文件
- 测试加载后使用 checkpoint 初始化模型
- 测试 `save_fixed_checkpoint` 函数能正确转换和保存 checkpoint
- 验证修复后的 checkpoint 能被标准 PyTorch 加载器加载
