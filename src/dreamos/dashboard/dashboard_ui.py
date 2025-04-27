import logging
import json
from datetime import datetime
import pyautogui
from typing import Dict, Any, List, Tuple

from PyQt5.QtCore import Qt, QTimer, QModelIndex
from PyQt5.QtGui import (
    QColor, QIcon, QKeySequence, QPixmap, QPainter, QCursor, QPen,
    QStandardItemModel, QStandardItem
)
from PyQt5.QtChart import (
    QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis, QLineSeries,
    QStackedBarSeries
)
from PyQt5.QtWidgets import (
    QMainWindow, QApplication, QMessageBox, QInputDialog
)

import dreamos.config as CFG
from dreamos.utils.ui_helpers import _qcolor, _md, _avatar
from dreamos.core.task_management import add_task, claim_task
from dreamos.core.agent_coords import _load_coords, save_agent_spot, click_agent_spot

class Dashboard(QMainWindow):
    # EDIT START: Phase 4 threshold constants
    SUCCESS_THRESHOLD = 0.8  # threshold for chart overlay
    FAILURE_THRESHOLD = 0.2  # threshold for chart overlay
    # EDIT END: Phase 4 threshold constants 

    def __init__(self):
        super().__init__()
        self.agent_escalations: Dict[str, Dict[str, Any]] = {}  # EDIT START: track per-agent escalations
        # EDIT START: initialize breach flags for agents threshold tracking
        self.agent_breach_flags: Dict[str, bool] = {}
        # EDIT END: initialize breach flags

        # --- Placeholder: Initialize UI elements and potentially axes here ---
        # Example: self._setup_charts()
        self.health_chart = QChart() # Placeholder initialization
        self.category_axis = QBarCategoryAxis() # Placeholder initialization
        self.value_axis = QValueAxis() # Placeholder initialization
        self.health_chart.addAxis(self.category_axis, Qt.AlignBottom) # Placeholder setup
        self.health_chart.addAxis(self.value_axis, Qt.AlignLeft) # Placeholder setup
        # --- End Placeholder ---

    def refresh(self):
        # --- EDIT START: Retrieve or Calculate required data ---
        # Ensure chart and axes are valid (assuming setup in __init__ or elsewhere)
        if not hasattr(self, 'health_chart') or not self.health_chart:
             logging.error("Health chart not initialized before refresh.")
             return
        # Retrieve axes from chart if not guaranteed by init (safer)
        # Assuming the axes were added with specific types during setup
        self.category_axis = next((ax for ax in self.health_chart.axes(Qt.Horizontal) if isinstance(ax, QBarCategoryAxis)), None)
        self.value_axis = next((ax for ax in self.health_chart.axes(Qt.Vertical) if isinstance(ax, QValueAxis)), None)

        if not self.category_axis or not self.value_axis:
            logging.error("Chart axes not found or not of expected type during refresh.")
            return

        # Placeholder: Fetch latest data needed for the refresh
        # Replace these with actual data retrieval logic (e.g., from a data store/manager)
        self.agent_scrape_stats: Dict[str, Dict[str, int]] = getattr(self, '_data_source', {}).get('agent_stats', {}) # Example fetch
        self.agent_metadata: Dict[str, Dict[str, Any]] = getattr(self, '_data_source', {}).get('agent_metadata', {}) # Example fetch
        agents_list: List[Tuple[str, str]] = getattr(self, '_data_source', {}).get('agents_list', []) # Example fetch (e.g., [('agent1', 'xy1'), ('agent2', 'xy2')])
        self.health_agents: List[str] = [aid for aid, xy in agents_list] # Example derived list

        # Calculate success/failure sets based on fetched stats
        success_values = [self.agent_scrape_stats.get(aid, {}).get('success', 0) for aid in self.health_agents]
        failure_values = [self.agent_scrape_stats.get(aid, {}).get('failure', 0) for aid in self.health_agents]
        success_set = QBarSet("Success")
        success_set.append(success_values)
        failure_set = QBarSet("Failure")
        failure_set.append(failure_values)
        # --- EDIT END: Retrieve or Calculate required data ---

        # Refresh series
        self.health_chart.removeAllSeries()
        series = QBarSeries()
        # Apply stacked vs grouped mode
        series.setStacked(getattr(self, '_stacked_mode', False))
        series.append(success_set)
        series.append(failure_set)
        self.health_chart.addSeries(series)
        # EDIT START: Phase 4 threshold lines
        # Draw horizontal threshold lines across categories
        cat_count = len(self.health_agents)
        # Success threshold
        st_line = QLineSeries()
        st_line.setName("Success Threshold")
        for x in range(cat_count):
            st_line.append(x, self.SUCCESS_THRESHOLD)
        pen_s = QPen(QColor(0, 200, 0))
        pen_s.setStyle(Qt.DashLine)
        pen_s.setWidth(2)
        st_line.setPen(pen_s)
        self.health_chart.addSeries(st_line)
        st_line.attachAxis(self.category_axis)
        st_line.attachAxis(self.value_axis)
        # Failure threshold
        ft_line = QLineSeries()
        ft_line.setName("Failure Threshold")
        for x in range(cat_count):
            ft_line.append(x, self.FAILURE_THRESHOLD)
        pen_f = QPen(QColor(200, 0, 0))
        pen_f.setStyle(Qt.DashLine)
        pen_f.setWidth(2)
        ft_line.setPen(pen_f)
        self.health_chart.addSeries(ft_line)
        ft_line.attachAxis(self.category_axis)
        ft_line.attachAxis(self.value_axis)
        # EDIT END: Phase 4 threshold lines
        # EDIT START: Phase 4.1 threshold breach tracking and warnings
        breach_found = False
        for aid, stats in self.agent_scrape_stats.items():
            suc = stats.get('success', 0)
            fail = stats.get('failure', 0)
            # Determine breach state per agent
            breach = (suc < self.SUCCESS_THRESHOLD) or (fail > self.FAILURE_THRESHOLD)
            # Persist flag for badge column
            self.agent_breach_flags[aid] = breach
            # On first detected breach, flash dashboard
            if breach and not breach_found:
                QTimer.singleShot(0, lambda: self._flash_color(QColor(255, 255, 0)))
                breach_found = True
        # EDIT END: Phase 4.1 threshold breach tracking and warnings
        # Update categories
        self.category_axis.clear()
        self.category_axis.append(self.health_agents)

        # Now include Priority, Description, and Breach Badge columns
        col_count = 6
        mdl = QStandardItemModel(len(agents_list), col_count, self)
        mdl.setHorizontalHeaderLabels(["Agent", "XY", "Scrapes ✅/❌", "Priority", "Description", "⚠️"])
        for r, (aid, xy) in enumerate(agents_list):
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
            # Breach badge column
            breach_flag = self.agent_breach_flags.get(aid, False)
            badge_item = QStandardItem("⚠️" if breach_flag else "")
            mdl.setItem(r, 5, badge_item)
        self.agent_tbl.setModel(mdl)
        # EDIT START: Phase 4.2 persistent breach badges
        # Hide badge column if no agents currently in breach
        has_breach = any(self.agent_breach_flags.get(aid, False) for aid in self.health_agents)
        self.agent_tbl.setColumnHidden(5, not has_breach)
        # EDIT END: Phase 4.2 persistent breach badges 

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
