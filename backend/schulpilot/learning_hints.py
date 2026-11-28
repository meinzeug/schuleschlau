"""Progressive help for the saved error. No extra model call or fuzzy success."""

import re
from fractions import Fraction
from math import gcd

from .answer_evaluation import normalized
from .checks import fraction_parts


def clarify_fraction_product_hint(question, text):
    """Explain the intermediate product only for a verified reduced choice task.

    This is a projection, not a migration of historical hint events or answers.
    Unknown task forms and inconsistent answer options remain unchanged.
    """
    if (not isinstance(text, str) or question.get("language")
            or question.get("type") != "choice"
            or not re.search(r"multiplizier", text, re.I)
            or not re.search(r"nenner", text, re.I)
            or re.search(r"kürz", text, re.I)):
        return text
    prompt = question.get("prompt", "")
    if not isinstance(prompt, str) or not re.search(r"vollständig\s+gekürzt\w*", prompt, re.I):
        return text
    # The saved question can use LaTeX even though its choices use `9/2`.
    # Normalize only simple, positive numeric fractions and explicit products;
    # unsupported fraction commands must not be silently overlooked.
    prompt = re.sub(
        r"\\[dt]?frac\s*\{\s*([1-9]\d{0,2})\s*\}\s*\{\s*([1-9]\d{0,2})\s*\}",
        r"\1/\2", prompt,
    )
    if re.search(r"\\[dt]?frac\b", prompt):
        return text
    prompt = re.sub(r"\\(?:cdotp|cdot|times)(?![A-Za-z])", " * ", prompt)
    expressions = list(re.finditer(
        r"(?<![\d/])([1-9]\d{0,2})\s*/\s*([1-9]\d{0,2})\s*(?:\*|×|·|mal)\s*([1-9]\d{0,2})(?![\d/])",
        prompt, re.I,
    ))
    if len(expressions) != 1 or len(re.findall(r"\d+\s*/\s*\d+", prompt)) != 1:
        return text
    numerator, denominator, factor = map(int, expressions[0].groups())
    product = numerator * factor
    if gcd(product, denominator) <= 1:
        return text
    key = question.get("answer")
    key_parts = fraction_parts(key) if isinstance(key, str) else None
    result = Fraction(product, denominator)
    if key_parts != (result.numerator, result.denominator):
        return text
    options = question.get("options")
    if not isinstance(options, list):
        return text
    parsed = [fraction_parts(option) for option in options if isinstance(option, str)]
    if sum(parts is not None and Fraction(*parts) == result for parts in parsed) != 1 or key_parts not in parsed:
        return text
    # This exact model error is not a valid first step for multiplying a
    # fraction by a whole number: changing both parts preserves the fraction.
    # Only replace a complete, unambiguous instruction; do not guess at longer
    # explanations or alter the saved event. Genuine expansion questions do
    # not pass the verified product/result guard above.
    if re.fullmatch(
        r"\s*multipliziere\s+(?:den\s+)?zähler\s+und\s+(?:den\s+)?nenner\s+"
        r"(?:(?:jeweils|beide)\s+)?mit\s+(?:der\s+zahl\s+)?\d{1,3}\s*[.!]?\s*",
        text, re.I,
    ):
        text = f"Multipliziere den Zähler mit {factor} und behalte den Nenner bei."
    return (f"{text.rstrip()} Das ergibt zuerst {product}/{denominator}. "
            "Kürze nun Zähler und Nenner durch dieselbe Zahl. "
            "Wähle den vollständig gekürzten Bruch.")


def match_parts(question, answer):
    if question["type"] != "match":
        return []
    given = answer.split(";")
    expected = question["answer"].split(";")
    return [{"label": pair.split("|")[0],
             "outcome": "correct" if i < len(given) and i < len(expected) and normalized(given[i]) == normalized(expected[i]) else "incorrect"}
            for i, pair in enumerate(question["options"])]


def next_hint(question, previous_answer, shown):
    shown = [clarify_fraction_product_hint(question, text) for text in shown]
    parts = match_parts(question, previous_answer or "") if previous_answer is not None else []
    wrong = next((i for i, part in enumerate(parts) if part["outcome"] != "correct"), None)
    candidates = []
    if wrong is not None:
        part = parts[wrong]
        right = question["answer"].split(";")[wrong]
        successes = sum(p["outcome"] == "correct" for p in parts)
        candidates.append(f"{successes} von {len(parts)} Zuordnungen stimmen. Schau noch einmal auf „{part['label']}“. Die anderen Paare kannst du lassen.")
        if "säugetier" in normalized(right):
            candidates.append(f"Zusatzwissen für „{part['label']}“: Überlege, womit die Mutter ihre Jungen ernährt. Die Tierklasse hat damit zu tun.")
            candidates.append("Zusatzwissen: Säugetiere ernähren ihre Jungen mit Milch. Nutze dieses Merkmal für die noch offene Zuordnung.")
        else:
            candidates.extend(h for h in question["hints"] if part['label'].casefold() in h.casefold())
            candidates.append(f"Vergleiche das Körpermerkmal von „{part['label']}“ mit den Klassen in deiner Erklärung.")
    if question.get("language") and previous_answer:
        from .language_evaluation import evaluate

        evaluation = evaluate(question, previous_answer)
        if evaluation["dimensions"].get("capitalization") == "incorrect":
            candidates.append(evaluation["reason"])
        meta = question["language"]
        expected = question["answer"]
        if meta.get("skill") == "spelling" and len(expected) == len(previous_answer) + 1:
            for i, character in enumerate(expected):
                if normalized(expected[:i] + expected[i+1:]) == normalized(previous_answer):
                    candidates.append(f"Prüfe die Schreibung: An Stelle {i+1} fehlt noch ein „{character}“. Ergänze es in deiner Antwort.")
                    break
    if not question.get("language") and previous_answer:
        from .answer_evaluation import fraction_addition_hint

        candidates.extend(fraction_addition_hint(question, previous_answer))
    if wrong is None:
        candidates.extend(question["hints"])
    if re.search(r"\bkleinst(?:e|es|en) gemeinsam(?:e|es|en) vielfache\b",
                 question.get("prompt", ""), re.I):
        candidates.append("Schreibe die Vielfachen beider Zahlen auf. Welche Zahl taucht in beiden Reihen zuerst auf?")
    if (question.get("type") == "short" and re.fullmatch(
            r"Nenne alle positiven Teiler von [1-9][0-9]{0,2}\. Trenne sie durch Kommas\.",
            question.get("prompt", ""))):
        candidates.append("Beginne bei 1 und prüfe die Zahlen der Reihe nach. Nur wenn die Division ohne Rest aufgeht, gehört die Zahl dazu.")
    # An explanation may contain the complete answer.  It is available via
    # the explicit explanation action, but must not be copied into an ordinary
    # hint just because the model supplied fewer than three hints.  Previously
    # saved hint events are intentionally left intact for replay and history.
    candidates.extend([
        "Schau dir die Angaben noch einmal an. Welchen Schritt kannst du zuerst machen?",
        "Was weißt du schon über dieses Thema? Nutze es für den nächsten Schritt.",
        "Wenn du nicht weiterkommst, öffne die Erklärung und schau dir den Weg an.",
    ])
    return next((value for candidate in candidates
                 if (value := clarify_fraction_product_hint(question, candidate)) not in shown), None)
