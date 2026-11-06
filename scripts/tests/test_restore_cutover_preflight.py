import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("preflight", Path(__file__).parents[1] / "restore_cutover_preflight.py")
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


def output(unit):
    if unit == p.BACKUP:
        exe = "/opt/schulpilot/current/venv/bin/python"
        script = "/opt/schulpilot/current/deploy/backup.py"
    else:
        exe = f"/opt/schulpilot/restore-runtimes/{p.OLD}/venv/bin/python"
        script = f"/opt/schulpilot/restore-runtimes/{p.OLD}/deploy/restore_check.py"
    return (
        "LoadState=loaded\nActiveState=inactive\nSubState=dead\nJob=\nType=oneshot\nNeedDaemonReload=no\n"
        f"ExecStart={{ path={exe} ; argv[]={exe} {script} ; ignore_errors=no ; pid=0 ; }}\n"
    )


def test_exact_old_state_is_read_only_and_never_authorizes_activation(monkeypatch):
    monkeypatch.setattr(Path, "is_file", lambda _: True)
    result = p.inspect(output, Path("/opt/schulpilot/restore-runtimes") / p.TARGET)
    assert result["status"] == "read_only_preflight_ok" and result["activation_authorized"] is False
    assert "no_offsite_or_recovery_test" in result["limitations"]


@pytest.mark.parametrize(
    "changed",
    [
        lambda x: x.replace("ActiveState=inactive", "ActiveState=active"),
        lambda x: x.replace("Job=\n", "Job=3\n"),
        lambda x: x.replace("NeedDaemonReload=no", "NeedDaemonReload=yes"),
        lambda x: x.replace("Type=oneshot", "Type=simple"),
        lambda x: x.replace("ignore_errors=no", "ignore_errors=yes"),
        lambda x: x.replace("ignore_errors=no", "ignore_errors=no ; } { path=/evil ; argv[]=/evil"),
        lambda x: x.replace("argv[]=", "argv[]=/bin/sh "),
        lambda x: x + "Job=\n",
    ],
)
def test_unknown_or_changed_state_refused(changed):
    with pytest.raises(ValueError):
        p.validate_unit(p.RESTORE, p.parse_show(changed(output(p.RESTORE))))


def test_incomplete_target_never_accepted(monkeypatch):
    monkeypatch.setattr(Path, "is_file", lambda _: False)
    with pytest.raises(ValueError):
        p.inspect(output, Path("/opt/schulpilot/restore-runtimes") / p.TARGET)


def test_other_target_never_accepted():
    with pytest.raises(ValueError):
        p.inspect(output, Path("/opt/schulpilot/current"))
