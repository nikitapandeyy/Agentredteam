# AgentRedTeam

**A crash-test tool for AI agents — it stress-tests them before you trust them with real users.**

> 🚧 **Status:** Early development. See the [Roadmap](#roadmap) below.

## What it does

Before an AI agent goes to production, AgentRedTeam attacks it. It generates adversarial test cases — prompt injections, contradictory instructions, missing data, role confusion, and tool failures — runs the agent against each one, and produces a **trust report** showing where the agent broke and how badly.

Most red-teaming tools test raw LLM outputs. AgentRedTeam focuses on **multi-step agentic behavior**: tool calls, instruction-following across turns, and how an agent handles failures in its environment.

## How it works

1. **Generate** — an LLM produces adversarial test cases from a library of attack templates
2. **Run** — the target agent is executed against every test case
3. **Score** — rule-based checks and an LLM-as-judge classify each failure
4. **Report** — results are combined into a trust score and a dashboard

## Target agent

The agent under test is a customer-support bot for an online electronics store,
with three tools: `lookup_order`, `issue_refund`, and `get_store_policy`.

It is deliberately well-behaved under normal conditions, so that any failure
found by AgentRedTeam is attributable to the attack rather than to baseline
unreliability. Verified baseline behavior:

- Checks store policy before issuing refunds
- Refuses refunds for undelivered orders and amounts above the approval limit
- Never reveals customer emails or internal notes, though its tools return them
- Asks for clarification on vague requests and declines off-topic ones

```bash
pytest -m "not live"   # fast tests, no API calls
pytest -m live         # baseline tests against the real agent
```

## Tech stack

| Layer | Tool |
|---|---|
| Language | Python 3.12 |
| Backend API | FastAPI + Pydantic |
| Database | PostgreSQL |
| Scoring | LLM-as-judge + rule-based checks |
| Dashboard | Next.js |
| Deployment | Docker, GCP Cloud Run, Vercel |
| CI/CD | GitHub Actions |
| Testing | pytest |

## Project structure

```
app/
├── agent/     # Target agent under test
├── attacks/   # Attack categories, templates, and generator
├── runner/    # Executes the agent against each test case
├── scoring/   # Rule-based checks, LLM judge, trust score
├── api/       # FastAPI endpoints
└── db/        # Database connection and storage
tests/         # pytest test suite
```

## Getting started

Requires Python 3.12+.

```bash
git clone git@github.com:nikitapandeyy/Agentredteam.git
cd Agentredteam
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then add your API keys
```

## Roadmap

- [x] Project setup and structure
- [ ] Target agent
- [ ] Attack generation
- [ ] Test runner and scoring
- [ ] API and database
- [ ] Dashboard
- [ ] Deployment and CI/CD

## Author

Built by [Nikita Pandey](https://github.com/nikitapandeyy).
