"""Conservative exact-answer check; this is not a semantic safety classifier."""

import re
import unicodedata


def normalize(text):
    text = unicodedata.normalize("NFKC", text).casefold()
    text = re.sub(r"\\(?:d?frac)\s*\{\s*(\d+)\s*\}\s*\{\s*(\d+)\s*\}", r"\1/\2", text)
    text = text.replace("⁄", "/").replace("∕", "/")
    text = re.sub(r"(?<=\d)\s*/\s*(?=\d)", "/", text)
    return " ".join(text.split())


def contains(text, value):
    # Avoid matching an integer inside a larger number or a fraction.
    boundary = r"(?<![\w/])" + (r"(?<!\d[.,])" if value.isdecimal() else "")
    suffix = r"(?![\w/])" + (r"(?![.,]\d)" if value.isdecimal() else "")
    return bool(re.search(boundary + re.escape(value).replace(r"\ ", r"\s+") + suffix, text))


def reveals_exact_answer(question, reply, *, visible_explanation=""):
    """Check displayed answer, citations and suggestions, not provider inputs.

    Only simple stored answer types are supported. An answer already given in
    the prompt cannot be hidden and is skipped except in a choice question.
    Single letters and very short words are intentionally not classified:
    semantic variants and paraphrases are outside this finite check.
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
    return False
