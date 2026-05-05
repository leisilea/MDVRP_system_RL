# Bugfix Requirements Document

## Introduction

在使用 `torch.load()` 加载模型检查点时，当指定 `map_location` 参数将模型映射到 CUDA 设备时，会触发 RNG (Random Number Generator) 状态错误："RNG state must be a torch.ByteTensor"。

根据 PyTorch 社区讨论 (https://discuss.pytorch.org/t/statefuldataloader-restore-error-for-rng-must-be-a-torch-bytetensor/221998)，这是因为 RNG 状态在使用 `map_location` 时被错误地映射到了 CUDA 设备，但 PyTorch 要求 RNG 状态必须保持在 CPU 上。

该错误发生在 `VPRL/vprl_sampler.py` 第 220 行的 `torch.load()` 调用中。用户只需要模型能够正常加载和推理，不需要保留训练相关的 RNG 状态。

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN 使用 `torch.load(model_path, map_location=map_location)` 加载包含 RNG 状态的检查点，且 `map_location` 指向 CUDA 设备时 THEN 系统抛出 "RNG state must be a torch.ByteTensor" 错误

1.2 WHEN 检查点中包含 Lightning 的 RNG 状态数据（如 `rng_states`）且使用 `map_location` 参数时 THEN RNG 状态被错误地映射到 CUDA 设备导致加载失败

### Expected Behavior (Correct)

2.1 WHEN 使用 `torch.load()` 加载模型检查点时 THEN 系统 SHALL 成功加载模型权重而不触发 RNG 状态错误

2.2 WHEN 检查点中包含 RNG 状态数据时 THEN 系统 SHALL 跳过或正确处理 RNG 状态，确保模型可以正常用于推理

### Unchanged Behavior (Regression Prevention)

3.1 WHEN 加载不包含 RNG 状态的检查点时 THEN 系统 SHALL CONTINUE TO 正常加载模型

3.2 WHEN 加载 RouteFinder 模型或 POMO 模型时 THEN 系统 SHALL CONTINUE TO 正确初始化模型并加载权重

3.3 WHEN 模型加载成功后进行推理时 THEN 系统 SHALL CONTINUE TO 生成正确的预测结果

3.4 WHEN 使用 `map_location='cpu'` 加载模型时 THEN 系统 SHALL CONTINUE TO 正常工作
