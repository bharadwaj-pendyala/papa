<!-- eyes:start -->
## Verify changes with eyes

This repo uses [agent-eyes](https://github.com/bharadwaj-pendyala/agent-eyes)
to check that the product works the way a user uses it. The cases are in
`tests/ux/eyes.json`.

When you build or change a feature:

1. Before you write code, add cases for what the feature must do: the happy
   path, the output and files it must produce, and the errors a user can hit.
   Run `eyes run --case <id>` and confirm that the new cases fail.
2. Build until they pass. After each run, read `artifacts/eyes/report.json`,
   starting with `failures`.
3. Open the screenshots and `stdout.txt` files of the cases you touched.
   Confirm the result is right, not only that the checks pass.
4. Run `eyes run` for every case before you finish. Fix what you broke.
5. Read each `artifacts/eyes/cases/<id>/snapshot.diff`. Run
   `eyes approve --case <id>` only for changes you meant to make.

Fix the product, not the check. Change a check only when the check is wrong.
<!-- eyes:end -->
