"""Extract a complete successful Gradle dependency tree without build paths."""

import argparse
import re
from pathlib import Path

CONFIGURATIONS = ("directReleaseRuntimeClasspath", "playReleaseRuntimeClasspath")


def extract(report, configuration):
    if configuration not in CONFIGURATIONS:
        raise ValueError("Unknown release configuration")
    if "BUILD SUCCESSFUL" not in report or "BUILD FAILED" in report:
        raise ValueError("Gradle did not report a successful build")
    lines = report.splitlines()
    prefix = configuration + " - Runtime classpath"
    starts = [i for i, line in enumerate(lines) if line.startswith(prefix)]
    if len(starts) != 1:
        raise ValueError("Expected exactly one matching Gradle configuration")
    tree = []
    for line in lines[starts[0] + 1:]:
        if not line.strip():
            break
        node = re.fullmatch(r"[ |+\\\-]*--- (.+)", line)
        if (not node or " FAILED" in line or not re.match(
                r"^(?:project :[A-Za-z0-9_:-]+|[A-Za-z0-9_.-]+:[A-Za-z0-9_.-]+(?::\S+| -> \S+))",
                node.group(1))):
            raise ValueError("Invalid or unresolved dependency in Gradle tree")
        tree.append(line)
    if not tree:
        raise ValueError("Empty Gradle dependency tree")
    value = prefix + "\n" + "\n".join(tree) + "\n"
    coordinates(value)
    return value


def coordinates(tree):
    """Return resolved Maven coordinates; Gradle constraints are not artifacts."""
    lines = tree.splitlines()
    if not lines or lines[0] not in {name + " - Runtime classpath" for name in CONFIGURATIONS}:
        raise ValueError("Invalid dependency tree header")
    result = set()
    for line in lines[1:]:
        prefix = re.fullmatch(r"[ |+\\\-]*--- (.+)", line)
        if not prefix or " FAILED" in line:
            raise ValueError("Invalid dependency tree")
        node = prefix.group(1)
        if re.fullmatch(r"project :[A-Za-z0-9_:-]+(?: \(\*\))?", node):
            continue
        match = re.fullmatch(
            r"([A-Za-z0-9_.-]+:[A-Za-z0-9_.-]+)(?::([^\s:]+))?(?: -> ([^\s:]+))?(?: \((?:c|\*)\))?",
            node,
        )
        if not match or not (match[3] or match[2]):
            raise ValueError("Dependency has no resolved Maven version")
        if node.endswith("(c)"):
            continue
        result.add((match[1], match[3] or match[2]))
    return sorted(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("configuration", choices=CONFIGURATIONS)
    parser.add_argument("report", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_text(extract(args.report.read_text(), args.configuration))


if __name__ == "__main__":
    main()
