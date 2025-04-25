# dashboard.py  – Dream.OS UI  v5 (Mailbox upgrade)
# -------------------------------------------------
# Highlights:
#     • Avatars + markdown bubbles
#     • Mailbox create / assign
#     • Live JSON-file refresh (watchdog) – no simulated messages
from __future__ import annotations

import json, logging, sys, uuid, time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pyautogui
from PyQt5.QtCore import (
    Qt, QAbstractTableModel, QModelIndex, QVariant, QTimer, QSortFilterProxyModel
)
from PyQt5.QtGui import (
    QColor, QIcon, QKeySequence, QPixmap
)
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QSplitter, QTabWidget, QComboBox, QTextBrowser,
    QToolBar, QAction, QMessageBox, QInputDialog, QTableView
)

# ───────────────────────── Backend shims ──────────────────────────
try:
    from dream_os.services.task_nexus import add_task, claim_task, get_all_tasks
except Exception:
    add_task = lambda task_type, content: uuid.uuid4().hex
    claim_task = lambda agent_id: False
    get_all_tasks = lambda: []

try:
    from core.hooks.chatgpt_responder import ChatGPTResponder
except Exception:
    ChatGPTResponder = None

try:
    from core.agent_utils import save_agent_spot, click_agent_spot, _load_coords
except Exception as e:
    print("agent_utils missing:", e)
    sys.exit(1)

try:
    import markdown  # optional, for nicer bubbles
except ImportError:
    markdown = None

# ───────────────────────── Config & logging ──────────────────────
@dataclass
class Config:
    refresh_ms: int = 4000
    mailbox_root: Path = Path(__file__).parent / "_agent_coordination" / "shared_mailboxes"
    avatar_dir: Path = Path(__file__).parent / "assets" / "avatars"
    logs_dir: Path = Path("logs")
    ui_log: str = "ui.log"
    default_agent: str = "agent_001"
    bubble_css: str = (
        "body{font-family:'Segoe UI';font-size:10pt}"  
        ".bubble{padding:6px;border-radius:8px;margin:4px 0;max-width:95%;}"  
        ".left{background:#f1f1f1;text-align:left}"  
        ".right{background:#d2eaff;text-align:right;margin-left:auto}"  
        ".meta{font-size:8pt;color:#666}"  
    )

CFG = Config()
CFG.logs_dir.mkdir(exist_ok=True)
logging.basicConfig(
    filename=CFG.logs_dir / CFG.ui_log,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

# ───────────────────────── helpers ───────────────────────────────
def _safe_json(path: Path) -> Dict | None:
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _qcolor(r: int, g: int, b: int) -> QColor:
    return QColor(r, g, b)


def _avatar(agent_id: str) -> QPixmap | None:
    p = CFG.avatar_dir / f"{agent_id}.png"
    if p.exists():
        return QPixmap(str(p)).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return None


def _md(text: str) -> str:
    if markdown:
        return markdown.markdown(text, extensions=["fenced_code"])
    return text.replace("\n", "<br>")

# ───────────────────────── Table models ──────────────────────────
class MailboxTable(QAbstractTableModel):
    HEAD = ["Mailbox", "Status", "Owner", "#Msgs"]

    def __init__(self):
        super().__init__()
        self.rows: List[Dict] = []

    def rowCount(self, *_) -> int:
        return len(self.rows)

    def columnCount(self, *_) -> int:
        return len(self.HEAD)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.HEAD[section]
        return QVariant()

    def data(self, idx: QModelIndex, role=Qt.DisplayRole):
        if not idx.isValid():
            return QVariant()
        row = self.rows[idx.row()]
        col = idx.column()
        if role == Qt.DisplayRole:
            if col == 0:
                return row["name"]
            if col == 1:
                return row["status"]
            if col == 2:
                return row["owner"]
            if col == 3:
                return str(len(row["messages"]))
        if role == Qt.BackgroundRole and col == 1:
            st = row["status"]
            if st == "CLAIMED":
                return _qcolor(255, 255, 180)
            if st == "online":
                return _qcolor(200, 255, 200)
            if st == "idle":
                return _qcolor(230, 230, 230)
        return QVariant()

    def refresh(self, rows: List[Dict]) -> None:
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()


class TaskTable(QAbstractTableModel):
    HEAD = ["ID", "Type", "Status", "Content"]

    def __init__(self):
        super().__init__()
        self.rows: List[Dict] = []

    def rowCount(self, *_) -> int:
        return len(self.rows)

    def columnCount(self, *_) -> int:
        return len(self.HEAD)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.HEAD[section]
        return QVariant()

    def data(self, idx: QModelIndex, role=Qt.DisplayRole):
        if not idx.isValid():
            return QVariant()
        r = self.rows[idx.row()]
        c = idx.column()
        if role == Qt.DisplayRole:
            return [r["id"][:8], r["type"], r["status"], r["content"]][c]
        if role == Qt.BackgroundRole and c == 2:
            return (
                _qcolor(255, 128, 128)
                if r["status"] == "failed"
                else _qcolor(180, 255, 180)
                if r["status"] == "completed"
                else None
            )
        return QVariant()

    def refresh(self, rows: List[Dict]) -> None:
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()


# ──────────────────────── Main Dashboard ────────────────────────
class Dashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dream.OS Dashboard")
        self.resize(1350, 840)
        self.responder = ChatGPTResponder(dev_mode=True) if ChatGPTResponder else None
        self.dev_mode = True

        # toolbar
        tb = QToolBar("Main")
        self.addToolBar(tb)
        self.auto_click = True
        act_click = QAction("Auto-Click", self, checkable=True, checked=True)
        act_click.triggered.connect(lambda v: setattr(self, "auto_click", v))
        tb.addAction(act_click)
        act_mode = QAction("Dev Mode", self, checkable=True, checked=True)
        act_mode.triggered.connect(self._flip_mode)
        tb.addAction(act_mode)
        new_box = QAction("➕ New Mailbox", self, triggered=self._create_mailbox)
        tb.addAction(new_box)

        # tabs
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self._init_tasks_tab()
        self._init_mailbox_tab()
        self._init_agents_tab()

        # models
        self.task_model = TaskTable()
        tproxy = QSortFilterProxyModel()
        tproxy.setSourceModel(self.task_model)
        self.task_view.setModel(tproxy)

        self.box_model = MailboxTable()
        bproxy = QSortFilterProxyModel()
        bproxy.setSourceModel(self.box_model)
        self.box_tbl.setModel(bproxy)

        # timers / watchdog
        self._init_refresh()

    # ───────── tabs ─────────
    def _init_tasks_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        self.task_view = QTableView()
        self.task_view.setSortingEnabled(True)
        lay.addWidget(QLabel("Tasks"))
        lay.addWidget(self.task_view)
        inject_row = QSplitter(Qt.Horizontal)
        self.task_type = QComboBox()
        self.task_type.addItems(["plan", "code", "social"])
        self.task_in = QLineEdit(placeholderText="Task description…")
        btn = QPushButton("Inject", clicked=self._inject_task)
        inject_row.addWidget(self.task_type)
        inject_row.addWidget(self.task_in)
        inject_row.addWidget(btn)
        lay.addWidget(inject_row)
        claim = QPushButton("Claim Next", clicked=self._claim_next)
        lay.addWidget(claim)
        self.tabs.addTab(w, "Tasks")

    def _init_mailbox_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        self.box_tbl = QTableView()
        self.box_tbl.setSortingEnabled(True)
        self.box_tbl.clicked.connect(self._load_box)
        self.msg_view = QTextBrowser()
        self.msg_view.document().setDefaultStyleSheet(CFG.bubble_css)
        reply_row = QSplitter(Qt.Horizontal)
        self.reply_in = QLineEdit(placeholderText="Reply…")
        send = QPushButton("Send ➤", clicked=self._send_reply)
        ai_btn = QPushButton("💡 Ask ChatGPT", clicked=self._ai_reply)
        reply_row.addWidget(self.reply_in)
        reply_row.addWidget(send)
        reply_row.addWidget(ai_btn)
        lay.addWidget(QLabel("Mailboxes"))
        lay.addWidget(self.box_tbl)
        lay.addWidget(QLabel("Conversation"))
        lay.addWidget(self.msg_view)
        lay.addWidget(reply_row)
        self.tabs.addTab(w, "Mailboxes")

    def _init_agents_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        self.agent_tbl = QTableView()
        lay.addWidget(self.agent_tbl)
        cap = QPushButton("Capture Spot", clicked=self._capture_spot)
        lay.addWidget(cap)
        self.tabs.addTab(w, "Agents")

    # ───────── refresh ─────────
    def _init_refresh(self):
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            class H(FileSystemEventHandler):
                def __init__(self, parent):
                    self.p = parent
                def on_any_event(self, *_):
                    QTimer.singleShot(0, self.p.refresh)

            self.observer = Observer()
            self.observer.schedule(H(self), CFG.mailbox_root, recursive=False)
            self.observer.start()
        except Exception:
            self.observer = None
        self.timer = QTimer(interval=CFG.refresh_ms, timeout=self.refresh)
        self.timer.start()
        self.refresh()

    def refresh(self) -> None:
        # tasks
        self.task_model.refresh(get_all_tasks())
        # boxes
        rows: List[Dict] = []
        CFG.mailbox_root.mkdir(parents=True, exist_ok=True)
        for p in CFG.mailbox_root.glob("mailbox_*.json"):
            data = _safe_json(p)
            if not data:
                continue
            # no simulation: let live agents respond
            rows.append({
                "name": p.name,
                "path": p,
                "status": data.get("status", ""),
                "owner": data.get("owner", ""),
                "messages": data.get("messages", []),
                "data": data,
            })
        self.box_model.refresh(rows)
        # agents
        coords = _load_coords()
        agents = [[aid, f"({c['x']},{c['y']})"] for aid, c in coords.items()]
        from PyQt5.QtGui import QStandardItemModel, QStandardItem
        mdl = QStandardItemModel(len(agents), 2, self)
        mdl.setHorizontalHeaderLabels(["Agent", "XY"])
        for r, (aid, xy) in enumerate(agents):
            mdl.setItem(r, 0, QStandardItem(aid))
            mdl.setItem(r, 1, QStandardItem(xy))
        self.agent_tbl.setModel(mdl)

    # ───────── mailbox helpers ─────────
    def _load_box(self, idx: QModelIndex) -> None:
        self.cur_box = self.box_model.rows[self.box_tbl.model().mapToSource(idx).row()]
        self._render_messages()

    def _render_messages(self) -> None:
        if not hasattr(self, "cur_box"):
            return
        html: List[str] = []
        for m in self.cur_box["messages"]:
            sender = m.get("sender", "?")
            ts = m.get("timestamp", "")
            content = _md(m.get("content", ""))
            # determine bubble side
            side = "left" if sender != CFG.default_agent and sender != "Dream.OS" else "right"
            # avatar or emoji fallback
            av = _avatar(sender)
            if av:
                avatar_html = f'<img src="{CFG.avatar_dir / f"{sender}.png"}" width="24"/>'
            else:
                avatar_html = "🐺" if side == "right" else "👤"
            html.append(
                f'<div class="bubble {side}">{avatar_html} ' +
                f'<span class="meta">{sender} {ts}</span><br>{content}</div>'
            )
        self.msg_view.setHtml("<br>".join(html))

    def _send_reply(self) -> None:
        if not hasattr(self, "cur_box") or not self.reply_in.text().strip():
            return
        msg = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "sender": "Dream.OS",
            "content": self.reply_in.text().strip(),
        }
        self.cur_box["messages"].append(msg)
        self.cur_box["data"]["messages"] = self.cur_box["messages"]
        self.cur_box["path"].write_text(json.dumps(self.cur_box["data"], indent=2))
        self.reply_in.clear()
        self.refresh()
        self._render_messages()

    def _ai_reply(self) -> None:
        if not hasattr(self, "cur_box") or not self.responder:
            return
        data = self.responder.respond_to_mailbox(self.cur_box["data"])
        self.cur_box["data"] = data
        self.cur_box["messages"] = data.get("messages", [])
        self.cur_box["path"].write_text(json.dumps(data, indent=2))
        self.refresh()
        self._render_messages()

    def _create_mailbox(self) -> None:
        name, ok = QInputDialog.getText(self, "New Mailbox", "Mailbox name?")
        if not ok or not name.strip():
            return
        owner, ok2 = QInputDialog.getText(self, "Owner", "Assign to agent (ID)?")
        mbx = {"status": "idle", "owner": owner.strip(), "messages": []}
        fpath = CFG.mailbox_root / f"mailbox_{name.strip()}.json"
        fpath.write_text(json.dumps(mbx, indent=2))
        self.refresh()

    # ───────── tasks / agents helpers ─────────
    def _inject_task(self) -> None:
        txt = self.task_in.text().strip()
        self.task_in.clear()
        if not txt:
            return
        add_task(self.task_type.currentText(), txt)
        self.refresh()

    def _claim_next(self) -> None:
        if claim_task(CFG.default_agent) and self.auto_click:
            try:
                click_agent_spot(CFG.default_agent)
            except Exception as e:
                logging.warning("click failure %s", e)
        self.refresh()

    def _capture_spot(self) -> None:
        QApplication.setOverrideCursor(Qt.CrossCursor)
        QMessageBox.information(self, "Capture", "Place cursor, press OK")
        x, y = pyautogui.position()
        QApplication.restoreOverrideCursor()
        aid, ok = QInputDialog.getText(self, "Agent ID", "Enter ID:")
        if ok and aid.strip():
            save_agent_spot(aid.strip(), (x, y))
            self.refresh()

    # ───────── dev / prod toggle ─────────
    def _flip_mode(self, checked: bool) -> None:
        self.dev_mode = checked
        if self.responder:
            self.responder.dev_mode = checked

    # hotkey passthrough
    def keyPressEvent(self, e) -> None:
        if e.matches(QKeySequence.InsertParagraphSeparator):
            pyautogui.hotkey("ctrl", "enter")
        elif e.matches(QKeySequence.DeleteStartOfWord):
            pyautogui.hotkey("ctrl", "backspace")
        super().keyPressEvent(e)

# ───────────────────────── bootstrap ───────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Dashboard()
    win.show()
    sys.exit(app.exec_())
