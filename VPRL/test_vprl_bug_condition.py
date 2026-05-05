"""
Bug Condition Exploration Test for VPRL CompatibilityUnpickler Integration

This test verifies that loading a RouteFinder checkpoint with old TorchRL API class names
fails on UNFIXED code with AttributeError.

CRITICAL: This test MUST FAIL on unfixed code - failure confirms the bug exists.
DO NOT attempt to fix the test or the code when it fails.

Expected outcome on UNFIXED code:
  - Test FAILS with AttributeError: "module 'torchrl.data.tensor_specs' has no attribute 'CompositeSpec'"
  
Expected outcome on FIXED code:
  - Test PASSES, confirming the bug is fixed
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
    Test suite for VPRL CompatibilityUnpickler integration bug condition.
    
    Bug Condition:
      - checkpoint_path exists
      - checkpoint contains old TorchRL API class names (CompositeSpec, BoundedTensorSpec, etc.)
      - VPRL sampler calls RouteFinderBase.load_from_checkpoint()
      - No CompatibilityUnpickler patch is applied
    
    Expected Behavior (after fix):
      - _load_model() returns True
      - model is successfully loaded and not None
      - model is in eval mode
      - model is on correct device
    """
    
    @pytest.fixture
    def checkpoint_path(self):
        """Path to checkpoint with old TorchRL API classes"""
        # Use the real checkpoint that contains CompositeSpec
        path = "models/vrpl_cvrp200.ckpt"
        if not os.path.exists(path):
            pytest.skip(f"Checkpoint file not found: {path}")
        return path
    
    @pytest.fixture
    def vprl_config(self):
        """VPRL configuration for testing"""
        return VPRLConfig(
            model_path="models/vrpl_cvrp200.ckpt",
            device='cpu',  # Use CPU for testing
            enable_vrpl=True
        )
    
    def test_load_old_api_checkpoint_fails_on_unfixed_code(self, checkpoint_path, vprl_config):
        """
        Test that loading a checkpoint with old TorchRL API class names fails on unfixed code.
        
        This test encodes the expected behavior after the fix:
          - _load_model() should return True
          - model should be loaded successfully
          - model should be in eval mode
          - model should be on correct device
        
        On UNFIXED code, this test will FAIL with AttributeError, confirming the bug exists.
        On FIXED code, this test will PASS, confirming the bug is fixed.
        
        Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3
        """
        # Create VPRL sampler
        sampler = VPRLSampler(config=vprl_config)
        
        # Attempt to load the model
        # On UNFIXED code: This will raise AttributeError
        # On FIXED code: This will succeed
        result = sampler._load_model(checkpoint_path)
        
        # Expected behavior after fix
        assert result is True, "Model loading should return True"
        assert sampler.model is not None, "Model should be loaded"
        assert not sampler.model.training, "Model should be in eval mode"
        
        # Verify model is on correct device
        # Get first parameter to check device
        first_param = next(sampler.model.parameters())
        expected_device = vprl_config.device
        if expected_device == 'cpu':
            assert first_param.device.type == 'cpu', f"Model should be on CPU, but is on {first_param.device}"
        else:
            assert first_param.device.type == 'cuda', f"Model should be on CUDA, but is on {first_param.device}"
    
    def test_diagnostic_check_old_api_classes_in_checkpoint(self, checkpoint_path):
        """
        Diagnostic test to confirm the checkpoint contains old TorchRL API class names.
        
        This test attempts to load the checkpoint and documents the error.
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
