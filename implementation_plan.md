# Implementation Plan

Fix markdownlint warnings across project documentation files to improve code quality and consistency.

Multiple markdown files in the project contain linting violations that need to be corrected. The issues include missing H1 headings, improper spacing around headings and lists, code blocks without language specifications, and missing trailing newlines. These fixes will ensure consistent documentation formatting across the project.

## Types

No type system changes required as this is a documentation formatting task.

## Files

Existing markdown files will be modified to fix linting violations.

- `.claude/agents/test-engineer.md`: Fix H1 heading, heading spacing, list spacing, code block spacing, and trailing newline
- `docs/CLAUDIA.md`: Already has H1 heading but needs trailing newline
- `docs/architecture-review-2026-01.md`: Fix code block languages, list marker spacing, and code block spacing
- `.agent/rules/test-engineer.md`: Fix H1 heading, heading spacing, list spacing, code block spacing, and trailing newline

No new files will be created. No files will be deleted or moved.

## Functions

No function changes required as this is a documentation formatting task.

## Classes

No class changes required as this is a documentation formatting task.

## Dependencies

No dependency changes required as this is a documentation formatting task.

## Testing

No testing changes required as this is a documentation formatting task. The existing test suite will validate that the fixes don't break any functionality.

## Implementation Order

1. Fix `.claude/agents/test-engineer.md` - comprehensive fixes needed
2. Fix `docs/architecture-review-2026-01.md` - multiple code block and spacing issues
3. Fix `.agent/rules/test-engineer.md` - similar issues to the .claude version
4. Fix `docs/CLAUDIA.md` - minimal fix for trailing newline