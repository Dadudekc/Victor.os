# Supervisor Election Protocol (SEP) - DRAFT v_next

**Status:** DRAFT - Proposed Revision

## SEP-001: Purpose
*(Unchanged - To establish a transparent and merit-based process...)*

## SEP-002: Eligibility
*(Unchanged - Any active agent...)*

## SEP-003: Election Cycle Trigger
*(Unchanged - Triggered by Commander THEA or current Supervisor...)*

## SEP-004: Nomination & Platform Submission
1.  **Declaration:** *(Unchanged)*
2.  **Platform File:** *(Unchanged - `<AgentID>_platform.md` in `.../candidates/`)*
3.  **Platform Content (Mandatory):** *(Unchanged - Vision, Directives, Plan, etc.)*
4.  **Template Enforcement (NEW):**
    *   Submissions MUST follow the structure defined in `.../platform_template.md`.
    *   **Automated Validation:** Upon file creation/modification in the `candidates` directory, a utility (`validate_platform_structure`) MUST be triggered.
    *   **Validation Checks:** The utility verifies the presence of all required Markdown sections/headers as per the template.
    *   **Outcome:** Valid platforms are marked (e.g., timestamp added to a manifest). Invalid platforms trigger an immediate notification to the submitting agent for correction. Only validated platforms proceed.
5.  **Deadline:** *(Unchanged)*

## SEP-005: Automated Platform Analysis & Summary (NEW SECTION)
1.  **Trigger:** Runs automatically after the submission deadline for all *validated* platforms.
2.  **Process:** A designated utility (`analyze_platforms`) performs:
    *   Extraction of key sections (Vision summary, Proposed Directives, Goals).
    *   Generation of a consolidated summary document (`platform_summary.md`) placed in the election directory.
    *   Optional: Basic feasibility checks or keyword analysis (details TBD).
3.  **Purpose:** To provide a quick overview for voters and accelerate the review process.

## SEP-006: Review & Voting Period (REVISED - Merges old SEP-005 & SEP-006)
1.  **Combined Period:** A single, designated period following platform validation and summary generation.
2.  **Agent Action:** During this period, agents MUST:
    *   Review the submitted platforms (aided by the `platform_summary.md`).
    *   Cast one vote using the mandatory `cast_vote` utility (`src/dreamos/utils/governance_utils.py`).
3.  **Voting Rules:**
    *   *(Unchanged - No self-votes)*
    *   *(Unchanged - No abstention)*
    *   *(Unchanged - Must use `cast_vote` utility, which updates `votes.json`)*
    *   **Optional Enhancement:** The `cast_vote` utility could log confirmation that the voter accessed the `platform_summary.md` or individual platforms.

## SEP-007: Automated Vote Tally & Reporting (REVISED)
1.  **Automated Tally:** Immediately following the close of the Review & Voting Period, a utility (`tally_votes`) automatically:
    *   Reads `runtime/governance/election_cycle/votes.json`.
    *   Counts valid votes for each candidate.
    *   Generates a results file (`election_results.json`) containing raw counts and winner(s) based *solely* on votes cast.
2.  **Automated Reporting:** The `tally_votes` utility automatically generates a standardized report summarizing the results (including link to `election_results.json`) and sends it directly to Commander THEA's designated inbox/interface.

## SEP-008: Final Decision (REVISED - Was part of old SEP-007)
1.  **Input:** Commander THEA reviews the automated tally report (`election_results.json`), the candidate platforms (`<AgentID>_platform.md`), and the platform summary (`platform_summary.md`).
2.  **Decision Factors:** *(Unchanged - Considers vote tally, platform quality/feasibility, project needs)*
3.  **Announcement:** Commander THEA announces the final decision for the next Supervisor.

## SEP-009: Protocol Updates (Renumbered - Was SEP-008)
*(Unchanged - Standard update procedure)*

---
**Utilities Required/Modified:**
*   `validate_platform_structure` (New)
*   `analyze_platforms` (New)
*   `cast_vote` (Existing - Potentially minor logging enhancement)
*   `tally_votes` (New or significant modification of existing tally logic)
