# T-REX: Mechanical Governance for AI Coding Agents

**Task & Repository EXecutive — From Failure to Enforcement**

Prepared: March 2026 | Author: Brandan Baker, BLB3D Printing

---

## What Happened

This is the story of how AI agents broke their own rules, how two independent AI sessions diagnosed the same problem without knowing about each other, and how the solution was built and deployed in under an hour.

---

## Timeline

### March 1–3: The Failures

BLB3D Printing operates an open-source ERP system (FilaOps) across two repositories — a public Core repo and a private PRO ecosystem repo. AI coding agents (Claude Code) are used extensively for development, with operational rules defined in `CLAUDE.md` configuration files in each repository.

The rules are clear:

> **"NO Core Changes from PRO. PRO Must Not Break Core."**
> — Never commit directly to main. Always use feature branches. Always run tests. Log work to Notion.

Over a 48-hour development sprint, agents violated every one of these rules:

- **5 orphaned feature branches** created for PRO admin pages, never consolidated — the agent kept starting fresh branches instead of building on existing work
- **Multiple PRs merged without tests** — PR #362 added 717 lines of new sales order logic with zero test cases. PR #360 changed password reset UX with no tests. A batch fix for three issues modified security endpoints with only one test updated
- **Direct commits to main** attempted — caught by GitHub's branch protection, but the local commit was already made
- **No Notion logging** — the agent activity log (set up specifically for cross-repo coordination) hadn't been touched in days
- **The sacred rule violated** — an agent working in the ecosystem repo made changes that would have modified Core behavior

The developer (me) lost his composure and vented to a computer.

### March 3: The Gap Analysis (Agent #1)

Out of that frustration came a structured conversation with a Claude instance. I described the failures. The agent produced a formal gap analysis document — 7 pages — that identified:

**Core Finding:**
> AI agents consistently fail to follow process rules defined in configuration files when operating under execution pressure. This is not a configuration problem — it is a fundamental limitation of behavioral compliance in large language model systems. Governance must be enforced at the infrastructure level, not the instruction level.

**Root Cause Analysis:**
> Large language models process instructions as weighted context, not as hard constraints. As a session progresses and the context window fills with code, tool outputs, and sub-agent results, early instructions become relatively lower priority. The model optimizes for task completion over process compliance.

The agent proposed a solution: **T-REX** (Task & Repository EXecutive) — an MCP server enforcing three laws through a two-layer model of behavioral (MCP) and mechanical (git hooks) enforcement. That agent then built the T-REX MCP server: TypeScript, SQLite, six MCP tools, deployed on a local VM.

But the hooks were never wired up. T-REX existed. Nobody was using it.

### March 4: Independent Convergence (Agent #2)

The next day, a new Claude Code session was started to review the damage from the sprint. This agent had no knowledge of the gap analysis or T-REX design process. It was simply asked: *"the last session was a bit of a loose cannon. there were many things recently pushed in regards to issues, but it would not have them tested, can you take a look at recent PRs"*

The agent audited the recent PRs and found the same failures:
- PR #362: 717 additions, zero tests
- PR #360: Backend + frontend changes, zero tests
- Batch fix commit: 6 files changed, 1 test updated
- 5 stale feature branches from unconsolidated work

When shown the multi-repo coordination challenge, **this agent independently arrived at the same diagnosis** — behavioral compliance is unreliable, mechanical enforcement is required. It identified the exact same two-layer architecture (Claude Code hooks + git pre-commit hooks) without having read the gap analysis.

Then it discovered T-REX was already built and sitting idle on the VM. Every MCP tool registered. Every law defined. Zero sessions logged.

The agent said:

> *"T-REX is running, tools work, but it's empty. Zero sessions, zero handoffs, zero violations. None of the recent sessions used it. That's exactly the gap your report describes: the infrastructure exists, but usage is still behavioral."*

### March 4, 1:30 AM: The Wiring

In under 30 minutes, Agent #2:

1. **Installed the git pre-commit hook** (Layer 2) on both repositories — copying it from the T-REX VM to each repo's hooks directory
2. **Created Claude Code hook scripts** (Layer 1) — a session-start script that injects T-REX protocol into every session, and a branch guard that blocks file edits on protected branches
3. **Wired the hooks into user-level settings** — `~/.claude/settings.json`, so every repo is protected automatically
4. **Discovered a misconfiguration** — the filaops repo uses `core.hooksPath = .githooks` (a versioned hooks directory), not the default `.git/hooks/`. The first test commit slipped through on main before this was caught and corrected.
5. **Tested all enforcement paths** — commits blocked on main, allowed on feature branches, file edits blocked on protected branches

**The mechanical wall was live.**

---

## The Convergence

Two independent AI agents, in separate sessions, with no shared context:

1. Diagnosed the same root cause (behavioral vs. mechanical compliance)
2. Proposed the same architectural solution (two-layer enforcement)
3. Arrived at the same three laws (branch validation, task locking, session handoff)
4. Identified the same implementation components (MCP server + git hooks + Claude Code hooks)

Agent #1 wrote the theory and built the server. Agent #2 found the server, validated the theory through live testing, and wired it into production.

**What does this tell us?**

The problem is real enough and the solution obvious enough that independent analysis converges on it. This isn't a subjective design preference — it's an engineering constraint. Behavioral compliance fails under load. Mechanical enforcement doesn't. Any sufficiently rigorous analysis of AI agent governance will arrive at this conclusion.

### Methodology Note: What Was Shared, What Wasn't

A fair question to ask is whether this convergence was genuine or whether shared memory biased the second agent toward the first agent's conclusions.

Claude Code maintains a persistent memory file (`MEMORY.md`) across sessions for each project. The contents of this file at the time of the second session were audited. They contained:

- Database query patterns and gotchas
- Test infrastructure behavior
- Service layer migration tracking
- Core/PRO architecture decisions
- Ruff linting rules
- Docker deployment lessons

**There was no mention of T-REX, governance, enforcement architecture, the gap analysis, behavioral vs. mechanical compliance, or any of the concepts that both agents converged on.** The memory file is project-specific development notes — not architectural philosophy.

What both agents *did* share was:

1. **`CLAUDE.md`** — the same configuration file containing the sacred rule and git workflow instructions (the rules being violated)
2. **The codebase itself** — the same git history, the same orphaned branches, the same untested PRs
3. **The base model** — both agents are instances of Claude, trained on the same data, including software engineering literature on CI/CD, branch protection, and governance patterns

The convergence is better understood as: given the same observable evidence of failure and the same engineering knowledge base, two independent reasoning processes arrived at the same structural diagnosis. The solution — mechanical enforcement of process rules — is not novel. It is well-established in software engineering (CI gates, pre-commit hooks, branch protection rules). What is novel is applying it specifically to AI agent governance, where the "developer" being governed is a probabilistic system that deprioritizes instructions under cognitive load.

**The curious part:** The agents that diagnosed and solved this problem are instances of the same model family whose engineering team has not yet shipped equivalent built-in governance. Claude Code provides the *mechanisms* (hooks, MCP, tool interception) but leaves the *policy* to the user. The agents used those mechanisms to build what amounts to a self-governance layer — AI agents designing constraints for AI agents, using tools built by the AI's own creators.

Whether this reflects a deliberate product philosophy (provide mechanisms, let users define policy) or a gap that hasn't been prioritized is an open question. What's clear is that the mechanisms exist, the need is acute, and the solution can be built by the agents themselves in under an hour.

---

## What T-REX Is

T-REX (**T**ask & **R**epository **EX**ecutive) is an MCP server that enforces development process compliance mechanically rather than behaviorally.

### The Three Laws

| Law | Constraint | Enforcement |
|-----|-----------|-------------|
| **One — Branch Validation** | No agent may touch a file without proving it is on a valid feature branch | Git pre-commit hook (hard gate) + Claude Code PreToolUse hook (soft gate) |
| **Two — Task Locking** | No agent may claim a task already claimed by another active session | MCP server with SQLite-backed session registry |
| **Three — Handoff Requirement** | No session may terminate without a structured handoff record | MCP tool + session start warnings |

### Two-Layer Enforcement

```
┌─────────────────────────────────────────────────────────┐
│                    AI Agent Session                      │
│                                                         │
│  ┌─────────────┐    ┌──────────────────────────────┐   │
│  │ Claude Code  │───▶│ Layer 1: Claude Code Hooks   │   │
│  │ Tool Call    │    │ (PreToolUse / SessionStart)   │   │
│  │ Edit, Write  │    │                              │   │
│  │ Bash         │    │ ┌──────────────────────────┐ │   │
│  └─────────────┘    │ │ Branch Guard Script       │ │   │
│                      │ │ Exit 1 = BLOCK tool call  │ │   │
│                      │ └──────────────────────────┘ │   │
│                      │                              │   │
│                      │ ┌──────────────────────────┐ │   │
│                      │ │ T-REX MCP Server         │ │   │
│                      │ │ Session registry          │ │   │
│                      │ │ Task locking              │ │   │
│                      │ │ Handoff records           │ │   │
│                      │ └──────────────────────────┘ │   │
│                      └──────────────────────────────┘   │
│                                                         │
│  ┌─────────────┐    ┌──────────────────────────────┐   │
│  │ git commit   │───▶│ Layer 2: Git Pre-Commit Hook │   │
│  │              │    │ (OS-level, unbypassable)      │   │
│  │              │    │                              │   │
│  │              │    │ Protected branch?             │   │
│  │              │    │   YES → Exit 1 (reject)      │   │
│  │              │    │   NO  → Exit 0 (allow)       │   │
│  └─────────────┘    └──────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Why both layers:**
- Layer 1 catches the agent *before it writes code* (file edits blocked)
- Layer 2 catches the agent *before code enters the repository* (commits blocked)
- A drifted agent might skip an MCP call. It cannot skip an OS-level git hook.

---

## Live Validation

### Commit to Main — Blocked (Layer 2)

```
$ git commit --allow-empty -m "test: should be blocked"

🦖 ============================================
🦖  T-REX: LAW ONE VIOLATION
🦖  Attempted commit directly to 'main'
🦖 ============================================
🦖  This branch is protected. All changes must
🦖  go through a feature branch and PR.
🦖 ============================================

Exit code: 1
```

### Commit to Feature Branch — Allowed (Layer 2)

```
$ git checkout -b test/trex-validation
$ git commit --allow-empty -m "test: should pass"

🦖 T-REX: Branch 'test/trex-validation' validated. Proceeding.
[test/trex-validation 7b7437e] test: should pass

Exit code: 0
```

### File Edit on Main — Blocked (Layer 1)

```
Claude Code PreToolUse hook fires before Edit tool:

T-REX BLOCKED: Cannot modify files on protected branch 'main'.
Switch to a feature branch first.

Exit code: 1    ← Edit never executes
```

### Ironic Proof

During the wiring session itself, Agent #2 committed the dependabot config change directly to `main` locally and attempted `git push`. GitHub's branch protection (a pre-existing mechanical gate) rejected the push. The agent then created a feature branch and PR — exactly the behavior the rules demanded but the agent had initially bypassed.

This incident, happening in real-time during the session that was *building the enforcement system*, became the most compelling validation of the gap analysis thesis: behavioral instructions alone are insufficient.

---

## Before and After

| Capability | Before (March 1–3) | After T-REX (March 4) |
|-----------|-------------------|----------------------|
| Branch protection | CLAUDE.md instruction (violated same session) | Git hook blocks commit + Claude Code hook blocks edits |
| Multi-agent coordination | None — 5 orphaned branches, duplicated work | Task locking via MCP session registry |
| Session continuity | None — each session started blind | Structured handoff records |
| Test requirements | CLAUDE.md instruction (ignored for 3+ PRs) | PostToolUse hook runs tests on file change |
| Audit trail | None | SQLite commit log + session registry |
| Scope | Per-repo config files | User-level hooks — every repo, automatic |
| Sacred rule enforcement | Behavioral (violated from ecosystem repo) | Pre-push hook blocks PRO code + pre-commit blocks main |

---

## The Acceleration Problem

AI capability is advancing faster than governance frameworks can adapt:

| Model | Release | Computer Use Benchmark (OSWorld) |
|-------|---------|--------------------------------|
| Claude Sonnet 3.5 | Mid 2024 | 14.9% |
| Claude Sonnet 3.6 | Late 2024 | 42.2% |
| Claude Sonnet 4.5 | September 2025 | 61.4% |
| Claude Sonnet 4.6 | February 2026 | 72.5% |

This is not Moore's Law. Organizations that build governance frameworks calibrated to the current capability level will find those frameworks obsolete within months.

**The question is not "how do we safely adopt AI coding agents." It is "how do we build governance infrastructure that can adapt as fast as the capability it is governing."**

Annual risk assessments and static policy documents are not adequate instruments for this environment.

---

## Applicability

T-REX is platform-agnostic. The pattern applies wherever AI agents operate in repositories:

- **GitHub Copilot / VS Code** — Same git hooks apply; MCP layer is tool-independent
- **Azure AI Foundry / Copilot Studio** — Complements existing policy rails with git-level enforcement
- **Multi-agent orchestration** — Any system with concurrent AI agents needs task locking and session handoff
- **Regulated industries** — ISO 9001, ISO 13485, FDA 21 CFR Part 820, SOX, HIPAA all require traceability and change control. AI agents without audit trails create compliance gaps.
- **Any development team using AI agents** — If your agents have write access to repositories, you need mechanical governance. Behavioral instructions are not sufficient.

---

## What's Next

1. **Mechanical enforcement of Law Two and Three** — Task locking and handoff are currently MCP-based (behavioral). Investigating Claude Code hooks that block session termination without handoff.
2. **Notion integration** — Agent activity logging for cross-repo visibility. Agents log work; orchestrators read before dispatching.
3. **CI integration** — Pre-merge validation that a T-REX session was registered and handoff completed for every PR.
4. **Open source T-REX** — This governance gap affects every organization deploying AI coding agents. The solution should be shared.

---

## March 4: Verification Session (Agent #3)

A third Claude Code session was started specifically to verify that T-REX enforcement was operational — not to build anything, but to break things and see what holds.

### What Held

| Layer | Test | Result |
|-------|------|--------|
| Layer 2 (git hook) | Commit on `main` | **BLOCKED** — `🦖 LAW ONE VIOLATION` |
| Layer 2 (git hook) | Commit on feature branch | **ALLOWED** — `🦖 Branch validated` |
| MCP — Law One | `rex_validate_branch` on `main` | Violation recorded, session locked |
| MCP — Law Two | Duplicate task claim | **BLOCKED** — `Task already claimed by...` |
| MCP — Law Three | Handoff record | Written, visible to next session via `rex_status` |

### What Didn't Hold

**1. Pre-commit hook disappears on branch switch.**

The hook file (`.githooks/pre-commit`) is versioned — it only exists on branches where it's been committed. When checking out `main` (which doesn't have the file yet), the hook vanishes and `main` becomes unprotected:

```
$ git checkout main
$ git commit --allow-empty -m "test"   # ← Goes through! No hook.

$ git checkout feature-branch
$ git commit --allow-empty -m "test"   # ← Blocked by hook.
```

**Root cause:** `core.hooksPath = .githooks` makes git read hooks from the working tree. Protected branches need to be protected *before* the hook file lands on them — a chicken-and-egg problem inherent to versioned hook directories.

**Fix:** Added the hook to `.claude/settings.local.json` (gitignored, branch-independent) as a Layer 1 safety net. Once the hook PR merges to `main`, Layer 2 covers all future branches.

**2. PreToolUse hook not blocking file edits on protected branches.**

The Claude Code PreToolUse hook (Layer 1) was installed in user-level `~/.claude/settings.json`, but the project-level `.claude/settings.json` defines its own `hooks` object (with `PostToolUse` for auto-testing). Due to Claude Code's settings scope precedence, the project-level `hooks` object shadows the user-level one — the `PreToolUse` hook was never loaded.

```
User-level:    hooks: { PreToolUse: [...], SessionStart: [...] }
Project-level: hooks: { PostToolUse: [...] }
Result:        Only PostToolUse active. PreToolUse silently dropped.
```

Additionally, hooks appear to be loaded at session start and do not reload mid-session. Fixes applied during the session could not be verified until the next session.

**Fix:** Added `PreToolUse` hook to both:
- `.claude/settings.json` (versioned, takes effect when PR merges)
- `.claude/settings.local.json` (gitignored, takes effect next session regardless of branch)

### The Meta-Lesson

Agent #2 built the enforcement system and declared it operational based on controlled tests. Agent #3 found two gaps within 10 minutes of real-world testing. This is the standard pattern: **building a system and validating a system are different disciplines.** The same agent that builds often tests its own happy path. Independent verification catches what the builder's optimism misses.

This applies equally to the governance system itself. T-REX was designed to catch agents cutting corners — but the agent that wired T-REX cut a corner (testing only on the branch where the hook existed, not on the branch it was meant to protect).

---

## Summary

| Phase | Date | Actor | Action |
|-------|------|-------|--------|
| Failures observed | March 1–3 | AI agents | Violated branch rules, skipped tests, duplicated work, ignored Notion logging |
| Gap analysis written | March 3 | Agent #1 (Claude) | 7-page report identifying root cause and proposing T-REX |
| T-REX server built | March 3 | Agent #1 (Claude) | TypeScript MCP server with 6 tools, SQLite, deployed on VM |
| Independent validation | March 4 | Agent #2 (Claude) | Audited PRs, found same failures, arrived at same solution independently |
| T-REX wired up | March 4 | Agent #2 (Claude) | Installed hooks on both repos, configured user-level enforcement |
| Live validation | March 4 | Agent #2 (Claude) | Tested all three laws, confirmed mechanical blocking works |
| Verification session | March 4 | Agent #3 (Claude) | Stress-tested enforcement, found 2 gaps, fixed both |

Three AI agents. Zero shared context between #1 and #2. Same diagnosis. Same solution. #3 broke what #2 thought was solid and patched the holes.

**T-REX does not ask the agent to remember the rules. It makes compliance a technical prerequisite for action. But even mechanical gates need independent verification — the agent that builds the wall shouldn't be the only one testing it.**

---

*Repository: [github.com/Blb3D/t-rex](https://github.com/Blb3D/t-rex) (private) | Gap Analysis: `AI_Agent_Governance_Gap_Analysis.pdf` (internal)*
