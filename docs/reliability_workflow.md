# Independent coding workflow

I use separately recorded ratings to assess whether the code definitions can be applied consistently. The current packet contains all 67 recorded units from three complete ROE sections. It includes structural units with no active codes and retains exact text and source-page context. It omits reference labels, primary codes, stances and coding rationales.

The packet and first-pass reference are frozen with file fingerprints. The original codebook and protocol amendment are also fingerprinted. The reference file is outside the rater directory. The comparison uses a preserved first-pass ledger snapshot, so later case entry can continue without changing the reference. Changes to packet boundaries or code definitions require a new packet version.

## Collect ratings

Export a portable copy for a separate rater:

```sh
./research reliability-kit --output reports/independent_coding_kit_2026-10-03.zip
```

The ZIP contains the unchanged frozen packet, a blank workspace, the original codebook and the protocol amendment. It preserves the folder structure needed by the definition links. Extract the entire archive before opening the HTML file. Reference labels, the empirical ledger, research findings and completed ratings are excluded. The export rejects modified workspace markup or filled-in blank forms and preserves existing output files. The [current kit](../reports/independent_coding_kit_2026-10-03.zip) is prepared for collection; no ratings have been received.

1. Open [the coding workspace](../data/research/reliability/three-orders-2026-10-02/rater/index.html). Give each rater only the `rater` directory, the original codebook and the protocol amendment. The two linked definition files must remain at their project locations or be supplied alongside the packet.
2. Read the definitions and complete the units independently. Use the source-page context to resolve cross-page paragraphs and attribution. Mark every code as present or absent, including all-zero units. Record ambiguity in the notes.
3. Enter the actual rater identity and document whether reference labels were concealed. Start and completion times are recorded by workspace activity. Save a draft to resume later; no ratings are stored automatically after the page closes.
4. Export completed ratings. The workspace requires all 11 codes for each of the 67 units. A draft is not a completed observation file.
5. Collect the second file separately if the intended comparison is human inter-rater agreement. Do not reuse the same rater under another name. Keep raw exports unchanged and record any later adjudication separately.

The default packet contains three complete orders, not a representative reliability sample of all 15 planned orders. The packet must be extended under a documented sampling rule once the empirical sample and coding coverage are complete.

## Validate and calculate agreement

Verify the frozen workspace:

```sh
./research reliability-packet
```

Evaluate one completed human file against the documented assisted first pass:

```sh
./research reliability-check /absolute/path/ratings-a.json --output reports/reliability-comparison.json
```

Evaluate two independently completed human files:

```sh
./research reliability-check /absolute/path/ratings-a.json \
  --second-ratings /absolute/path/ratings-b.json \
  --output reports/human-inter-rater-agreement.json
```

The output file must be new; existing results are preserved. The importer rejects changed packet inputs, missing units, duplicate units, blanks, booleans, invalid code lists, missing blinding documentation, identical reported identities in a two-rater comparison and implausible timestamps. Rating activity must follow the packet freeze and precede import.

## Interpret the result

The report calculates Cohen's kappa separately for each code, alongside raw agreement, marginal counts and the four cells of the binary agreement table. The planned 0.70 target applies to MKT, PEER, OWN, GRAD and CONC. A code with no variation can have undefined kappa even when all ratings agree; it does not establish perfect reliability or satisfy the target.

A human-to-first-pass comparison and human inter-rater agreement are reported as different comparison types. Identity and blinding remain reported attestations. File checks cannot authenticate a person or independently prove that reference labels were concealed. Agreement from clustered paragraphs is also not evidence that three independent cases represent the entire sample.

No completed independent observation files exist in the current release. The workspace is ready for collection; independent reliability remains unmeasured.
