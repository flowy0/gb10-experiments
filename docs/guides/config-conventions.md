# Config Conventions

Rules for editing the YAML config files in this repo. Indentation is load-bearing in all three files — a wrong indent silently changes the structure.

## Universal rules

- **Never delete model definitions** — comment them out with `# ` (preserves rollback history).
- **Validate after every edit:**
  - llama-swap: `python3 -c "import yaml; yaml.safe_load(open('llama-swap/config.yaml'))"`
  - litellm: `python3 -c "import yaml; yaml.safe_load(open('litellm/config.yaml'))"`
  - compose: `docker compose -f docker-compose.yml config`
- **Use `sed -i` for group member changes**, not whole-file Python scripts.
- **Exact text match, not line numbers**, when adding entries near existing ones.
- **After config changes:** `docker compose restart llama-swap` (llama-swap reloads its config). For compose service flag changes: `docker compose up -d --force-recreate <service>`.
- **If a model definition gets corrupted:** restore with `git checkout HEAD -- llama-swap/config.yaml`.

## YAML indentation by file

### docker-compose.yml

| Element | Indent | Column | Example |
|---|---|---|---|
| Service key | 6 spaces | **7** | `      sglang-qwen38:` |
| Properties (`image:`, `runtime:`, `ports:`, `container_name:`, `cpuset:`) | 8 spaces | **9** | `        container_name:` |
| Nested items (`- "8888:8888"`, `- /model`) | 12 spaces | **13** | `            - "8888:8888"` |
| `command:` entries | 12 spaces | **13** | `            - /model` |
| `environment:` vars | 12 spaces | **13** | `            - HF_HOME=...` |
| Comment `#` + proper indent | 4+ spaces | varies | `    # commented service` |

### llama-swap/config.yaml

| Element | Indent | Example |
|---|---|---|
| Top-level keys (`models:`, `groups:`) | 0 spaces | `models:` |
| Model keys | 4 spaces | `    unsloth-gemma4-26b-a4b-qat-mtp2:` |
| Model properties (`name:`, `ttl:`, `cmd:`) | 8 spaces | `        name: "My Model"` |
| Block scalar `cmd:` content | 12 spaces | `            docker run --rm \` |
| Groups | 4 spaces | `    research:` |
| Group properties (`swap:`, `exclusive:`) | 8 spaces | `        swap: true` |
| Group members | 12 spaces | `            - unsloth-gemma4-26b-a4b-qat-mtp2:` |

### litellm/config.yaml

| Element | Indent | Example |
|---|---|---|
| `model_list:` | 0 spaces | `model_list:` |
| Model entries (`- model_name:`) | 2 spaces | `  - model_name:` |
| `litellm_params:` | 4 spaces | `    litellm_params:` |
| Sub-properties (`model:`, `api_base:`) | 6 spaces | `      model: openai/...` |
| `api_key:` | 6 spaces | `      api_key: dummy` |
| `model_info:` / `allowed_openai_params:` | 4 / 6 spaces | nested lists at 8 |
