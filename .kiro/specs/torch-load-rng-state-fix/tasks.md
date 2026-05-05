# Implementation Plan

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - RNG State CUDA Loading Error
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: For deterministic bugs, scope the property to the concrete failing case(s) to ensure reproducibility
  - Test that loading a checkpoint with RNG state using `map_location='cuda:0'` succeeds (from Bug Condition in design)
  - The test should verify: `torch.load(checkpoint_path, map_location='cuda:0')` completes without "RNG state must be a torch.ByteTensor" error
  - Test with RouteFinder and POMO checkpoints that contain Lightning RNG states
  - The test assertions should match the Expected Behavior Properties from design: model loads successfully, weights are initialized, inference works
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS with "RNG state must be a torch.ByteTensor" error (this is correct - it proves the bug exists)
  - Document counterexamples found to understand root cause (e.g., which RNG state keys cause the issue, device mismatch details)
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 1.2_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Non-CUDA and Non-RNG Loading Behavior
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for non-buggy inputs:
    - Loading checkpoints with `map_location='cpu'` (should work)
    - Loading checkpoints without RNG state (should work)
    - Model inference after loading (should work)
  - Write property-based tests capturing observed behavior patterns from Preservation Requirements:
    - For all checkpoints loaded with `map_location='cpu'`, loading succeeds and model works
    - For all checkpoints without RNG state, loading with any map_location succeeds
    - For all successfully loaded models, inference functions (policy, get_reward) produce valid outputs
  - Property-based testing generates many test cases for stronger guarantees
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 3. Fix for RNG state loading error when using CUDA map_location

  - [x] 3.1 Implement the fix in VPRL/vprl_sampler.py
    - Modify `_load_model` function (lines 195-220) to handle RNG state correctly
    - Add logic to load checkpoint to CPU first, remove RNG states if present, then load model
    - Implementation approach:
      ```python
      # Load checkpoint to CPU first
      checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
      
      # Remove RNG states if present
      if 'rng_states' in checkpoint:
          del checkpoint['rng_states']
      
      # Then load model with cleaned checkpoint or move to target device
      ```
    - Ensure compatibility with existing CompatibilityUnpickler logic
    - Preserve all existing error handling and logging
    - _Bug_Condition: isBugCondition(input) where input.checkpoint_contains_rng == True AND input.map_location IN ['cuda', 'cuda:0', 'cuda:1', ...]_
    - _Expected_Behavior: Model loads successfully without RNG state error, weights are on correct device, model can perform inference (from design Property 1)_
    - _Preservation: CPU loading, non-RNG checkpoints, inference functionality, TorchRL compatibility must remain unchanged (from design Property 2)_
    - _Requirements: 1.1, 1.2, 2.1, 2.2, 3.1, 3.2, 3.3, 3.4_

  - [x] 3.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - RNG State CUDA Loading Success
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - Verify that loading checkpoints with RNG state to CUDA devices now succeeds
    - Verify that model weights are correctly loaded and on the target device
    - Verify that model can perform inference after loading
    - _Requirements: 2.1, 2.2_

  - [x] 3.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Non-CUDA and Non-RNG Loading Behavior
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after fix (no regressions):
      - CPU loading continues to work
      - Non-RNG checkpoint loading continues to work
      - Model inference continues to work correctly
      - TorchRL compatibility is preserved

- [x] 4. Checkpoint - Ensure all tests pass
  - Run all tests (bug condition + preservation)
  - Verify no regressions in existing functionality
  - Test with real RouteFinder and POMO checkpoints
  - Ensure all tests pass, ask the user if questions arise
