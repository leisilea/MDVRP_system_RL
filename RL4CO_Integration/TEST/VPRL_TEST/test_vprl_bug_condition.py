"""
VPRL CompatibilityUnpickler 集成的 Bug 条件探索测试

此测试验证在未修复的代码上,加载带有旧 TorchRL API 类名的 RouteFinder checkpoint 会失败并抛出 AttributeError。

关键: 此测试在未修复的代码上必须失败 - 失败确认 bug 存在。
不要尝试修复测试或代码当它失败时。

未修复代码的预期结果:
  - 测试失败并抛出 AttributeError: "module 'torchrl.data.tensor_specs' has no attribute 'CompositeSpec'"
  
修复后代码的预期结果:
  - 测试通过,确认 bug 已修复
"""

import pytest
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from VPRL.vprl_sampler import VPRLSampler
from VPRL.config import VPRLConfig


class TestVPRLBugCondition:
    """
    VPRL CompatibilityUnpickler 集成 bug 条件的测试套件
    
    Bug 条件:
      - checkpoint_path 存在
      - checkpoint 包含旧 TorchRL API 类名(CompositeSpec, BoundedTensorSpec 等)
      - VPRL sampler 调用 RouteFinderBase.load_from_checkpoint()
      - 没有应用 CompatibilityUnpickler 补丁
    
    预期行为(修复后):
      - _load_model() 返回 True
      - 模型成功加载且不为 None
      - 模型处于 eval 模式
      - 模型在正确的设备上
    """
    
    @pytest.fixture
    def checkpoint_path(self):
        """包含旧 TorchRL API 类的 checkpoint 路径"""
        # 使用包含 CompositeSpec 的真实 checkpoint
        path = "models/vrpl_cvrp200.ckpt"
        if not os.path.exists(path):
            pytest.skip(f"Checkpoint file not found: {path}")
        return path
    
    @pytest.fixture
    def vprl_config(self):
        """用于测试的 VPRL 配置"""
        return VPRLConfig(
            model_path="models/vrpl_cvrp200.ckpt",
            device='cpu',  # 使用 CPU 进行测试
            enable_vrpl=True
        )
    
    def test_load_old_api_checkpoint_fails_on_unfixed_code(self, checkpoint_path, vprl_config):
        """
        测试在未修复的代码上加载带有旧 TorchRL API 类名的 checkpoint 会失败
        
        此测试编码了修复后的预期行为:
          - _load_model() 应该返回 True
          - 模型应该成功加载
          - 模型应该处于 eval 模式
          - 模型应该在正确的设备上
        
        在未修复的代码上,此测试将失败并抛出 AttributeError,确认 bug 存在。
        在修复后的代码上,此测试将通过,确认 bug 已修复。
        
        需求: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3
        """
        # 创建 VPRL sampler
        sampler = VPRLSampler(config=vprl_config)
        
        # 尝试加载模型
        # 在未修复的代码上: 这将抛出 AttributeError
        # 在修复后的代码上: 这将成功
        result = sampler._load_model(checkpoint_path)
        
        # 修复后的预期行为
        assert result is True, "Model loading should return True"
        assert sampler.model is not None, "Model should be loaded"
        assert not sampler.model.training, "Model should be in eval mode"
        
        # 验证模型在正确的设备上
        # 获取第一个参数以检查设备
        first_param = next(sampler.model.parameters())
        expected_device = vprl_config.device
        if expected_device == 'cpu':
            assert first_param.device.type == 'cpu', f"Model should be on CPU, but is on {first_param.device}"
        else:
            assert first_param.device.type == 'cuda', f"Model should be on CUDA, but is on {first_param.device}"
    
    def test_diagnostic_check_old_api_classes_in_checkpoint(self, checkpoint_path):
        """
        诊断测试,确认 checkpoint 包含旧 TorchRL API 类名
        
        此测试尝试加载 checkpoint 并记录错误
        """
        import torch
        import pickle
        
        print(f"\n{'='*60}")
        print("Diagnostic: Checking checkpoint for old TorchRL API classes")
        print(f"{'='*60}")
        print(f"Checkpoint path: {checkpoint_path}")
        
        try:
            # Try to load with standard torch.load
            checkpoint = torch.load(checkpoint_path, map_location='cpu')
            print("✓ Checkpoint loaded successfully with standard torch.load")
            print(f"  Checkpoint keys: {list(checkpoint.keys())}")
        except AttributeError as e:
            print(f"✗ AttributeError encountered: {e}")
            print(f"  This confirms the checkpoint contains old TorchRL API class names")
            print(f"  Error type: {type(e).__name__}")
            print(f"  Error message: {str(e)}")
            
            # Document the error for root cause analysis
            if "CompositeSpec" in str(e):
                print("  → Detected: CompositeSpec (should be Composite)")
            if "BoundedTensorSpec" in str(e):
                print("  → Detected: BoundedTensorSpec (should be Bounded)")
            if "UnboundedContinuousTensorSpec" in str(e):
                print("  → Detected: UnboundedContinuousTensorSpec (should be UnboundedContinuous)")
            if "UnboundedDiscreteTensorSpec" in str(e):
                print("  → Detected: UnboundedDiscreteTensorSpec (should be UnboundedDiscrete)")
        
        print(f"{'='*60}\n")


if __name__ == "__main__":
    # Run the test
    pytest.main([__file__, "-v", "-s"])
