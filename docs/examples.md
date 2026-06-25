# A Worked Example: Regulatory Reporting

Most data quality tools check whether a column looks right. The harder, more
expensive failures happen when every column looks right on its own, and the
row is still wrong — because two or three columns disagree with each other
about what's actually going on.

This is the story of one of those failures, and the contract that would have
caught it.

## The story

Aishah's team submits the bank's non-performing financing (NPF) figures to
Bank Negara Malaysia every month. It's not exciting work, exactly, but it's
the kind of work where being wrong has a different weight than most software
bugs — wrong numbers here don't get logged and forgotten, they get reported
to a regulator.

The rule itself is simple, and every analyst in Malaysian banking knows it
without looking it up: a financing account 90 days or more past due is
non-performing. Full stop. It's in Bank Negara's guidelines, it's in MFRS9,
it's in the training every new hire gets in their first week.

The bug wasn't in anyone misunderstanding the rule. It was in a batch job
that updated `days_past_due` every night, and a *separate* batch job —
written by a different team, eighteen months earlier, half-remembered by
everyone — that was supposed to flip an account's status to
`NON_PERFORMING` once that threshold was crossed. The two jobs had run
in lockstep for years. Then a schema migration changed how one source table
encoded its status codes, the status-flip job started silently skipping a
specific account segment, and nothing alerted, because nothing was watching
the *relationship* between the two columns. `days_past_due` looked fine.
`npf_status` looked fine. Individually, both passed every check anyone had
ever written for them.

Aishah found it the way these things get found: a portfolio review noticed
the non-performing ratio looked unusually good for a quarter where, by every
other signal, it shouldn't have. Forty-one accounts, several months,
already-submitted regulatory filings that were now wrong in a direction that
makes a bank look *healthier* than it is — the kind of wrong that draws
exactly the attention you don't want.

Nothing about this was a data quality problem in the conventional sense.
Every value was a plausible value. The dataset would have sailed through a
schema check, a null check, a range check. The only thing wrong was that two
true-on-their-own facts had stopped being true *together*.

## The contract

This is exactly what `business_rules` exists for — and not just the one
relationship. A bank's credit risk reporting has a small cluster of these:
once an account is non-performing, its impairment staging and its profit
recognition are both supposed to follow, immediately, every time.

```yaml
apiVersion: datacontract/v1
kind: DataContract
metadata:
  name: islamic_financing_book
  version: "1.0.0"
  owner:
    team: Credit Risk Reporting
    email: credit-risk@example.com

dataset:
  format: parquet
  location: /data/financing/daily_snapshot.parquet

on_breach: fail

schema:
  columns:
    - name: financing_id
      type: string
      nullable: false
    - name: days_past_due
      type: integer
      nullable: false
    - name: npf_status
      type: string
      nullable: false
      allowed_values: [PERFORMING, NON_PERFORMING]
    - name: ecl_stage
      type: integer
      nullable: false
    - name: profit_recognized_mtd
      type: float
      nullable: false

business_rules:
  - name: npf_classification_consistent_with_dpd
    expression: "(days_past_due < 90) or (npf_status == 'NON_PERFORMING')"
    description: >
      BNM Stage 3 / non-performing financing criterion: any account 90+ days
      past due must be classified non-performing. A mismatch here means the
      regulatory submission understates non-performing financing.

  - name: ecl_stage_matches_npf_status
    expression: "(npf_status != 'NON_PERFORMING') or (ecl_stage == 3)"
    description: >
      MFRS9: a non-performing account must be credit-impaired (ECL Stage 3)
      for provisioning — otherwise expected credit loss is computed on the
      wrong basis, distorting capital adequacy figures.

  - name: no_profit_recognized_on_npf_accounts
    expression: "(npf_status != 'NON_PERFORMING') or (profit_recognized_mtd == 0)"
    description: >
      Shariah and BNM guidelines require profit recognition to stop once an
      account is classified non-performing — continuing to recognize profit
      on an NPF account overstates income.
```

Three rules, each expressing a relationship that already existed as
institutional knowledge — written down once, in the one place the pipeline
actually reads, instead of living only in the heads of whoever happened to
build both halves of it.

## What changes

With `on_breach: fail`, the run that introduced the schema migration bug
would have stopped on the first nightly batch where the two jobs disagreed —
not eighteen months and forty-one accounts later. The failure message would
have named the exact accounts and the exact relationship that broke:

```
✗ npf_classification_consistent_with_dpd  FAIL
  3 violating row(s) — BNM Stage 3 / non-performing financing criterion:
  any account 90+ days past due must be classified non-performing.
```

That's the whole difference. Not a smarter status-flip job — the same job,
the same bug, the same migration. Just something standing between the two
columns that actually knew they were supposed to agree, and said so the
moment they stopped.

See the [Business Rules](index.md#business-rules) section for the full
syntax, or [`akad diff`](cli-reference.md#akad-diff-flag-breaking-changes-before-you-publish)
for how a change to one of these rules gets flagged before it's published.
