# IMPLEMENTATION_PLAN.md — pairs-trading-honest-costs

This is a deliberately small, self-paced project — not sized like
`lob-alpha-engine` or `stat-arb-optimizer`. Suggested pacing assumes
roughly **4-5 hrs/week**, and the whole project should be completable in
under a month of part-time work. Resist the temptation to expand scope
during the build — see `PROJECT.md` §6 on keeping the tech stack minimal.

## Week 1: Research Design + Data + Cointegration Testing
- Phase 0, Phase 0.5 (research design, recorded before any data is
  downloaded), Phase 1, Phase 2
- Milestone: full record of every candidate pair tested, with test
  statistics and p-values, not just the winning pair

## Week 2: Signal + Gross Backtest
- Phase 3, Phase 4
- Milestone: look-ahead-bias test passes, gross-of-costs backtest
  produces a complete metrics set

## Week 3: Realistic Costs — the central deliverable
- Phase 5
- Do not rush this phase or treat it as a quick multiplier applied to
  Phase 4's results — the cost model should be genuinely thought through
  (what would a retail or small-fund trader actually pay to execute this
  strategy on this pair, at this frequency?)
- Milestone: `docs/results.md` complete with the gross-vs-net table and a
  specific, mechanistic explanation of the gap

## Week 4: CI + README (the actual deliverable)
- Phase 6, Phase 7 (optional), Phase 8
- Milestone: README structured exactly per `PROJECT.md` §9, reads as an
  honest research finding

## Dependency Notes

- Do not select the final pair (end of Phase 2) without recording the
  full set of pairs tested — this record cannot be reconstructed
  afterward if not kept at the time, and it's required for the
  multiple-testing disclosure.
- The cost model is decided in Phase 0.5, BEFORE any backtest is run —
  decide the cost assumptions on their own merits (what's realistic for
  this instrument/frequency), then apply them in Phase 5, rather than
  picking cost parameters that produce a particular narrative.
- This project's short timeline is intentional — if it starts expanding
  toward multiple pairs, multiple signal variants, or additional
  instruments, that's scope creep away from this project's actual point
  (depth of honesty on one simple, well-executed idea) and should be
  redirected back to the original scope.
