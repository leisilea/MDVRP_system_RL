"""
修复RouteFinder checkpoint加载的兼容性问题

解决CompositeSpec在新版TorchRL中被重命名的问题
"""
import pickle
import torch
from pathlib import Path


class CompatibilityUnpickler(pickle.Unpickler):
    """自定义Unpickler，处理TorchRL API变化"""
    
    def find_class(self, module, name):
        # 处理CompositeSpec -> Composite的重命名
        if module == 'torchrl.data.tensor_specs' and name == 'CompositeSpec':
            from torchrl.data.tensor_specs import Composite
            return Composite
        
        # 处理BoundedTensorSpec -> Bounded的重命名
        if module == 'torchrl.data.tensor_specs' and name == 'BoundedTensorSpec':
            try:
                from torchrl.data.tensor_specs import Bounded
                return Bounded
            except ImportError:
                pass
        
        # 处理UnboundedContinuousTensorSpec -> UnboundedContinuous
        if module == 'torchrl.data.tensor_specs' and name == 'UnboundedContinuousTensorSpec':
            try:
                from torchrl.data.tensor_specs import UnboundedContinuous
                return UnboundedContinuous
            except ImportError:
                pass
        
        # 处理UnboundedDiscreteTensorSpec -> UnboundedDiscrete
        if module == 'torchrl.data.tensor_specs' and name == 'UnboundedDiscreteTensorSpec':
            try:
                from torchrl.data.tensor_specs import UnboundedDiscrete
                return UnboundedDiscrete
            except ImportError:
                pass
        
        return super().find_class(module, name)


def load_checkpoint_compatible(checkpoint_path):
    """
    兼容地加载checkpoint
    
    Args:
        checkpoint_path: checkpoint文件路径
        
    Returns:
        加载的checkpoint字典
    """
    checkpoint_path = Path(checkpoint_path)
    
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")
    
    print(f"Loading checkpoint with compatibility fix: {checkpoint_path}")
    
    # Monkey-patch the UnpicklerWrapper class creation in torch.serialization._load
    import torch.serialization
    _original_load = torch.serialization._load
    
    def _patched_load(zip_file, map_location, pickle_module, pickle_file='data.pkl', overall_storage=None, **pickle_load_args):
        """Patched _load that injects our CompatibilityUnpickler's find_class logic"""
        # We need to patch the UnpicklerWrapper class that gets created inside _load
        # Save the original pickle_module.Unpickler
        original_unpickler = pickle_module.Unpickler
        
        # Create a new Unpickler class that uses our find_class logic
        class PatchedUnpickler(original_unpickler):
            def find_class(self, mod_name, name):
                # First check TorchRL API remappings
                if mod_name == 'torchrl.data.tensor_specs':
                    if name == 'CompositeSpec':
                        from torchrl.data.tensor_specs import Composite
                        return Composite
                    elif name == 'BoundedTensorSpec':
                        try:
                            from torchrl.data.tensor_specs import Bounded
                            return Bounded
                        except ImportError:
                            pass
                    elif name == 'UnboundedContinuousTensorSpec':
                        try:
                            from torchrl.data.tensor_specs import UnboundedContinuous
                            return UnboundedContinuous
                        except ImportError:
                            pass
                    elif name == 'UnboundedDiscreteTensorSpec':
                        try:
                            from torchrl.data.tensor_specs import UnboundedDiscrete
                            return UnboundedDiscrete
                        except ImportError:
                            pass
                
                # Default behavior
                return super().find_class(mod_name, name)
        
        # Temporarily replace the Unpickler class
        try:
            pickle_module.Unpickler = PatchedUnpickler
            return _original_load(zip_file, map_location, pickle_module, pickle_file, overall_storage, **pickle_load_args)
        finally:
            # Restore original Unpickler
            pickle_module.Unpickler = original_unpickler
    
    try:
        torch.serialization._load = _patched_load
        checkpoint = torch.load(
            checkpoint_path,
            map_location='cpu',
            pickle_module=pickle,
            weights_only=False
        )
    finally:
        # Restore original function
        torch.serialization._load = _original_load
    
    print("✓ Checkpoint loaded successfully")
    return checkpoint


def save_fixed_checkpoint(input_path, output_path):
    """
    加载旧checkpoint并保存为兼容新版本的格式
    
    Args:
        input_path: 原始checkpoint路径
        output_path: 输出checkpoint路径
    """
    print(f"Loading original checkpoint: {input_path}")
    checkpoint = load_checkpoint_compatible(input_path)
    
    print(f"Saving fixed checkpoint: {output_path}")
    torch.save(checkpoint, output_path)
    
    print("✓ Fixed checkpoint saved")
    return output_path


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python fix_checkpoint_loader.py <checkpoint_path>")
        print("  python fix_checkpoint_loader.py <input_path> <output_path>")
        sys.exit(1)
    
    if len(sys.argv) == 2:
        # 测试加载
        checkpoint = load_checkpoint_compatible(sys.argv[1])
        print(f"Checkpoint keys: {list(checkpoint.keys())}")
    else:
        # 转换并保存
        save_fixed_checkpoint(sys.argv[1], sys.argv[2])
