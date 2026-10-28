# Working on the research code

Use a separate branch for a change. Describe the question or bug, the files affected and how the change was checked. A useful issue includes the command or browser action, expected behavior and the observed result.

## Data changes

Keep acquired source documents immutable. Record the publisher URL, retrieval date and SHA-256 hash before adding an observation. Corrections need the original value, replacement value, reason and source page. Do not edit a historical release to make it agree with a new result.

Missing observations stay missing unless a source resolves them. Synthetic data belong in software tests. A completed rating must come from an actual separate rating exercise with the required provenance.

## Code changes

Run `python -m scripts.check_calculations` for changes to calculations, browser tools or compiled outputs. Document-dependent checks need the separately restored original files. If an input or analysis file changes, rebuild its outputs and inspect any numerical differences before updating an artifact fingerprint.

Comments should explain choices that are not obvious from the code, such as a date cutoff, unit conversion, denominator or uncertainty estimator. Keep function descriptions short. Avoid comments that simply repeat the next line.

No account credentials, local virtual environments, private correspondence or hosting sessions belong in a commit. Third-party notices must remain with their files.
