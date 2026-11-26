"""Recognize an explicitly taught common-denominator comparison procedure.

The result is a literal source excerpt, never a model-created or inferred rule.
It does not create exercises, alter learning evidence, or call a provider.
"""

import hashlib
import math
import re
import unicodedata
from fractions import Fraction

_STEPS = re.compile(
    r"(?:finde|bestimme|ermittle)\s+(?:zuerst\s+)?(?:das\s+)?"
    r"(?:kleinste\w*\s+gemeinsame\w*\s+vielfache\w*|kgv)"
    r"(?:\s*\(\s*kgv\s*\))?\s+(?:von\s+)?(?:den|der|beiden|die)\s+nenner\w*"
    r"(?P<between_one>.{0,180}?)"
    r"erweitere\s+(?:beide\s+)?brüche\s+auf\s+(?:den\s+)?"
    r"(?:gleichen|gemeinsamen)\s+nenner"
    r"(?P<between_two>.{0,180}?)"
    r"vergleiche\s+(?:dann\s+)?(?:die\s+)?zähler\b",
    re.IGNORECASE | re.DOTALL,
)
_DENIAL = re.compile(
    r"\b(?:nicht|niemals|keinesfalls|falsch\w*|fehlerhaft\w*|gegenbeispiel\w*|"
    r"später|morgen|erst\s+nächste\w*|nur\s+(?:bei|für))\b",
    re.IGNORECASE,
)


def evidence(content):
    """Return an ordered, bounded, literal rule only when all steps are explicit."""
    if not isinstance(content, str) or not content:
        return None
    for match in _STEPS.finditer(content):
        quote = match.group().strip()
        if len(quote) > 500 or _DENIAL.search(quote):
            continue
        # A later heading, negation, or unrelated exercise is not a continuation
        # of the first step. Numbered headings within the rule remain allowed.
        if any(re.search(r"\n\s*\n", match[name]) for name in ("between_one", "between_two")):
            continue
        markers = [re.findall(r"\b([1-9])\s*[.)]\s*schritt\b", match[name], re.I)
            for name in ("between_one", "between_two")]
        if markers[0] not in ([], ["2"]) or markers[1] not in ([], ["3"]):
            continue
        line_start = content.rfind("\n", 0, match.start()) + 1
        line_end = content.find("\n", match.end())
        prefix = content[line_start:match.start()]
        suffix = content[match.end():line_end if line_end >= 0 else len(content)]
        previous = next((line.strip() for line in reversed(content[:line_start].splitlines()) if line.strip()), "")
        if _DENIAL.search(prefix) or _DENIAL.search(suffix) or _DENIAL.search(previous):
            continue
        return quote
    return None


_NUMBERED = (
    re.compile(r"(?is)^\s*1\s*[.)]\s*schritt\s*:\s*(?P<quote>(?:finde|bestimme|ermittle)\s+(?:zuerst\s+)?(?:das\s+)?"
        r"(?:kleinste\w*\s+gemeinsame\w*\s+vielfache\w*|kgv)(?:\s*\(\s*kgv\s*\))?\s+"
        r"(?:von\s+)?(?:den|der|beiden|die)\s+nenner\w*)"),
    re.compile(r"(?is)^\s*2\s*[.)]\s*schritt\s*:\s*(?P<quote>erweitere\s+(?:beide\s+)?brüche\s+auf\s+(?:den\s+)?"
        r"(?:(?:gleichen|gemeinsamen)\s+nenner|[„\"]?kgv\s*[-–]\s*nenner[“\"]?))"),
    re.compile(r"(?is)^\s*3\s*[.)]\s*schritt\s*:\s*(?P<quote>vergleiche\s+(?:dann\s+)?(?:die\s+)?zähler\b)"),
)


def rule(content):
    """Return independently quotable, correctly ordered explicit rule steps.

    OCR may store numbered instructions in distinct safe blocks. We accept
    these only as three separately quoted positive statements, never as a
    fabricated continuous quotation. Excluded blocks are not read or cited.
    """
    quote = evidence(content)
    if quote is not None:
        return {"version": 1, "kind": "continuous", "quotes": [quote]}
    if not isinstance(content, str):
        return None
    blocks = content.split("\n\n")
    chosen, positions = [], []
    for position, block in enumerate(blocks):
        if len(chosen) >= 3:
            break
        match = _NUMBERED[len(chosen)].match(block)
        if match is None:
            if chosen and re.match(r"(?is)^\s*[1-9]\s*[.)]\s*schritt\s*:", block):
                return None  # Do not splice two different numbered procedures.
            continue
        # Only the instruction sentence can be evidence. A visible correction,
        # negation or contradictory continuation quarantines that step.
        line_end = block.find("\n", match.end())
        tail = block[match.end():line_end if line_end >= 0 else len(block)]
        if _DENIAL.search(match.group()) or _DENIAL.search(tail):
            return None
        chosen.append(match.group("quote").strip())
        positions.append(position)
    if len(chosen) != 3 or positions != sorted(set(positions)):
        return None
    if positions[-1] - positions[0] > 6 or sum(map(len, blocks[positions[0]:positions[-1] + 1])) > 900:
        return None
    if positions[0] > 0 and _DENIAL.search(blocks[positions[0] - 1]):
        return None
    if positions[-1] + 1 < len(blocks) and re.match(
            r"(?i)^\s*(?:achtung\s*:\s*)?(?:falsch\w*|nicht|fehlerhaft\w*|gegenbeispiel\w*)\b",
            blocks[positions[-1] + 1]):
        return None
    # A visible contrary statement between the numbered steps is not ignored.
    if any(_DENIAL.search(block) for block in blocks[positions[0]:positions[-1] + 1]):
        return None
    return {"version": 1, "kind": "numbered_safe_blocks", "quotes": chosen}


def comparison_signature(prompt):
    """Conservatively canonicalize an explicit two-fraction comparison."""
    if not isinstance(prompt, str):
        return None
    text = unicodedata.normalize("NFKC", prompt).casefold()
    if (not re.search(r"vergleich|gr(?:ö|oe|o)ss?er|kleiner", text)
            or re.search(r"erweit|kürz|kuerz|addier", text)):
        return None
    pairs = re.findall(r"(?<![\w/])(\d{1,4})\s*/\s*(\d{1,4})(?![\w/]|[.,][0-9])", text)
    if len(pairs) != 2 or any(int(denominator) == 0 for _, denominator in pairs):
        return None
    return "compare", tuple(sorted((str(int(numerator)), str(int(denominator))) for numerator, denominator in pairs))


def plan(content, previous_prompts, count, seed):
    """Plan bounded, novel comparisons after a literal procedure was verified.

    This is private planning data, not evidence of a learner's answer. The
    caller must bind each question, solution and graphic to the same source
    revision and recheck history before publishing it.
    """
    from .math_tasks import _task
    from .package_prepared_graphics import _fraction_bases

    source_rule = rule(content)
    if (source_rule is None or type(count) is not int or not 1 <= count <= 5
            or not isinstance(seed, str) or not isinstance(previous_prompts, list)
            or any(not isinstance(prompt, str) for prompt in previous_prompts)):
        return []
    excluded = {comparison_signature(prompt) for prompt in previous_prompts} - {None}
    originals = {tuple(base["numbers"]) for base, _ in _fraction_bases(content)}
    pool = []
    for b in range(2, 13):
        for d in range(b + 1, 13):
            if math.lcm(b, d) > 24:
                continue
            for a in range(1, b):
                for c in range(1, d):
                    if (a, b) in originals or (c, d) in originals or Fraction(a, b) == Fraction(c, d):
                        continue
                    prompt, answer = _task("compare", (a, b, c, d), "apply")
                    signature = comparison_signature(prompt)
                    if signature is not None and signature not in excluded:
                        pool.append(((a, b, c, d), prompt, answer, signature))
    pool.sort(key=lambda item: hashlib.sha256(f"{seed}|{item[0]}".encode()).digest())
    result, seen = [], set(excluded)
    for numbers, prompt, answer, signature in pool:
        if signature in seen:
            continue
        seen.add(signature)
        result.append({"type": "short", "prompt": prompt, "answer": answer,
            "options": [], "accepted": [], "source_excerpt": source_rule["quotes"][0],
            "comparison": {"left": list(numbers[:2]), "right": list(numbers[2:]),
                "common_denominator": math.lcm(numbers[1], numbers[3])}})
        if len(result) == count:
            return result
    return []  # Never silently repeat or truncate when the finite pool is exhausted.
