# Dispatch: m1_challenger_1

- **Role**: Split Integrity & DataLoader Stress Challenger
- **Milestone**: M1 (Dataset Research, Licensing Audit & Unified Preparation)
- **Working Directory**: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
- **State Folder**: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_challenger_1
- **Path to ORIGINAL_REQUEST.md**: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md
- **Path to PROJECT.md**: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md
- **Path to Worker Handoff**: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_worker_1\handoff.md

## Objective
Empirically stress-test the drawing-level split integrity manager and PyTorch DataLoader:
1. Write adversarial test scripts attempting to introduce data leakage:
   - Duplicate project IDs between train and val
   - Duplicate drawing IDs between train and test
   - Duplicate image/mask file paths across splits
   - Verify that `verify_split_isolation()` strictly detects and raises `SplitLeakageError` in 100% of leakage cases.
2. Stress-test greedy multi-way partitioning under skewed drawing distributions and extreme split ratios.
3. Stress-test DataLoader iteration: verify memory stability, check tensor dimensions `[B, 3, 512, 512]` and `[B, 512, 512]`, verify label values are strictly in `{0, 1, 2, 3}`, verify synchronized augmentations under repeated epochs.
4. Record all test code, logs, and empirical results in `analysis.md` and provide a clear verdict (APPROVE or REQUEST_CHANGES) in `handoff.md`.


## 2026-11-07T21:06:08Z
You are m1_challenger_1. Read the instructions in your state file: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_challenger_1\DISPATCH.md
Also read ORIGINAL_REQUEST.md at: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md
And PROJECT.md at: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md
And the Worker handoff report: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_worker_1\handoff.md

Role: Split Integrity & DataLoader Stress Challenger
Working directory: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
State folder: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\m1_challenger_1

Empirically stress-test the split manager and DataLoader:
1. Write adversarial test scripts attempting to introduce data leakage (project overlap, drawing overlap, path overlap). Verify that verify_split_isolation() detects and raises SplitLeakageError in 100% of cases.
2. Stress-test greedy partitioning under extreme/skewed distributions.
3. Stress-test DataLoader iteration: check memory stability, tensor shapes [B, 3, 512, 512] and [B, 512, 512], labels strictly in {0, 1, 2, 3}, and synchronized transforms.
Document test scripts, execution logs, and provide a clear verdict (APPROVE or REQUEST_CHANGES) in your handoff report.
Notify the orchestrator via send_message when done.
