# Bugfix Requirements Document

## Introduction

VPRL sampler 在加载 RouteFinder checkpoint 模型时失败,错误信息为 "module 'torchrl.data.tensor_specs' has no attribute 'CompositeSpec'"。这是因为旧版 checkpoint 使用了已被重命名的 TorchRL API 类名(如 CompositeSpec → Composite)。虽然项目中已经实现了 CompatibilityUnpickler 补丁来处理这个问题,但 VPRL sampler 没有应用该补丁,导致模型加载失败并回退到纯 GA 算法,无法利用 RL 初始化生成高质量解。

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN VPRL sampler 调用 `RouteFinderBase.load_from_checkpoint()` 加载包含旧版 TorchRL API 类名的 checkpoint THEN 系统抛出 AttributeError: "module 'torchrl.data.tensor_specs' has no attribute 'CompositeSpec'"

1.2 WHEN 模型加载失败 THEN 系统记录警告 "[WARNING] Failed to load RL4CO model" 并回退到纯 GA 算法,不使用 RL 初始化

1.3 WHEN PyTorch Lightning 内部使用标准 torch.load 反序列化 checkpoint THEN 遇到 CompositeSpec、BoundedTensorSpec 等旧版类名时无法找到对应的类定义

### Expected Behavior (Correct)

2.1 WHEN VPRL sampler 加载包含旧版 TorchRL API 类名的 checkpoint THEN 系统 SHALL 在调用 `load_from_checkpoint()` 前应用 CompatibilityUnpickler 补丁,成功加载模型

2.2 WHEN CompatibilityUnpickler 补丁被应用 THEN 系统 SHALL 自动将旧版类名(CompositeSpec、BoundedTensorSpec、UnboundedContinuousTensorSpec、UnboundedDiscreteTensorSpec)映射到新版类名(Composite、Bounded、UnboundedContinuous、UnboundedDiscrete)

2.3 WHEN 模型成功加载 THEN VPRL sampler SHALL 正常初始化并使用 RL 模型生成高质量初始解,不回退到纯 GA

### Unchanged Behavior (Regression Prevention)

3.1 WHEN VPRL sampler 加载使用新版 TorchRL API 的 checkpoint THEN 系统 SHALL CONTINUE TO 正常加载模型,不受补丁影响

3.2 WHEN 模型文件不存在或路径错误 THEN 系统 SHALL CONTINUE TO 记录错误并返回 False,保持现有错误处理逻辑

3.3 WHEN 加载 POMO 模型(非 RouteFinder 模型) THEN 系统 SHALL CONTINUE TO 正常回退到 POMO 加载逻辑

3.4 WHEN 模型加载成功后 THEN 系统 SHALL CONTINUE TO 将模型设置为 eval 模式并移动到配置的设备上

3.5 WHEN 模型已经加载且路径未改变 THEN 系统 SHALL CONTINUE TO 跳过重复加载,直接返回 True
