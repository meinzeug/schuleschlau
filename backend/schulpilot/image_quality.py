"""Distinguish actual image/readability warnings from visual-display limits."""

VISUAL_OVERFLOW_WARNING = "Nicht alle Bildbefunde werden angezeigt. Schau dir das Foto an."


def poor_image(material):
    """Keep all existing quality and reading signals except the UI-only limit."""
    warnings = material.quality_warnings or []
    return bool(material.uncertainties or material.legibility in ("partial", "unreadable")
                or any(warning != VISUAL_OVERFLOW_WARNING for warning in warnings))
