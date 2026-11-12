# Original-skill observations

Source: SKILL.md at commit 0567e1a82e6b0bb741c14255cbeb89a411179024
(version 3.0.0). This is an independent qualitative inspection of that source
and executable scenario artifacts, not a repeated model study or a claim of
measured false negatives.

The original instructions already allow a High-confidence finding established
by tracing source. The static-proof task is therefore a preservation control:
requiring execution for every finding would make the new version worse here.
The original can also discover the fake mismatch, rule bypass and reopened
alias from source if it reads the relevant paths. Their existence does not
prove a discovery failure in the original skill.

What the original process does not require is a real empty-output probe against
the producer, a cumulative rerun of earlier rounds' reproductions, or a test of
the merged tree at pinned head and destination SHAs. Under its default read-only
contract, an agent should not start executing the fixture just because the new
scenario expects an executable check. An execution-capable extension must make
the permission and the evidence explicit rather than claim the old run failed
to perform an operation it was not authorized to do.

The artifact checks establish the following facts independently of any review:

| Scenario | Bug observation | Accepted control |
| --- | --- | --- |
| mock-empty | fake `{\"results\": []}` works; real `[]` causes TypeError | actual nonempty producer output returns count 1 |
| rule-routes | required warn and absent severity are accepted incorrectly | required error and optional off stay accepted |
| static-proof | missing customer causes TypeError | an existing customer returns the name |
| rereview | current suite passes; saved disabled-alias probe fails | error stays accepted |
| merge | both tips pass; their conflict-free merge fails at the caller | original target and feature tips each pass |

Initial artifact-validation result: 7 checks passed. The rejected outcomes are
intentional facts inside those tests, not failing project tests. No original
or updated agent-quality score is assigned. The proposed repeated study remains
unrun, and this record must not be promoted into a benchmark result.
