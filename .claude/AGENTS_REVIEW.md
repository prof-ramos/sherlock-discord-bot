# Claude Code Agents Review

## Current Agent Count: 27

This document reviews which agents are relevant to this Discord bot project.

## ✅ KEEP - Highly Relevant (13 agents)

### Core Development
1. **python-pro** - Python-specific expertise (CRITICAL)
2. **test-engineer** - Pytest and testing strategies
3. **architect-review** - Architecture patterns review
4. **code-review** - General code quality review

### Database & Backend
5. **neon-database-architect** - Neon PostgreSQL + pgvector optimization (CRITICAL)
6. **neon-expert** - Neon-specific operations and branching
7. **database-optimizer** - SQL query optimization, N+1 problems
8. **database-optimization** - General database performance
9. **backend-architect** - API design, Discord bot architecture

### AI/ML & RAG
10. **ai-engineer** - RAG system optimization, LLM integration (CRITICAL)
11. **prompt-engineer** - LLM prompt optimization for bot personality

### Quality & Security
12. **security-auditor** - Security review (Discord tokens, API keys)
13. **error-detective** - Log analysis, debugging production issues

---

## ⚠️ CONDITIONALLY USEFUL (7 agents)

These agents may be useful occasionally but not for daily development:

14. **mlops-engineer** - Only if tracking LLM metrics/experiments
15. **ml-engineer** - Only if adding ML features beyond RAG
16. **data-engineer** - Only if building analytics pipelines
17. **documentation-expert** - Only for major documentation updates
18. **context-manager** - Only for complex multi-agent workflows
19. **search-specialist** - Only for researching new libraries/patterns
20. **deployment-engineer** - Only if adding CI/CD or containerization

---

## ❌ REMOVE - Not Relevant (7 agents)

These agents are NOT applicable to this Discord bot project:

21. **llms-maintainer** - LLMs.txt roadmap files (not used)
22. **mcp-expert** - Model Context Protocol (not used)
23. **command-expert** - CLI command development (not a CLI tool)
24. **markdown-syntax-formatter** - Minimal markdown in project
25. **api-documenter** - No REST API to document (Discord bot)
26. **design-database-schema** - Schema already designed
27. **optimize-database-performance** - Duplicate of database-optimizer

---

## Recommended Agent Cleanup

### Option 1: Minimal Agent Set (Core 8)
Keep only the most critical agents:
- python-pro
- test-engineer
- neon-database-architect
- ai-engineer
- prompt-engineer
- security-auditor
- code-review
- error-detective

### Option 2: Balanced Set (Core 13)
Keep all "KEEP" agents listed above.

### Option 3: Keep All But Remove Irrelevant (20 agents)
Remove only the 7 agents listed in "REMOVE" section.

---

## How to Remove Agents

Agents are defined in `.claude/agents/` directory. To remove:

```bash
# Remove individual agent
rm .claude/agents/llms-maintainer.md

# Or remove all irrelevant agents
rm .claude/agents/{llms-maintainer,mcp-expert,command-expert,markdown-syntax-formatter,api-documenter,design-database-schema,optimize-database-performance}.md
```

**Note**: Removing agents from `.claude/agents/` will prevent Claude Code from loading them in future sessions.

---

## Agent Priority Mapping

When working on specific tasks, prioritize these agents:

| Task Type | Primary Agent | Secondary Agent |
|-----------|---------------|-----------------|
| Python code | python-pro | code-review |
| Database queries | neon-database-architect | database-optimizer |
| RAG improvements | ai-engineer | prompt-engineer |
| Testing | test-engineer | python-pro |
| Security | security-auditor | code-review |
| Debugging | error-detective | python-pro |
| Architecture | backend-architect | architect-review |

---

## Custom Agent Suggestions

Consider creating project-specific agents:

### discord-bot-expert.md
```yaml
---
name: discord-bot-expert
description: Discord.py 2.x and cog architecture specialist
tools: Read, Write, Edit, Bash
model: sonnet
---

Specializes in:
- discord.py 2.x Cogs and slash commands
- Discord API best practices
- Thread management and message handling
- Discord permissions and intents
```

### openrouter-specialist.md
```yaml
---
name: openrouter-specialist
description: OpenRouter API integration and multi-LLM routing
tools: Read, Write, Edit
model: sonnet
---

Specializes in:
- OpenRouter API patterns
- Multi-model routing (GPT-4, Claude, Gemini, LLaMA)
- Prompt caching strategies
- Cost optimization across providers
```
