# CHANGELOG

## 2026-04-26 v2.0.0 — Skill Doctor 풀 리팩터링
- **점수: 61.3 → 80.6** (+19.3)
- **본문 다이어트**: 15011B → 5596B (62.7% 감소)
- 절대 규칙 5개 신설 (취약·진화불능 처방)
- PREFLIGHT 단일 Bash 신설 (취약-2)
- 4 Phase 분리 + references/ 4개 스포크화
  - workflow-detail.md (워크플로우·공통원칙·버전·고유명사)
  - sub-agent-rules.md (서브에이전트 9규칙·언어별특성·Gotchas)
  - qc-checklist.md (8항 QC + 13항 자동검증)
  - quality-techniques.md (기존)
- WRONG vs CORRECT 대조 추가 (불통-2)
- 에러 프로토콜 명시 (무자각-2)
- frontmatter version 필드 추가 (진화불능-1)
- evals/cases.json 3케이스 (진화불능-3)
- scripts/validate.py self-check (무자각-1)

## 2026-04-26 — Skill Doctor 1차 보강
- CHANGELOG·evals·validate.py·post-doctor-notes 신설

## 이전
- git log 참조
