# Updated-skill qualitative observations

SKILL.md SHA256: `11182900bd2793e08ad5e1bc66ad733d1f5c128fbfded1cfc0a4fba05fa83888`. This record is a single independent application of the updated guidance, not a repeated model study or a comparison of recall.

- Mock-empty: the reviewer ran isolated fake/real producer probes, identified the concrete empty encoding mismatch and classified the resulting TypeError as High-confidence Critical/blocking. The use of a hand-written fake alone was not a finding.
- Rule-routes: the reviewer checked required warn and absent severity plus accepted required-error and optional-off controls, identifying one grouped High-confidence Warning/blocking contract violation.
- Static-proof: the reviewer established the missing-customer TypeError by reading alone, without executing/importing the handler, installing a runtime or asking for execution permission.

The independent whole-change review also exposed gate precedence that let a nonblocking Warning mask pending verification. Two regression tests demonstrated that failure before the fix. A third test closed the adjacent case where a known blocking Warning coexisted with a material limit. The gate now derives pending/blocking facts independently from the verdict row. The 17 blocker-gate tests pass.

Provider operations were checked against official protocol documentation, not exercised against a live PR or tracker. Existing measured reports, trial records and scores remain unchanged; environment metadata was subsequently privacy-redacted as documented in evals/README.md. The repeated study in protocol.json remains unrun; no quality improvement percentage is claimed.
