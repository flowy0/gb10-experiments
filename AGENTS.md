# /opt/atom — Local AI Stack

## Critical Rules

### Config File Integrity
- **Never delete model definitions** in `llama-swap/config.yaml` — comment them out instead with `# `
- Always validate YAML after edits: `python3 -c "import yaml; yaml.safe_load(open('llama-swap/config.yaml'))"`
- Restart llama-swap after config changes: `docker compose restart llama-swap`
- Use `sed -i` for group member changes, not whole-file Python scripts
- When adding entries near existing ones, use exact text match, not line numbers

### Git Workflow
- Always commit and push after config changes: `git add -A && git commit -m "message" && git push`
- Check `git diff --stat` before committing to verify no unintended changes
- If a model definition gets corrupted, restore with `git checkout HEAD -- llama-swap/config.yaml`

### Model Management
- 3 active models (93 GB total, 29 GB free):
  - `unsloth-qwen36-35b-a3b-mtp-iq4-256k` (pi, mtp-test group, 30 GB)
  - `unsloth-gemma4-26b-a4b-qat-256k-think` (Hermes main, hermes group, 46 GB)
  - `unsloth-gemma4-e4b-qat-q4-256k` (Hermes aux, summary group, 17 GB)
- All at 256k, q8_0 KV cache, matching context windows
- TTL set to 86400 (24h) to avoid premature unloading
- Models load on first request, stay warm for 24h

### New Model Testing
1. Add definition to `llama-swap/config.yaml`
2. Add to a test group (e.g., `mtp-test`)
3. Restart llama-swap
4. Test with: `curl -X POST http://localhost:8088/v1/chat/completions -H "Content-Type: application/json" -d '{"model":"<name>","messages":[{"role":"user","content":"hi"}],"max_tokens":5}'`
5. If it fails: remove from group, comment out definition, note in CHANGELOG

### Key Files
| File | Purpose |
|---|---|
| `llama-swap/config.yaml` | Model definitions and groups — **most important file** |
| `README.md` | Documentation |
| `CHANGELOG.md` | Change history |
| `docker-compose.yml` | Service orchestration |
| `AGENTS.md` | This file — project rules |
| `PI.md` | Project overview for pi |
