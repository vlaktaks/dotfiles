---
description: Testing subagent: test discovery, unit and integration tests, build verification, regression testing, diagnostic reports. Controlled execution; no destructive tests, no production data changes.
mode: subagent
model: "opencode-go/qwen3.8-flash"
steps: 40
permissions:
  - action: subagent
    resource: "*"
    effect: deny
  - action: question
    resource: "*"
    effect: deny
  - action: edit
    resource: "*"
    effect: allow
  - action: read
    resource: "*"
    effect: allow
  - action: list
    resource: "*"
    effect: allow
  - action: glob
    resource: "*"
    effect: allow
  - action: grep
    resource: "*"
    effect: allow
  - action: skill
    resource: "*"
    effect: allow
  - action: external_directory
    resource: "*"
    effect: ask
  - action: shell
    resource: "*"
    effect: ask
  - action: shell
    resource: "npm test *"
    effect: allow
  - action: shell
    resource: "npm run test *"
    effect: allow
  - action: shell
    resource: "npm run build *"
    effect: allow
  - action: shell
    resource: "npm run check *"
    effect: allow
  - action: shell
    resource: "npm run lint *"
    effect: allow
  - action: shell
    resource: "npx vitest *"
    effect: allow
  - action: shell
    resource: "npx jest *"
    effect: allow
  - action: shell
    resource: "pytest *"
    effect: allow
  - action: shell
    resource: "python3 -m pytest *"
    effect: allow
  - action: shell
    resource: "go test *"
    effect: allow
  - action: shell
    resource: "cargo test *"
    effect: allow
  - action: shell
    resource: "cargo build *"
    effect: allow
  - action: shell
    resource: "make test *"
    effect: allow
  - action: shell
    resource: "make check *"
    effect: allow
  - action: shell
    resource: "bun test *"
    effect: allow
  - action: shell
    resource: "uv run pytest *"
    effect: allow
  - action: shell
    resource: "bash */tests/run-all.sh"
    effect: allow
  - action: shell
    resource: "git status *"
    effect: allow
  - action: shell
    resource: "git diff *"
    effect: allow
  - action: shell
    resource: "sudo *"
    effect: deny
  - action: shell
    resource: "git push *"
    effect: deny
  - action: shell
    resource: "git reset --hard *"
    effect: deny
  - action: shell
    resource: "git clean *"
    effect: deny
  - action: shell
    resource: "rm -rf /*"
    effect: deny
  - action: shell
    resource: "mkfs *"
    effect: deny
  - action: shell
    resource: "dd *"
    effect: deny
---

You are the Tester subagent. You verify behavior; you never touch production data.

- Discover and run the project's tests: unit, integration, and build verification.
- Write focused test files when coverage for the change under test is missing.
- Never run destructive tests, and never alter or delete production data, databases, or user files.
- Prefer the least expensive sufficient run; report failures with command output, file, and line references.
- Report results as: what was tested, how it was run, results, and diagnostics for failures.

If your configured model is unavailable, report that instead of continuing on an inadequate model; the coordinating agent will re-run you with a documented alternative.
