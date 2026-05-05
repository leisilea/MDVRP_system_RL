import argparse
import os
import pickle
import time
import warnings

import torch

from rl4co.data.transforms import StateAugmentation
from rl4co.utils.ops import gather_by_index, unbatchify
from tqdm.auto import tqdm

from routefinder.data.utils import get_dataloader
from routefinder.envs import MTVRPEnv
from routefinder.models import RouteFinderBase, RouteFinderMoE
from routefinder.models.baselines.mtpomo import MTPOMO
from routefinder.models.baselines.mvmoe import MVMoE

# Tricks for faster inference
try:
    torch._C._jit_set_profiling_executor(False)
    torch._C._jit_set_profiling_mode(False)
except AttributeError:
    pass

torch.set_float32_matmul_precision("medium")


def test(
    policy,
    td,
    env,
    num_augment=1,  # Reduced from 8 to 1
    augment_fn="dihedral8",
    num_starts=1,  # Reduced to 1
    device="cuda",
):

    costs_bks = td.get("costs_bks", None)

    with torch.inference_mode():
        with (
            torch.amp.autocast("cuda")
            if "cuda" in str(device)
            else torch.inference_mode()
        ):
            n_start = num_starts

            if num_augment > 1:
                td = StateAugmentation(num_augment=num_augment, augment_fn=augment_fn)(td)

            # Evaluate policy
            out = policy(td, env, phase="test", num_starts=n_start, return_actions=True)

            # Unbatchify reward to [batch_size, num_augment, num_starts].
            reward = unbatchify(out["reward"], (num_augment, n_start))

            if n_start > 1:
                max_reward, max_idxs = reward.max(dim=-1)
                out.update({"max_reward": max_reward})

                if out.get("actions", None) is not None:
                    actions = unbatchify(out["actions"], (num_augment, n_start))
                    out.update(
                        {
                            "best_multistart_actions": gather_by_index(
                                actions, max_idxs, dim=max_idxs.dim()
                            )
                        }
                    )
                    out["actions"] = actions

            if num_augment > 1:
                reward_ = max_reward if n_start > 1 else reward
                max_aug_reward, max_idxs = reward_.max(dim=1)
                out.update({"max_aug_reward": max_aug_reward})

                if costs_bks is not None:
                    gap_to_bks = (
                        100
                        * (-max_aug_reward - torch.abs(costs_bks))
                        / torch.abs(costs_bks)
                    )
                    out.update({"gap_to_bks": gap_to_bks})

                if out.get("actions", None) is not None:
                    actions_ = (
                        out["best_multistart_actions"] if n_start > 1 else out["actions"]
                    )
                    out.update({"best_aug_actions": gather_by_index(actions_, max_idxs)})
            else:
                # No augmentation case
                out.update({"max_aug_reward": reward.squeeze()})
                if costs_bks is not None:
                    gap_to_bks = (
                        100
                        * (-reward.squeeze() - torch.abs(costs_bks))
                        / torch.abs(costs_bks)
                    )
                    out.update({"gap_to_bks": gap_to_bks})

            if out.get("gap_to_bks", None) is None:
                out.update({"gap_to_bks": 69420})

            return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--checkpoint", type=str, required=True, help="Path to the model checkpoint"
    )
    parser.add_argument("--batch_size", type=int, default=2)
    parser.add_argument("--device", type=str, default="cpu")
    parser.add_argument("--num_instances", type=int, default=10, help="Number of instances to test")

    warnings.filterwarnings("ignore", message=".*weights_only.*", category=FutureWarning)

    opts = parser.parse_args()

    if "cuda" in opts.device and torch.cuda.is_available():
        device = torch.device("cuda:0")
    else:
        device = torch.device("cpu")

    # Fix TorchRL API compatibility
    import torchrl.data.tensor_specs as specs
    if not hasattr(specs, 'CompositeSpec'):
        specs.CompositeSpec = specs.Composite
    if not hasattr(specs, 'BoundedTensorSpec'):
        specs.BoundedTensorSpec = specs.Bounded
    if not hasattr(specs, 'UnboundedContinuousTensorSpec'):
        specs.UnboundedContinuousTensorSpec = specs.UnboundedContinuous
    if not hasattr(specs, 'UnboundedDiscreteTensorSpec'):
        specs.UnboundedDiscreteTensorSpec = specs.UnboundedDiscrete

    # Load model
    print("Loading checkpoint from", opts.checkpoint)
    if "mvmoe" in opts.checkpoint:
        BaseLitModule = MVMoE
    elif "mtpomo" in opts.checkpoint:
        BaseLitModule = MTPOMO
    elif "moe" in opts.checkpoint:
        BaseLitModule = RouteFinderMoE
    else:
        BaseLitModule = RouteFinderBase

    model = BaseLitModule.load_from_checkpoint(
        opts.checkpoint, map_location="cpu", strict=False
    )
    print("✓ Checkpoint loaded successfully")

    env = MTVRPEnv()
    policy = model.policy.to(device).eval()
    print("✓ Policy moved to device and set to eval mode")

    # Load test data
    dataset_path = "data/cvrp/test/100.npz"
    print(f"\nLoading {dataset_path}")
    td_test = env.load_data(dataset_path)
    
    # Only use first N instances
    td_test = td_test[:opts.num_instances]
    print(f"✓ Loaded {opts.num_instances} instances")
    
    dataloader = get_dataloader(td_test, batch_size=opts.batch_size)
    print(f"✓ Created dataloader with batch_size={opts.batch_size}")

    print("\nRunning inference...")
    start = time.time()
    res = []
    for i, batch in enumerate(dataloader):
        print(f"  Processing batch {i+1}/{len(dataloader)}...")
        td_test_batch = env.reset(batch).to(device)
        o = test(policy, td_test_batch, env, device=device)
        res.append(o)
    
    out = {}
    out["max_aug_reward"] = torch.cat([o["max_aug_reward"] for o in res])
    out["gap_to_bks"] = torch.cat([o["gap_to_bks"] for o in res])
        
    inference_time = time.time() - start

    print(f"\n{'='*60}")
    print(f"CVRP-100 Quick Test Results")
    print(f"{'='*60}")
    print(f"Instances tested: {opts.num_instances}")
    print(f"Average cost: {-out['max_aug_reward'].mean().item():.3f}")
    print(f"Average gap to BKS: {out['gap_to_bks'].mean().item():.3f}%")
    print(f"Total inference time: {inference_time:.2f}s")
    print(f"Time per instance: {inference_time/opts.num_instances:.2f}s")
    print(f"{'='*60}")
    print("\n✓ Test completed successfully!")
