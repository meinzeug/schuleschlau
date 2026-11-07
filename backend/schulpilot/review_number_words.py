"""Conservative German numeral recognition for prior-question exclusions."""
import re


def written_numbers(prompts):
    """Recognize German cardinal numbers 1–120 in prior questions conservatively."""
    ones = {1: 'eins', 2: 'zwei', 3: 'drei', 4: 'vier', 5: 'fuenf', 6: 'sechs',
            7: 'sieben', 8: 'acht', 9: 'neun', 10: 'zehn', 11: 'elf', 12: 'zwoelf',
            13: 'dreizehn', 14: 'vierzehn', 15: 'fuenfzehn', 16: 'sechzehn',
            17: 'siebzehn', 18: 'achtzehn', 19: 'neunzehn'}
    tens = {20: 'zwanzig', 30: 'dreissig', 40: 'vierzig', 50: 'fuenfzig',
            60: 'sechzig', 70: 'siebzig', 80: 'achtzig', 90: 'neunzig'}
    variants = {n: [name] for n, name in ones.items()}
    variants.update({n: [name] for n, name in tens.items()})
    for number in range(21, 100):
        if number % 10:
            first = 'ein' if number % 10 == 1 else ones[number % 10]
            variants[number] = [first + r'[\s-]*und[\s-]*' + tens[number // 10 * 10]]
    variants[100] = [r'(?:ein)?hundert']
    for number in range(101, 121):
        variants[number] = [r'(?:ein)?hundert[\s-]*(?:und[\s-]*)?' + value
                            for value in variants[number - 100]]
    joined = ' '.join(prompts).casefold().replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')
    return {number for number, names in variants.items() if any(
        re.search(r'(?<![a-z])' + name + r'(?![a-z])', joined) for name in names)}
