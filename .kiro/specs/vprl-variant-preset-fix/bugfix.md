# Bugfix Requirements Document

## Introduction

当VPRL尝试为MDVRP生成初始解时,系统遇到错误:"Cannot use subsample if variant_preset is not specified"。该错误导致所有depot的解生成失败,最终系统回退到纯GA_Java求解器。

根本原因是:模型的MTVRPGenerator配置为variant_preset='all'和subsample=True,但手动创建的TensorDict缺少subsample所需的字段或格式不正确,导致环境reset时subsample逻辑失败。

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN VPRL调用model.env.reset(td)且模型的generator.subsample=True时 THEN 系统抛出错误"Cannot use subsample if variant_preset is not specified"

1.2 WHEN 所有depot的解生成都失败时 THEN 系统回退到纯GA_Java求解器,没有使用任何VPRL生成的初始解

1.3 WHEN 手动创建的TensorDict传递给配置了subsample=True的环境时 THEN subsample_problems()方法无法正确处理TensorDict

### Expected Behavior (Correct)

2.1 WHEN VPRL调用model.env.reset(td)且模型的generator.subsample=True时 THEN 系统应该成功初始化环境并生成解,不抛出错误

2.2 WHEN 为每个depot生成解时 THEN 系统应该成功生成有效的初始解,而不是全部失败

2.3 WHEN 手动创建的TensorDict传递给配置了subsample=True的环境时 THEN TensorDict应该包含所有必需的字段,使subsample_problems()能够正确处理

### Unchanged Behavior (Regression Prevention)

3.1 WHEN 模型的generator.subsample=False时 THEN 系统应该继续正常工作,不受此修复影响

3.2 WHEN 使用不同的variant_preset配置时 THEN 系统应该继续支持所有现有的variant_preset选项

3.3 WHEN 转换生成的解为Cordeau格式时 THEN 解转换逻辑应该保持不变

3.4 WHEN VPRL生成失败需要回退到GA_Java时 THEN 回退机制应该继续正常工作
