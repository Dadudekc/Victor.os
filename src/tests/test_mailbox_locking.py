import concurrent.futures
import multiprocessing
import json
from pathlib import Path

from dreamos.core.comms.mailbox_utils import write_mailbox_message, read_mailbox_messages


def _write_message(args):
    agent_id, msg, mailbox_dir = args
    from dreamos.core.comms import mailbox_utils
    mailbox_utils.MAILBOX_ROOT = mailbox_dir
    message = {"sender": agent_id, "content": msg}
    write_mailbox_message(agent_id, message)


def test_mailbox_locking(tmp_path):
    mailbox_root = tmp_path / "runtime" / "agent_comms" / "agent_mailboxes"
    # patch MAILBOX_ROOT for this test
    from dreamos.core.comms import mailbox_utils

    mailbox_utils.MAILBOX_ROOT = mailbox_root

    agent = "Agent-9"
    messages = [f"message {i}" for i in range(5)]

    with multiprocessing.Pool(processes=5) as pool:
        pool.map(_write_message, [(agent, m, mailbox_root) for m in messages])

    inbox = mailbox_root / agent / "inbox.json"
    assert inbox.exists()
    with open(inbox, "r") as f:
        data = json.load(f)
    assert len(data) == len(messages)
    contents = [m["content"] for m in data]
    for msg in messages:
        assert msg in contents


