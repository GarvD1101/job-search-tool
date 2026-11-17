# AI Usage Log

Record of AI tools, roles, and prompts used during project development.

## Tools and Roles

1. Claude: Used by project owner for high-level architecture discussions, design decisions, and planning.
2. Antigravity Agent: Implementation agent for code generation, database schema management, test execution, and documentation drafts following owner instructions.

## Prompts and Directives

### Bootstrap and Phase 0 Directives
- Objective: Setup project foundation, database schema with RLS, secrets verification script, CI workflow, and compliance documentation.
- Constraints Enforced:
  - No secrets in logs or git history.
  - Plain English prose, no em dashes, no marketing language.
  - Strict compliance with public APIs and ATS board limits.
  - Postgres direct owner connection bypassing RLS.
