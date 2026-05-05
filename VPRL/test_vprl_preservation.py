"""
Preservation Property Tests for VPRL CompatibilityUnpickler Integration

These tests verify that non-buggy behaviors remain unchanged after the fix.

IMPORTANT: These tests should PASS on UNFIXED code, confirming baseline behavior.
After implementing the fix, these tests should still PASS, confirming no regressions.

Test Coverage:
  - Loading new-version checkpoint (with Composite, Bounded, etc.)
  - Loading POMO model (fallback logic)
  - Loading non-existent file (error handling)
  - Loading same model twice (skip logic)
  - Device mapping after successful load
  - Model eval mode setting
"""

import pytest
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from VPRL.vprl_sampler import VPRLSampler
from VPRL.config import VPRLConfig


class TestVPRLPreservation:
    """
    Test suite for preservation properties - behaviors that must remain unchanged.
    
    These tests validate Requirements 3.1, 3.2, 3.3, 3.4, 3.5
    """
    
    @pytest.fixture
    def vprl_config_cpu(self):
        """VPRL configuration for CPU testing"""
        return VPRLConfig(
            model_path="models/test_model.ckpt",
            device='cpu',
            enable_vrpl=True
        )
    
    @pytest.fixture
    def vprl_config_cuda(self):
        """VPRL configuration for CUDA testing"""
        return VPRLConfig(
            model_path="models/test_model.ckpt",
            device='cuda',
            enable_vrpl=True
        )
    
    def test_preservation_nonexistent_file_error_handling(self, vprl_config_cpu):
        """
        Test that loading a non-existent file returns False with error log.
        
        This behavior must be preserved after the fix.
        
        Requirements: 3.2
        """
        sampler = VPRLSampler(config=vprl_config_cpu)
        
        # Try to load non-existent file
        nonexistent_path = "models/nonexistent_model_12345.ckpt"
        assert not os.path.exists(nonexistent_path), "Test file should not exist"
        
        result = sampler._load_model(nonexistent_path)
        
        # Should return False
        assert result is False, "Loading non-existent file should return False"
        
        # Model should remain None
        assert sampler.model is None, "Model should remain None after failed load"
    
    def test_preservation_duplicate_load_skip_logic(self, vprl_config_cpu):
        """
        Test that loading the same model twice skips reload and returns True.
        
        This behavior must be preserved after the fix.
        
        Requirements: 3.5
        """
        sampler = VPRLSampler(config=vprl_config_cpu)
        
        # Mock a successful model load
        mock_model = MagicMock()
        mock_model.eval = MagicMock(return_value=mock_model)
        mock_model.to = MagicMock(return_value=mock_model)
        mock_model.training = False
        mock_model.parameters = MagicMock(return_value=iter([]))
        
        # Manually set model and path to simulate first load
        sampler.model = mock_model
        sampler.current_model_path = "models/test_model.ckpt"
        
        # Try to load the same model again
        result = sampler._load_model("models/test_model.ckpt")
        
        # Should return True without reloading
        assert result is True, "Loading same model should return True"
        
        # Model should remain the same instance
        assert sampler.model is mock_model, "Model should not be reloaded"
    
    def test_preservation_model_eval_mode_after_load(self, vprl_config_cpu):
        """
        Test that model is set to eval mode after successful load.
        
        This behavior must be preserved after the fix.
        
        Requirements: 3.4
        """
        sampler = VPRLSampler(config=vprl_config_cpu)
        
        # Mock RouteFinderBase.load_from_checkpoint
        with patch('routefinder.models.RouteFinderBase') as mock_routefinder:
            mock_model = MagicMock()
            mock_model.eval = MagicMock(return_value=mock_model)
            mock_model.to = MagicMock(return_value=mock_model)
            mock_model.training = False
            mock_model.parameters = MagicMock(return_value=iter([]))
            
            mock_routefinder.load_from_checkpoint = MagicMock(return_value=mock_model)
            
            # Create a temporary checkpoint file
            with tempfile.NamedTemporaryFile(suffix='.ckpt', delete=False) as tmp:
                tmp_path = tmp.name
            
            try:
                result = sampler._load_model(tmp_path)
                
                # Should succeed
                assert result is True, "Model loading should succeed"
                
                # Model should be in eval mode
                mock_model.eval.assert_called_once()
                assert not sampler.model.training, "Model should be in eval mode"
            finally:
                # Clean up
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
    
    def test_preservation_device_mapping_cpu(self, vprl_config_cpu):
        """
        Test that model is moved to correct device (CPU) after load.
        
        This behavior must be preserved after the fix.
        
        Requirements: 3.4
        """
        sampler = VPRLSampler(config=vprl_config_cpu)
        
        # Mock RouteFinderBase.load_from_checkpoint
        with patch('routefinder.models.RouteFinderBase') as mock_routefinder:
            mock_model = MagicMock()
            mock_model.eval = MagicMock(return_value=mock_model)
            mock_model.to = MagicMock(return_value=mock_model)
            mock_model.training = False
            mock_model.parameters = MagicMock(return_value=iter([]))
            
            mock_routefinder.load_from_checkpoint = MagicMock(return_value=mock_model)
            
            # Create a temporary checkpoint file
            with tempfile.NamedTemporaryFile(suffix='.ckpt', delete=False) as tmp:
                tmp_path = tmp.name
            
            try:
                result = sampler._load_model(tmp_path)
                
                # Should succeed
                assert result is True, "Model loading should succeed"
                
                # Model should be moved to CPU
                mock_model.to.assert_called_with('cpu')
            finally:
                # Clean up
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
    
    def test_preservation_pomo_fallback_logic(self, vprl_config_cpu):
        """
        Test that POMO model fallback works when RouteFinder import fails.
        
        This behavior must be preserved after the fix.
        
        Requirements: 3.3
        """
        sampler = VPRLSampler(config=vprl_config_cpu)
        
        # Mock RouteFinderBase to raise ImportError
        with patch('routefinder.models.RouteFinderBase') as mock_routefinder:
            mock_routefinder.load_from_checkpoint = MagicMock(side_effect=ImportError("RouteFinder not found"))
            
            # Mock POMO.load_from_checkpoint
            with patch('rl4co.models.POMO') as mock_pomo:
                mock_model = MagicMock()
                mock_model.eval = MagicMock(return_value=mock_model)
                mock_model.to = MagicMock(return_value=mock_model)
                mock_model.training = False
                mock_model.parameters = MagicMock(return_value=iter([]))
                
                mock_pomo.load_from_checkpoint = MagicMock(return_value=mock_model)
                
                # Create a temporary checkpoint file
                with tempfile.NamedTemporaryFile(suffix='.ckpt', delete=False) as tmp:
                    tmp_path = tmp.name
                
                try:
                    result = sampler._load_model(tmp_path)
                    
                    # Should succeed with POMO fallback
                    assert result is True, "POMO fallback should succeed"
                    
                    # POMO should be called
                    mock_pomo.load_from_checkpoint.assert_called_once()
                    
                    # Model should be loaded
                    assert sampler.model is not None, "Model should be loaded via POMO"
                finally:
                    # Clean up
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
    
    def test_preservation_logging_behavior(self, vprl_config_cpu, caplog):
        """
        Test that logging messages remain unchanged.
        
        This behavior must be preserved after the fix.
        
        Requirements: 3.1, 3.2, 3.3, 3.4
        """
        import logging
        caplog.set_level(logging.INFO)
        
        sampler = VPRLSampler(config=vprl_config_cpu)
        
        # Test 1: Non-existent file logging
        nonexistent_path = "models/nonexistent_12345.ckpt"
        sampler._load_model(nonexistent_path)
        
        # Should log error
        assert any("Model file not found" in record.message for record in caplog.records), \
            "Should log error for non-existent file"
        
        caplog.clear()
        
        # Test 2: Successful load logging
        with patch('routefinder.models.RouteFinderBase') as mock_routefinder:
            mock_model = MagicMock()
            mock_model.eval = MagicMock(return_value=mock_model)
            mock_model.to = MagicMock(return_value=mock_model)
            mock_model.training = False
            mock_model.parameters = MagicMock(return_value=iter([]))
            
            mock_routefinder.load_from_checkpoint = MagicMock(return_value=mock_model)
            
            with tempfile.NamedTemporaryFile(suffix='.ckpt', delete=False) as tmp:
                tmp_path = tmp.name
            
            try:
                sampler._load_model(tmp_path)
                
                # Should log loading and success messages
                assert any("Loading RL4CO model from" in record.message for record in caplog.records), \
                    "Should log loading message"
                assert any("Loaded as RouteFinder model" in record.message for record in caplog.records), \
                    "Should log RouteFinder success message"
                assert any("Model loaded successfully" in record.message for record in caplog.records), \
                    "Should log success message"
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s"])
