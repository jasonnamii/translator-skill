# multilingual-translator

> 🇰🇷 [한국어 README](./README.ko.md)

**A structured multilingual translation engine that prioritizes structural integrity over raw translation quality — ensuring callouts, div styles, wiki-links, and tables survive the translation process intact.**

## Prerequisites

- **Claude Cowork or Claude Code** environment
- Obsidian Vault (for wiki-link validation)

## Goal

Most translation failures aren't about meaning — they're about structure. When translating structured `.md` documents with callouts, HTML divs, wiki-links, and tables, LLM agents tend to silently drop or alter structural elements. This skill prevents that by enforcing structural QC, sub-agent orchestration rules, and a mandatory quality pipeline.

## When & How to Use

Triggers automatically when translating structured `.md` documents into multiple languages. The skill manages the full pipeline: intent annotation → 2-pass translation (faithful → native polish) → back-translation verification → scoring rubric → structural QC via `qc_diff.py`. Each language gets its own dedicated agent.

## Use Cases

| Scenario | Prompt | What Happens |
|---|---|---|
| Translate a program doc to 5 languages | `"이 문서 EN/CN/JP/TH/ID로 번역해줘"` | Runs full pipeline: intent tags → 2-pass per language → back-translation → scoring → QC |
| Fix structural drift in a translation | `"CN 번역본 구조 편차 수정해줘"` | Runs qc_diff.py, identifies mismatches, applies surgical fixes via 수정4 protocol |
| Add a new language to existing translations | `"베트남어 추가해줘"` | Extends language table, creates VN translation following the same pipeline |

## Key Features

- **Structural QC automation** — `qc_diff.py` validates 13 items (heading count, callout count, div style attributes, wiki-link integrity, etc.) with exit code enforcement
- **2-pass translation** — Pass 1 for faithful accuracy, Pass 2 for native polish. Role separation is strict
- **Back-translation verification** — Separate agent reverse-translates to detect meaning loss or distortion
- **Scoring rubric** — 4-axis evaluation (accuracy, naturalness, tone consistency, cultural appropriateness) by a dedicated scoring agent
- **Intent annotation** — Pre-tags each section with purpose ([urgency], [trust], [emotion], [info], [persuade]) to guide translation tone
- **Native expression dictionary** — Managed lookup table preventing awkward literal translations
- **Sub-agent orchestration** — 1 language = 1 agent, structure template pre-delivery, section-level verification
- **Language-specific gotchas** — Built-in reference for CN/JP/TH/ID/EN quirks and failure patterns

## Works With

- **[trigger-dictionary](https://github.com/jasonnamii/trigger-dictionary)** — 수정4 protocol for surgical fix of translation drift
- **[design-skill](https://github.com/jasonnamii/design-skill)** — When translating apple-design-style documents with HTML divs

## Installation

```bash
git clone https://github.com/jasonnamii/multilingual-translator.git ~/.claude/skills/multilingual-translator
```

## Update

```bash
cd ~/.claude/skills/multilingual-translator && git pull
```

Skills placed in `~/.claude/skills/` are automatically available in Claude Code and Cowork sessions.

## Part of Cowork Skills

This is one of 25+ custom skills. See the full catalog: [github.com/jasonnamii/cowork-skills](https://github.com/jasonnamii/cowork-skills)

## License

MIT License — feel free to use, modify, and share.