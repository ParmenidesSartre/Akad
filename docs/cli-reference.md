# CLI Reference

```
akad infer     --name NAME      [--format parquet|sql]  [--location PATH | --connection-string URL --table-name NAME]  [--output PATH]
akad check     --contract PATH
akad publish   --contract PATH  --registry-url URL
akad validate  --contract PATH  [--registry-url URL]  [--output text|json]
akad list      --registry-url URL
akad history   --name NAME      --registry-url URL     [--limit N]
```

| Command | Purpose | CI-friendly |
|---|---|---|
| `akad infer` | Profile an existing dataset and scaffold a starter contract YAML | — |
| `akad check` | Parse and validate contract YAML syntax without touching data | Yes — catches typos before they hit a pipeline |
| `akad publish` | Register a contract version with the registry | — |
| `akad validate` | Run full validation against the dataset; exits `1` on breach | Yes — fail the build on a breach |
| `akad list` | List all current contracts in the registry | — |
| `akad history` | Show recent validation runs for a contract | — |

## `akad infer` — scaffold a starter contract

Profiles an existing dataset and writes a starter contract YAML — column types, nullability, low-cardinality `allowed_values`, key-like column quality rules, and a volume band around the observed row count.

```bash
akad infer --name daily_sales --location data/daily_sales.parquet \
  --owner-team "Data Engineering" --owner-email data@example.com \
  --output contracts/daily_sales.yaml
```

For a SQL dataset, use `--format sql --connection-string ... --table-name ...` instead of `--location`.

This is a **starting point, not a finished contract** — every inferred rule reflects only what the data looked like when profiled, not the business rules it's supposed to follow:

- `allowed_values` is only inferred for string columns where values repeat and stay under a cardinality cap — but it still only knows about values seen in the sample. A rare-but-valid value not present when you ran `infer` will show up as a breach later.
- Volume bounds are a 0.5×–2× band around the observed row count — adjust to your pipeline's actual expected range.
- `on_breach` always defaults to `warn` — switch to `fail` deliberately once you trust the contract.
- Freshness rules are never inferred — there's no reliable signal for `max_age_hours` from a single snapshot.

Review and tighten the output before relying on it in CI or production.
