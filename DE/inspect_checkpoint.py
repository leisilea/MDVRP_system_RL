"""Inspect checkpoint structure"""
import torch
import torch.serialization
import pickle

# Apply TorchRL compatibility patch
_original_load = torch.serialization._load

def _patched_load(zip_file, map_location, pickle_module, 
                pickle_file='data.pkl', overall_storage=None, 
                **pickle_load_args):
    """Patched _load that injects CompatibilityUnpickler's find_class logic"""
    original_unpickler = pickle_module.Unpickler
    
    class PatchedUnpickler(original_unpickler):
        def find_class(self, mod_name, name):
            # TorchRL API remappings for old checkpoints
            if mod_name == 'torchrl.data.tensor_specs':
                if name == 'CompositeSpec':
                    from torchrl.data.tensor_specs import Composite
                    return Composite
                elif name == 'BoundedTensorSpec':
                    from torchrl.data.tensor_specs import Bounded
                    return Bounded
                elif name == 'UnboundedContinuousTensorSpec':
                    from torchrl.data.tensor_specs import UnboundedContinuous
                    return UnboundedContinuous
                elif name == 'UnboundedDiscreteTensorSpec':
                    from torchrl.data.tensor_specs import UnboundedDiscrete
                    return UnboundedDiscrete
            return super().find_class(mod_name, name)
    
    try:
        pickle_module.Unpickler = PatchedUnpickler
        return _original_load(zip_file, map_location, pickle_module, 
                            pickle_file, overall_storage, **pickle_load_args)
    finally:
        pickle_module.Unpickler = original_unpickler

torch.serialization._load = _patched_load

checkpoint_path = 'models/vrpl_cvrp50.ckpt'
checkpoint = torch.load(checkpoint_path, map_location='cpu', weights_only=False)

print("Checkpoint keys:")
for key in checkpoint.keys():
    print(f"  - {key}")

if 'hyper_parameters' in checkpoint:
    print("\nHyperparameters:")
    for key, value in checkpoint['hyper_parameters'].items():
        print(f"  - {key}: {value}")

torch.serialization._load = _original_load
