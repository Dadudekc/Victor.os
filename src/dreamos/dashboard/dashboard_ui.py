from PyQt5.QtGui import (
    QColor, QIcon, QKeySequence, QPixmap, QPainter, QCursor, QPen
)
from PyQt5.QtChart import QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis, QLineSeries
from PyQt5.QtChart import QStackedBarSeries
from PyQt5.QtCore import QTimer
from typing import Dict, Any

class Dashboard(QMainWindow):
    # EDIT START: Phase 4 threshold constants
    SUCCESS_THRESHOLD = 50
    FAILURE_THRESHOLD = 10
    # EDIT END: Phase 4 threshold constants 

    def __init__(self):
        super().__init__()
        self.agent_escalations: Dict[str, Dict[str, Any]] = {}  # EDIT START: track per-agent escalations
        # EDIT START: initialize breach flags for agents threshold tracking
        self.agent_breach_flags: Dict[str, bool] = {}
        # EDIT END: initialize breach flags

    def refresh(self):
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

        from PyQt5.QtGui import QStandardItemModel, QStandardItem
        # Now include Priority, Description, and Breach Badge columns
        col_count = 6
        mdl = QStandardItemModel(len(agents), col_count, self)
        mdl.setHorizontalHeaderLabels(["Agent", "XY", "Scrapes ✅/❌", "Priority", "Description", "⚠️"])
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
            # Breach badge column
            breach_flag = self.agent_breach_flags.get(aid, False)
            badge_item = QStandardItem("⚠️" if breach_flag else "")
            mdl.setItem(r, 5, badge_item)
        self.agent_tbl.setModel(mdl)
        # EDIT START: Phase 4.2 persistent breach badges
        # Hide badge column if no agents currently in breach
        has_breach = any(self.agent_breach_flags.get(aid, False) for aid in self.agent_scrape_stats.keys())
        self.agent_tbl.setColumnHidden(5, not has_breach)
        # EDIT END: Phase 4.2 persistent breach badges 