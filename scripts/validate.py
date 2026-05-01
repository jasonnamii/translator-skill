#!/usr/bin/env python3
"""Self-check validator for this skill (post Skill Doctor 2026-04)."""
import sys, os, json, re

def main(skill_dir):
    skill_md = os.path.join(skill_dir, 'SKILL.md')
    errors = []
    warnings = []
    
    if not os.path.isfile(skill_md):
        errors.append(f"SKILL.md missing: {skill_md}")
        return errors, warnings
    
    with open(skill_md, encoding='utf-8') as f:
        text = f.read()
    
    size = len(text.encode('utf-8'))
    if size > 10240:
        warnings.append(f"SKILL.md size {size}B > 10KB (consider references/ split)")
    
    if not re.search(r'(?i)gotchas?', text):
        warnings.append("Gotchas 섹션 없음")
    if not re.search(r'(?i)preflight|🚦', text):
        warnings.append("PREFLIGHT 단계 없음")
    if 'STOP' not in text and '중단' not in text:
        warnings.append("에러 STOP 프로토콜 명시 없음")
    
    cases_json = os.path.join(skill_dir, 'evals', 'cases.json')
    if not os.path.isfile(cases_json):
        warnings.append("evals/cases.json 없음")
    
    if not os.path.isfile(os.path.join(skill_dir, 'CHANGELOG.md')):
        warnings.append("CHANGELOG.md 없음")
    
    return errors, warnings

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else '.'
    errs, warns = main(target)
    result = {"errors": errs, "warnings": warns, "skill_dir": target}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(1 if errs else 0)
