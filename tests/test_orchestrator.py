import pytest
import dreamos.orchestrator as orchestrator
import dreamos.cursor_interface as cursor_interface
import dreamos.chatgpt_interface as chatgpt_interface
import dreamos.evaluator as evaluator


def test_run_cycle_single(monkeypatch):
    # track prompt injections
    calls = []
    def fake_send(ctx):
        calls.append(ctx.copy())
    monkeypatch.setattr(cursor_interface, "send_prompt", fake_send)

    # fetch_reply returns draft then final
    def fake_fetch(final=False):
        return "draft_reply" if not final else "final_reply"
    monkeypatch.setattr(cursor_interface, "fetch_reply", fake_fetch)

    # refine returns a refined prompt
    monkeypatch.setattr(chatgpt_interface, "refine", lambda c: "refined_reply")

    # evaluate always passes
    monkeypatch.setattr(evaluator, "evaluate", lambda out, ctx: True)

    # run the cycle
    result = orchestrator.run_cycle({"prompt": "initial"})
    assert result == "final_reply"
    # ensure two prompts: initial and refined
    assert len(calls) == 2
    assert calls[0]["prompt"] == "initial"
    assert calls[1]["prompt"] == "refined_reply"


def test_run_cycle_loop(monkeypatch):
    calls = []
    monkeypatch.setattr(cursor_interface, "send_prompt", lambda ctx: calls.append(ctx.copy()))

    # first draft reply and final reply sequences
    monkeypatch.setattr(cursor_interface, "fetch_reply", lambda final=False: (
        "draft1" if not final else "bad_final" if len(calls) < 2 else "good_final"
    ))

    # refine echoes prompt
    monkeypatch.setattr(chatgpt_interface, "refine", lambda c: c.get("reply", "") + "_refined")

    # evaluate fails on bad_final, passes on good_final
    monkeypatch.setattr(evaluator, "evaluate", lambda out, ctx: out == "good_final")

    # initial context
    ctx = {"prompt": "start"}
    result = orchestrator.run_cycle(ctx)
    assert result == "good_final"
    # should have run at least two cycles of send_prompt
    assert len(calls) >= 4
    # check last sent prompt is refined bad_final
    assert calls[-2]["prompt"] == "bad_final_refined"
    assert calls[-1]["prompt"] == "bad_final_refined" 
