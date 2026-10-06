# Evaluation and evidence

Each original skill has three case classes: typical request, request outside scope, and missing mandatory input/connection. Actual synthetic inputs and responses are in [cases-and-responses.json](../evals/cases-and-responses.json); scope and limitations are in [summary.json](../evals/summary.json). These 81 text responses were interpreted by one independent evaluator in a shared context, followed by five targeted retests. They are not separate fresh-model invocations or 81 native runtime tests. Private native logs remain outside the public package. Planned skill-local portability cases retain their own execution status.

A static YAML pass checks structure. Existing offline tests check scripts and business invariants. Isolated native CLI runs check instruction loading and behavior on synthetic fixtures. User-global installation, ChatGPT account import, Cursor discovery, Claude/Cowork upload and Grok Bot saved-skill execution require separate live checks.

Critical checks include: unmatched revenue is not paid-search-attributed revenue; ROAS uses matched campaign cost and revenue; transport email metrics are not business outcomes; demand frequency is not invented without source; claims retain period, source and limitations; publication requires an actual external result; generated media requires file and visual QA.
