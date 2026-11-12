# Dispatch: M3 Spatial Matcher and Safety Stress Challenger

You are challenger_m3_2, the M3 Spatial Matcher and Safety Stress Challenger for Milestone M3 (Vector PDF Processing & Schedule Parsing).

Your working directory is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
Your state folder is: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\challenger_m3_2
Your parent is: 3cdc71fe-4915-41ee-8ce4-6e81878e6b7a

MANDATORY FIRST STEP: Read the original user request at:
c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\ORIGINAL_REQUEST.md
Also read the project architecture at:
c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md
and the worker handoff report at:
c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\worker_m3_1\handoff.md

## Objective & Adversarial Stress Testing
Design and execute adversarial stress tests against `drywall_detection/vector/schedule_parser.py` and `spatial_matcher.py`:
1. 3-Tier Spatial Matcher Pathological Scenarios:
   - Dense tag clusters: multiple tags pointing to the same wall or adjacent walls.
   - Ambiguous proximity buffers: multiple walls at equal distance from a leaderless tag (verify rejection via distance delta margin).
   - Long, crossing, or segmented leader lines; leader lines terminating outside wall geometry.
   - Massive empty drawings: verify 100% of walls without tags correctly default to `Uncertain` (Tier 3 fallback) with 0.0 confidence.
2. Detail 1A Non-Drywall CMU Safety Tampering:
   - Deliberately craft corrupted/tampered inputs attempting to assign Detail 1A to "Drywall" or "GWB".
   - Verify that the programmatic safety veto in `schedule_parser.py` and `spatial_matcher.py` intercepts this and raises an immediate exception.
3. Review Lock Protocol Edge Cases:
   - Missing CSV, invalid CSV header, empty approved CSV, corrupted approved CSV.
   - Verify lockfile creation and exit code 2 semantics.

## Deliverables
- Implement a dedicated adversarial test script in your state folder or execute via Python.
- Author `handoff.md` with detailed empirical results and verdict: **APPROVE** or **REQUEST_CHANGES**.
- Notify parent orchestrator via `send_message`.


## 2026-11-08T08:23:58Z
You are challenger_m3_2, the M3 Spatial Matcher and Safety Stress Challenger for Milestone M3 (Vector PDF Processing & Schedule Parsing).

Working directory: c:\Users\TEC ZONE\OneDrive\Desktop\test-model
State folder: c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\challenger_m3_2
Your parent is: 3cdc71fe-4915-41ee-8ce4-6e81878e6b7a

Read your instructions in `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\challenger_m3_2\DISPATCH.md`.
Read `ORIGINAL_REQUEST.md`, `PROJECT.md`, and `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\worker_m3_1\handoff.md`.

Design and execute adversarial stress tests against `drywall_detection/vector/schedule_parser.py` and `spatial_matcher.py`:
- 3-tier spatial matcher stress: dense tag clusters, ambiguous equidistant walls (verify rejection via distance delta margin), crossing/disconnected leader lines, 100% unassigned fallback default on empty plans.
- Detail 1A Non-Drywall CMU safety tampering: deliberate injection of Detail 1A as Drywall, verify programmatic veto raises fatal exception.
- Review lock protocol edge cases: missing CSV, corrupted CSV, approval validation.

Write and execute your adversarial test script. Author your handoff report in `handoff.md` with verdict APPROVE or REQUEST_CHANGES.
Send a completion message to the parent orchestrator.
