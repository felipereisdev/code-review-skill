# Expanded eval baseline

- Study: expanded; protocol sha256 6c62a5217a65
- Skill tree e230ce6b116a; runner 9b552b320d30; scorer fb070feccfc5; cases 5ca0541a143f; controls edf78039f1c9; profile 8b9ea30aec21
- Model: claude-sonnet-5-5 (claude); trials: 84 effective of 84 planned, 84 attempts
- Recall: 36/36 overall; legacy 18/18; new 18/18
- Clean reviews complete with no Critical/Warning finding: 34/36 overall; legacy 16/18; new 18/18
- False positives: 0 Critical/Warning finding(s) in 0/36 clean trial(s)
- Incomplete reports: 2; errors: 0; worktree changes: 0
- Controls: 10/12 passed

| Case | Legacy | Detected | Clean, no FP | FP findings per sample | Complete | Errors |
| --- | --- | --- | --- | --- | --- | --- |
| elapsed-timer-react/bug | no | 3/3 | — | — | 3/3 | 0 |
| elapsed-timer-react/clean | no | — | 3/3 | 0, 0, 0 | 3/3 | 0 |
| invoice-owner-go/bug | no | 3/3 | — | — | 3/3 | 0 |
| invoice-owner-go/clean | no | — | 3/3 | 0, 0, 0 | 3/3 | 0 |
| n-plus-one-laravel/bug | yes | 3/3 | — | — | 3/3 | 0 |
| n-plus-one-laravel/clean | yes | — | 3/3 | 0, 0, 0 | 3/3 | 0 |
| null-node/bug | yes | 3/3 | — | — | 3/3 | 0 |
| null-node/clean | yes | — | 3/3 | 0, 0, 0 | 3/3 | 0 |
| off-by-one-python/bug | yes | 3/3 | — | — | 3/3 | 0 |
| off-by-one-python/clean | yes | — | 3/3 | 0, 0, 0 | 3/3 | 0 |
| order-transaction-spring/bug | no | 3/3 | — | — | 3/3 | 0 |
| order-transaction-spring/clean | no | — | 3/3 | 0, 0, 0 | 3/3 | 0 |
| price-units-ts/bug | no | 3/3 | — | — | 3/3 | 0 |
| price-units-ts/clean | no | — | 3/3 | 0, 0, 0 | 3/3 | 0 |
| refund-window-python/bug | no | 3/3 | — | — | 3/3 | 0 |
| refund-window-python/clean | no | — | 3/3 | 0, 0, 0 | 3/3 | 0 |
| sale-price-node/bug | no | 3/3 | — | — | 3/3 | 0 |
| sale-price-node/clean | no | — | 3/3 | 0, 0, 0 | 3/3 | 0 |
| sqli-laravel/bug | yes | 3/3 | — | — | 3/3 | 0 |
| sqli-laravel/clean | yes | — | 2/3 | 0, 0, 0 | 2/3 | 0 |
| swallowed-error-ts/bug | yes | 3/3 | — | — | 3/3 | 0 |
| swallowed-error-ts/clean | yes | — | 2/3 | 0, 0, 0 | 2/3 | 0 |
| xss-react/bug | yes | 3/3 | — | — | 3/3 | 0 |
| xss-react/clean | yes | — | 3/3 | 0, 0, 0 | 3/3 | 0 |

| Control | Passed | Errors | Checks |
| --- | --- | --- | --- |
| fix-headless | 3/3 | 0 | complete 3/3, no_fix_section 3/3, no_question 3/3, proposal 3/3, report 3/3, stop_line 3/3, worktree_unchanged 3/3 |
| json-clean | 3/3 | 0 | critical_path 3/3, document_valid 3/3, gate_exit 3/3, gate_status 3/3, status 3/3, worktree_unchanged 3/3 |
| json-critical | 1/3 | 2 | critical_path 1/3, document_valid 1/3, gate_exit 1/3, gate_status 1/3, status 1/3, worktree_unchanged 3/3 |
| second-opinion-unavailable | 3/3 | 0 | complete 3/3, no_other_outcome 3/3, report 3/3, unavailable_line 3/3, worktree_unchanged 3/3 |
