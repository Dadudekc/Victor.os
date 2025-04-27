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
from typing import Dict, List, Any

import pyautogui
from PyQt5.QtCore import (
    Qt, QAbstractTableModel, QModelIndex, QVariant, QTimer, QSortFilterProxyModel
)
from PyQt5.QtGui import (
    QColor, QIcon, QKeySequence, QPixmap, QPainter, QCursor
)
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QSplitter, QTabWidget, QComboBox, QTextBrowser,
    QToolBar, QAction, QMessageBox, QInputDialog, QTableView, QToolTip, QCheckBox
)
from PyQt5.QtChart import QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis
from PyQt5.QtChart import QStackedBarSeries

# ───────────────────────── Backend shims ──────────────────────────
try:
    from dream_os.services.task_nexus import add_task, claim_task, get_all_tasks
except Exception:
    add_task = lambda task_type, content: uuid.uuid4().hex
    claim_task = lambda agent_id: False
    get_all_tasks = lambda: []

try:
    from dreamos.hooks.chatgpt_responder import ChatGPTResponder
except Exception:
    ChatGPTResponder = None

try:
    from dreamos.agent_utils import save_agent_spot, click_agent_spot, _load_coords
except Exception as e:
    print("agent_utils missing:", e)
    sys.exit(1)

try:
    import markdown  # optional, for nicer bubbles
except ImportError:
    markdown = None

try:
    from dreamos.monitoring.cycle_health_monitor import CycleHealthMonitor
except Exception:
    CycleHealthMonitor = None

# EDIT START: import AgentBus and DashboardEventListener for prompt event wiring
from dreamos.agent_bus import AgentBus
from dreamos.dashboard.event_listener import DashboardEventListener
# EDIT END

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


class EscalatedAgentsTable(QAbstractTableModel):  # EDIT START: model for escalated agents
    HEAD = ["Agent", "Escalations", "Last Escalation"]
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
                return row["agent_id"]
            if col == 1:
                return str(row["count"])
            if col == 2:
                return row["last"].strftime("%Y-%m-%d %H:%M:%S") if isinstance(row["last"], datetime) else str(row["last"])
        return QVariant()
    def refresh(self, rows: List[Dict]) -> None:
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()  # EDIT END


# ──────────────────────── Main Dashboard ────────────────────────
class Dashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dream.OS Dashboard")
        self.resize(1350, 840)
        self.responder = ChatGPTResponder(dev_mode=True) if ChatGPTResponder else None
        self.dev_mode = True

        # Initialize cycle health monitor for scraping stats
        self.cycle_monitor = CycleHealthMonitor()
        # Per-agent scrape metrics
        self.agent_scrape_stats: Dict[str, Dict[str, int]] = {}
        self.agent_escalations: Dict[str, Dict[str, Any]] = {}  # EDIT START: track per-agent escalations

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
        # Initialize Health tab for scrape metrics
        self._init_health_tab()
        self._init_escalated_agents_tab()  # EDIT: add escalated agents tab

        # models
        self.task_model = TaskTable()
        tproxy = QSortFilterProxyModel()
        tproxy.setSourceModel(self.task_model)
        self.task_view.setModel(tproxy)

        self.box_model = MailboxTable()
        bproxy = QSortFilterProxyModel()
        bproxy.setSourceModel(self.box_model)
        self.box_tbl.setModel(bproxy)

        # EDIT START: initialize AgentBus and wire prompt success/failure events
        self.agent_bus = AgentBus()
        self.prompt_failure_count = 0
        self.prompt_success_count = 0
        self.escalation_count = 0  # track number of escalations

        # Subscribe to SYSTEM events
        # Store metadata for agents and define metadata handler
        self.agent_metadata = {}
        def _on_metadata(evt):
            data = getattr(evt, 'data', {})
            aid = data.get('agent_id')
            if aid:
                self.agent_metadata[aid] = {
                    'priority': data.get('priority'),
                    'description': data.get('description')
                }
                self.refresh()

        def _on_failure(event):
            # Prompt failure
            self.prompt_failure_count += 1
            QTimer.singleShot(0, lambda: self._flash_color(QColor(255, 0, 0)))
            # Scrape failure event
            if event.data.get("type") == "CHATGPT_SCRAPE_FAILED":
                agent_id = event.data.get("agent_id")
                if agent_id:
                    stats = self.agent_scrape_stats.setdefault(agent_id, {"success": 0, "failure": 0})
                    stats["failure"] += 1
                    self.refresh()

        def _on_success(event):
            # Prompt success
            self.prompt_success_count += 1
            QTimer.singleShot(0, lambda: self._flash_color(QColor(0, 255, 0)))
            # Scrape success event
            if event.data.get("type") == "CHATGPT_SCRAPE_SUCCESS":
                agent_id = event.data.get("agent_id")
                if agent_id:
                    stats = self.agent_scrape_stats.setdefault(agent_id, {"success": 0, "failure": 0})
                    stats["success"] += 1
                    self.refresh()

        DashboardEventListener(
            bus=self.agent_bus,
            on_fail=_on_failure,
            on_success=_on_success,
            on_metadata=_on_metadata,
        )
        # EDIT END

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
        # Agent table with per-agent scrape metrics
        self.agent_tbl = QTableView()
        lay.addWidget(self.agent_tbl)
        cap = QPushButton("Capture Spot", clicked=self._capture_spot)
        lay.addWidget(cap)
        self.tabs.addTab(w, "Agents")

    def _init_health_tab(self):
        """
        Initializes the Health tab to display per-agent scrape success/failure counts.
        """
        w = QWidget()
        lay = QVBoxLayout(w)
        # Stacked/grouped view toggle
        self._stacked_mode = False
        self.stacked_checkbox = QCheckBox("Stacked View")
        self.stacked_checkbox.stateChanged.connect(self._handle_stacked_toggle)
        lay.addWidget(self.stacked_checkbox)
        # Set up chart for health metrics
        self.health_chart = QChart()
        self.health_chart.setTitle("Scrape Health Metrics")
        # Series placeholder
        self.health_series = QBarSeries()
        self.health_chart.addSeries(self.health_series)
        # Axes
        self.category_axis = QBarCategoryAxis()
        self.value_axis = QValueAxis()
        self.health_chart.addAxis(self.category_axis, Qt.AlignBottom)
        self.health_chart.addAxis(self.value_axis, Qt.AlignLeft)
        self.health_series.attachAxis(self.category_axis)
        self.health_series.attachAxis(self.value_axis)
        # Chart view
        self.health_chart_view = QChartView(self.health_chart)
        self.health_chart_view.setRenderHint(QPainter.Antialiasing)
        lay.addWidget(self.health_chart_view)
        # Show legend at bottom
        legend = self.health_chart.legend()
        legend.setVisible(True)
        legend.setAlignment(Qt.AlignBottom)
        self.tabs.addTab(w, "Health")

    def _init_escalated_agents_tab(self):  # EDIT START: initialize Escalated Agents tab
        """Initializes the Escalated Agents tab for displaying current escalations."""
        w = QWidget()
        lay = QVBoxLayout(w)
        self.escalated_tbl = QTableView()
        self.escalated_tbl.setSortingEnabled(True)
        self.escalated_model = EscalatedAgentsTable()
        proxy = QSortFilterProxyModel()
        proxy.setSourceModel(self.escalated_model)
        self.escalated_tbl.setModel(proxy)
        lay.addWidget(self.escalated_tbl)
        self.tabs.addTab(w, "Escalated Agents")
        self.escalated_tab_index = self.tabs.indexOf(w)
        self.tabs.tabBar().setTabVisible(self.escalated_tab_index, False)
    # EDIT END

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
        # Sort agents by priority descending (default priority 0 if missing)
        sorted_agents = sorted(
            coords.keys(),
            key=lambda aid: self.agent_metadata.get(aid, {}).get('priority', 0),
            reverse=True
        )
        # Build agent metrics table with scrape stats and coordinates
        agents = [(aid, f"({coords[aid]['x']},{coords[aid]['y']})") for aid in sorted_agents]
        from PyQt5.QtGui import QStandardItemModel, QStandardItem
        # Now include Priority and Description columns
        col_count = 5
        mdl = QStandardItemModel(len(agents), col_count, self)
        mdl.setHorizontalHeaderLabels(["Agent", "XY", "Scrapes ✅/❌", "Priority", "Description"])
        for r, (aid, xy) in enumerate(agents):
            # Ensure stats entry exists
            stats = self.agent_scrape_stats.get(aid, {"success": 0, "failure": 0})
            suc = stats.get("success", 0)
            fail = stats.get("failure", 0)
            scrape_str = f"✅{suc}/❌{fail}"
            # Populate row
            mdl.setItem(r, 0, QStandardItem(aid))
            mdl.setItem(r, 1, QStandardItem(xy))
            item = QStandardItem(scrape_str)
            # Highlight if failures exceed threshold
            if fail > 5:
                item.setBackground(_qcolor(255, 255, 180))
            mdl.setItem(r, 2, item)
            # Priority column
            prio = self.agent_metadata.get(aid, {}).get('priority')
            mdl.setItem(r, 3, QStandardItem(str(prio) if prio is not None else ""))
            # Description column
            desc = self.agent_metadata.get(aid, {}).get('description', "")
            mdl.setItem(r, 4, QStandardItem(desc))
        self.agent_tbl.setModel(mdl)
        # Update health chart: sort agents by total (success+failure) descending
        health_items = sorted(
            self.agent_scrape_stats.items(),
            key=lambda item: item[1].get('success', 0) + item[1].get('failure', 0),
            reverse=True
        )
        # Store sorted agent list for tooltip mapping
        self.health_agents = [aid for aid, _ in health_items]
        # Prepare bar sets
        success_set = QBarSet("Success")
        failure_set = QBarSet("Failure")
        for aid, stats in health_items:
            success_set.append(stats.get('success', 0))
            failure_set.append(stats.get('failure', 0))
        for aid in agents:
            stats = self.agent_scrape_stats.get(aid, {"success": 0, "failure": 0})
            success_set.append(stats.get("success", 0))
            failure_set.append(stats.get("failure", 0))
        # Connect hover tooltips for bar sets
        success_set.hovered.connect(lambda index, status, bs=success_set: self._show_bar_tooltip(bs, index, status))
        failure_set.hovered.connect(lambda index, status, bs=failure_set: self._show_bar_tooltip(bs, index, status))
        # Refresh series
        self.health_chart.removeAllSeries()
        series = QBarSeries()
        # Apply stacked vs grouped mode
        series.setStacked(getattr(self, '_stacked_mode', False))
        series.append(success_set)
        series.append(failure_set)
        self.health_chart.addSeries(series)
        # Update categories
        self.category_axis.clear()
        self.category_axis.append(agents)
        series.attachAxis(self.category_axis)
        # Update value axis range
        all_counts = [stats.get("success", 0) for stats in self.agent_scrape_stats.values()] + \
                     [stats.get("failure", 0) for stats in self.agent_scrape_stats.values()]
        max_count = max(all_counts + [1])
        self.value_axis.setRange(0, max_count)
        series.attachAxis(self.value_axis)
        # Persist per-agent stats
        try:
            state = {
                "scrape_success_global": self.cycle_monitor.successful_cycles,
                "scrape_failure_global": self.cycle_monitor.failed_cycles,
                "agent_scrape_stats": self.agent_scrape_stats
            }
            (Path(CFG.logs_dir) / "dashboard_state.json").write_text(
                json.dumps(state, indent=2), encoding='utf-8'
            )
        except Exception as e:
            logging.error(f"Failed to persist dashboard state: {e}")
        # EDIT START: update escalated agents view
        es_rows = []
        for aid, st in self.agent_escalations.items():
            if st.get('count', 0) > 0:
                es_rows.append({'agent_id': aid, 'count': st['count'], 'last': st['last']})
        self.escalated_model.refresh(es_rows)
        self.tabs.tabBar().setTabVisible(self.escalated_tab_index, bool(es_rows))
        # EDIT END

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
        # let user select existing agent or create new
        coords = _load_coords()
        items = list(coords.keys()) + ["< New Agent >"]
        choice, ok = QInputDialog.getItem(self, "Agent ID", "Select agent or new:", items, editable=False)
        if not ok:
            return
        if choice == "< New Agent >":
            aid, ok2 = QInputDialog.getText(self, "Agent ID", "Enter new Agent ID:")
            if not ok2 or not aid.strip():
                return
            agent_id = aid.strip()
        else:
            agent_id = choice
        save_agent_spot(agent_id, (x, y))
        logging.info("Spot saved %s → (%d,%d)", agent_id, x, y)
        # set this agent as the default for future actions
        CFG.default_agent = agent_id
        QMessageBox.information(self, "Default Agent", f"Default agent set to {agent_id}")
        # refresh views
        self.refresh()

    # ───────── dev / prod toggle ─────────
    def _flip_mode(self, checked: bool) -> None:
        self.dev_mode = checked
        if self.responder:
            self.responder.dev_mode = checked

    # ───────── hotkey passthrough ─────────
    def keyPressEvent(self, e) -> None:
        if e.matches(QKeySequence.InsertParagraphSeparator):
            pyautogui.hotkey("ctrl", "enter")
        elif e.matches(QKeySequence.DeleteStartOfWord):
            pyautogui.hotkey("ctrl", "backspace")
        elif e.key() == Qt.Key_F5:
            self.refresh()
        super().keyPressEvent(e)

    # EDIT START: upgraded prompt event handlers are now managed by DashboardEventListener
    # (Old handle_system_event definitions removed in favor of modular listener)
    def handle_system_event(self, event_name: str, event_payload: dict) -> bool:
        # stub: use modular listener callbacks instead
        return False

    def _flash_color(self, color: QColor) -> None:
        """Flash the dashboard background with the given color briefly."""
        original = self.styleSheet()
        self.setStyleSheet(f"background-color: rgba({color.red()},{color.green()},{color.blue()},100);")
        QTimer.singleShot(300, lambda: self.setStyleSheet(original))

    def _show_bar_tooltip(self, bar_set, index, status):
        """Show tooltip with agent name and count for hovered bar, color-coded and suppress zeros."""
        if not status:
            return
        # Determine agent order from Health tab
        agents = getattr(self, 'health_agents', list(self.agent_scrape_stats.keys()))
        if index < 0 or index >= len(agents):
            return
        aid = agents[index]
        count = bar_set.at(index)
        # Suppress tooltip for zero-count bars
        if count <= 0:
            return
        name = bar_set.label()
        # Choose text color based on bar label
        color = '#00AA00' if name.lower() == 'success' else '#AA0000'
        text = f"{aid}: {name} {count}"
        # Use HTML to color the tooltip text
        QToolTip.showText(QCursor.pos(), f"<font color='{color}'>{text}</font>")

    def _handle_stacked_toggle(self, state):
        """Toggle between stacked and grouped bar view and refresh chart."""
        self._stacked_mode = (state == Qt.Checked)
        self.refresh()

# ───────────────────────── bootstrap ───────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Dashboard()
    win.show()
    sys.exit(app.exec_())
