# dashboard.py  – Dream.OS UI  v3
from __future__ import annotations

import json
import logging
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List
from datetime import datetime

import pyautogui
from PyQt5.QtCore import (
    Qt,
    QAbstractTableModel,
    QModelIndex,
    QVariant,
    QTimer,
    QSortFilterProxyModel,
)
from PyQt5.QtGui import QKeySequence, QColor, QIcon, QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QTableView,
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTabWidget,
    QComboBox,
    QTextEdit,
    QToolBar,
    QAction,
    QMessageBox,
    QInputDialog,
)

# ───────────────────────── Back-end stubs (if missing) ─────────────────────
try:
    from dream_os.services.task_nexus import add_task, claim_task, get_all_tasks
except Exception:  # pragma: no cover
    add_task = lambda task_type, content: uuid.uuid4().hex
    claim_task = lambda agent_id: False
    get_all_tasks = lambda: []

try:
    from core.hooks.chatgpt_responder import ChatGPTResponder
except Exception:  # pragma: no cover
    ChatGPTResponder = None

try:
    from core.agent_utils import save_agent_spot, click_agent_spot, _load_coords
except Exception as e:  # pragma: no cover
    print(f"Critical import miss: {e}")
    sys.exit(1)

# ───────────────────────── configuration + logging ─────────────────────────
@dataclass
class Config:
    refresh_ms: int = 5000
    mailbox_root: Path = Path(__file__).parent / "_agent_coordination" / "shared_mailboxes"
    logs_dir: Path = Path("logs")
    ui_log: str = "ui.log"
    default_agent: str = "agent_001"


CFG = Config()
CFG.logs_dir.mkdir(exist_ok=True)
logging.basicConfig(
    filename=CFG.logs_dir / CFG.ui_log,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

# ───────────────────────── helpers ─────────────────────────
def _safe_json(path: Path) -> Dict | None:
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _qcolor(r: int, g: int, b: int) -> QColor:
    return QColor(r, g, b)


# ───────────────────────── Table models─────────────────────
class TaskModel(QAbstractTableModel):
    HEADERS = ["ID", "Type", "Status", "Content"]

    def __init__(self) -> None:
        super().__init__()
        self.tasks: List[Dict] = []
        self._index: Dict[str, Dict] = {}

    # Qt model overrides
    def rowCount(self, *_):  # noqa: N802
        return len(self.tasks)

    def columnCount(self, *_):  # noqa: N802
        return len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):  # noqa: N802
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return QVariant()

    def data(self, index: QModelIndex, role=Qt.DisplayRole):  # noqa: N802
        if not index.isValid():
            return QVariant()
        task = self.tasks[index.row()]
        col = index.column()
        if role == Qt.DisplayRole:
            if col == 0:
                return task["id"][:8]
            if col == 1:
                return task["type"]
            if col == 2:
                return task["status"]
            if col == 3:
                return task["content"]
        if role == Qt.BackgroundRole and col == 2:
            status = task["status"]
            if status == "failed":
                return _qcolor(255, 128, 128)
            if status == "completed":
                return _qcolor(128, 255, 128)
        return QVariant()

    # incremental update
    def refresh(self, new_tasks: List[Dict]) -> None:
        new_index = {t["id"]: t for t in new_tasks}
        # detect modifications
        changed_rows = []
        if len(new_tasks) != len(self.tasks):
            self.beginResetModel()
            self.tasks = new_tasks
            self._index = new_index
            self.endResetModel()
            return
        for row, task in enumerate(self.tasks):
            incoming = new_index.get(task["id"])
            if not incoming:
                continue
            if incoming != task:
                self.tasks[row] = incoming
                changed_rows.append(row)
        for r in changed_rows:
            top_left = self.index(r, 0)
            bottom_right = self.index(r, self.columnCount() - 1)
            self.dataChanged.emit(top_left, bottom_right, [])  # type: ignore[arg-type]


# ───────────────────────── MailboxModelV4 ─────────────────────────
class MailboxModelV4(QAbstractTableModel):
    HEADERS = ["Mailbox", "Status", "Owner", "#Msgs"]
    def __init__(self) -> None:
        super().__init__()
        self.entries: List[Dict] = []
    def rowCount(self, *_): return len(self.entries)
    def columnCount(self, *_): return len(self.HEADERS)
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role==Qt.DisplayRole and orientation==Qt.Horizontal:
            return self.HEADERS[section]
        return QVariant()
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid(): return QVariant()
        row = self.entries[index.row()]
        col = index.column()
        if role==Qt.DisplayRole:
            if col==0: return row["name"]
            if col==1: return row.get("status", "")
            if col==2: return row.get("owner", "")
            if col==3: return str(len(row.get("messages", [])))
        if role==Qt.BackgroundRole and col==1:
            status = row.get("status", "")
            if status=="CLAIMED": return _qcolor(255,255,180)
            if status=="online": return _qcolor(180,255,180)
            if status=="idle": return _qcolor(220,220,220)
        return QVariant()
    def refresh(self, raw_mailboxes: List[Dict]) -> None:
        self.beginResetModel(); self.entries = raw_mailboxes; self.endResetModel()


# ───────────────────────── Main Window ─────────────────────────
class DashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dream.OS Dashboard")
        self.resize(1280, 820)

        # state switches
        self.auto_click = True
        self.dev_mode = True
        self.responder = ChatGPTResponder(dev_mode=True) if ChatGPTResponder else None

        # build UI
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self._init_toolbar()
        self._init_tasks_tab()
        self._init_mailboxes_tab()
        self._init_agents_tab()
        self._init_comm_tab()

        # data models
        self.task_model = TaskModel()
        self.task_proxy = QSortFilterProxyModel()
        self.task_proxy.setSourceModel(self.task_model)
        self.task_view.setModel(self.task_proxy)
        self.mail_model = MailboxModelV4()
        self.mail_proxy = QSortFilterProxyModel()
        self.mail_proxy.setSourceModel(self.mail_model)
        self.mail_view = QTableView()
        self.mail_view.setModel(self.mail_proxy)

        # refresh driver (watchdog optional)
        self._init_refresh_strategy()

    # ───────────────── toolbar / toggles ─────────────────
    def _init_toolbar(self):
        tb = QToolBar("Main")
        self.addToolBar(tb)

        self.auto_click_act = QAction("Auto-Click", self, checkable=True, checked=True)
        self.auto_click_act.triggered.connect(lambda v: setattr(self, "auto_click", v))
        tb.addAction(self.auto_click_act)

        self.mode_act = QAction(QIcon(), "Dev Mode", self, checkable=True, checked=True)
        self.mode_act.toggled.connect(self._flip_mode)
        tb.addAction(self.mode_act)

    def _flip_mode(self, checked: bool):
        self.dev_mode = checked
        if self.responder:
            self.responder.dev_mode = checked
        self.mode_act.setText("Dev Mode" if checked else "Prod Mode")
        logging.info("Responder mode set to %s", self.mode_act.text())

    # ───────────────── build tabs ─────────────────
    def _init_tasks_tab(self):
        w = QWidget(); lay = QVBoxLayout(w)
        self.task_view = QTableView()
        self.task_view.setSortingEnabled(True)
        lay.addWidget(QLabel("Live Task Queue")); lay.addWidget(self.task_view)

        row = QWidget(); row_lay = QSplitter(Qt.Horizontal); row.setLayout(QVBoxLayout()); row.layout().addWidget(row_lay)
        self.task_type_cb = QComboBox(); self.task_type_cb.addItems(["plan", "code", "social"])
        self.task_input = QLineEdit(placeholderText="Task description…")
        add_btn = QPushButton("Inject", clicked=self._inject_task)
        row_lay.addWidget(self.task_type_cb); row_lay.addWidget(self.task_input); row_lay.addWidget(add_btn)
        lay.addWidget(row)

        claim_btn = QPushButton("Claim next", clicked=self._claim_next)
        lay.addWidget(claim_btn)
        self.tabs.addTab(w, "Tasks")

    def _init_mailboxes_tab(self):
        w, lay = QWidget(), QVBoxLayout(w)
        self.mail_model = MailboxModelV4()
        self.mail_proxy = QSortFilterProxyModel()
        self.mail_proxy.setSourceModel(self.mail_model)
        self.mail_table = QTableView()
        self.mail_table.setModel(self.mail_proxy)
        self.mail_table.setSortingEnabled(True)
        self.mail_table.clicked.connect(self._load_mailbox_view)
        self.msg_view = QTextEdit(readOnly=True)
        self.msg_reply = QLineEdit(placeholderText="Reply to this mailbox...")
        send_btn = QPushButton("Send ➤", clicked=self._send_reply)
        auto_btn = QPushButton("💡 Respond via ChatGPT", clicked=self._auto_respond)
        lay.addWidget(QLabel("Shared Mailboxes")); lay.addWidget(self.mail_table)
        lay.addWidget(QLabel("Messages")); lay.addWidget(self.msg_view)
        lay.addWidget(self.msg_reply); lay.addWidget(send_btn); lay.addWidget(auto_btn)
        self.tabs.addTab(w, "Mailboxes")

    def _init_agents_tab(self):
        w = QWidget(); lay = QVBoxLayout(w)
        self.agent_view = QTableView()
        lay.addWidget(QLabel("Agent Spots")); lay.addWidget(self.agent_view)
        cap_btn = QPushButton("Capture Spot", clicked=self._capture_spot)
        lay.addWidget(cap_btn)
        self.tabs.addTab(w, "Agents")

    def _init_comm_tab(self):
        w = QWidget(); lay = QVBoxLayout(w)
        self.comm_edit = QTextEdit(readOnly=True)
        lay.addWidget(self.comm_edit)
        self.tabs.addTab(w, "Comm")

    # ───────────────── refresh strategy ─────────────────
    def _init_refresh_strategy(self):
        try:
            from watchdog.observers import Observer  # type: ignore
            from watchdog.events import FileSystemEventHandler  # type: ignore

            class _Handler(FileSystemEventHandler):
                def __init__(self, parent: "DashboardWindow"):
                    self.parent = parent

                def on_any_event(self, *_):
                    # Schedule refresh on the main Qt thread
                    QTimer.singleShot(0, self.parent.refresh_all)

            self.observer = Observer()
            self.observer.schedule(_Handler(self), CFG.mailbox_root, recursive=False)
            self.observer.start()
            # task nexus polling still via timer
        except ImportError:
            logging.info("watchdog not installed – falling back to timer.")
            self.observer = None

        self.timer = QTimer(self, interval=CFG.refresh_ms, timeout=self.refresh_all)
        self.timer.start()

    # ───────────────── data refreshers ─────────────────
    def refresh_all(self):
        self._refresh_tasks()
        self._refresh_mailboxes()
        self._refresh_agents()

    def _refresh_tasks(self):
        tasks = get_all_tasks()
        self.task_model.refresh(tasks)

    def _refresh_mailboxes(self):
        boxes: List[Dict] = []
        CFG.mailbox_root.mkdir(parents=True, exist_ok=True)
        for p in CFG.mailbox_root.glob("mailbox_*.json"):
            data = _safe_json(p)
            if not data: continue
            boxes.append({
                "name": p.name,
                "path": p,
                "status": data.get("status", ""),
                "owner": data.get("owner", ""),
                "messages": data.get("messages", []),
                "data": data,
            })
        self.mail_model.refresh(boxes)

    def _refresh_agents(self):
        coords = _load_coords()
        # Build plain rows list
        rows = [[aid, f"({c['x']},{c['y']})"] for aid, c in coords.items()]
        # Use QStandardItemModel for simplicity
        model = QStandardItemModel(len(rows), 2, self)
        model.setHorizontalHeaderLabels(["Agent ID", "Coordinates"])
        for r, (agent_id, coord) in enumerate(rows):
            model.setItem(r, 0, QStandardItem(agent_id))
            model.setItem(r, 1, QStandardItem(coord))
        self.agent_view.setModel(model)

    # ───────────────── actions ─────────────────
    def _inject_task(self):
        text = self.task_input.text().strip()
        if not text:
            return
        tid = add_task(self.task_type_cb.currentText(), text)
        logging.info("Task injected %s", tid)
        self.task_input.clear()
        self._refresh_tasks()

    def _claim_next(self):
        if claim_task(CFG.default_agent):
            if self.auto_click:
                try:
                    click_agent_spot(CFG.default_agent)
                except Exception as e:
                    logging.warning("Spot click failed: %s", e)
        self._refresh_tasks()

    def _load_mailbox_view(self, idx: QModelIndex) -> None:
        box = self.mail_model.entries[self.mail_proxy.mapToSource(idx).row()]
        self._active_mailbox = box
        lines = [f"[{m['timestamp']}] {m['sender']}:\n{m['content']}\n" for m in box.get("messages", [])]
        self.msg_view.setPlainText("\n".join(lines))

    def _send_reply(self) -> None:
        text = self.msg_reply.text().strip()
        if not text or not hasattr(self, "_active_mailbox"): return
        box = self._active_mailbox
        new_msg = {"timestamp": datetime.now().strftime("%H:%M:%S"), "sender": "Dream.OS", "content": text}
        box["messages"].append(new_msg)
        box["data"]["messages"] = box["messages"]
        box["path"].write_text(json.dumps(box["data"], indent=2))
        self.msg_reply.clear(); self._refresh_mailboxes()
        self._load_mailbox_view(self.mail_table.currentIndex())

    def _auto_respond(self) -> None:
        if not hasattr(self, "_active_mailbox") or not self.responder: return
        box = self._active_mailbox
        new_data = self.responder.respond_to_mailbox(box["data"])
        box["data"] = new_data; box["messages"] = new_data.get("messages", [])
        box["path"].write_text(json.dumps(new_data, indent=2))
        self._refresh_mailboxes(); self._load_mailbox_view(self.mail_table.currentIndex())

    def _capture_spot(self):
        QApplication.setOverrideCursor(Qt.CrossCursor)
        QMessageBox.information(self, "Capture", "Position mouse & press OK.")
        x, y = pyautogui.position()
        QApplication.restoreOverrideCursor()
        aid, ok = QInputDialog.getText(self, "Agent ID", "Enter ID:")
        if ok and aid.strip():
            save_agent_spot(aid.strip(), (x, y))
            logging.info("Spot saved %s → (%d,%d)", aid, x, y)
            self._refresh_agents()

    # global hot keys
    def keyPressEvent(self, ev):  # noqa: N802
        if ev.matches(QKeySequence.InsertParagraphSeparator):  # Ctrl + Enter
            pyautogui.hotkey("ctrl", "enter")
        elif ev.matches(QKeySequence.DeleteStartOfWord):  # Ctrl + Backspace
            pyautogui.hotkey("ctrl", "backspace")
        super().keyPressEvent(ev)


# ───────────────────────── bootstrap ────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = DashboardWindow()
    win.show()
    sys.exit(app.exec_())
