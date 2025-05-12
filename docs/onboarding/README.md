# Dream.OS Onboarding & Training

## 1. Overview
Centralizes all onboarding, training, and stub artifacts.

## 2. Structure
- **core/** → Essential contracts & validators  
- **tools/** → CLI utilities for onboarding  
- **training/** → Agent test scripts & routers  
- **archive/** → Legacy stubs & prototypes  
- **manual_tests/** → Hand‑run scenarios

## 3. Usage
1. **In CI:** `bash scripts/onboarding_migration.sh`  
2. **Local dev:** Inspect `docs/onboarding/` and run core scripts.  

## 4. Agent Identity Primer
See `core/agent_identity_primer.md` for how agents self‑recognize and correct drift. 