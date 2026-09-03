# What "Flint" Is

**Flint is a small, powerful desktop computer that runs large AI language models at home.**

It is an NVIDIA DGX Spark — about the size of a Mac mini — with 128 GB of memory. That memory is what makes it special: it is big enough to hold a full modern AI model, so Flint does not need the internet to think. The models run locally, on Flint itself.

## What Flint does

Flint hosts one main AI model — **Qwen3.8-27B** — plus a shelf of smaller helper models. They power:

- **Coding agents** — AI assistants (called pi, OpenCode, or Claude Code) that can read, write, and fix code across your projects. Flint is the "brain" they talk to. You can run one of these agents from any computer on your home network, and Flint does the heavy thinking.
- **A chat website** — a friendly web page (Open Web UI) where you can just talk to the model.
- **Special helpers** — a model that reads images, a model that summarizes long text, a model that turns words into number vectors for search, and a research-grade backup model.

The main model can:

- **Think before answering** — it works through hard problems step by step, and you can see the thinking
- **See images** — you can show it a screenshot, a diagram, or a photo
- **Use tools** — it can look things up or take actions on its own, which is what makes the coding agents possible
- **Hold very long conversations** — up to about 200,000 words of context in one go

## How you reach the chat website

**From any device on your home network:** open `https://chat.testerlab.online` in a browser. It shows the green lock, just like any trusted website — but the traffic never leaves your house. (A small program called Caddy points the address to Flint and keeps the connection secure.)

**From this machine directly:** `http://localhost:3000`

The page is private to your network. People on the internet cannot reach it.

## What is running on it

| Service | Plain-English job |
|---|---|
| **The main model** (SGLang) | The big "brain" — always on, always ready |
| **LiteLLM** | The traffic controller — one front door for every program that wants to talk to the brain |
| **llama-swap** | The shelf of helper models — they wake up when needed and go back to sleep to save memory |
| **Open Web UI** | A normal chat website for humans |
| **Caddy** | The doorbell — gives the chat website its clean address and secure connection |
| **Prometheus + Grafana** | The instrument panel — health, speed, and memory gauges |

## The one rule that matters

Flint is powerful, but it has a limit: it cannot run too many big models at once. If you overload it, the whole machine can freeze and need a restart. In practice this means: *one big helper model at a time*. The system watches itself and will tell you (or restart things) if memory gets tight.

## How people use it

Any device on your home network can connect. A laptop on the couch can run a coding agent that actually thinks on Flint, in the next room. Friends on your network can open the chat website at the address above. Everything speaks the same standard "language" (an OpenAI-compatible interface), so most AI tools work with it out of the box.

---

*Technical details live in the guides: [main-model.md](guides/main-model.md), [reverse-proxy.md](guides/reverse-proxy.md), [monitoring.md](guides/monitoring.md).*
