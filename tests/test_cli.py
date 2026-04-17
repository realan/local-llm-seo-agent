from click.testing import CliRunner

from app.main import cli


def test_demo_accepts_named_scenario_option(monkeypatch):
    runner = CliRunner()

    class FakeClient:
        def health_status(self):
            return True, "ok"

    monkeypatch.setattr("app.main.OllamaClient", lambda: FakeClient())
    monkeypatch.setattr("app.main._run_demo_scenario", lambda client, task, scenario: True)

    result = runner.invoke(cli, ["demo", "--scenario", "calculator"])

    assert result.exit_code == 0
    assert "Running: Calculator" in result.output


def test_demo_rejects_unknown_scenario():
    runner = CliRunner()

    result = runner.invoke(cli, ["demo", "--scenario", "unknown"])

    assert result.exit_code != 0
    assert "Invalid value for '--scenario'" in result.output


def test_chat_runs_until_exit(monkeypatch):
    runner = CliRunner()
    calls = []

    class FakeClient:
        def health_status(self):
            return True, "ok"

    def fake_run(client, task, scenario):
        calls.append((task, scenario))
        return True

    monkeypatch.setattr("app.main.OllamaClient", lambda: FakeClient())
    monkeypatch.setattr("app.main._run_demo_scenario", fake_run)

    result = runner.invoke(cli, ["chat"], input="Calculate 2+2\nexit\n")

    assert result.exit_code == 0
    assert calls == [("Calculate 2+2", "chat")]
    assert "Chat Mode" in result.output
    assert "Chat closed." in result.output


def test_demo_can_register_excel_capable_runner(monkeypatch):
    runner = CliRunner()

    class FakeClient:
        def health_status(self):
            return True, "ok"

    captured = {}

    def fake_run(client, task, scenario):
        captured["task"] = task
        captured["scenario"] = scenario
        return True

    monkeypatch.setattr("app.main.OllamaClient", lambda: FakeClient())
    monkeypatch.setattr("app.main._run_demo_scenario", fake_run)

    result = runner.invoke(
        cli,
        ["demo", "--task", "Open samples/products.xlsx and count the rows"],
    )

    assert result.exit_code == 0
    assert captured == {
        "task": "Open samples/products.xlsx and count the rows",
        "scenario": "custom",
    }
