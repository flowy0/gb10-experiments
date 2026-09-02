# Git Workflow

Every change to this repo — config edits, new models, benchmarks, doc updates — follows the same workflow.

## Rules

1. **Commit and push after every change:**
   ```bash
   git add -A && git commit -m "message" && git push
   ```
2. **Check `git diff --stat` before committing** to verify no unintended changes.
3. **Update `CHANGELOG.md`** with a dated entry for every change: new models, config changes, benchmarks, doc updates. Entries go at the top under a `## YYYY-MM-DD` header, newest first.
4. **Never delete model definitions** — comment them out so rollback is a two-line revert. If a definition gets corrupted, restore it:
   ```bash
   git checkout HEAD -- llama-swap/config.yaml
   ```
5. The `.gitignore` excludes some local artifacts (bench JSON run cards, model caches, build dirs). Run cards live in `docs/qwen38-test-runs/` locally and are summarized in the CHANGELOG rather than committed.

## History conventions

- The changelog is the primary history record. It documents incidents (with dates), flips, and measurements.
- `docs/HISTORICAL.md` holds previous stack configurations.
- Commit messages describe the what and the why (e.g. `promote: DFlash2 as main draft (soak PASS 200/200)`).
