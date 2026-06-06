# Flint Bench v3

Long-context benchmark harness for Flint / GB10 local LLM testing via llama-swap.

This version merges two ideas:

1. Deterministic task scoring, like your `longctx_bench.py` / `longctx_tasks.py` setup.
2. Memory and pressure observability from the earlier scaffold.

It is designed to answer:

- Does 128K beat 64K for this model?
- Which long-context model should be used for code, research, or agent work?
- What is the memory/PSI cost while running each model?

## Folder structure

```text
/opt/atom/bench/
├── pyproject.toml
├── models.yaml
├── tasks.yaml
├── make_longctx_prompts.py
├── scorer.py
├── run_bench.py
├── analyze_results.py
├── run_generate_prompts.sh
├── run_all.sh
├── prompts/generated/
├── results/
└── logs/
```

## Install

```bash
cd /opt/atom
unzip flint-bench-v3.zip
mv flint-bench bench
cd /opt/atom/bench
uv sync
```

If `/opt/atom/bench` already exists:

```bash
cd /opt/atom
unzip flint-bench-v3.zip
cp -r flint-bench/* /opt/atom/bench/
cd /opt/atom/bench
uv sync
```

## Generate prompts

Generate all 32K/64K/128K synthetic prompts and answer keys:

```bash
cd /opt/atom/bench
./run_generate_prompts.sh --force
```

Generate only 64K and 128K:

```bash
./run_generate_prompts.sh --force --tiers 64k 128k
```

Generated prompts are stored in:

```text
prompts/generated/
```

Answer keys are stored in:

```text
prompts/generated/answer_keys.json
```

## Dry run

Preview tasks without calling models:

```bash
uv run python run_bench.py --dry --tiers 128k
```

## Run a focused benchmark

Recommended first run:

```bash
uv run python run_bench.py \
  --models qwen3-coder-30b-a3b-q4-64k granite-4.1-8b-q5-128k gemma4-26b-a4b-q4-128k \
  --tiers 64k 128k
```

Run only 128K code/repo tasks:

```bash
uv run python run_bench.py \
  --models qwen3-coder-30b-a3b-q4-128k granite-4.1-8b-q5-128k \
  --tiers 128k \
  --tasks duplicate_logic repo_architecture bug_risk refactor_plan
```

Run everything configured in `models.yaml` and `tasks.yaml`:

```bash
./run_all.sh
```

## Outputs

Each run writes:

```text
results/summary-YYYYMMDD-HHMMSS.csv
results/run-YYYYMMDD-HHMMSS.json
results/memory-YYYYMMDD-HHMMSS-MODEL.csv
results/response-YYYYMMDD-HHMMSS-MODEL-TASK.txt
results/raw-YYYYMMDD-HHMMSS-MODEL-TASK.json
```

The summary CSV includes:

- model
- task
- tier
- deterministic score
- score reason
- latency
- prompt size
- API token usage if returned
- raw response file
- memory file

The memory CSV includes:

- Docker memory for AI containers
- system MemAvailable
- swap usage
- PSI memory pressure

## Analyze latest results

```bash
uv run python analyze_results.py
```

Analyze a specific summary:

```bash
uv run python analyze_results.py results/summary-YYYYMMDD-HHMMSS.csv
```

## Important interpretation notes

- This is still synthetic, but it is harder than v1 because prompts have real size tiers and explicit ground truth.
- Use 64K vs 128K comparisons to decide whether the extra context is worth the memory and latency.
- A 128K model should not become default unless it improves repo recall, duplicate logic detection, long document synthesis, or instruction-following under depth.
- For first-pass safety, run 128K heavy models one at a time.

## Recommended routing tests

Default two-model candidate:

```text
unsloth-qwen3-coder-30b-a3b-q4-64k
+
unsloth-granite-4.1-8b-q5-128k
```

Specialist tests:

```text
long-context code:     unsloth-qwen3-coder-30b-a3b-q4-128k
long-context research: unsloth-granite-4.1-8b-q5-128k
long-context agent:    unsloth-gemma4-26b-a4b-q4-128k
budget long-context:   unsloth-granite-4.1-8b-q4-128k
```
