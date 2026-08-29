# Development Guide

## Purpose

This document defines the engineering workflow for Amazone_Clone. The repository is maintained not only as source code, but also as a traceable engineering and educational history.

## 1. Work Item Flow

Every meaningful change starts with a GitHub Issue.

```text
Issue
  -> investigation / planning
  -> branch
  -> implementation
  -> tests
  -> Pull Request
  -> review
  -> requested changes (if needed)
  -> re-review
  -> approval
  -> merge
  -> case study (when educationally valuable)
```

## 2. Issue Rules

An Issue should describe the problem before prescribing the implementation.

Required concepts where applicable:

- problem;
- context;
- scope;
- out of scope;
- architecture constraints;
- acceptance criteria;
- tests / verification;
- educational goal.

For bugs, `Root Cause` is intentionally left empty until investigation establishes it.

## 3. Branch Rules

Use one branch per Issue.

```text
feature/EDU-123-short-description
bugfix/EDU-123-short-description
arch/EDU-123-short-description
refactor/EDU-123-short-description
docs/EDU-123-short-description
```

Do not develop directly on `main`.

## 4. Commit Convention

Use:

```text
<ISSUE-ID>: <Imperative description>
```

Examples:

```text
EDU-024: Add ownership validation
EDU-024: Add unauthorized access regression test
EDU-024: Move validation to application layer
```

Rules:

1. Reference the Issue.
2. Put a colon and one space between the Issue ID and the description.
3. Start the description with a capital imperative verb.
4. Do not use Conventional Commit prefixes such as `fix:`, `feat:`, or similar.
5. Describe one logical change.
6. Use imperative wording.
7. Avoid generic messages such as `fix`, `update`, or `changes`.
8. Do not mix unrelated changes.

## 5. Pull Requests

Every PR must explain:

- the problem;
- root cause, when known;
- approach;
- alternatives considered when relevant;
- exact changes;
- tests and verification;
- architectural impact;
- educational value when applicable.

A PR is a technical explanation of the change, not only a list of files.

## 6. Code Review

Review is part of the engineering history.

Review comments should explain:

1. what is wrong or risky;
2. which rule or invariant is involved;
3. why the proposed change is insufficient;
4. what should be changed.

A requested change should normally result in a new, understandable commit.

## 7. Tests

A defect fix should normally include a regression test.

Tests should demonstrate the behavior described by the acceptance criteria, not merely increase coverage.

## 8. Architecture

Architectural rules are defined by `ARCHITECTURE.md` at the repository root and related documents under `docs/`.

If a change introduces or modifies an architectural decision, create or update an ADR under `docs/adr/`.

## 9. ADR Rules

Create an ADR when a decision has meaningful consequences for:

- module boundaries;
- dependency direction;
- persistence;
- authentication / authorization;
- API contracts;
- concurrency / consistency;
- infrastructure;
- technology selection.

Do not create an ADR for routine implementation details.

## 10. Educational Cases

When a real engineering problem contains a useful lesson, create a case study under `docs/case-studies/`.

A case study should preserve the path:

```text
problem -> discovery -> investigation -> root cause -> alternatives -> decision -> implementation -> review -> tests -> result -> lesson
```

The case study should describe what actually happened. It must not rewrite history into a fictional perfect solution.

## 11. Definition of Done

A task is done only when applicable:

- [ ] Problem is solved.
- [ ] Acceptance criteria are satisfied.
- [ ] Tests are added or updated.
- [ ] Regression coverage exists for a bug fix.
- [ ] Architecture rules are respected.
- [ ] Review comments are resolved.
- [ ] Documentation is updated when required.
- [ ] ADR is created or updated when required.
- [ ] Educational case is created when the task is marked as an educational case.
- [ ] PR is approved and merged.

## 12. Traceability Rule

A future reader should be able to move from:

```text
Issue -> Branch -> Commits -> PR -> Review -> Tests -> Merge -> Documentation
```

without guessing why a significant change was made.
