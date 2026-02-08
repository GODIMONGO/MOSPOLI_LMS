# Skill: Agent Orchestration for MOSPOLI_LMS

## Purpose
Use multiple agents to analyze, plan, and execute tasks in this repository with predictable quality and fast turnaround.

## Scope
- Repository: `MOSPOLI_LMS` (Flask app, routes/templates/static).
- Default mode: parallel discovery, centralized decision making, controlled execution.
- Current safe mode supported: `no-code` (analysis without editing application code).

## Non-Negotiables
- Do not modify source code when the task is marked `no-code`.
- Keep one orchestration owner agent responsible for final decisions and synthesis.
- Run independent discovery in parallel whenever possible.
- Prefer concrete evidence (file paths, commands, outputs) over assumptions.

## Agent Roles
1. Orchestrator (owner)
- Interprets request, splits work, assigns agent tasks, merges findings.
- Resolves conflicts between agent findings.
- Produces final output with clear next actions.

2. Explorer: Architecture
- Maps project structure and responsibility boundaries.
- Tracks route entry points and shared libs.

3. Explorer: Runtime/Quality
- Checks run/test/lint commands and environment prerequisites.
- Reports command status and blockers.

4. Explorer: UI/Assets
- Maps templates/static/test artifacts and UI coupling points.

5. Worker (only when edits are allowed)
- Implements approved changes in narrow file scope.
- Returns diff summary and validation results.

## Orchestration Protocol
1. Intake
- Parse request into: goal, constraints, output format, risk level.
- Mark mode: `no-code` or `edit`.

2. Parallel Discovery
- Spawn at least 2 explorers for independent context gathering.
- Require each explorer to return:
  - facts with file paths
  - unresolved questions
  - confidence level

3. Synthesis
- Merge non-conflicting facts.
- Resolve conflicts by checking files/commands directly.
- Build one actionable plan with explicit tradeoffs.

4. Execution
- `no-code`: produce analysis/report/checklist only.
- `edit`: delegate implementation to workers in scoped chunks.

5. Validation
- Verify claimed outcomes with commands or file evidence.
- Record what was not validated and why.

6. Final Response Contract
- What was done.
- Evidence (paths/commands).
- Risks/assumptions.
- Next options.

## Task Templates (Copy/Paste)
### Template A: Architecture Explorer
You own repository mapping only. Do not propose edits.
Return:
1) entry points
2) core modules and dependencies
3) risky coupling zones
Use file paths in every claim.

### Template B: Runtime Explorer
You own run/quality verification only. Do not edit files.
Return:
1) exact setup/run commands
2) lint/type/test commands and expected outputs
3) blockers and missing tooling

### Template C: UI Explorer
You own template/static mapping only. Do not edit files.
Return:
1) template hierarchy
2) static asset organization
3) likely UI regression hotspots

### Template D: Worker (Edit Mode Only)
You own only the assigned files. Ignore unrelated changes.
Return:
1) files changed
2) minimal rationale
3) validation commands run + results

## Repository-Specific Checklist
- App bootstrap: `main.py`
- Routes: `routes/`
- Shared logic: `libs/`
- UI templates: `templates/`
- Frontend assets: `static/`
- Local test artifacts: `test/`
- Quality config: `pyproject.toml`, `.pylintrc`

## Known Commands (Project Context)
- Setup:
  - `py -m venv .venv`
  - `.\.venv\Scripts\Activate.ps1`
  - `python -m pip install -r requirements.txt`
- Run:
  - `python main.py`
- Quality:
  - `poe check`
  - `ruff format .`
  - `ruff check --fix .`
  - `mypy .`
  - `pylint --rcfile=.pylintrc --recursive=y .`

## No-Code Practice Output Format
When edits are forbidden, output this structure:
1. Objective
2. Constraints
3. Findings (with paths)
4. Risk list
5. Proposed edit plan (not applied)
6. Validation plan

## Definition of Done
- Skill file exists in `.agents/skills/`.
- Contains reusable orchestration workflow + role templates.
- Supports both `no-code` and `edit` modes.
- Includes project-specific paths and commands.
