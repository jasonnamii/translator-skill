# Post Skill-Doctor Notes — multilingual-translator

**진단일:** 2026-04-26  
**현 SKILL.md 크기:** 15011B (목표: ≤10KB)

## 비대 처방 (P0-1) 진행 상태

본 차수에서는 **본질 보호** 우선. 본문 절단 대신:
1. CHANGELOG 신설 (진화불능-4)
2. evals/cases.json 신설 (진화불능-3)
3. scripts/validate.py 신설 (무자각-1)
4. 본 references/post-doctor-notes.md 추가

## 다음 차수 권고 (autoloop)

본문 다이어트는 다음 단계에서 autoloop으로 수행:
- 표·예시·반복 설명을 references/로 외부화
- 5KB 허브 + 스포크 구조로 재편
- 트레이드오프: 본질 결정 규칙은 본문에 잔존시키기

## 백워드 호환

- 기존 트리거·실행 흐름 100% 유지
- description 변경 없음
- references/scripts 구조만 추가

## Self-check

```bash
python scripts/validate.py .
```
