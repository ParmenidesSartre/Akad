# CLI Reference

```
akad check     --contract PATH
akad publish   --contract PATH  --registry-url URL
akad validate  --contract PATH  [--registry-url URL]  [--output text|json]
akad list      --registry-url URL
akad history   --name NAME      --registry-url URL     [--limit N]
```

| Command | Purpose | CI-friendly |
|---|---|---|
| `akad check` | Parse and validate contract YAML syntax without touching data | Yes — catches typos before they hit a pipeline |
| `akad publish` | Register a contract version with the registry | — |
| `akad validate` | Run full validation against the dataset; exits `1` on breach | Yes — fail the build on a breach |
| `akad list` | List all current contracts in the registry | — |
| `akad history` | Show recent validation runs for a contract | — |
