#!/usr/bin/env python3
"""
QC Diff Tool for Multilingual Markdown Documents

Compare original .md document vs translated .md document structure.
Validates that both documents maintain the same structural elements:
- Heading counts (H1-H6) + sequence alignment (difflib)
- Callout blocks (> [!type])
- Tables
- Div/HTML blocks + style attribute comparison
- Code blocks
- Wikilinks ([[...]]) + TOC↔heading cross-validation
- Image embeds (![[...]] or ![...]())
- List items (- / * / numbered)
- File size ratio

Usage:
    python qc_diff.py <original.md> <translated.md> [--json]

    --json    Output results as JSON instead of table

Exit codes:
    0 - All structure elements match
    1 - One or more mismatches detected
    2 - File not found or other error
"""

import difflib
import json as json_lib
import re
import sys
from pathlib import Path


def read_file(filepath: str) -> tuple[str, int]:
    """
    Read markdown file and return content + file size in bytes.

    Args:
        filepath: Path to markdown file

    Returns:
        Tuple of (content, file_size_bytes)

    Raises:
        FileNotFoundError: If file does not exist
        IOError: If file cannot be read
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    content = path.read_text(encoding='utf-8')
    file_size = path.stat().st_size

    return content, file_size


def count_headings(content: str) -> dict[str, int]:
    """
    Count headings by level (H1-H6).

    Args:
        content: Markdown content

    Returns:
        Dict mapping heading level to count (e.g., {'H1': 2, 'H2': 5, ...})
    """
    counts = {}
    for level in range(1, 7):
        pattern = f'^{"#" * level} '
        matches = re.findall(pattern, content, re.MULTILINE)
        counts[f'H{level}'] = len(matches)
    return counts


def extract_heading_sequence(content: str) -> list[dict[str, any]]:
    """
    Extract ordered sequence of headings with level and text.

    Returns: [{"level": 2, "text": "섹션 제목", "line_num": 5}, ...]
    """
    headings = []
    for i, line in enumerate(content.splitlines(), 1):
        m = re.match(r'^(#{1,6})\s+(.+)', line)
        if m:
            headings.append({
                "level": len(m.group(1)),
                "text": m.group(2).strip(),
                "line_num": i,
            })
    return headings


def diff_heading_sequences(
    orig_headings: list[dict], trans_headings: list[dict]
) -> list[dict]:
    """
    Use difflib.SequenceMatcher to align heading sequences and identify
    missing, extra, or reordered headings.

    Returns: list of issues [{"type": "missing"|"extra"|"moved", "detail": ...}, ...]
    """
    issues = []
    orig_tags = [f"H{h['level']}:{h['text']}" for h in orig_headings]
    trans_tags = [f"H{h['level']}:{h['text'][:30]}" for h in trans_headings]

    # Use structural level only for alignment (text will differ in translation)
    orig_levels = [f"H{h['level']}" for h in orig_headings]
    trans_levels = [f"H{h['level']}" for h in trans_headings]

    sm = difflib.SequenceMatcher(None, orig_levels, trans_levels)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "delete":
            for k in range(i1, i2):
                issues.append({
                    "type": "missing_heading",
                    "original_line": orig_headings[k]["line_num"],
                    "detail": f"원본 L{orig_headings[k]['line_num']} '{orig_headings[k]['text'][:40]}' 가 번역본에 없음",
                })
        elif tag == "insert":
            for k in range(j1, j2):
                issues.append({
                    "type": "extra_heading",
                    "translated_line": trans_headings[k]["line_num"],
                    "detail": f"번역본 L{trans_headings[k]['line_num']} '{trans_headings[k]['text'][:40]}' 가 원본에 없음",
                })
        elif tag == "replace":
            # Level mismatch at same position
            for orig_k, trans_k in zip(range(i1, i2), range(j1, j2)):
                if orig_levels[orig_k] != trans_levels[trans_k]:
                    issues.append({
                        "type": "level_mismatch",
                        "original_line": orig_headings[orig_k]["line_num"],
                        "translated_line": trans_headings[trans_k]["line_num"],
                        "detail": f"레벨 불일치: 원본 {orig_levels[orig_k]} vs 번역 {trans_levels[trans_k]}",
                    })
    return issues


def extract_div_styles(content: str) -> list[dict[str, str]]:
    """
    Extract all div tags with their style attributes for comparison.

    Returns: [{"line_num": 5, "tag": "<div style=\"...\">", "styles": {"border": "1px...", ...}}, ...]
    """
    results = []
    for i, line in enumerate(content.splitlines(), 1):
        for m in re.finditer(r'<\s*div\s+([^>]*style\s*=\s*"([^"]*)"[^>]*)>', line, re.IGNORECASE):
            style_str = m.group(2)
            styles = {}
            for prop in style_str.split(";"):
                prop = prop.strip()
                if ":" in prop:
                    k, v = prop.split(":", 1)
                    styles[k.strip().lower()] = v.strip()
            results.append({
                "line_num": i,
                "tag": m.group(0)[:80],
                "styles": styles,
            })
    return results


def diff_div_styles(
    orig_styles: list[dict], trans_styles: list[dict]
) -> list[dict]:
    """
    Compare div style attributes between original and translated.
    Position-matched (1st div vs 1st div, etc.).

    Returns: list of issues
    """
    issues = []

    if len(orig_styles) != len(trans_styles):
        issues.append({
            "type": "div_count_mismatch",
            "detail": f"div 개수 불일치: 원본 {len(orig_styles)} vs 번역 {len(trans_styles)}",
        })

    for idx, (orig, trans) in enumerate(zip(orig_styles, trans_styles)):
        orig_s = orig["styles"]
        trans_s = trans["styles"]

        all_keys = set(orig_s.keys()) | set(trans_s.keys())
        for key in all_keys:
            orig_val = orig_s.get(key)
            trans_val = trans_s.get(key)
            if orig_val != trans_val:
                issues.append({
                    "type": "div_style_mismatch",
                    "div_index": idx + 1,
                    "property": key,
                    "original": orig_val,
                    "translated": trans_val,
                    "detail": f"div#{idx+1} style '{key}': '{orig_val}' → '{trans_val}'",
                })

    return issues


def validate_toc_links(content: str) -> list[dict]:
    """
    Check that TOC wikilinks ([[#heading]]) match actual heading text.

    Returns: list of issues (broken TOC links)
    """
    issues = []
    # Extract all headings
    headings_text = set()
    for line in content.splitlines():
        m = re.match(r'^#{1,6}\s+(.+)', line)
        if m:
            headings_text.add(m.group(1).strip())

    # Extract TOC-style wikilinks
    for i, line in enumerate(content.splitlines(), 1):
        for m in re.finditer(r'\[\[#([^\]|]+)(?:\|[^\]]+)?\]\]', line):
            link_target = m.group(1).strip()
            if link_target not in headings_text:
                issues.append({
                    "type": "broken_toc_link",
                    "line_num": i,
                    "link": link_target,
                    "detail": f"L{i} TOC 링크 '[[#{link_target}]]' → 매칭 헤딩 없음",
                })

    return issues


def count_list_items(content: str) -> int:
    """
    Count list items (- item, * item, 1. item).

    Args:
        content: Markdown content

    Returns:
        Number of list items found
    """
    pattern = r'^\s*(?:[-*]|\d+\.)\s+'
    matches = re.findall(pattern, content, re.MULTILINE)
    return len(matches)


def count_callouts(content: str) -> int:
    """
    Count callout blocks (> [!type]).

    Args:
        content: Markdown content

    Returns:
        Number of callout blocks found
    """
    pattern = r'^> \[!'
    matches = re.findall(pattern, content, re.MULTILINE)
    return len(matches)


def count_tables(content: str) -> int:
    """
    Count markdown tables (lines with | delimiters and separator row).

    Args:
        content: Markdown content

    Returns:
        Number of tables found
    """
    lines = content.split('\n')
    table_count = 0
    in_table = False

    for i, line in enumerate(lines):
        if '|' in line:
            # Check if next line is a separator (contains |, -, :)
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                if re.match(r'^\s*\|[\s\-:|]+\|\s*$', next_line):
                    if not in_table:
                        table_count += 1
                        in_table = True
                else:
                    in_table = False
            else:
                in_table = False
        else:
            in_table = False

    return table_count


def count_html_divs(content: str) -> int:
    """
    Count HTML div blocks and other block-level HTML elements.

    Args:
        content: Markdown content

    Returns:
        Number of HTML block elements found
    """
    # Match opening div tags (case-insensitive)
    pattern = r'<\s*div\s*(?:\s+[^>]*)?\s*>'
    matches = re.findall(pattern, content, re.IGNORECASE)
    return len(matches)


def count_code_blocks(content: str) -> int:
    """
    Count fenced code blocks (``` or ~~~).

    Args:
        content: Markdown content

    Returns:
        Number of code blocks found (divide by 2 since each block has open+close)
    """
    backtick_pattern = r'```'
    tilde_pattern = r'~~~'

    backticks = len(re.findall(backtick_pattern, content))
    tildes = len(re.findall(tilde_pattern, content))

    # Each code block has opening and closing fence
    code_blocks = (backticks + tildes) // 2
    return code_blocks


def count_wikilinks(content: str) -> int:
    """
    Count wikilinks ([[...]]).

    Args:
        content: Markdown content

    Returns:
        Number of wikilinks found
    """
    pattern = r'\[\[[^\]]+\]\]'
    matches = re.findall(pattern, content)
    return len(matches)


def count_image_embeds(content: str) -> int:
    """
    Count image embeds (![[...]] or ![...]()).

    Args:
        content: Markdown content

    Returns:
        Number of image embeds found
    """
    # Wikilink style: ![[...]]
    wikilink_pattern = r'!\[\[[^\]]+\]\]'
    wikilink_matches = re.findall(wikilink_pattern, content)

    # Standard markdown style: ![...]()
    markdown_pattern = r'!\[([^\]]*)\]\([^)]+\)'
    markdown_matches = re.findall(markdown_pattern, content)

    return len(wikilink_matches) + len(markdown_matches)


def calculate_size_ratio(size1: int, size2: int) -> float:
    """
    Calculate ratio of size2 to size1.

    Args:
        size1: First file size in bytes
        size2: Second file size in bytes

    Returns:
        Ratio as float (size2 / size1)
    """
    if size1 == 0:
        return 0.0
    return size2 / size1


# ============================================================
# 퍼지 감지: 문단 대응 + 미번역 잔류 + 용어 일관성
# ============================================================

# 언어 감지용 유니코드 범위
_LANG_RANGES = {
    "korean": re.compile(r'[\uAC00-\uD7AF\u3130-\u318F]'),      # 한글
    "japanese": re.compile(r'[\u3040-\u309F\u30A0-\u30FF]'),      # 히라가나+카타카나
    "chinese": re.compile(r'[\u4E00-\u9FFF]'),                    # CJK 통합 한자
    "latin": re.compile(r'[a-zA-Z]'),                              # 라틴
    "cyrillic": re.compile(r'[\u0400-\u04FF]'),                    # 키릴
}


def detect_dominant_script(text: str) -> str:
    """텍스트의 지배적 문자 체계를 감지."""
    counts = {}
    for name, pattern in _LANG_RANGES.items():
        counts[name] = len(pattern.findall(text))
    if not any(counts.values()):
        return "unknown"
    return max(counts, key=counts.get)


def _split_paragraphs(content: str) -> list[dict]:
    """마크다운을 빈줄 기준으로 문단 분리. 구조 요소(heading, table, div, code)는 태깅."""
    paragraphs = []
    current_lines = []
    start_line = 1

    for i, line in enumerate(content.splitlines(), 1):
        if line.strip() == "":
            if current_lines:
                text = "\n".join(current_lines)
                ptype = "text"
                first = current_lines[0].strip()
                if first.startswith("#"):
                    ptype = "heading"
                elif first.startswith("|"):
                    ptype = "table"
                elif first.startswith("<div") or first.startswith("<"):
                    ptype = "html"
                elif first.startswith("```") or first.startswith("~~~"):
                    ptype = "code"
                elif first.startswith(">"):
                    ptype = "callout"
                paragraphs.append({
                    "start_line": start_line,
                    "text": text,
                    "type": ptype,
                    "line_count": len(current_lines),
                })
                current_lines = []
            start_line = i + 1
        else:
            current_lines.append(line)

    # 마지막 문단
    if current_lines:
        text = "\n".join(current_lines)
        paragraphs.append({
            "start_line": start_line,
            "text": text,
            "type": "text",
            "line_count": len(current_lines),
        })

    return paragraphs


def detect_paragraph_gaps(
    original_content: str, translated_content: str
) -> list[dict]:
    """문단 수 대응 검증 — 구조 타입별로 원본과 번역본의 문단 수 비교.
    누락/추가 문단 감지.
    """
    issues = []
    orig_paras = _split_paragraphs(original_content)
    trans_paras = _split_paragraphs(translated_content)

    # 타입별 카운트 비교
    orig_type_counts = {}
    trans_type_counts = {}
    for p in orig_paras:
        orig_type_counts[p["type"]] = orig_type_counts.get(p["type"], 0) + 1
    for p in trans_paras:
        trans_type_counts[p["type"]] = trans_type_counts.get(p["type"], 0) + 1

    all_types = set(orig_type_counts.keys()) | set(trans_type_counts.keys())
    for ptype in all_types:
        orig_c = orig_type_counts.get(ptype, 0)
        trans_c = trans_type_counts.get(ptype, 0)
        if ptype == "text":
            # 텍스트 문단은 ±20% 허용 (번역 시 문단 분리/병합 가능)
            tolerance = max(2, int(orig_c * 0.2))
            if abs(orig_c - trans_c) > tolerance:
                issues.append({
                    "type": "paragraph_count_gap",
                    "element": ptype,
                    "original": orig_c,
                    "translated": trans_c,
                    "detail": f"'{ptype}' 문단 수 차이: 원본 {orig_c} vs 번역 {trans_c} (허용 ±{tolerance})",
                })
        else:
            # 구조 요소는 정확히 일치해야 함
            if orig_c != trans_c:
                issues.append({
                    "type": "paragraph_count_gap",
                    "element": ptype,
                    "original": orig_c,
                    "translated": trans_c,
                    "detail": f"'{ptype}' 블록 수 불일치: 원본 {orig_c} vs 번역 {trans_c}",
                })

    # 전체 줄 수 비율 경고
    orig_lines = len(original_content.splitlines())
    trans_lines = len(translated_content.splitlines())
    if orig_lines > 0:
        line_ratio = trans_lines / orig_lines
        if line_ratio < 0.6 or line_ratio > 1.8:
            issues.append({
                "type": "line_count_ratio",
                "original": orig_lines,
                "translated": trans_lines,
                "ratio": round(line_ratio, 2),
                "detail": f"줄 수 비율 이상: {trans_lines}/{orig_lines} = {line_ratio:.2f}x (정상 범위 0.6~1.8x)",
            })

    return issues


def detect_untranslated_residue(
    original_content: str, translated_content: str,
    min_length: int = 8,
) -> list[dict]:
    """번역본에 원본 언어가 남아있는 구간 감지.

    원본의 지배적 문자 체계를 파악 → 번역본에서 해당 문자 체계가
    일정 길이 이상 연속으로 나타나는 구간을 '미번역 잔류'로 보고.
    (heading 텍스트, 고유명사, 코드블록 내부는 제외)
    """
    issues = []
    orig_script = detect_dominant_script(original_content)
    trans_script = detect_dominant_script(translated_content)

    # 원본과 번역본의 문자 체계가 같으면 (같은 언어권 → 의미 없음)
    if orig_script == trans_script or orig_script == "unknown":
        return issues

    # 원본 문자 체계 패턴
    orig_pattern = _LANG_RANGES.get(orig_script)
    if not orig_pattern:
        return issues

    # 번역본에서 원본 문자 체계가 연속으로 나타나는 구간 찾기
    # 코드블록 제거
    clean_trans = re.sub(r'```[\s\S]*?```', '', translated_content)
    clean_trans = re.sub(r'~~~[\s\S]*?~~~', '', clean_trans)
    # HTML 태그 내 속성값 제거
    clean_trans = re.sub(r'<[^>]+>', '', clean_trans)

    lines = clean_trans.splitlines()
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        # 헤딩 제외 (원본 헤딩을 참고용으로 남기는 경우)
        if stripped.startswith("#"):
            continue
        # 위키링크 내부 제외
        stripped_no_wiki = re.sub(r'\[\[[^\]]+\]\]', '', stripped)

        # 원본 문자 체계 연속 구간 찾기
        orig_chars = orig_pattern.findall(stripped_no_wiki)
        if len(orig_chars) >= min_length:
            # 해당 줄에서 원본 문자 비율
            total_chars = len(re.findall(r'\S', stripped_no_wiki))
            if total_chars > 0:
                orig_ratio = len(orig_chars) / total_chars
                if orig_ratio > 0.4:  # 40% 이상이 원본 문자면 미번역
                    issues.append({
                        "type": "untranslated_residue",
                        "line_num": i,
                        "original_script": orig_script,
                        "char_count": len(orig_chars),
                        "ratio": round(orig_ratio, 2),
                        "snippet": stripped[:80],
                        "detail": f"L{i} 미번역 잔류 의심 ({orig_script} {len(orig_chars)}자, {orig_ratio:.0%}): '{stripped[:60]}...'",
                    })

    return issues


def compare_documents(original_content: str, translated_content: str,
                     original_size: int, translated_size: int) -> dict:
    """
    Compare structure and metadata of original vs translated documents.

    Args:
        original_content: Content of original markdown file
        translated_content: Content of translated markdown file
        original_size: Size of original file in bytes
        translated_size: Size of translated file in bytes

    Returns:
        Dict with comparison results
    """
    results = {}

    # Heading counts
    original_headings = count_headings(original_content)
    translated_headings = count_headings(translated_content)
    results['headings'] = {
        'original': original_headings,
        'translated': translated_headings,
        'match': original_headings == translated_headings
    }

    # Callout count
    original_callouts = count_callouts(original_content)
    translated_callouts = count_callouts(translated_content)
    results['callouts'] = {
        'original': original_callouts,
        'translated': translated_callouts,
        'match': original_callouts == translated_callouts
    }

    # Table count
    original_tables = count_tables(original_content)
    translated_tables = count_tables(translated_content)
    results['tables'] = {
        'original': original_tables,
        'translated': translated_tables,
        'match': original_tables == translated_tables
    }

    # HTML div count
    original_divs = count_html_divs(original_content)
    translated_divs = count_html_divs(translated_content)
    results['html_blocks'] = {
        'original': original_divs,
        'translated': translated_divs,
        'match': original_divs == translated_divs
    }

    # Code block count
    original_code = count_code_blocks(original_content)
    translated_code = count_code_blocks(translated_content)
    results['code_blocks'] = {
        'original': original_code,
        'translated': translated_code,
        'match': original_code == translated_code
    }

    # Wikilink count
    original_wikilinks = count_wikilinks(original_content)
    translated_wikilinks = count_wikilinks(translated_content)
    results['wikilinks'] = {
        'original': original_wikilinks,
        'translated': translated_wikilinks,
        'match': original_wikilinks == translated_wikilinks
    }

    # Image embed count
    original_images = count_image_embeds(original_content)
    translated_images = count_image_embeds(translated_content)
    results['image_embeds'] = {
        'original': original_images,
        'translated': translated_images,
        'match': original_images == translated_images
    }

    # List items
    original_lists = count_list_items(original_content)
    translated_lists = count_list_items(translated_content)
    list_tolerance = max(2, int(original_lists * 0.1))  # 10% or 2, whichever larger
    list_match = abs(original_lists - translated_lists) <= list_tolerance
    results['list_items'] = {
        'original': original_lists,
        'translated': translated_lists,
        'tolerance': list_tolerance,
        'match': list_match
    }

    # File size ratio
    size_ratio = calculate_size_ratio(original_size, translated_size)
    size_warning = size_ratio > 1.5 or (size_ratio < 0.5 and size_ratio > 0)
    results['file_size'] = {
        'original_bytes': original_size,
        'translated_bytes': translated_size,
        'ratio': size_ratio,
        'warning': size_warning,
        'match': not size_warning
    }

    # === Extended checks (difflib-based) ===

    # Heading sequence alignment
    orig_headings_seq = extract_heading_sequence(original_content)
    trans_headings_seq = extract_heading_sequence(translated_content)
    heading_issues = diff_heading_sequences(orig_headings_seq, trans_headings_seq)
    results['heading_alignment'] = {
        'issues': heading_issues,
        'match': len(heading_issues) == 0,
    }

    # Div style attribute comparison
    orig_div_styles = extract_div_styles(original_content)
    trans_div_styles = extract_div_styles(translated_content)
    div_style_issues = diff_div_styles(orig_div_styles, trans_div_styles)
    results['div_styles'] = {
        'original_count': len(orig_div_styles),
        'translated_count': len(trans_div_styles),
        'issues': div_style_issues,
        'match': len(div_style_issues) == 0,
    }

    # TOC link validation (translated only — original assumed correct)
    toc_issues = validate_toc_links(translated_content)
    results['toc_links'] = {
        'broken_count': len(toc_issues),
        'issues': toc_issues,
        'match': len(toc_issues) == 0,
    }

    # === Fuzzy checks ===

    # Paragraph correspondence (type-level count comparison)
    para_issues = detect_paragraph_gaps(original_content, translated_content)
    results['paragraph_gaps'] = {
        'issues': para_issues,
        'match': len(para_issues) == 0,
    }

    # Untranslated residue detection (cross-script analysis)
    residue_issues = detect_untranslated_residue(original_content, translated_content)
    results['untranslated_residue'] = {
        'count': len(residue_issues),
        'issues': residue_issues,
        'match': len(residue_issues) == 0,
    }

    return results


def format_heading_results(heading_results: dict) -> str:
    """Format heading comparison results for table display."""
    original = heading_results['original']
    translated = heading_results['translated']
    match = heading_results['match']

    original_str = ', '.join(f"{k}:{v}" for k, v in original.items() if v > 0)
    translated_str = ', '.join(f"{k}:{v}" for k, v in translated.items() if v > 0)
    match_symbol = 'PASS' if match else 'FAIL'

    return original_str, translated_str, match_symbol


def print_results_table(results: dict, original_path: str, translated_path: str):
    """
    Print comparison results in table format.

    Args:
        results: Comparison results dict
        original_path: Path to original file
        translated_path: Path to translated file
    """
    print("\n" + "=" * 100)
    print(f"QC DIFF REPORT")
    print("=" * 100)
    print(f"Original:  {original_path}")
    print(f"Translated: {translated_path}")
    print("=" * 100)
    print()

    # Header
    print(f"{'Element':<20} {'Original':<30} {'Translated':<30} {'Match':<10}")
    print("-" * 100)

    # Headings
    orig_h, trans_h, match_h = format_heading_results(results['headings'])
    print(f"{'Headings':<20} {orig_h:<30} {trans_h:<30} {match_h:<10}")

    # Callouts
    orig_c = results['callouts']['original']
    trans_c = results['callouts']['translated']
    match_c = 'PASS' if results['callouts']['match'] else 'FAIL'
    print(f"{'Callouts':<20} {str(orig_c):<30} {str(trans_c):<30} {match_c:<10}")

    # Tables
    orig_t = results['tables']['original']
    trans_t = results['tables']['translated']
    match_t = 'PASS' if results['tables']['match'] else 'FAIL'
    print(f"{'Tables':<20} {str(orig_t):<30} {str(trans_t):<30} {match_t:<10}")

    # HTML Blocks
    orig_div = results['html_blocks']['original']
    trans_div = results['html_blocks']['translated']
    match_div = 'PASS' if results['html_blocks']['match'] else 'FAIL'
    print(f"{'HTML Blocks':<20} {str(orig_div):<30} {str(trans_div):<30} {match_div:<10}")

    # Code Blocks
    orig_code = results['code_blocks']['original']
    trans_code = results['code_blocks']['translated']
    match_code = 'PASS' if results['code_blocks']['match'] else 'FAIL'
    print(f"{'Code Blocks':<20} {str(orig_code):<30} {str(trans_code):<30} {match_code:<10}")

    # Wikilinks
    orig_wiki = results['wikilinks']['original']
    trans_wiki = results['wikilinks']['translated']
    match_wiki = 'PASS' if results['wikilinks']['match'] else 'FAIL'
    print(f"{'Wikilinks':<20} {str(orig_wiki):<30} {str(trans_wiki):<30} {match_wiki:<10}")

    # Image Embeds
    orig_img = results['image_embeds']['original']
    trans_img = results['image_embeds']['translated']
    match_img = 'PASS' if results['image_embeds']['match'] else 'FAIL'
    print(f"{'Image Embeds':<20} {str(orig_img):<30} {str(trans_img):<30} {match_img:<10}")

    # List Items
    orig_li = results['list_items']['original']
    trans_li = results['list_items']['translated']
    match_li = 'PASS' if results['list_items']['match'] else 'FAIL'
    tol = results['list_items']['tolerance']
    print(f"{'List Items':<20} {str(orig_li):<30} {f'{trans_li} (±{tol})':<30} {match_li:<10}")

    # File Size
    orig_size = results['file_size']['original_bytes']
    trans_size = results['file_size']['translated_bytes']
    ratio = results['file_size']['ratio']
    size_status = 'PASS' if not results['file_size']['warning'] else 'WARNING'
    print(f"{'File Size':<20} {f'{orig_size} bytes':<30} {f'{trans_size} bytes':<30} {size_status:<10}")
    print(f"{'  (ratio)':<20} {f'1.0x':<30} {f'{ratio:.2f}x':<30}")

    print("-" * 100)

    # Heading Alignment (extended)
    ha = results.get('heading_alignment', {})
    ha_status = 'PASS' if ha.get('match', True) else 'FAIL'
    ha_count = len(ha.get('issues', []))
    print(f"{'Heading Align':<20} {'(difflib sequence)':<30} {f'{ha_count} issues':<30} {ha_status:<10}")
    for issue in ha.get('issues', [])[:5]:
        print(f"  → {issue['detail']}")

    # Div Style Attributes (extended)
    ds = results.get('div_styles', {})
    ds_status = 'PASS' if ds.get('match', True) else 'FAIL'
    ds_count = len(ds.get('issues', []))
    ds_orig = ds.get("original_count", 0)
    print(f"{'Div Styles':<20} {f'{ds_orig} divs':<30} {f'{ds_count} issues':<30} {ds_status:<10}")
    for issue in ds.get('issues', [])[:5]:
        print(f"  → {issue['detail']}")

    # TOC Link Validation (extended)
    toc = results.get('toc_links', {})
    toc_status = 'PASS' if toc.get('match', True) else 'FAIL'
    toc_count = toc.get('broken_count', 0)
    print(f"{'TOC Links':<20} {'(translated only)':<30} {f'{toc_count} broken':<30} {toc_status:<10}")
    for issue in toc.get('issues', [])[:5]:
        print(f"  → {issue['detail']}")

    # Paragraph Gaps (fuzzy)
    pg = results.get('paragraph_gaps', {})
    pg_status = 'PASS' if pg.get('match', True) else 'FAIL'
    pg_count = len(pg.get('issues', []))
    print(f"{'Paragraph Gaps':<20} {'(fuzzy block count)':<30} {f'{pg_count} issues':<30} {pg_status:<10}")
    for issue in pg.get('issues', [])[:5]:
        print(f"  → {issue['detail']}")

    # Untranslated Residue (fuzzy)
    ur = results.get('untranslated_residue', {})
    ur_status = 'PASS' if ur.get('match', True) else 'FAIL'
    ur_count = ur.get('count', 0)
    print(f"{'Untranslated':<20} {'(cross-script scan)':<30} {f'{ur_count} residues':<30} {ur_status:<10}")
    for issue in ur.get('issues', [])[:5]:
        print(f"  → {issue['detail']}")

    print("=" * 100)
    print()


def results_to_json(results: dict) -> dict:
    """Convert results to JSON-serializable dict with pass/fail summary."""
    all_match = all(
        results[key].get('match', True)
        for key in results
    )

    # Collect all issues
    all_issues = []
    for key in ('heading_alignment', 'div_styles', 'toc_links', 'paragraph_gaps', 'untranslated_residue'):
        if key in results:
            all_issues.extend(results[key].get('issues', []))

    return {
        "passed": all_match,
        "summary": {
            key: {
                "match": results[key].get('match', True),
                "original": results[key].get('original'),
                "translated": results[key].get('translated'),
            }
            for key in ('headings', 'callouts', 'tables', 'html_blocks',
                        'code_blocks', 'wikilinks', 'image_embeds',
                        'list_items', 'file_size')
        },
        "extended_issues": all_issues,
        "file_size_ratio": results['file_size']['ratio'],
    }


def main():
    """Main entry point."""
    json_mode = '--json' in sys.argv
    args = [a for a in sys.argv[1:] if a != '--json']

    if len(args) != 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)

    original_path = args[0]
    translated_path = args[1]

    try:
        original_content, original_size = read_file(original_path)
        translated_content, translated_size = read_file(translated_path)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)
    except IOError as e:
        print(f"ERROR: Could not read file: {e}", file=sys.stderr)
        sys.exit(2)

    # Compare documents
    results = compare_documents(original_content, translated_content,
                               original_size, translated_size)

    if json_mode:
        output = results_to_json(results)
        print(json_lib.dumps(output, ensure_ascii=False, indent=2))
    else:
        # Print results table
        print_results_table(results, original_path, translated_path)

    # Determine exit code
    all_match = all(
        results[key].get('match', True)
        for key in results
    )

    if not json_mode:
        if all_match:
            print("Status: All structural elements match!")
        else:
            print("Status: MISMATCHES DETECTED - review table above")

    sys.exit(0 if all_match else 1)


if __name__ == '__main__':
    main()
