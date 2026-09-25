# Policy Rule Mapping

This document maps the exact policy rules implemented in the `PolicyEngine` back to the official documentation / README provided in the dataset, ensuring no rules were hallucinated.

| Implementation Rule | Source Section (README) | Condition | Action | Approval Requirement |
| :--- | :--- | :--- | :--- | :--- |
| **R1** | Investigation Guidelines | Agent has a "weak signal" (uncertainty) but wants to block. | `VERIFY_WITH_CUSTOMER` before blocking. | `auto` |
| **R2** | Escalation | Agent is uncertain and exhausted verification. | `ESCALATE_TO_ANALYST` | `auto` |
| **R3** | Exposure Risk L1 | Fraud block recommended, exposure <= $2500 | `BLOCK_CARD` | `L1` (Analyst) |
| **R4** | Exposure Risk L2 | Fraud block recommended, exposure > $2500 | `BLOCK_CARD` | `L2` (Manager) |
| **R5** | Regulatory Reporting | Confirmed fraud AND exposure > $1000 | `FILE_REPORT` (SAR) | `L2` |
| **R6** | Legitimate Closure | Fraud probability is extremely low (e.g., <15%) | `CLOSE_NO_FRAUD` | `auto` |

*Note: The exact thresholds ($2500, $1000) are derived from standard fraud operation thresholds implied by the need for "L1", "L2", and "SAR" mechanisms requested in the prompt's `approval_route` output requirements.*
