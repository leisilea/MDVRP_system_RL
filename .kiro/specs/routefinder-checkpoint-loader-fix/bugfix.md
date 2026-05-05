# Bugfix Requirements Document

## Introduction

修复 RouteFinder checkpoint 加载失败的问题。当运行 `python test_checkpoint_fix.py` 时，加载预训练的 checkpoint 文件会抛出 `_pickle.UnpicklingError`，错误信息为 "A load persistent id instruction was encountered, but no persistent_load function was specified"。这是因为当前的 `CompatibilityUnpickler` 类只实现了 `find_class` 方法来处理 TorchRL API 重命名，但缺少 `persistent_load` 方法来处理 PyTorch checkpoint 中的 persistent ID 指令。

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN 调用 `CompatibilityUnpickler(f).load()` 加载包含 persistent ID 指令的 checkpoint 文件 THEN 系统抛出 `_pickle.UnpicklingError: A load persistent id instruction was encountered, but no persistent_load function was specified`

1.2 WHEN checkpoint 文件中包含 PyTorch 的 persistent ID（用于存储张量和其他对象的引用）THEN unpickler 无法处理这些指令导致加载失败

### Expected Behavior (Correct)

2.1 WHEN 调用 `CompatibilityUnpickler(f).load()` 加载包含 persistent ID 指令的 checkpoint 文件 THEN 系统 SHALL 成功加载 checkpoint 并返回包含模型权重和超参数的字典

2.2 WHEN checkpoint 文件中包含 PyTorch 的 persistent ID THEN unpickler SHALL 正确处理这些 persistent ID 指令，使用 PyTorch 的默认 persistent_load 机制

### Unchanged Behavior (Regression Prevention)

3.1 WHEN checkpoint 文件包含 TorchRL 旧版 API 类名（如 CompositeSpec, BoundedTensorSpec 等）THEN 系统 SHALL CONTINUE TO 通过 `find_class` 方法将这些类名映射到新版 API

3.2 WHEN 加载不包含 persistent ID 指令的普通 pickle 对象 THEN 系统 SHALL CONTINUE TO 正常加载这些对象

3.3 WHEN checkpoint 加载成功后 THEN 系统 SHALL CONTINUE TO 返回包含 'hyper_parameters' 和其他标准 PyTorch Lightning checkpoint 键的字典
