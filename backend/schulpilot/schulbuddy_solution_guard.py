"""Conservative exact-answer check; this is not a semantic safety classifier."""

import re
import unicodedata
from fractions import Fraction

_NUMBER = re.compile(
    r"(?<![\w/.,])(?:"
    r"(?P<whole>[+-]?\d{1,5})\s+(?P<mixed_num>\d{1,5})/(?P<mixed_den>[1-9]\d{0,4})"
    r"|(?P<num>[+-]?\d{1,5})/(?P<den>[1-9]\d{0,4})"
    r"|(?P<decimal>[+-]?\d{1,5}[.,]\d{1,5})"
    r")(?![\w/])"
)
_FRACTION_ANSWER = re.compile(r"[+-]?\d{1,5}/[1-9]\d{0,4}\Z")


def normalize(text):
    text = unicodedata.normalize("NFKC", text).casefold()
    text = text.replace("−", "-")
    text = re.sub(r"\\(?:d?frac)\s*\{\s*(\d+)\s*\}\s*\{\s*(\d+)\s*\}", r"\1/\2", text)
    text = text.replace("⁄", "/").replace("∕", "/")
    text = re.sub(r"(?<=\d)\s*/\s*(?=\d)", "/", text)
    return " ".join(text.split())


def contains(text, value):
    # Avoid matching an integer inside a larger number or a fraction.
    boundary = r"(?<![\w/])" + (r"(?<!\d[.,])" if value.isdecimal() else "")
    suffix = r"(?![\w/])" + (r"(?![.,]\d)" if value.isdecimal() else "")
    return bool(re.search(boundary + re.escape(value).replace(r"\ ", r"\s+") + suffix, text))


def contains_whole_number(text, value):
    """A signed standalone integer, never part of a decimal or fraction."""
    if value == 0:
        literal = r"[+-]?0"
    elif value > 0:
        literal = r"\+?" + re.escape(str(value))
    else:
        literal = re.escape(str(value))
    return bool(re.search(r"(?<![\w/.,+\-])" + literal + r"(?![\w/]|[.,]\d)", text))


def fraction_values(text):
    """Read only finite literal fraction, decimal and mixed-number forms."""
    result = set()
    for match in _NUMBER.finditer(text):
        if match["whole"] is not None:
            whole, numerator, denominator = int(match["whole"]), int(match["mixed_num"]), int(match["mixed_den"])
            if numerator >= denominator:
                continue
            part = Fraction(numerator, denominator)
            result.add(Fraction(whole) - part if match["whole"].startswith("-") else Fraction(whole) + part)
        elif match["num"] is not None:
            result.add(Fraction(int(match["num"]), int(match["den"])))
        else:
            result.add(Fraction(match["decimal"].replace(",", ".")))
    return result


def reveals_exact_answer(question, reply, *, visible_explanation="", mathematics=False):
    """Check displayed answer, citations and suggestions, not provider inputs.

    Only simple stored answer types are supported. An answer already given in
    the prompt or opened explanation is skipped except in a choice question.
    Numeric equivalence is limited to explicit fractions in mathematics;
    single letters, very short words and semantic paraphrases are not covered.
    """
    if not isinstance(question, dict) or question.get("type") not in ("short", "gap", "choice"):
        return False
    accepted = question.get("accepted")
    answers = [question.get("answer"), *(accepted if isinstance(accepted, list) else [])]
    prompt = normalize(question.get("prompt") if isinstance(question.get("prompt"), str) else "")
    visible = normalize(visible_explanation) if isinstance(visible_explanation, str) else ""
    pieces = [reply.get("answer"), reply.get("next_question")]
    pieces.extend(reply.get("starters") or [])
    pieces.extend(citation.get("quote") for citation in reply.get("sources", []) if isinstance(citation, dict))
    displayed = normalize("\n".join(piece for piece in pieces if isinstance(piece, str)))
    for answer in answers:
        if not isinstance(answer, str):
            continue
        value = normalize(answer)
        if not value or (len(value) < 3 and not value.isdecimal()):
            continue
        if question.get("type") != "choice" and (contains(prompt, value) or contains(visible, value)):
            continue
        if contains(displayed, value):
            return True
        # This is disclosure prevention, not answer grading. Only a stored
        # literal fraction in mathematics is compared; a value already in the
        # displayed prompt/explanation is not treated as newly disclosed.
        if (mathematics and question.get("type") in ("short", "gap") and not question.get("language")
                and _FRACTION_ANSWER.fullmatch(value)):
            numerator, denominator = value.split("/")
            expected = Fraction(int(numerator), int(denominator))
            if (expected not in fraction_values(prompt) and expected not in fraction_values(visible)
                    and expected in fraction_values(displayed)):
                return True
            # A fraction can simplify to an integer (2/2 → 1). Only compare
            # standalone signed integer tokens, never digits inside another
            # fraction or decimal, and do not hide a number already shown.
            if expected.denominator == 1 and not contains_whole_number(prompt, expected.numerator) \
                    and not contains_whole_number(visible, expected.numerator) \
                    and contains_whole_number(displayed, expected.numerator):
                return True
    return False
