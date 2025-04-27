from PyQt5.QtGui import (
    QColor, QIcon, QKeySequence, QPixmap, QPainter, QCursor, QPen
)
from PyQt5.QtChart import QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis, QLineSeries
from PyQt5.QtChart import QStackedBarSeries

class Dashboard(QMainWindow):
    # EDIT START: Phase 4 threshold constants
    SUCCESS_THRESHOLD = 50
    FAILURE_THRESHOLD = 10
    # EDIT END: Phase 4 threshold constants 

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
        # Update categories
        self.category_axis.clear() 