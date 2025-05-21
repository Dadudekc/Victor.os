"""
TBOW Tactics Charting Module

This module provides charting functionality for the TBOW Tactics system:
1. Sparkline charts for quick market context
2. Analytics charts for performance tracking
3. Custom chart widgets for PyQt5 integration
"""

import logging
from typing import Dict, Any, List, Optional
import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QPainter, QPen, QColor, QPainterPath

class SparklineChart(QWidget):
    """
    Custom sparkline chart widget for PyQt5.
    
    Features:
    - Compact price visualization
    - Color-coded trend
    - Optional volume overlay
    - Customizable time range
    """
    
    def __init__(
        self,
        parent=None,
        width: int = 200,
        height: int = 50,
        show_volume: bool = False
    ):
        """Initialize sparkline chart."""
        super().__init__(parent)
        self.setFixedSize(width, height)
        self.show_volume = show_volume
        
        # Data
        self.prices = []
        self.volumes = []
        self.timestamps = []
        
        # Style
        self.up_color = QColor(0, 150, 0)  # Green
        self.down_color = QColor(150, 0, 0)  # Red
        self.volume_color = QColor(100, 100, 100, 100)  # Gray with alpha
        
        # Initialize empty chart
        self.update_data([], [], [])
    
    def update_data(
        self,
        prices: List[float],
        volumes: Optional[List[float]] = None,
        timestamps: Optional[List[Any]] = None
    ):
        """Update chart data."""
        self.prices = prices
        self.volumes = volumes or []
        self.timestamps = timestamps or []
        self.update()
    
    def paintEvent(self, event):
        """Paint the sparkline chart."""
        if not self.prices:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calculate scaling
        price_min = min(self.prices)
        price_max = max(self.prices)
        price_range = price_max - price_min or 1.0
        
        # Calculate points
        points = []
        for i, price in enumerate(self.prices):
            x = (i / (len(self.prices) - 1)) * (self.width() - 1)
            y = self.height() - 1 - ((price - price_min) / price_range) * (self.height() - 1)
            points.append((x, y))
        
        # Draw volume bars if enabled
        if self.show_volume and self.volumes:
            vol_max = max(self.volumes)
            for i, vol in enumerate(self.volumes):
                x = (i / (len(self.volumes) - 1)) * (self.width() - 1)
                height = (vol / vol_max) * (self.height() * 0.3)
                painter.fillRect(
                    QRect(x - 1, self.height() - height, 2, height),
                    self.volume_color
                )
        
        # Draw price line
        path = QPainterPath()
        path.moveTo(points[0][0], points[0][1])
        for x, y in points[1:]:
            path.lineTo(x, y)
        
        # Set color based on trend
        if self.prices[-1] > self.prices[0]:
            painter.setPen(QPen(self.up_color, 1))
        else:
            painter.setPen(QPen(self.down_color, 1))
        
        painter.drawPath(path)

class PerformanceChart(QWidget):
    """
    Performance tracking chart widget.
    
    Features:
    - Win rate visualization
    - Checklist compliance tracking
    - Emotion profile analysis
    - Customizable metrics
    """
    
    def __init__(
        self,
        parent=None,
        width: int = 400,
        height: int = 300,
        chart_type: str = "winrate"
    ):
        """Initialize performance chart."""
        super().__init__(parent)
        self.setFixedSize(width, height)
        self.chart_type = chart_type
        
        # Data
        self.data = []
        self.labels = []
        
        # Style
        self.colors = {
            "win": QColor(0, 150, 0),
            "loss": QColor(150, 0, 0),
            "neutral": QColor(100, 100, 100)
        }
        
        # Initialize empty chart
        self.update_data([], [])
    
    def update_data(self, data: List[float], labels: List[str]):
        """Update chart data."""
        self.data = data
        self.labels = labels
        self.update()
    
    def paintEvent(self, event):
        """Paint the performance chart."""
        if not self.data:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw based on chart type
        if self.chart_type == "winrate":
            self._draw_winrate(painter)
        elif self.chart_type == "compliance":
            self._draw_compliance(painter)
        elif self.chart_type == "emotion":
            self._draw_emotion(painter)
    
    def _draw_winrate(self, painter: QPainter):
        """Draw win rate chart."""
        # Calculate bar width and spacing
        bar_width = (self.width() - 40) / len(self.data)
        spacing = 10
        
        # Draw bars
        for i, (rate, label) in enumerate(zip(self.data, self.labels)):
            x = 20 + i * (bar_width + spacing)
            height = (rate / 100) * (self.height() - 40)
            
            # Draw bar
            painter.fillRect(
                QRect(x, self.height() - height - 20, bar_width, height),
                self.colors["win"]
            )
            
            # Draw label
            painter.drawText(
                QRect(x, self.height() - 15, bar_width, 15),
                Qt.AlignCenter,
                label
            )
    
    def _draw_compliance(self, painter: QPainter):
        """Draw checklist compliance chart."""
        # Calculate points for line chart
        points = []
        for i, score in enumerate(self.data):
            x = 20 + (i / (len(self.data) - 1)) * (self.width() - 40)
            y = self.height() - 20 - (score / 100) * (self.height() - 40)
            points.append((x, y))
        
        # Draw line
        path = QPainterPath()
        path.moveTo(points[0][0], points[0][1])
        for x, y in points[1:]:
            path.lineTo(x, y)
        
        painter.setPen(QPen(self.colors["win"], 2))
        painter.drawPath(path)
        
        # Draw points
        for x, y in points:
            painter.fillRect(QRect(x - 3, y - 3, 6, 6), self.colors["win"])
    
    def _draw_emotion(self, painter: QPainter):
        """Draw emotion profile chart."""
        # Calculate angles for pie chart
        total = sum(self.data)
        if total == 0:
            return
            
        start_angle = 0
        for i, (value, label) in enumerate(zip(self.data, self.labels)):
            angle = (value / total) * 360
            
            # Draw pie slice
            painter.setPen(QPen(self.colors["neutral"], 1))
            painter.setBrush(self.colors["win"] if i % 2 == 0 else self.colors["loss"])
            painter.drawPie(
                QRect(20, 20, self.width() - 40, self.height() - 60),
                int(start_angle * 16),
                int(angle * 16)
            )
            
            # Draw label
            mid_angle = (start_angle + angle/2) * np.pi / 180
            x = self.width()/2 + np.cos(mid_angle) * (self.width()/2 - 40)
            y = self.height()/2 + np.sin(mid_angle) * (self.height()/2 - 40)
            painter.drawText(
                QRect(x - 30, y - 10, 60, 20),
                Qt.AlignCenter,
                label
            )
            
            start_angle += angle

class ChartContainer(QWidget):
    """
    Container widget for organizing multiple charts.
    
    Features:
    - Flexible layout management
    - Chart grouping
    - Title and legend support
    """
    
    def __init__(self, parent=None):
        """Initialize chart container."""
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.charts = {}
    
    def add_chart(
        self,
        name: str,
        chart: QWidget,
        title: Optional[str] = None
    ):
        """Add a chart to the container."""
        if title:
            title_label = QLabel(title)
            title_label.setAlignment(Qt.AlignCenter)
            self.layout.addWidget(title_label)
        
        self.layout.addWidget(chart)
        self.charts[name] = chart
    
    def get_chart(self, name: str) -> Optional[QWidget]:
        """Get a chart by name."""
        return self.charts.get(name)
    
    def update_chart(
        self,
        name: str,
        data: List[float],
        labels: Optional[List[str]] = None
    ):
        """Update a chart's data."""
        chart = self.charts.get(name)
        if chart:
            chart.update_data(data, labels or []) 