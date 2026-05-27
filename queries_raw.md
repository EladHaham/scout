# Scout Phase 1 — Dogfooding Log

Repo: scout indexing itself
Indexed symbols: 151 (233 parsed, 72 selectively skipped)
Total unique queries: 9 (with 2 duplicate captures from `phase1_pull.py -n 1` being run twice)

---

## Query 1

- **Original prompt**: "Where is the structural hash computed? What does it hash?"
- **Constructed query**: `structural_hash`
- **Query type**: **targeted**
- **Fallback tier**: 2
- **Top score**: 0.435
- **Direct symbols returned**: structural_hash, SymbolNote, is_stale, SymbolContext, SymbolEdges, SymbolHit
- **Neighbor symbols returned**: \_build_signature, \_extract_symbols, \_get_language, \_notes_root, \_should_note, \_should_skip, build_call_graph, extract_lines, generate_notes, get_context, is_test_file, load_all_notes, load_note, main, parse, parse_file, save_call_graph, save_note
- **Token count**: 7989
- **Latency**: 1184ms
- **Did Claude answer well?** **yes**
- **What was missing (if not)?** Nothing — answer was precise: located `structural_hash` in `parsers/base.py:21-23`, showed the SHA-256 implementation, correctly distinguished how Python/TS handle it (name + signature only, body excluded) vs TOML/JSON (name + signature + full content), and tied it correctly to `is_stale` in `store.py:59-61` and the `dirty`/`skipped` flow in `generate_notes`.
- **Notes**: Interesting that this scored 0.435 (tier 2) despite being a bare symbol name. Likely because `structural_hash` is both a _function name_ and a _field name_ on `SymbolNote` — embedding similarity is competing across two different referents. The first six direct hits are all related types (SymbolNote, SymbolEdges, SymbolHit) plus the function itself. Worth noting: top hit was the function, but score-wise the related dataclasses crowded the result.

---

## Query 2

- **Original prompt**: "How does scout decide when an index is stale?"
- **Constructed query**: `index stale fingerprint`
- **Query type**: **targeted**
- **Fallback tier**: 2
- **Top score**: 0.408
- **Direct symbols returned**: IndexStatus, repo_state_fingerprint, \_IndexState, is_stale, \_IndexState.status, \_IndexState.\_run
- **Neighbor symbols returned**: RepoMapResult, \_build_instructions, \_current_fingerprint, \_git_output, \_index_is_stale, \_load_repo_map, \_save_index_fingerprint, build_retrieval_index, create_server, generate_notes, get_repo_map, load_cached_map, log_notes_run, main, normalize_repo_path, save_cached_map, stdout_to_stderr
- **Token count**: 6908
- **Latency**: 314ms
- **Did Claude answer well?** **yes**
- **What was missing (if not)?** Nothing — Claude correctly identified the _two distinct layers_ of staleness (repo-wide fingerprint, per-symbol structural hash), located both in the right files (`server.py:48-52` and `store.py:59-61`), traced the three trigger sites (`create_server`, `scout_context`, explicit `scout_notes`), and correctly described the subtle interaction with `below_threshold` — that small-change runs don't update the fingerprint, so the repo stays marked stale.
- **Notes**: This one is a strong tier-2 hit. The retrieval gave Claude all the pieces (`_index_is_stale`, `repo_state_fingerprint`, `_save_index_fingerprint`, `_current_fingerprint`, `_IndexState._run`) and Claude assembled them correctly. Demonstrates that tier-2 with a good spread of neighbors is _functionally_ as good as tier-1 for multi-component answers.

---

## Query 3

- **Original prompt**: "How does indexing work end to end?"
- **Constructed query**: `build_retrieval_index embed_texts`
- **Query type**: **orientational**
- **Fallback tier**: 1
- **Top score**: 0.540
- **Direct symbols returned**: embed_texts, build_index, \_IndexState.\_run, IndexEntry, embed_query, QueryDetail
- **Neighbor symbols returned**: ScoutConfig, \_current_fingerprint, \_embedding_cache_path, \_get_client, \_hash_text, \_index_path, \_load_cache, \_save_cache, \_save_index_fingerprint, build_retrieval_index, generate_notes, get_context, load_config, load_index, log_notes_run, stdout_to_stderr
- **Token count**: 7058
- **Latency**: 314ms
- **Did Claude answer well?** **yes**
- **What was missing (if not)?** Nothing — produced a complete six-step pipeline writeup, correctly identified the two-stage decoupling (note generation vs. embedding), explained the `MIN_DIRTY_FOR_API` gate, called out that only `purpose` is embedded (not body or signature), described the file:symbol compound key disambiguation, and named all the on-disk artifacts with their roles.
- **Notes**: **Key finding.** This is the most orientational query possible, and Claude answered it excellently — but the constructed query was _narrow_ (`build_retrieval_index embed_texts`), and the transcript shows Claude made **multiple iterative scout_context calls** to fill in gaps ("Let me pull a few more pieces to fill in gaps I don't have yet — embedding, building the vector index, and the call graph internals"). The retrieval alone wasn't comprehensive; the **multi-call iteration** is what made the answer comprehensive. This contradicts the plan's prediction that orientational queries would fail at function-level granularity. The real finding: orientational queries succeed not because retrieval is good at them, but because the MCP architecture lets the LLM iterate.

---

## Query 4 (duplicate capture of Query 3)

Skipping — same data as Query 3, captured because `phase1_pull.py -n 1` was run twice between Claude queries.

---

## Query 5

- **Original prompt**: "What's the architecture? What are the main pieces and how do they connect?"
- **Constructed query**: `scout-app electron main`
- **Query type**: **orientational**
- **Fallback tier**: 1
- **Top score**: 0.459
- **Direct symbols returned**: load_config, findScoutMcp, writeState, ScoutConfig, build_index, App
- **Neighbor symbols returned**: \_index_path, build_retrieval_index, embed_query, embed_texts, get_context, save_default_config
- **Token count**: 4278
- **Latency**: 341ms
- **Did Claude answer well?** **yes**
- **What was missing (if not)?** Nothing structurally — produced a 1000-word architecture overview with an ASCII diagram, correctly identified the three top-level pieces (core Python lib, MCP server, Electron dashboard), described the strict downward dependency direction (`domain ← adapters/storage ← notes/retrieval ← service.py`), and accurately named the "what's notably absent" properties (no DB, no vector DB, no file watcher, no HTTP server).
- **Notes**: **Same finding as Query 3 in a more striking form.** The constructed query (`scout-app electron main`) is _narrow_ and the top hits are dashboard-side symbols (`findScoutMcp`, `writeState`, `App`), but the _answer_ is a sweeping architectural overview that barely uses what retrieval returned. Claude leaned heavily on the **repo map injected into the server's instructions** plus its general code-reading ability. The retrieval was almost incidental. This is the cleanest example of "scout is useful but not central for sweeping orientational queries."

---

## Query 6

- **Original prompt**: "What does MIN_DIRTY_FOR_API do?"
- **Constructed query**: `MIN_DIRTY_FOR_API threshold notes`
- **Query type**: **targeted**
- **Fallback tier**: 2
- **Top score**: 0.310
- **Direct symbols returned**: NotesRunEvent, \_looks_like_junk_path, readEnvKeys, NotesResult, Repo
- **Neighbor symbols returned**: \_build_repo_map, \_candidate_repo_map_path, \_collect_repo_files, \_filter_repo_map, generate_notes
- **Token count**: 3037
- **Latency**: 984ms
- **Did Claude answer well?** **partial → yes after retry**
- **What was missing (if not)?** The first retrieval missed entirely — top hits were `NotesRunEvent`, `_looks_like_junk_path`, `readEnvKeys` (none of which contain `MIN_DIRTY_FOR_API`). Claude's first response was a _guess_ based on the constant's name ("It's likely a threshold constant meaning..."). On the user's explicit "ask scout" follow-up, Claude ran a more specific second search and got `generate_notes` in the neighbors, then correctly inferred the behavior from how it's _used_. Found the right answer but never found the _definition_ of the constant itself.
- **Notes**: **CRITICAL FINDING.** This is the cleanest "what doesn't work" data point in the whole batch. **Module-level constants are not indexed.** The parser (`parsers/python.py`) only emits `ParsedSymbol` for `ast.FunctionDef`, `ast.AsyncFunctionDef`, and `ast.ClassDef` — module-level assignments like `MIN_DIRTY_FOR_API = 5`, `_SOURCE_GLOBS = [...]`, `_SKIP_DIRS = {...}` have no notes, no embeddings, no retrieval target. Score 0.310 isn't "low confidence retrieval" — it's "I retrieved unrelated symbols because the actual thing you asked about doesn't exist in my index." This is invisible from the dashboard, which just shows a low score. **Fix:** extend the parser to emit module-level assignments as a new symbol type (`constant`). This is a real, actionable bug surfaced by dogfooding.

---

## Query 7

- **Original prompt**: "How does the call graph handle imports?"
- **Constructed query**: `build_call_graph imports`
- **Query type**: **targeted**
- **Fallback tier**: 1
- **Top score**: 0.550
- **Direct symbols returned**: build_call_graph, load_call_graph, save_call_graph, QueryDetail, build_parser, pyproject.toml
- **Neighbor symbols returned**: CallGraph, CallGraph.from_dict, SymbolEdges, \_extract_calls, \_extract_imports, \_find_node, \_graph_path, \_is_test_file, \_load_call_graph, generate_notes, main
- **Token count**: 6588
- **Latency**: 337ms
- **Did Claude answer well?** **yes**
- **What was missing (if not)?** Nothing — laid out the three-stage import handling correctly: `_extract_imports` builds the per-file name→module dict, `_extract_calls` classifies calls against the import map (bare names vs. attribute calls, with the `scout.` prefix check distinguishing internal vs. external), and `build_call_graph` resolves to internal symbols using exact match → `bare_names` fallback. Correctly noted Python-only limitation, test-file exclusion, and the class-walking bug fix.
- **Notes**: Strong tier-1 hit, clean execution. Worth noting Claude proactively called out the "first-seen wins for ambiguous bare names" footgun — that's the kind of thing my audit also flagged. The `pyproject.toml` direct hit at position 6 is amusing (irrelevant for an imports question) — symptom of TOML files being indexed as whole-file symbols with weak signatures.

---

## Query 8 (duplicate capture of Query 7)

Skipping — same data as Query 7.

---

## Query 9

- **Original prompt**: "What's in the README?"
- **Constructed query**: (used `scout_read_file` directly — no `scout_context` event logged)
- **Query type**: **targeted (file-level, not symbol-level)**
- **Fallback tier**: n/a
- **Top score**: n/a
- **Direct symbols returned**: n/a
- **Neighbor symbols returned**: n/a
- **Token count**: n/a
- **Latency**: n/a
- **Did Claude answer well?** **yes**
- **What was missing (if not)?** Nothing — accurate summary of the README, including the pipeline layers, language support, requirements, CLI commands, caching layout, and known limitations. Claude proactively noted the README's project-structure tree might not match current layout, offering to verify.
- **Notes**: **Finding.** Claude did _not_ call `scout_context` for this — it called `scout_read_file` directly. Correct routing: READMEs aren't symbols, retrieval would be the wrong tool. **`scout_read_file` is a legitimate secondary tool, not just retrieval scaffolding.** The MCP server gives Claude two tools and Claude picks the right one based on query shape. This wasn't in the plan's design-choices list — it should be.

---

## Query 10

- **Original prompt**: "What's wrong with the typescript parser?"
- **Constructed query**: (used `scout_read_file` on `parsers/typescript.py` plus a `scout_context` follow-up)
- **Query type**: **analytical**
- **Fallback tier**: see below
- **Top score**: see below
- **Direct symbols returned**: parse_file, parse, \_get_language, is_test_file, parse, parse
- **Neighbor symbols returned**: \_extract_symbols, generate_notes
- **Token count**: 4227
- **Latency**: 446ms
- **Constructed query (for the follow-up context call)**: `parse_file dispatcher languages`
- **Fallback tier (follow-up)**: 1
- **Top score (follow-up)**: 0.478
- **Did Claude answer well?** **YES — found 9 real bugs**
- **What was missing (if not)?** Nothing. Claude flagged: (1) nested classes silently dropped due to recursion gate, (2) decorated methods get wrong line ranges, (3) signature regex eats comma-separated params, (4) `export default () =>` and `export const foo: Handler = () =>` patterns missed, (5) same-name top-level functions collide because TS symbols aren't file-scoped, (6) `_should_note` treats `_foo` as private but ignores TS's actual `private`/`protected` keywords, (7) catch-all `except Exception: return []` swallows real bugs with no logging, (8) README's call-graph claim applies only to Python, (9) `namespace`/`module` declarations are never walked into.
- **Notes**: **MAJOR FINDING.** Claude used Scout to find real bugs in Scout that I missed in my code audit. Particularly damning: the signature regex bug (`re.sub(r":\s*[\w<>\[\]|&,\s]+", "", params_text)` includes a comma in the character class, so `(a: number, b: string)` collapses to `(a)` — meaning every multi-param TS function has a structurally wrong hash). This isn't a writeup point — it's a real bug that should be fixed before the post claims "TypeScript support." Three of the bugs are critical (nested classes, signature regex, namespace handling); the rest are real but lower priority. **This is the strongest argument for the post's thesis** — that good code retrieval makes code understanding (and bug-finding) materially faster.

---

## Query 11

- **Original prompt**: "Where does the threading happen, and what does it protect?"
- **Constructed query**: `threading Lock`
- **Query type**: **targeted**
- **Fallback tier**: 1
- **Top score**: 0.464
- **Direct symbols returned**: \_IndexState, \_IndexState.start, \_IndexState.\_run, ScoutEvent, \_IndexState.status, ScoutEvent
- **Neighbor symbols returned**: \_current_fingerprint, \_save_index_fingerprint, build_retrieval_index, create_server, generate_notes, log_notes_run, stdout_to_stderr
- **Token count**: 4777
- **Latency**: 432ms
- **Did Claude answer well?** **yes**
- **What was missing (if not)?** Nothing — correctly identified `_IndexState` as the only threading site, explained the lock's three protected fields (`running`, `last_result`, `last_error`), described the two race conditions it defends against (double-start, torn reads in `status()`), and proactively called out what the lock does _not_ protect (filesystem writes, reads during writes, multiple-repo case, the `stdout_to_stderr` global mutation race that only works because of the test-and-set).
- **Notes**: Strong tier-1 answer. The "what it does NOT protect" section was genuinely useful — Claude inferred concurrency implications I hadn't documented anywhere. Top hits were exactly the right symbols (`_IndexState` and its three methods). Demonstrates retrieval works well when the symbols are uniquely-named.

---

# Synthesis

## Distribution

- Targeted: 6 (queries 1, 2, 6, 7, 9, 11)
- Orientational: 2 (queries 3, 5)
- Analytical: 1 (query 10)

## Tier distribution (unique queries only)

- T1: 6
- T2: 3
- T3: 0
- T4: 0
- Not applicable (used `scout_read_file` instead): queries 9, 10

## Score distribution

- Highest: 0.550 (`build_call_graph imports`, tier 1)
- Lowest: 0.310 (`MIN_DIRTY_FOR_API threshold notes`, tier 2 — failed because constants aren't indexed)
- Average across 9 unique: ~0.466

## Findings

### Finding 1 — Constants aren't indexed (critical)

The parser only emits `ParsedSymbol` for functions, classes, and methods. Module-level assignments like `MIN_DIRTY_FOR_API` exist in the code but have no notes, no embeddings, no retrieval target. Query 6 demonstrated this cleanly. The failure is invisible from the dashboard (just looks like low-confidence retrieval). Concrete fix: extend the parser to emit `ast.Assign` nodes at module scope as a new `constant` symbol type.

### Finding 2 — The MCP architecture, not the retrieval algorithm, makes orientational queries work

Queries 3 and 5 both produced excellent answers despite narrow retrieval. The mechanism: the repo map injected into server instructions provides orientation; multiple `scout_context` calls from Claude fill in detail; Claude synthesizes. This contradicts the plan's prediction that orientational queries would fail at function-level granularity. The real story is more interesting than the predicted one: "function-level retrieval is narrow by design, but the MCP loop compensates."

### Finding 3 — `scout_read_file` is a real secondary tool

Queries 9 and 10 used `scout_read_file` instead of `scout_context`. Correct routing — READMEs and full source files aren't symbols. The tool surface is broader than just retrieval, and Claude picks correctly based on query shape. Worth elevating in the design-choices list — currently buried.

### Finding 4 — Scout found 9 real bugs in its own TypeScript parser

Query 10 produced a list of bugs in `parsers/typescript.py` that I missed in my own code audit. Three are critical (nested classes silently dropped, signature regex eats commas, namespace declarations ignored). The other six are real but lower priority. This is the strongest concrete demonstration of Scout's value — and the bugs should be fixed before the post claims first-class TypeScript support.

### Finding 5 — Dashboard cross-contamination is real but manageable

Most queries returned a mix of Python backend symbols and TypeScript dashboard symbols. Sometimes irrelevant (`QueryDetail` in a `build_call_graph imports` query), sometimes appropriate (`findScoutMcp` for an architecture overview). Not a blocker — the LLM filters effectively — but a data point for the "selective indexing" discussion. Could be addressed by adding `dashboard/` to `_SKIP_DIRS` or by file-type-aware retrieval weighting.

### Finding 6 — Tier 2 isn't a failure mode; it's a useful tier

3 of 9 queries landed in tier 2 and _all 3 produced excellent answers_. The plan implicitly framed tier 2 as a degradation step ("when confidence drops, widen the lens"), but tier 2 retrieval gave Claude exactly the right symbols plus useful neighbors for follow-up reasoning. The actual degradation story should be reframed: tier 2 is the _normal_ operating mode for many useful queries; only tier 3 and tier 4 would indicate genuine failure (and you never reached them).

## Best 2–3 examples for the post

### Hero "what works" example: Query 11 (threading)

- Targeted, tier 1, score 0.464
- Returns exactly the right cluster (`_IndexState`, `_IndexState.start`, `_IndexState._run`, `_IndexState.status`)
- Claude's answer was _better than the in-code documentation_ — it correctly inferred what the lock _doesn't_ protect, which isn't written down anywhere
- Cost: 4777 tokens, 432ms

### Hero "what doesn't work" example: Query 6 (MIN_DIRTY_FOR_API)

- Targeted, tier 2, score 0.310
- Retrieval returned unrelated symbols because constants aren't indexed
- Claude initially _guessed_ from the name; only after explicit "ask scout" did it run a second search and infer behavior from usage
- Failure mode is invisible from dashboard — just looks like low score
- Has a concrete, actionable fix

### Hero "unexpected" example: Query 10 (TypeScript bugs)

- Analytical query
- Used both `scout_read_file` and `scout_context`
- Found 9 real bugs in code I'd audited carefully twice
- Best concrete demonstration of Scout's value: "the tool that helps you understand code well enough to find bugs in it"

## What to do next

1. **Decide whether to fix the three critical TypeScript parser bugs before publishing.** The signature regex bug is bad enough that it's hard to claim "TS support" honestly.
2. **Document the constants-not-indexed limitation** in the README (or fix it — it's maybe a 20-line change to `parsers/python.py`).
3. **Start the post.** You have more than enough data. Three hero examples, six findings, two design-choice additions to surface (`scout_read_file` as a first-class tool, "tier 2 is not failure").
