"""Order attempts of one question using their persisted sequence number."""

def question_order(attempt):
    number = (attempt.evaluation or {}).get("attempt_number")
    return attempt.created, number if isinstance(number, int) and not isinstance(number, bool) else 0, attempt.id
