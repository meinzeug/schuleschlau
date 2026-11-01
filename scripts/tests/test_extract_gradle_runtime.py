"""Incomplete or unresolved Gradle output is never recorded as an inventory."""

import importlib.util
from pathlib import Path

import pytest

path = Path(__file__).resolve().parents[1] / "extract_gradle_runtime.py"
spec = importlib.util.spec_from_file_location("extract_gradle_runtime", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
CONFIG = "directReleaseRuntimeClasspath"
GOOD = "noise\n" + CONFIG + " - Runtime classpath of '/directRelease'.\n" + (
    "+--- org.example:lib:1.0 -> 1.1\n|    \\--- org.example:child:2.0 (*)\n\n"
) + "BUILD SUCCESSFUL in 1s\n"


def test_extracts_only_the_requested_tree():
    value = module.extract(GOOD, CONFIG)
    assert "org.example:lib:1.0 -> 1.1" in value
    assert "org.example:child:2.0" in value
    assert "noise" not in value and "BUILD SUCCESSFUL" not in value
    assert module.coordinates(value) == [("org.example:child", "2.0"), ("org.example:lib", "1.1")]


def test_constraints_and_local_projects_are_not_artifacts():
    value = CONFIG + " - Runtime classpath\n" + (
        "+--- project :example\n|    +--- org.example:lib -> 3.0\n"
        "|    \\--- org.example:bom:3.0 (c)\n"
    )
    assert module.coordinates(value) == [("org.example:lib", "3.0")]


@pytest.mark.parametrize("tree", ["not a tree\n+--- org.example:lib:1\n",
    CONFIG + " - Runtime classpath\n+--- org.example:lib:1 FAILED\n",
    CONFIG + " - Runtime classpath\n+--- /private/path\n",
    CONFIG + " - Runtime classpath\n+--- org.example:lib:1 -> project :other\n"])
def test_query_rejects_invalid_saved_trees(tree):
    with pytest.raises(ValueError):
        module.coordinates(tree)


@pytest.mark.parametrize("report", [
    GOOD.replace("BUILD SUCCESSFUL", "BUILD FAILED"),
    GOOD.replace("org.example:lib:1.0 -> 1.1", "org.example:lib:1.0 FAILED"),
    GOOD.replace(CONFIG, "debugRuntimeClasspath"),
    GOOD.replace("+--- org.example:lib:1.0 -> 1.1\n|    \\--- org.example:child:2.0 (*)\n", ""),
    GOOD.replace("+--- org.example:lib:1.0 -> 1.1", "+--- /private/path"),
])
def test_rejects_incomplete_or_mismatched_tree(report):
    with pytest.raises(ValueError):
        module.extract(report, CONFIG)
