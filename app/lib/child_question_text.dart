/// Removes the internal phase label from the fixed fraction-component template.
/// The saved prompt and all task instructions remain unchanged on the server.
String childQuestionText(String prompt) {
  final template = RegExp(
    r'^(Wie lautet der (?:Zähler|Nenner) des Bruchs [0-9]{1,2}/[0-9]{1,2}\?) '
    r'Neues Übungsbeispiel zum (?:Verstehen|Fehlerkorrigieren|Anwenden|Erinnern): ',
  );
  return prompt.replaceFirstMapped(template, (match) => '${match[1]} ');
}
