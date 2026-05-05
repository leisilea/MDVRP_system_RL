# torch-load-rng-state-fix Bugfix Design

## Overview

该 bug 发生在使用 `torch.load()` 加载 PyTorch Lightning 检查点时，当指定 `map_location` 参数将模型映射到 CUDA 设备时，检查点中的 RNG (Random Number Generator) 状态被错误地映射到 CUDA 设备，导致 PyTorch 抛出 "RNG state must be a torch.ByteTensor" 错误。

修复策略是在加载检查点后，使用 `weights_only=False` 参数并添加自定义的 RNG 状态过滤逻辑，确保 RNG 状态保持在 CPU 上或直接跳过 RNG 状态的加载，因为推理场景不需要恢复训练时的随机数生成器状态。

## Glossary

- **Bug_Condition (C)**: 当使用 `torch.load(model_path, map_location=device)` 加载包含 RNG 状态的检查点，且 `map_location` 指向 CUDA 设备时触发
- **Property (P)**: 模型检查点应该成功加载，模型权重正确初始化，可以正常用于推理
- **Preservation**: 不包含 RNG 状态的检查点加载、使用 CPU 作为 map_location 的加载、以及模型推理功能必须保持不变
- **RNG State**: PyTorch 的随机数生成器状态，包括 CPU RNG、CUDA RNG 等，用于训练时的可重复性
- **map_location**: `torch.load()` 的参数，用于指定将张量加载到哪个设备（CPU 或 CUDA）
- **Lightning Checkpoint**: PyTorch Lightning 保存的检查点文件，包含模型权重、优化器状态、RNG 状态等训练相关数据

## Bug Details

### Bug Condition

该 bug 在使用 `torch.load()` 加载 Lightning 检查点时触发，当 `map_location` 参数指向 CUDA 设备（如 `'cuda:0'`）时，检查点中的 RNG 状态（通常存储在 `rng_states` 键下）会被映射到 CUDA 设备。然而，PyTorch 要求 RNG 状态必须是 CPU 上的 `torch.ByteTensor`，导致加载失败。

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type LoadCheckpointInput {
    model_path: str,
    map_location: str or torch.device,
    checkpoint_contains_rng: bool
  }
  OUTPUT: boolean
  
  RETURN input.checkpoint_contains_rng == True
         AND input.map_location IN ['cuda', 'cuda:0', 'cuda:1', ...]
         AND torch.load() attempts to restore RNG state
END FUNCTION
```

### Examples

- **Example 1**: 加载 RouteFinder 检查点到 CUDA
  - Input: `torch.load('routefinder.ckpt', map_location='cuda:0')`
  - Expected: 模型成功加载，权重在 CUDA 上
  - Actual: 抛出 "RNG state must be a torch.ByteTensor" 错误

- **Example 2**: 加载 POMO 检查点到 CUDA
  - Input: `torch.load('pomo_model.ckpt', map_location='cuda:0')`
  - Expected: 模型成功加载，可以进行推理
  - Actual: 抛出 RNG 状态错误

- **Example 3**: 加载包含 Lightning 元数据的检查点
  - Input: 检查点包含 `state_dict`, `hyper_parameters`, `rng_states` 等键
  - Expected: 只加载模型权重和超参数，跳过 RNG 状态
  - Actual: 尝试恢复 RNG 状态导致错误

- **Edge Case**: 加载到 CPU 应该正常工作
  - Input: `torch.load('model.ckpt', map_location='cpu')`
  - Expected: 正常加载，包括 RNG 状态（如果需要）
  - Actual: 应该继续正常工作

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- 加载不包含 RNG 状态的检查点必须继续正常工作
- 使用 `map_location='cpu'` 加载检查点必须继续正常工作
- 模型加载后的推理功能（`model.policy()`, `model.env.get_reward()` 等）必须保持不变
- RouteFinder 和 POMO 模型的初始化和权重加载逻辑必须保持不变
- 现有的 TorchRL 兼容性补丁（CompatibilityUnpickler）必须继续工作

**Scope:**
所有不涉及"使用 CUDA 作为 map_location 加载包含 RNG 状态的检查点"的场景都应该完全不受影响。这包括:
- 加载到 CPU 的所有操作
- 不包含 RNG 状态的检查点加载
- 模型推理和预测功能
- 其他设备映射场景

## Hypothesized Root Cause

基于 PyTorch 社区讨论和错误信息，最可能的原因是:

1. **RNG 状态设备映射错误**: `torch.load()` 的 `map_location` 参数会将检查点中的所有张量（包括 RNG 状态）映射到指定设备，但 PyTorch 内部要求 RNG 状态必须保持在 CPU 上作为 `ByteTensor`

2. **Lightning 检查点结构**: Lightning 保存的检查点包含训练相关的元数据（如 `rng_states`），这些数据在推理时不需要，但 `torch.load()` 或 `load_from_checkpoint()` 会尝试恢复它们

3. **缺少 RNG 状态过滤**: 当前代码直接使用 `torch.load()` 或 `load_from_checkpoint()`，没有过滤或特殊处理 RNG 状态

4. **设备不匹配**: 检查点可能在不同的 CUDA 设备上训练（如 `cuda:1`），加载到 `cuda:0` 时 RNG 状态的设备映射出现问题

## Correctness Properties

Property 1: Bug Condition - RNG State Handling for CUDA Loading

_For any_ checkpoint loading operation where the checkpoint contains RNG state and map_location points to a CUDA device, the fixed loading function SHALL successfully load the model weights while either skipping RNG state restoration or ensuring RNG state remains on CPU, allowing the model to be used for inference without errors.

**Validates: Requirements 2.1, 2.2**

Property 2: Preservation - Non-CUDA and Non-RNG Loading

_For any_ checkpoint loading operation that does NOT involve both RNG state and CUDA map_location (e.g., loading to CPU, loading checkpoints without RNG state, or loading minimal checkpoints), the fixed code SHALL produce exactly the same behavior as the original code, preserving all existing model loading and inference functionality.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

## Fix Implementation

### Changes Required

假设我们的根因分析正确，需要进行以下修改:

**File**: `VPRL/vprl_sampler.py`

**Function**: `_load_model` (lines 195-220)

**Specific Changes**:

1. **添加 RNG 状态过滤逻辑**: 在调用 `torch.load()` 时，添加自定义的加载逻辑来跳过或正确处理 RNG 状态
   - 使用 `weights_only=False` 参数（如果 PyTorch 版本支持）
   - 或者先加载检查点，然后手动删除 RNG 状态相关的键

2. **修改 map_location 处理**: 对于包含 RNG 状态的检查点，先加载到 CPU，提取模型权重，然后再将模型移动到目标设备

3. **使用 Lightning 的 load_from_checkpoint 参数**: 如果使用 `load_from_checkpoint()`，添加参数来跳过 RNG 状态恢复

4. **添加错误处理**: 捕获 RNG 状态相关的错误，提供更清晰的错误信息或自动回退到安全的加载方式

5. **保持兼容性**: 确保修改不影响现有的 TorchRL 兼容性补丁和其他加载逻辑

**具体实现方案**:

方案 A: 使用 `weights_only=False` 和手动过滤
```python
# Load checkpoint to CPU first
checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)

# Remove RNG states if present
if 'rng_states' in checkpoint:
    del checkpoint['rng_states']

# Then load model with cleaned checkpoint
```

方案 B: 使用临时文件和重新保存
```python
# Load to CPU, clean, save to temp, then load to target device
checkpoint = torch.load(model_path, map_location='cpu')
# Clean RNG states
# Save to temp file
# Load from temp file with target map_location
```

方案 C: 修改 load_from_checkpoint 调用
```python
# Use Lightning's built-in parameter to skip RNG restoration
model = Model.load_from_checkpoint(
    model_path,
    map_location=map_location,
    # Add parameter to skip RNG state restoration if available
)
```

推荐使用方案 A，因为它最简单且不需要临时文件。

## Testing Strategy

### Validation Approach

测试策略采用两阶段方法：首先在未修复的代码上运行测试以确认 bug 存在并理解根因，然后验证修复后的代码能够正确加载模型并保持现有功能不变。

### Exploratory Bug Condition Checking

**Goal**: 在实施修复之前，在未修复的代码上演示 bug。确认或反驳根因分析。如果反驳，需要重新假设根因。

**Test Plan**: 编写测试来模拟使用不同 `map_location` 参数加载包含 RNG 状态的检查点。在未修复的代码上运行这些测试以观察失败并理解根因。

**Test Cases**:
1. **CUDA Loading Test**: 使用 `map_location='cuda:0'` 加载包含 RNG 状态的检查点（在未修复代码上会失败）
2. **CPU Loading Test**: 使用 `map_location='cpu'` 加载相同检查点（应该成功，用于对比）
3. **RouteFinder Model Test**: 测试 RouteFinder 模型的加载（在未修复代码上会失败）
4. **POMO Model Test**: 测试 POMO 模型的加载（在未修复代码上会失败）

**Expected Counterexamples**:
- 使用 CUDA map_location 时抛出 "RNG state must be a torch.ByteTensor" 错误
- 可能的原因：RNG 状态被映射到 CUDA 设备，违反了 PyTorch 的要求

### Fix Checking

**Goal**: 验证对于所有满足 bug 条件的输入，修复后的函数产生预期行为。

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  result := _load_model_fixed(input.model_path, input.map_location)
  ASSERT result.success == True
  ASSERT result.model is not None
  ASSERT result.model can perform inference
END FOR
```

### Preservation Checking

**Goal**: 验证对于所有不满足 bug 条件的输入，修复后的函数产生与原函数相同的结果。

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT _load_model_original(input) == _load_model_fixed(input)
END FOR
```

**Testing Approach**: 推荐使用基于属性的测试进行保留性检查，因为:
- 它自动生成跨输入域的多个测试用例
- 它能捕获手动单元测试可能遗漏的边缘情况
- 它为所有非 bug 输入提供强有力的保证，确保行为不变

**Test Plan**: 首先在未修复的代码上观察 CPU 加载和无 RNG 状态检查点的行为，然后编写基于属性的测试来捕获该行为。

**Test Cases**:
1. **CPU Loading Preservation**: 验证使用 `map_location='cpu'` 加载检查点继续正常工作
2. **Non-RNG Checkpoint Preservation**: 验证加载不包含 RNG 状态的检查点继续正常工作
3. **Inference Preservation**: 验证模型加载后的推理功能（生成解决方案、计算成本）继续正常工作
4. **TorchRL Compatibility Preservation**: 验证现有的 TorchRL 兼容性补丁继续工作

### Unit Tests

- 测试使用不同 `map_location` 参数加载检查点（'cpu', 'cuda:0', 'cuda:1'）
- 测试加载包含和不包含 RNG 状态的检查点
- 测试 RouteFinder 和 POMO 模型的加载
- 测试边缘情况（检查点文件不存在、损坏的检查点等）

### Property-Based Tests

- 生成随机的 map_location 参数（CPU 和各种 CUDA 设备）并验证加载成功
- 生成随机的检查点结构（有/无 RNG 状态）并验证正确处理
- 测试加载后的模型在多种场景下能够正常推理

### Integration Tests

- 测试完整的 VPRL 工作流程，从加载模型到生成解决方案
- 测试在不同设备配置下的模型加载和推理
- 测试与 GA_Java 集成时的模型加载和使用
