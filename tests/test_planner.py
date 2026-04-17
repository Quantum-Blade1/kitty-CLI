from kittycode.agent.planner import Planner


class _Result:
    def __init__(self, output):
        self.output = output


class _FakeRouter:
    def generate(self, prompt, task_type="Thought"):
        if "architectural engine" in prompt[0]["content"]:
            return _Result(
                {
                    "content": (
                        '{"scope":"Project","reasoning":"Needs file operations",'
                        '"queue":[{"step":"List files","executable":true},{"step":"Summarize code","executable":false}]}'
                    )
                }
            ), "fake-model"
        return _Result({"content": "Reflection note"}), "fake-model"


def test_planner_parses_scope_and_queue():
    planner = Planner(router=_FakeRouter())
    queue = planner.generate_plan("Analyze this repo and report.")

    assert planner.current_scope == "Project"
    assert len(queue) == 2
    assert queue[0]["step"] == "List files"
    assert queue[0]["executable"] is True
    assert queue[1]["executable"] is False
