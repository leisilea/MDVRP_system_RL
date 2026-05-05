# Implementation Plan

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Persistent ID 处理失败
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: For deterministic bugs, scope the property to the concrete failing case(s) to ensure reproducibility
  - Test implementation details from Bug Condition in design
  - The test assertions should match the Expected Behavior Properties from design
  - Test that loading checkpoint with persistent ID succeeds (from Bug Condition: checkpoint_contains_persistent_ids AND unpickler_encounters_PERSID_opcode)
  - Test that result is a dict containing 'hyper_parameters' or 'state_dict' keys
  - Test that no UnpicklingError is raised
  - Run test on UNFIXED code (CompatibilityUnpickler without persistent_load method)
  - **EXPECTED OUTCOME**: Test FAILS with "_pickle.UnpicklingError: A load persistent id instruction was encountered, but no persistent_load function was specified" (this is correct - it proves the bug exists)
  - Document counterexamples found to understand root cause
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 1.2, 2.1, 2.2_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - find_class 功能保持不变
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for non-buggy inputs
  - Write property-based tests capturing observed behavior patterns from Preservation Requirements
  - Property-based testing generates many test cases for stronger guarantees
  - Test that find_class correctly maps TorchRL API names (CompositeSpec → Composite, BoundedTensorSpec → Bounded, etc.)
  - Test that checkpoint structure (keys like 'hyper_parameters', 'state_dict') remains unchanged
  - Test that loading non-PyTorch pickle objects works correctly
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 3. Fix for CompatibilityUnpickler persistent_load 缺失

  - [x] 3.1 Implement the fix
    - Add persistent_load method to CompatibilityUnpickler class in RL4CO_Integration/routefinder/fix_checkpoint_loader.py
    - Method should accept persistent ID parameter and delegate to parent class implementation
    - Ensure find_class method remains unchanged and continues to work
    - _Bug_Condition: isBugCondition(input) where checkpoint_contains_persistent_ids(input.file_handle) AND CompatibilityUnpickler.persistent_load is None_
    - _Expected_Behavior: For any checkpoint file with persistent ID, CompatibilityUnpickler SHALL successfully load checkpoint and return dict with model weights and hyperparameters_
    - _Preservation: find_class method SHALL continue to handle TorchRL API remapping; checkpoint structure SHALL remain unchanged; non-persistent-ID pickle loading SHALL work identically_
    - _Requirements: 1.1, 1.2, 2.1, 2.2, 3.1, 3.2, 3.3_

  - [x] 3.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Persistent ID 处理成功
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.1, 2.2_

  - [x] 3.3 Verify preservation tests still pass
    - **Property 2: Preservation** - find_class 功能保持不变
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after fix (no regressions)
    - _Requirements: 3.1, 3.2, 3.3_

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
