# CLAUDIA.md - Project Style Guide

## Language Standards

- **Primary Language**: Portuguese (Brazil) [pt-BR]
- **Documentation**: All user-facing documentation (README, etc.) and codebase comments/docstrings
  should be in Portuguese.
- **Code**: Variable names, function names, and class names should use English (standard Python
  convention) to ensure broad compatibility and readability with libraries, but descriptive comments
  and business logic explanations should remain in Portuguese.
- **Review Documents**: Architecture reviews and audit reports may be in English for international
  compatibility (e.g., CodeRabbit, external auditors).

## Code Style

- Follow PEP 8.
- Use `ruff` for linting and formatting.
- Type hints are mandatory for all public functions.
