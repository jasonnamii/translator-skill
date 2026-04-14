# multilingual-translator

> 🇺🇸 [English README](./README.md)

**구조화된 .md 문서의 다국어 번역 운영 도구. 번역 품질보다 구조 일치가 더 자주 실패한다는 전제 하에, 콜아웃·div·위키링크·테이블이 번역 과정에서 깨지는 것을 방지하는 운영 시스템.**

## 사전 요구

- **Claude Cowork 또는 Claude Code** 환경
- Obsidian Vault (위키링크 검증용)

## 목표

번역 실패의 대부분은 의미가 아니라 구조에서 발생한다. 콜아웃, HTML div, 위키링크, 테이블이 포함된 .md 문서를 번역할 때 LLM 에이전트가 구조 요소를 누락하거나 변형하는 것을 방지한다. 구조 QC, 서브에이전트 운영 규칙, 번역 품질 파이프라인을 강제 적용.

## 사용 시점 & 방법

구조화된 .md 문서를 다국어로 번역할 때 자동 발동. 의도주석→2패스 번역(충실직역→네이티브윤문)→백트랜슬레이션→채점루브릭→구조QC(qc_diff.py) 전체 파이프라인을 관리. 언어당 1에이전트 배정.

## 사용 사례

| 상황 | 프롬프트 | 동작 |
|---|---|---|
| 프로그램 문서 5개 언어 번역 | `"이 문서 EN/CN/JP/TH/ID로 번역해줘"` | 의도태그→2패스→역번역→채점→QC 풀파이프라인 실행 |
| 번역본 구조 편차 수정 | `"CN 번역본 구조 편차 수정해줘"` | qc_diff.py 실행→불일치 식별→수정4 프로토콜로 외과적 수정 |
| 기존 번역에 새 언어 추가 | `"베트남어 추가해줘"` | 언어 테이블 확장, 동일 파이프라인으로 VN 번역 생성 |

## 주요 기능

- **구조 QC 자동화** — `qc_diff.py`로 13개 항목 검증 (헤딩 수, 콜아웃 수, div style 속성값, 위키링크 유효성 등). exit code 0 필수
- **2패스 번역** — 1패스 충실 직역 + 2패스 네이티브 윤문. 역할 분리 엄격
- **백트랜슬레이션 검증** — 별도 에이전트가 역번역하여 의미 손실·왜곡 검출
- **채점 루브릭** — 4축(정확성·자연스러움·톤일관성·문화적적절성) 평가. 번역 에이전트와 별도 에이전트가 채점
- **의도 주석** — 섹션별 목적 태그([긴박], [신뢰], [감성], [정보], [설득])로 번역 톤 가이드
- **네이티브 표현 사전** — 직역 방지용 현지 표현 매핑 테이블 관리
- **서브에이전트 운영** — 1언어 1에이전트, 구조 템플릿 선제공, 섹션 단위 검증
- **언어별 특성 레퍼런스** — CN/JP/TH/ID/EN 고유 함정과 실패 패턴 내장

## 연동 스킬

- **[trigger-dictionary](https://github.com/jasonnamii/trigger-dictionary)** — 번역 편차 수정 시 수정4 프로토콜 적용
- **[design-skill](https://github.com/jasonnamii/design-skill)** — apple-design-style HTML div 문서 번역 시 연동

## 설치

```bash
git clone https://github.com/jasonnamii/multilingual-translator.git ~/.claude/skills/multilingual-translator
```

## 업데이트

```bash
cd ~/.claude/skills/multilingual-translator && git pull
```

`~/.claude/skills/`에 배치된 스킬은 Claude Code 및 Cowork 세션에서 자동으로 사용 가능합니다.

## Cowork Skills

25개 이상의 커스텀 스킬 중 하나입니다. 전체 카탈로그: [github.com/jasonnamii/cowork-skills](https://github.com/jasonnamii/cowork-skills)

## 라이선스

MIT License — 자유롭게 사용, 수정, 공유 가능합니다.