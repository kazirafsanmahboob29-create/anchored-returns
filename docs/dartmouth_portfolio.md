# Portfolio publication

The current portfolio is [kazirafsanmahboob.host.dartmouth.edu](https://kazirafsanmahboob.host.dartmouth.edu/). The [research article](https://kazirafsanmahboob.host.dartmouth.edu/research/anchored-returns/) presents the question, methods, figures and findings. The separate [workbench](https://kazirafsanmahboob.host.dartmouth.edu/tools/anchored-returns/) provides the browser calculations. The [GitHub repository](https://github.com/kazirafsanmahboob29-create/anchored-returns) distributes the research code and included data.

## What this repository contains

- `presentation/` is the local research interface. Start it with the snapshot command in the [reproduction guide](REPRODUCIBILITY.md).
- `wordpress/` is the portable application export, including the browser models and official Treasury and BLS connectors.
- `portfolio/` contains the earlier Journeys page fragments and their builder inputs. Its WordPress IDs and template instructions apply to that earlier publication, not the current host.
- `web/` contains the optional Worker service and a preserved export. Server storage, PDF delivery and deployment bindings require a configured host.

The current WordPress theme is maintained outside this repository. GitHub changes do not automatically update the portfolio. Original source files may still have recorded Journeys media URLs; those remain source locations rather than the canonical article address.

## Updating the published research

1. Rebuild and check the affected research outputs before changing a reported finding.
2. Keep the dated inputs and release manifests that support the old result.
3. Update the article and workbench through the current WordPress installation. Upload changed figures and record their media URLs.
4. Check the public article, workbench, downloads, figure loading and narrow-screen layout.
5. Keep the repository README and article consistent about sample coverage, data vintage and verification status.

A presentation change does not alter a quoted source or an original coding record. Native R checks are recorded in the research release; prepared Stata syntax is not evidence of an executed Stata run.
