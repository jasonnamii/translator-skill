---
name: multilingual-translator
description: |
  다국어 번역 운영 도구. 구조화된 .md 문서의 번역 실행→구조 일치 QC→서브에이전트 관리를 1회 호출로 수행. 다국어 문서 작업시 자동발동.
  P1: 번역, 다국어, 영어번역, 중국어번역, 일본어번역, 태국어번역, 인도네시아어번역, multilingual, translation, 번역운영.
  P2: 번역해줘, 번역 실행, translate, translate this, 다국어로 만들어줘.
  P3: multilingual translation, structural QC, sub-agent translation, localization.
  P4: .md 문서를 다국어로 변환할 때, 번역본 구조 편차 수정 시, 서브에이전트 번역 관리 시.
  P5: _EN.md로, _CN.md로, _JP.md로, _TH.md로, _ID.md로.
  NOT: 일반 텍스트 번역(→직접수행), UP 수정(→up-manager), 단순 용어 확인(→직접수행).
vault_dependency: SOFT
version: 2.0.0
---

# 다국어 번역 운영 도구

구조화된 문서를 다국어로 번역할 때, **내용 번역보다 구조 일치가 더 자주 실패한다.** 이 스킬은 그 실패를 방지하는 운영 규칙과 QC 체크리스트를 제공한다.

---

## ⛔ 절대 규칙 (5개)

| # | 규칙 | 위반 시 |
|---|------|--------|
| 1 | **원본→번역본 단방향 수정** — 번역본만 고치면 원본 불일치 | FAIL + 원본 갱신 후 재배포 |
| 2 | **qc_diff.py 통과 = 완료 조건** — exit code 0 미달성 시 완료 선언 금지 | STOP + 재시도 |
| 3 | **1언어 1에이전트** — 한 에이전트가 2개 언어 처리 금지 | 격리 실패 + 품질 저하 |
| 4 | **골격(skeleton) 검증 선행** — 빈 골격 qc PASS 후에만 텍스트 채우기 | 텍스트 완성 후 구조 FAIL = 전체 재작업 |
| 5 | **번역≠역번역≠채점 에이전트 분리** — 자기평가 편향 차단 | 평가 무효 |

---

## 🚦 PREFLIGHT (단일 Bash)

```bash
# 입력 검증: 원본 SoT, 대상 언어, qc_diff.py 가용성 3체크
test -f "$SOURCE" && echo "$LANGS" | grep -qE "(EN|CN|JP|TH|ID|KO)" && \
  python3 ${CLAUDE_SKILL_DIR}/scripts/qc_diff.py --help >/dev/null 2>&1
# 실패 시 STOP + 보고
```

| 체크 | 실패 시 |
|------|--------|
| ① 원본 SoT 존재 | STOP, 사용자에게 원본 경로 요청 |
| ② 대상 언어 식별 (5+1) | STOP, 언어 코드 명시 요청 |
| ③ qc_diff.py 가용 | STOP, 스킬 재설치 요청 |

---

## 실행 흐름 (4 Phase)

```
PREFLIGHT → ① 워크플로우 → ② 서브에이전트 운영 → ③ QC 검증 → ④ 산출물 제공
```

| Phase | 핵심 결정 | 상세 |
|-------|----------|------|
| ① 워크플로우 | 원본→EN→나머지 4언어 병렬 / 6대 공통 원칙 / 버전 표기 / 고유명사 매핑 | `→ references/workflow-detail.md` |
| ② 서브에이전트 | 1언어=1에이전트 / 골격 선행 / 9대 운영 규칙 / 언어별 특성 | `→ references/sub-agent-rules.md` |
| ③ QC 검증 | qc_diff.py 13항목 자동 + 8항목 수동 / FAIL 항목 재수정 | `→ references/qc-checklist.md` |
| ④ 품질 기법 | 의도주석·네이티브사전·2패스·백트랜슬레이션·채점루브릭 5대 기법 | `→ references/quality-techniques.md` |

---

## 핵심 명령

```bash
# 자동 QC (필수, 완료 조건)
python3 ${CLAUDE_SKILL_DIR}/scripts/qc_diff.py <원본.md> <번역본.md>
python3 ${CLAUDE_SKILL_DIR}/scripts/qc_diff.py <원본.md> <번역본.md> --json

# Self-check (배포 전)
python3 ${CLAUDE_SKILL_DIR}/scripts/validate.py .
```

---

## §INV NO_WORK_LABEL (산출물·대화 본질 보호)

| 항목 | 정의 |
|------|------|
| RULE | 산출물·대화 = 인간 언어. 작업 라벨 ZERO. (1만 페이지 1단어 = FAIL) |
| 판정 | "이 단어, 사전 없이 읽을 수 있나?" NO → 작업 라벨 → 금지 |
| ALLOW | 업계 전문용어(QC·LQA·i18n·l10n·DTP·CAT·TM·MT) · 고유명사 · 법조문 |
| CONVERT | 라벨 발견 → 실명·평문 풀어쓰기 |
| SELF_CHECK | 번역본 출력 직전 자체 스캔. 1개라도 발견 = 차단·재작성 |

---

## Gotchas (Top 5 — 상세는 sub-agent-rules.md)

- **가장 흔한 실패**: 번역 내용은 맞는데 구조(콜아웃·테이블·div) 편차 → qc_diff.py 통과 의무
- **ID(인도네시아어) 1순위 위험**: 콜아웃 누락 + div 변경 + 신규 섹션 동시 발생 빈도 최고
- **TH(태국어) 파일 크기 +40%**: UTF-8 멀티바이트 정상이나 매번 원인 확인
- **역방향 수정 유혹**: 번역본만 고치면 원본 불일치 → 절대규칙 1
- **수정4 미적용**: 직접 패치 = old 잔존(잡탕)·중복삽입 → trigger-dictionary §6 필수

---

## ❌ WRONG vs ✅ CORRECT

```
❌ WRONG: 번역본에서 오타 발견 → 번역본만 수정
✅ CORRECT: 원본에 동일 오타 확인 → 원본 수정 → 5개 언어 동기 재배포

❌ WRONG: "간단한 문서니까" 골격 검증 스킵 → 텍스트 완성 후 누락 발견 → 전체 재작업
✅ CORRECT: 빈 골격 생성 → qc_diff.py PASS → 텍스트 채우기

❌ WRONG: qc_diff.py FAIL 1건 "사소하니 넘김"
✅ CORRECT: FAIL 0건 PASS = 완료 조건 (절대규칙 2)
```

---

## 에러 프로토콜

| 상황 | 행동 |
|------|------|
| PREFLIGHT 실패 | STOP + 사용자에게 1줄 보고 |
| qc_diff.py FAIL | 수정 후 1회 재시도. 2회 실패 = STOP + 보고 (루프 하드캡) |
| 서브에이전트 무응답 | max 2회 재호출. 그래도 실패 = 다른 언어 우선 진행, 누락 보고 |
| 알 수 없는 에러 | thumbs-down으로 Anthropic 피드백 + CHANGELOG에 재현조건 기록 |
