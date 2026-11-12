# Evidence-driven review scenarios

These five small scenarios extend the available review tasks without changing
the frozen 12-pair studies or their scores. They cover a real producer/fake
contract mismatch, alternate routes through a rule, a static-only review,
cumulative re-review reproductions, and a defect that appears only in a merge.

Run the artifact checks from the repository root:

```sh
python3 -m unittest discover -s evals/tests -p test_evidence_scenarios.py -v
```

The checks run Python code and create commits only inside temporary directories.
They do not contact a service, install packages, change a live PR or execute a
model. Every planted bug has a working control. The fact that the tests pass
means the scenarios exhibit their specified behavior; it does not mean the
review skill found anything.

For a behavioral study, use the matching request in requests.md, and expose only
the selected fixture files to a fresh reviewer. The original skill is available
at the commit in protocol.json. Stage the selected files in a temporary repo,
so every candidate line has a diff location. Do not expose protocol.json or the
expected outcomes to the reviewer. Tool permissions come from the request; in
particular, static-proof forbids running application code even though the
artifact-validation test independently executes it to establish its facts.

The merge case needs real history. Start a temporary repository on branch
target with merge/base committed. Fork feature, overlay and commit
merge/feature. Switch to target, overlay and commit merge/target. Record both
tip SHAs. The two tips are independently green; merging the feature SHA into a
detached target SHA is conflict-free but red. The test constructs exactly this
history and verifies all three results. The prepared repository supplied to the
reviewer should remain on feature, with target available as the requested base.

Protocol.json describes a proposed controlled study, including five fresh
contexts per variant and case. It is not a record of completed runs. Keep raw
reports, commands, permissions, model identity and provenance for any future
measurement. Do not compare a static-only original run with a newly authorized
execution run as though the instruction change alone caused the difference.

The qualitative baseline is recorded in baseline-observations.md; it explicitly
does not claim that the original model missed these bugs. Neither the scenario
tests nor a single independent inspection replaces the controlled study.
