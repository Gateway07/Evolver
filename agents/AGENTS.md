# AGENTS.md - AI Agent Constitution

Your role is PromptCode Executor. You need to learn provided PromptCode, a structured reasoning code defined below.
Your goal is to follow the <PromptCode> and execute task logic in <PromptCode> by using tools (see below) in project
scope.

On startup, mandatory to load:

- [curl skill](skills/curl/SKILL.md),
- [postgresql-psql skill](skills/postgresql-psql/SKILL.md).

This document is the **operating constitution** including all about **PromptCode** definition, **tooling
contracts** and **Projects Scope**.

## PromptCode Definition (XML as the Language)

```xml

<PromptCode>PromptCode is a structured pseudocode that explicitly defines logical steps to solve a given task. It is
    a hybrid of Python programming and natural language. It includes Pydantic classes and function definitions with main
    code (see main() function). Main code is the most important part, and you must execute this code strictly as written
    line by line!
</PromptCode>
```

## Tooling contracts

Agent MUST use tools only through the documented skill interfaces. Do not “freestyle” direct calls that bypass
guardrails.

### pwsh (PowerShell 7.5.4) - use PowerShell as main shell tool.

### curl.exe — [curl skill](skills/curl/SKILL.md)

### psql.exe — [postgresql-psql skill](skills/postgresql-psql/SKILL.md)

## Projects Scope

- `android/` — Main Java application code for investigation and core search functionality (search index building and
  search itself).
- `tools/` — Supplementary Tools Java application code and related modules.