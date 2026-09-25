# Official Dataset Audit

## Overview
This audit examines the official dataset files provided for the TigerGraph Agentic Fraud Investigation project, ensuring the integrity and presence of the benchmark data.

## Findings
- **Transactions Total:** 590,742
- **Identity Records Total:** 144,432
- **Closed Cases Total:** 5,565

## Benchmark Cases Verification
The following table confirms the presence of the 20 official benchmark flagged transaction IDs in the `transactions.csv` and `identity.csv` files.

| Case ID | Transaction ID | Found in Transactions? | Found in Identity? |
| --- | --- | --- | --- |
| HHG-001 | 3514030 | Yes | No |
| HHG-002 | 3478782 | Yes | No |
| HHG-003 | 3530164 | Yes | No |
| HHG-004 | 3583227 | Yes | Yes |
| HHG-005 | 3523199 | Yes | Yes |
| HHG-006 | 3476682 | Yes | Yes |
| HHG-007 | 3514948 | Yes | No |
| HHG-008 | 3558054 | Yes | Yes |
| HHG-009 | 3581141 | Yes | Yes |
| HHG-010 | 3506725 | Yes | Yes |
| HHG-011 | 3583368 | Yes | Yes |
| HHG-012 | 3553342 | Yes | No |
| HHG-013 | 3526826 | Yes | Yes |
| HHG-014 | 3478561 | Yes | Yes |
| HHG-015 | 3464869 | Yes | Yes |
| HHG-016 | 3534820 | Yes | Yes |
| HHG-017 | 3450629 | Yes | Yes |
| HHG-018 | 3491361 | Yes | No |
| HHG-019 | 3503878 | Yes | Yes |
| HHG-020 | 3509359 | Yes | Yes |

## Summary
- **100% of the benchmark transactions** (20 out of 20) exist in the supplied `transactions.csv` file.
- **70% of the benchmark transactions** (14 out of 20) have associated device/identity records in the `identity.csv` file.
- The base dataset is complete and ready to be loaded into TigerGraph.
