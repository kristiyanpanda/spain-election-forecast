# Outputs of the 17 October 2026 run

A copy of `outputs/` as written by the provisional run with data to 17 October 2026 (commit
`2181471`), kept for comparison with later runs. `polls_long.parquet` is the poll file that run
used. The posterior trace (`traces/next.nc`, 286 MB) is not included.

Headline of that run, for 29 November: PP 131 seats (104-157), PSOE 107 (83-133), Vox 66 (48-87);
PP + Vox majority 93 %. It differs from later runs in method as well as data: it counted every
tracker release as a poll, gave each CIS-based series its own vote when centring house effects, and
moved assumed parts of Podemos's vote into other lists (see `docs/methods_note.md` §12 and §13).
