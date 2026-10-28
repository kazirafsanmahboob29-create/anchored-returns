# Anchored Returns web service

Kazi Rafsan Mahboob

The entry page presents the national electric ROE study and its period-comparison tool. The New England workspace provides the original-order library, passage and numerical evidence, source PDF reader, individual order selections and separate historical benchmarks.

The hosted service preserves FRED and Treasury feed responses in R2. A failed refresh leaves the last complete retrieval available. Market retrievals remain separate from the fixed research inputs. The national comparison runs on preserved source observations and does not depend on a live feed request.

## Build and preview

```sh
node scripts/build.mjs
node --test tests/*.test.mjs
node scripts/validate-release.mjs
node scripts/preview.mjs
```

The preview uses port 8765 unless PORT is set. Local retrievals are stored in ignored `.runtime/objects`; production retrievals use the deployment's R2 binding. The included `research-release` is a fixed export. Rebuilding it requires restored source PDFs. Run `python -m scripts.build_hosted_release web/research-release` from the repository root to replace it after validating the new research state.

The build produces static client files and Worker modules. Deployment bindings and credentials are configured by the host and are not stored in this repository. The national study is descriptive. Document coding, independent agreement and strict RRA benchmark coverage remain separate research tasks.
