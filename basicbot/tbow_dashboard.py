"""
TBOW Tactics Dashboard

This module implements a PyQt5-based dashboard for the TBOW Tactics trading system.
It provides real-time visualization of:
- Market context
- Technical indicators
- Trading bias
- Checklist compliance
- Trade journal
- Historical replay
- Risk management
"""

import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTabWidget, QGridLayout, QFrame,
    QTextEdit, QComboBox, QSpinBox, QCheckBox, QProgressBar,
    QLineEdit, QRadioButton, QButtonGroup, QFileDialog,
    QGroupBox, QScrollArea, QDateTimeEdit, QDoubleSpinBox
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QDateTime
from PyQt5.QtGui import QFont, QColor, QPalette, QPixmap

from basicbot.tbow_tactics import TBOWTactics
from basicbot.tbow_replay import TBOWReplay
from basicbot.tbow_risk import TBOWRisk
from basicbot.tbow_charts import SparklineChart, PerformanceChart, ChartContainer
from basicbot.strategy import Strategy

class PriceBox(QFrame):
    """Custom widget for displaying price information."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.StyledPanel)
        layout = QVBoxLayout(self)
        
        # Price label
        self.price_label = QLabel("0.00")
        self.price_label.setFont(QFont("Arial", 24, QFont.Bold))
        layout.addWidget(self.price_label)
        
        # Change label
        self.change_label = QLabel("0.00%")
        self.change_label.setFont(QFont("Arial", 16))
        layout.addWidget(self.change_label)
    
    def update_price(self, price: float, change: float):
        """Update price and change display."""
        self.price_label.setText(f"${price:.2f}")
        self.change_label.setText(f"{change:+.2f}%")
        
        # Set color based on change
        color = "green" if change > 0 else "red" if change < 0 else "gray"
        self.change_label.setStyleSheet(f"color: {color}")

class VolumePulseMeter(QProgressBar):
    """Custom widget for displaying volume pulse."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setOrientation(Qt.Horizontal)
        self.setRange(0, 100)
        self.setTextVisible(False)
        self.setStyleSheet("""
            QProgressBar {
                border: 1px solid gray;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
    
    def update_volume(self, current: float, average: float):
        """Update volume pulse based on current vs average."""
        ratio = min(current / average * 100, 100)
        self.setValue(int(ratio))

class TBOWDashboard(QMainWindow):
    """Main dashboard window for TBOW Tactics."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TBOW Tactics Dashboard")
        self.setGeometry(100, 100, 1600, 1000)
        
        # Initialize TBOW Tactics
        self.tbow = None
        self.current_symbol = None
        self.current_timeframe = None
        
        # Setup UI
        self.setup_ui()
        
        # Start refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(5000)  # 5 second refresh
        
        # Initial data load
        self.refresh_data()
    
    def setup_ui(self):
        """Setup the dashboard UI."""
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Add top bar with symbol selector and price box
        top_bar = self.create_top_bar()
        main_layout.addLayout(top_bar)
        
        # Create tab widget
        self.tabs = QTabWidget()
        
        # Add tabs
        self.market_tab = self.create_market_tab()
        self.indicators_tab = self.create_indicators_tab()
        self.bias_tab = self.create_bias_tab()
        self.checklist_tab = self.create_checklist_tab()
        self.journal_tab = self.create_journal_tab()
        self.analytics_tab = self.create_analytics_tab()
        self.replay_tab = self.create_replay_tab()
        
        self.tabs.addTab(self.market_tab, "Market Context")
        self.tabs.addTab(self.indicators_tab, "Indicators")
        self.tabs.addTab(self.bias_tab, "Trading Bias")
        self.tabs.addTab(self.checklist_tab, "Checklist")
        self.tabs.addTab(self.journal_tab, "Trade Journal")
        self.tabs.addTab(self.analytics_tab, "Analytics")
        self.tabs.addTab(self.replay_tab, "Replay")
        
        main_layout.addWidget(self.tabs)
        
        # Add risk management panel
        risk_panel = self.create_risk_panel()
        main_layout.addWidget(risk_panel)
        
        # Add status bar
        self.statusBar().showMessage("Ready")
    
    def create_top_bar(self) -> QHBoxLayout:
        """Create the top bar with symbol selector and price box."""
        layout = QHBoxLayout()
        
        # Symbol selector
        symbol_label = QLabel("Symbol:")
        self.symbol_input = QComboBox()
        self.symbol_input.addItems(["SPY", "QQQ", "AAPL", "MSFT", "TSLA"])
        self.symbol_input.currentTextChanged.connect(self.on_symbol_changed)
        
        # Timeframe selector
        timeframe_label = QLabel("Timeframe:")
        self.timeframe_input = QComboBox()
        self.timeframe_input.addItems(["1Min", "5Min", "15Min", "1H", "4H", "1D"])
        self.timeframe_input.currentTextChanged.connect(self.on_timeframe_changed)
        
        # Price box
        self.price_box = PriceBox()
        
        # Volume pulse meter
        self.volume_pulse = VolumePulseMeter()
        self.volume_pulse.setFixedWidth(200)
        
        # Add widgets to layout
        layout.addWidget(symbol_label)
        layout.addWidget(self.symbol_input)
        layout.addWidget(timeframe_label)
        layout.addWidget(self.timeframe_input)
        layout.addWidget(self.price_box)
        layout.addWidget(self.volume_pulse)
        layout.addStretch()
        
        return layout
    
    def create_market_tab(self) -> QWidget:
        """Create the market context tab."""
        tab = QWidget()
        layout = QGridLayout(tab)
        
        # Left panel - Macro Snapshot
        macro_frame = QGroupBox("Macro Snapshot")
        macro_layout = QVBoxLayout(macro_frame)
        
        # SPY & QQQ charts
        self.spy_chart = SparklineChart(show_volume=True)
        self.qqq_chart = SparklineChart(show_volume=True)
        
        macro_layout.addWidget(QLabel("SPY"))
        macro_layout.addWidget(self.spy_chart)
        macro_layout.addWidget(QLabel("QQQ"))
        macro_layout.addWidget(self.qqq_chart)
        
        # Correlation meter
        corr_frame = QFrame()
        corr_layout = QHBoxLayout(corr_frame)
        corr_layout.addWidget(QLabel("Correlation:"))
        self.corr_label = QLabel("0%")
        corr_layout.addWidget(self.corr_label)
        macro_layout.addWidget(corr_frame)
        
        # VIX level
        vix_frame = QFrame()
        vix_layout = QHBoxLayout(vix_frame)
        vix_layout.addWidget(QLabel("VIX:"))
        self.vix_label = QLabel("0.00")
        vix_layout.addWidget(self.vix_label)
        macro_layout.addWidget(vix_frame)
        
        # News feed
        news_frame = QGroupBox("Top Headlines")
        news_layout = QVBoxLayout(news_frame)
        self.news_text = QTextEdit()
        self.news_text.setReadOnly(True)
        news_layout.addWidget(self.news_text)
        macro_layout.addWidget(news_frame)
        
        layout.addWidget(macro_frame, 0, 0)
        
        # Right panel - Pre-Market Analysis
        pre_market_frame = QGroupBox("Pre-Market Analysis")
        pre_market_layout = QVBoxLayout(pre_market_frame)
        
        # Gap indicator
        gap_frame = QFrame()
        gap_layout = QHBoxLayout(gap_frame)
        gap_layout.addWidget(QLabel("Gap:"))
        self.gap_label = QLabel("No Gap")
        gap_layout.addWidget(self.gap_label)
        pre_market_layout.addWidget(gap_frame)
        
        # Volume map
        volume_frame = QGroupBox("Session Volume Map")
        volume_layout = QVBoxLayout(volume_frame)
        self.volume_map = QProgressBar()
        self.volume_map.setOrientation(Qt.Horizontal)
        volume_layout.addWidget(self.volume_map)
        pre_market_layout.addWidget(volume_frame)
        
        # Market alignment checkbox
        self.market_aligned = QCheckBox("TSLA aligned with market?")
        pre_market_layout.addWidget(self.market_aligned)
        
        layout.addWidget(pre_market_frame, 0, 1)
        
        return tab
    
    def create_indicators_tab(self) -> QWidget:
        """Create the indicators tab."""
        tab = QWidget()
        layout = QGridLayout(tab)
        
        # MACD Module
        macd_frame = QGroupBox("MACD")
        macd_layout = QVBoxLayout(macd_frame)
        
        # Direction
        direction_frame = QFrame()
        direction_layout = QHBoxLayout(direction_frame)
        direction_layout.addWidget(QLabel("Direction:"))
        self.macd_direction = QLabel("Unknown")
        direction_layout.addWidget(self.macd_direction)
        macd_layout.addWidget(direction_frame)
        
        # Curl detection
        curl_frame = QFrame()
        curl_layout = QHBoxLayout(curl_frame)
        curl_layout.addWidget(QLabel("Curl Detected:"))
        self.macd_curl = QLabel("No")
        curl_layout.addWidget(self.macd_curl)
        macd_layout.addWidget(curl_frame)
        
        # Histogram
        self.macd_hist = QProgressBar()
        self.macd_hist.setOrientation(Qt.Horizontal)
        macd_layout.addWidget(self.macd_hist)
        
        layout.addWidget(macd_frame, 0, 0)
        
        # RSI Module
        rsi_frame = QGroupBox("RSI")
        rsi_layout = QVBoxLayout(rsi_frame)
        
        # Current value
        self.rsi_value = QLabel("50")
        self.rsi_value.setFont(QFont("Arial", 24, QFont.Bold))
        rsi_layout.addWidget(self.rsi_value)
        
        # Oversold/Overbought
        self.rsi_zone = QLabel("Neutral")
        rsi_layout.addWidget(self.rsi_zone)
        
        # Reversal signal
        self.rsi_reversal = QLabel("No Reversal")
        rsi_layout.addWidget(self.rsi_reversal)
        
        layout.addWidget(rsi_frame, 0, 1)
        
        # VWAP Module
        vwap_frame = QGroupBox("VWAP")
        vwap_layout = QVBoxLayout(vwap_frame)
        
        # Price vs VWAP
        self.vwap_position = QLabel("Unknown")
        vwap_layout.addWidget(self.vwap_position)
        
        # Recent cross
        self.vwap_cross = QLabel("No Recent Cross")
        vwap_layout.addWidget(self.vwap_cross)
        
        layout.addWidget(vwap_frame, 0, 2)
        
        # Volume Module
        volume_frame = QGroupBox("Volume")
        volume_layout = QVBoxLayout(volume_frame)
        
        # Live volume bar
        self.volume_bar = QProgressBar()
        volume_layout.addWidget(self.volume_bar)
        
        # Spike detection
        self.volume_spike = QLabel("No Spike")
        volume_layout.addWidget(self.volume_spike)
        
        layout.addWidget(volume_frame, 1, 0)
        
        # Bollinger Module
        bb_frame = QGroupBox("Bollinger Bands")
        bb_layout = QVBoxLayout(bb_frame)
        
        # Squeeze alert
        self.bb_squeeze = QLabel("No Squeeze")
        bb_layout.addWidget(self.bb_squeeze)
        
        # Position
        self.bb_position = QLabel("Unknown")
        bb_layout.addWidget(self.bb_position)
        
        layout.addWidget(bb_frame, 1, 1, 1, 2)
        
        return tab
    
    def create_bias_tab(self) -> QWidget:
        """Create the trading bias tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Bias Summary Box
        bias_frame = QGroupBox("Bias Summary")
        bias_layout = QVBoxLayout(bias_frame)
        
        # Directional bias
        self.bias_direction = QLabel("NEUTRAL")
        self.bias_direction.setFont(QFont("Arial", 36, QFont.Bold))
        self.bias_direction.setAlignment(Qt.AlignCenter)
        bias_layout.addWidget(self.bias_direction)
        
        # Confidence score
        self.bias_confidence = QLabel("DNP")
        self.bias_confidence.setFont(QFont("Arial", 36, QFont.Bold))
        self.bias_confidence.setAlignment(Qt.AlignCenter)
        bias_layout.addWidget(self.bias_confidence)
        
        # Setup grade reasoning
        self.bias_reasoning = QLabel("No clear setup")
        self.bias_reasoning.setAlignment(Qt.AlignCenter)
        bias_layout.addWidget(self.bias_reasoning)
        
        layout.addWidget(bias_frame)
        
        # Setup Mode Selector
        mode_frame = QGroupBox("Setup Mode")
        mode_layout = QHBoxLayout(mode_frame)
        
        self.mode_group = QButtonGroup()
        self.scalp_mode = QRadioButton("Scalp")
        self.swing_mode = QRadioButton("Swing")
        self.observe_mode = QRadioButton("Observation Only")
        
        self.mode_group.addButton(self.scalp_mode)
        self.mode_group.addButton(self.swing_mode)
        self.mode_group.addButton(self.observe_mode)
        
        mode_layout.addWidget(self.scalp_mode)
        mode_layout.addWidget(self.swing_mode)
        mode_layout.addWidget(self.observe_mode)
        
        layout.addWidget(mode_frame)
        
        # Alert Switches
        alert_frame = QGroupBox("Alerts")
        alert_layout = QVBoxLayout(alert_frame)
        
        self.alert_a_plus = QCheckBox("Notify me on A+ Setup")
        self.alert_confluence = QCheckBox("Show audio/popup when confluence shifts")
        self.alert_autolog = QCheckBox("Autopopulate trade log on setup match")
        
        alert_layout.addWidget(self.alert_a_plus)
        alert_layout.addWidget(self.alert_confluence)
        alert_layout.addWidget(self.alert_autolog)
        
        layout.addWidget(alert_frame)
        
        return tab
    
    def create_checklist_tab(self) -> QWidget:
        """Create the checklist tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Live Checklist Display
        checklist_frame = QGroupBox("Live Checklist")
        checklist_layout = QVBoxLayout(checklist_frame)
        
        # Create checklist items
        self.checklist_items = {}
        
        items = [
            ("MACD curling in my bias", True),
            ("VWAP confirmed or broken clean", True),
            ("Tape slowed at S/R", False),
            ("Entry candle shows rejection", False),
            ("Risk level defined", False),
            ("Bias matches market", True)
        ]
        
        for text, auto in items:
            frame = QFrame()
            item_layout = QHBoxLayout(frame)
            
            check = QCheckBox(text)
            check.setEnabled(not auto)
            item_layout.addWidget(check)
            
            if auto:
                status = QLabel("Auto")
                status.setStyleSheet("color: gray")
                item_layout.addWidget(status)
            
            checklist_layout.addWidget(frame)
            self.checklist_items[text] = check
        
        layout.addWidget(checklist_frame)
        
        # Decision Meter
        meter_frame = QGroupBox("Decision Meter")
        meter_layout = QVBoxLayout(meter_frame)
        
        self.decision_meter = QProgressBar()
        self.decision_meter.setRange(0, 6)
        meter_layout.addWidget(self.decision_meter)
        
        self.decision_label = QLabel("Not Ready")
        self.decision_label.setAlignment(Qt.AlignCenter)
        meter_layout.addWidget(self.decision_label)
        
        layout.addWidget(meter_frame)
        
        return tab
    
    def create_journal_tab(self) -> QWidget:
        """Create the trade journal tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Entry Form
        form_frame = QGroupBox("Trade Entry")
        form_layout = QVBoxLayout(form_frame)
        
        # Bias selection
        bias_frame = QFrame()
        bias_layout = QHBoxLayout(bias_frame)
        bias_layout.addWidget(QLabel("Bias:"))
        self.bias_long = QRadioButton("Long")
        self.bias_short = QRadioButton("Short")
        self.bias_none = QRadioButton("None")
        bias_layout.addWidget(self.bias_long)
        bias_layout.addWidget(self.bias_short)
        bias_layout.addWidget(self.bias_none)
        form_layout.addWidget(bias_frame)
        
        # Entry reason
        form_layout.addWidget(QLabel("Why You Entered:"))
        self.entry_reason = QTextEdit()
        form_layout.addWidget(self.entry_reason)
        
        # Checklist score
        self.checklist_score = QLabel("Checklist Score: 0/6")
        form_layout.addWidget(self.checklist_score)
        
        # Screenshot upload
        screenshot_frame = QFrame()
        screenshot_layout = QHBoxLayout(screenshot_frame)
        screenshot_layout.addWidget(QLabel("Screenshot:"))
        self.screenshot_btn = QPushButton("Upload")
        self.screenshot_btn.clicked.connect(self.upload_screenshot)
        screenshot_layout.addWidget(self.screenshot_btn)
        form_layout.addWidget(screenshot_frame)
        
        # Result
        result_frame = QFrame()
        result_layout = QHBoxLayout(result_frame)
        result_layout.addWidget(QLabel("Result:"))
        self.result_win = QRadioButton("Win")
        self.result_loss = QRadioButton("Loss")
        self.result_flat = QRadioButton("Flat")
        result_layout.addWidget(self.result_win)
        result_layout.addWidget(self.result_loss)
        result_layout.addWidget(self.result_flat)
        form_layout.addWidget(result_frame)
        
        # RR Outcome
        rr_frame = QFrame()
        rr_layout = QHBoxLayout(rr_frame)
        rr_layout.addWidget(QLabel("RR Outcome:"))
        self.rr_input = QLineEdit()
        rr_layout.addWidget(self.rr_input)
        form_layout.addWidget(rr_frame)
        
        # Emotion tags
        emotion_frame = QFrame()
        emotion_layout = QHBoxLayout(emotion_frame)
        emotion_layout.addWidget(QLabel("Emotion:"))
        self.emotion_hesitant = QCheckBox("Hesitated")
        self.emotion_confident = QCheckBox("Confident")
        self.emotion_rushed = QCheckBox("Rushed")
        self.emotion_patient = QCheckBox("Patient")
        emotion_layout.addWidget(self.emotion_hesitant)
        emotion_layout.addWidget(self.emotion_confident)
        emotion_layout.addWidget(self.emotion_rushed)
        emotion_layout.addWidget(self.emotion_patient)
        form_layout.addWidget(emotion_frame)
        
        layout.addWidget(form_frame)
        
        # Export options
        export_frame = QGroupBox("Export Options")
        export_layout = QVBoxLayout(export_frame)
        
        self.export_csv = QCheckBox("Auto-export as CSV")
        self.export_notion = QCheckBox("Sync to Notion")
        
        export_layout.addWidget(self.export_csv)
        export_layout.addWidget(self.export_notion)
        
        layout.addWidget(export_frame)
        
        # Daily summary
        summary_frame = QGroupBox("Daily Summary")
        summary_layout = QVBoxLayout(summary_frame)
        
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        summary_layout.addWidget(self.summary_text)
        
        layout.addWidget(summary_frame)
        
        return tab
    
    def create_analytics_tab(self) -> QWidget:
        """Create the analytics tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Create chart container
        self.analytics_charts = ChartContainer()
        
        # Setup win rate chart
        self.winrate_chart = PerformanceChart(chart_type="winrate")
        self.analytics_charts.add_chart(
            "winrate",
            self.winrate_chart,
            "Setup Win Rate by Confidence Score"
        )
        
        # Checklist compliance chart
        self.compliance_chart = PerformanceChart(chart_type="compliance")
        self.analytics_charts.add_chart(
            "compliance",
            self.compliance_chart,
            "Checklist Compliance Correlation"
        )
        
        # Trade duration chart
        self.duration_chart = PerformanceChart(chart_type="winrate")
        self.analytics_charts.add_chart(
            "duration",
            self.duration_chart,
            "Average Time in Trade"
        )
        
        # Emotion profile chart
        self.emotion_chart = PerformanceChart(chart_type="emotion")
        self.analytics_charts.add_chart(
            "emotion",
            self.emotion_chart,
            "Emotion Profile"
        )
        
        layout.addWidget(self.analytics_charts)
        
        return tab
    
    def create_replay_tab(self) -> QWidget:
        """Create the replay tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Date range selector
        date_frame = QGroupBox("Date Range")
        date_layout = QHBoxLayout(date_frame)
        
        self.start_date = QDateTimeEdit()
        self.start_date.setDateTime(QDateTime.currentDateTime().addDays(-1))
        self.end_date = QDateTimeEdit()
        self.end_date.setDateTime(QDateTime.currentDateTime())
        
        date_layout.addWidget(QLabel("Start:"))
        date_layout.addWidget(self.start_date)
        date_layout.addWidget(QLabel("End:"))
        date_layout.addWidget(self.end_date)
        
        self.load_replay_btn = QPushButton("Load Replay")
        self.load_replay_btn.clicked.connect(self.load_replay)
        date_layout.addWidget(self.load_replay_btn)
        
        layout.addWidget(date_frame)
        
        # Replay controls
        control_frame = QGroupBox("Replay Controls")
        control_layout = QHBoxLayout(control_frame)
        
        self.prev_btn = QPushButton("Previous")
        self.prev_btn.clicked.connect(self.replay_prev)
        self.next_btn = QPushButton("Next")
        self.next_btn.clicked.connect(self.replay_next)
        self.export_btn = QPushButton("Export Analysis")
        self.export_btn.clicked.connect(self.export_replay)
        
        control_layout.addWidget(self.prev_btn)
        control_layout.addWidget(self.next_btn)
        control_layout.addWidget(self.export_btn)
        
        layout.addWidget(control_frame)
        
        # Replay display
        display_frame = QGroupBox("Replay Display")
        display_layout = QGridLayout(display_frame)
        
        # Current state
        self.replay_time = QLabel("--:--")
        self.replay_time.setFont(QFont("Arial", 24, QFont.Bold))
        display_layout.addWidget(self.replay_time, 0, 0)
        
        self.replay_price = QLabel("$0.00")
        self.replay_price.setFont(QFont("Arial", 24, QFont.Bold))
        display_layout.addWidget(self.replay_price, 0, 1)
        
        # Setup analysis
        self.replay_bias = QLabel("Bias: --")
        display_layout.addWidget(self.replay_bias, 1, 0)
        
        self.replay_confidence = QLabel("Confidence: --")
        display_layout.addWidget(self.replay_confidence, 1, 1)
        
        self.replay_score = QLabel("Setup Score: --")
        display_layout.addWidget(self.replay_score, 2, 0)
        
        self.replay_alignment = QLabel("Market Aligned: --")
        display_layout.addWidget(self.replay_alignment, 2, 1)
        
        layout.addWidget(display_frame)
        
        # Initialize replay system
        self.replay = None
        
        return tab
    
    def create_risk_panel(self) -> QWidget:
        """Create the risk management panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Account settings
        account_frame = QGroupBox("Account Settings")
        account_layout = QGridLayout(account_frame)
        
        account_layout.addWidget(QLabel("Account Equity:"), 0, 0)
        self.equity_input = QDoubleSpinBox()
        self.equity_input.setRange(0, 1000000)
        self.equity_input.setValue(100000)
        self.equity_input.setPrefix("$")
        account_layout.addWidget(self.equity_input, 0, 1)
        
        account_layout.addWidget(QLabel("Max Risk/Trade:"), 1, 0)
        self.risk_input = QDoubleSpinBox()
        self.risk_input.setRange(0.1, 5.0)
        self.risk_input.setValue(1.0)
        self.risk_input.setSuffix("%")
        account_layout.addWidget(self.risk_input, 1, 1)
        
        account_layout.addWidget(QLabel("Max Daily DD:"), 2, 0)
        self.dd_input = QDoubleSpinBox()
        self.dd_input.setRange(1.0, 10.0)
        self.dd_input.setValue(3.0)
        self.dd_input.setSuffix("%")
        account_layout.addWidget(self.dd_input, 2, 1)
        
        layout.addWidget(account_frame)
        
        # Position calculator
        calc_frame = QGroupBox("Position Calculator")
        calc_layout = QGridLayout(calc_frame)
        
        calc_layout.addWidget(QLabel("Entry Price:"), 0, 0)
        self.entry_input = QDoubleSpinBox()
        self.entry_input.setRange(0, 10000)
        self.entry_input.setPrefix("$")
        calc_layout.addWidget(self.entry_input, 0, 1)
        
        calc_layout.addWidget(QLabel("Stop Loss:"), 1, 0)
        self.stop_input = QDoubleSpinBox()
        self.stop_input.setRange(0, 10000)
        self.stop_input.setPrefix("$")
        calc_layout.addWidget(self.stop_input, 1, 1)
        
        calc_layout.addWidget(QLabel("Target:"), 2, 0)
        self.target_input = QDoubleSpinBox()
        self.target_input.setRange(0, 10000)
        self.target_input.setPrefix("$")
        calc_layout.addWidget(self.target_input, 2, 1)
        
        self.calc_btn = QPushButton("Calculate")
        self.calc_btn.clicked.connect(self.calculate_position)
        calc_layout.addWidget(self.calc_btn, 3, 0, 1, 2)
        
        layout.addWidget(calc_frame)
        
        # Results display
        results_frame = QGroupBox("Results")
        results_layout = QGridLayout(results_frame)
        
        self.position_size = QLabel("Position Size: --")
        results_layout.addWidget(self.position_size, 0, 0)
        
        self.position_value = QLabel("Position Value: --")
        results_layout.addWidget(self.position_value, 0, 1)
        
        self.rr_ratio = QLabel("R:R Ratio: --")
        results_layout.addWidget(self.rr_ratio, 1, 0)
        
        self.risk_amount = QLabel("Risk Amount: --")
        results_layout.addWidget(self.risk_amount, 1, 1)
        
        layout.addWidget(results_frame)
        
        # Daily stats
        stats_frame = QGroupBox("Daily Stats")
        stats_layout = QGridLayout(stats_frame)
        
        self.daily_pnl = QLabel("Daily P&L: $0.00")
        stats_layout.addWidget(self.daily_pnl, 0, 0)
        
        self.current_dd = QLabel("Current DD: 0.00%")
        stats_layout.addWidget(self.current_dd, 0, 1)
        
        self.trades_today = QLabel("Trades Today: 0")
        stats_layout.addWidget(self.trades_today, 1, 0)
        
        self.red_zone = QLabel("Red Zone: No")
        self.red_zone.setStyleSheet("color: green")
        stats_layout.addWidget(self.red_zone, 1, 1)
        
        layout.addWidget(stats_frame)
        
        # Initialize risk management
        self.risk = TBOWRisk(
            account_equity=self.equity_input.value(),
            max_risk_per_trade=self.risk_input.value() / 100,
            max_daily_drawdown=self.dd_input.value() / 100
        )
        
        return panel
    
    def upload_screenshot(self):
        """Handle screenshot upload."""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select Screenshot",
            "",
            "Image Files (*.png *.jpg *.jpeg)"
        )
        if file_name:
            # TODO: Implement screenshot handling
            pass
    
    def on_symbol_changed(self, symbol: str):
        """Handle symbol change."""
        self.current_symbol = symbol
        self.initialize_tbow()
        self.refresh_data()
    
    def on_timeframe_changed(self, timeframe: str):
        """Handle timeframe change."""
        self.current_timeframe = timeframe
        self.initialize_tbow()
        self.refresh_data()
    
    def initialize_tbow(self):
        """Initialize TBOW Tactics with current settings."""
        if self.current_symbol and self.current_timeframe:
            self.tbow = TBOWTactics(
                symbol=self.current_symbol,
                timeframe=self.current_timeframe
            )
    
    def refresh_data(self):
        """Refresh dashboard data."""
        if not self.tbow:
            return
            
        try:
            # Get market data
            data = self.tbow.strategy.fetch_historical_data()
            if data is None or data.empty:
                self.statusBar().showMessage("No data available")
                return
            
            # Update price box
            latest = data.iloc[-1]
            self.price_box.update_price(
                latest["close"],
                (latest["close"] - data.iloc[-2]["close"]) / data.iloc[-2]["close"] * 100
            )
            
            # Update volume pulse
            self.volume_pulse.update_volume(
                latest["volume"],
                data["volume"].rolling(20).mean().iloc[-1]
            )
            
            # Update SPY/QQQ sparklines
            spy_data = self.tbow.strategy.fetch_historical_data(symbol="SPY")
            qqq_data = self.tbow.strategy.fetch_historical_data(symbol="QQQ")
            
            if spy_data is not None and not spy_data.empty:
                self.spy_chart.update_data(
                    spy_data["close"].tolist(),
                    spy_data["volume"].tolist(),
                    spy_data.index.tolist()
                )
            
            if qqq_data is not None and not qqq_data.empty:
                self.qqq_chart.update_data(
                    qqq_data["close"].tolist(),
                    qqq_data["volume"].tolist(),
                    qqq_data.index.tolist()
                )
            
            # Scan market context
            context = self.tbow.scan_market_context(data)
            self.update_market_tab(context)
            
            # Analyze indicators
            indicators = self.tbow.analyze_indicators(data)
            self.update_indicators_tab(indicators)
            
            # Generate bias
            bias = self.tbow.generate_bias(context, indicators)
            self.update_bias_tab(bias)
            
            # Check compliance
            checklist = self.tbow.check_compliance(context, indicators)
            self.update_checklist_tab(checklist)
            
            # Update analytics
            self.update_analytics_tab()
            
            # Update status
            self.statusBar().showMessage(
                f"Last updated: {datetime.now().strftime('%H:%M:%S')}"
            )
            
        except Exception as e:
            self.statusBar().showMessage(f"Error: {str(e)}")
    
    def update_market_tab(self, context: Dict[str, Any]):
        """Update market context tab."""
        # Update correlation
        self.corr_label.setText(f"{context.get('correlation', 0):.1f}%")
        
        # Update VIX
        self.vix_label.setText(f"{context.get('vix', 0):.2f}")
        
        # Update gap
        if context["gaps"]["has_gap"]:
            gap_text = f"{context['gaps']['direction'].upper()} GAP ({context['gaps']['size']:.1f}%)"
            self.gap_label.setText(gap_text)
            self.gap_label.setStyleSheet(
                f"color: {'green' if context['gaps']['direction'] == 'up' else 'red'}"
            )
        else:
            self.gap_label.setText("No Gap")
            self.gap_label.setStyleSheet("color: gray")
        
        # Update volume map
        self.volume_map.setValue(int(context.get('volume_ratio', 0) * 100))
        
        # Update market alignment
        self.market_aligned.setChecked(context.get('market_aligned', False))
    
    def update_indicators_tab(self, indicators: Dict[str, Any]):
        """Update indicators tab."""
        # Update MACD
        macd = indicators["macd"]
        self.macd_direction.setText(macd["trend"].upper())
        self.macd_curl.setText("Yes" if macd.get("curl", False) else "No")
        self.macd_hist.setValue(int(macd["histogram"] * 100))
        
        # Update RSI
        rsi = indicators["rsi"]
        self.rsi_value.setText(f"{rsi['value']:.1f}")
        self.rsi_zone.setText(rsi["trend"].upper())
        self.rsi_reversal.setText("Reversal Signal" if rsi.get("reversal", False) else "No Reversal")
        
        # Update VWAP
        vwap = indicators["vwap"]
        self.vwap_position.setText(f"Price {vwap['position'].upper()} VWAP")
        self.vwap_cross.setText("Recent Cross" if vwap.get("crossed", False) else "No Recent Cross")
        
        # Update volume
        volume = indicators["volume"]
        self.volume_bar.setValue(int(volume["strength"] * 100))
        self.volume_spike.setText(
            f"Spike: {volume.get('last_spike', 'None')}"
            if volume.get("spike", False)
            else "No Spike"
        )
        
        # Update Bollinger Bands
        bb = indicators["bollinger"]
        self.bb_squeeze.setText(
            f"Squeeze: {bb.get('squeeze_percent', 0):.1f}%"
            if bb["squeeze"]
            else "No Squeeze"
        )
        self.bb_position.setText(bb["position"].upper())
    
    def update_bias_tab(self, bias: Dict[str, Any]):
        """Update bias tab."""
        # Update bias direction
        self.bias_direction.setText(bias["bias"])
        self.bias_direction.setStyleSheet(
            f"color: {'green' if bias['bias'] == 'BULLISH' else 'red' if bias['bias'] == 'BEARISH' else 'gray'}"
        )
        
        # Update confidence
        self.bias_confidence.setText(bias["confidence"])
        self.bias_confidence.setStyleSheet(
            f"color: {'green' if bias['confidence'] == 'A+' else 'orange' if bias['confidence'] == 'B' else 'red'}"
        )
        
        # Update reasoning
        self.bias_reasoning.setText(bias.get("reasoning", "No clear setup"))
    
    def update_checklist_tab(self, checklist: Dict[str, Any]):
        """Update checklist tab."""
        # Update checklist items
        for item, check in self.checklist_items.items():
            if item in checklist:
                check.setChecked(checklist[item]["status"])
        
        # Update decision meter
        passed_checks = sum(1 for item in checklist.values() if item["status"])
        self.decision_meter.setValue(passed_checks)
        
        # Update decision label
        if passed_checks >= 5:
            self.decision_label.setText("Trade Valid")
            self.decision_label.setStyleSheet("color: green")
        elif passed_checks >= 3:
            self.decision_label.setText("High Risk")
            self.decision_label.setStyleSheet("color: orange")
        else:
            self.decision_label.setText("Do Not Enter")
            self.decision_label.setStyleSheet("color: red")
    
    def load_replay(self):
        """Load historical data for replay."""
        try:
            # Initialize replay system
            self.replay = TBOWReplay(
                symbol=self.current_symbol,
                timeframe=self.current_timeframe
            )
            
            # Load historical data
            success = self.replay.load_historical_data(
                start_date=self.start_date.dateTime().toPyDateTime(),
                end_date=self.end_date.dateTime().toPyDateTime()
            )
            
            if success:
                self.statusBar().showMessage("Replay data loaded")
                self.replay_next()  # Load first candle
            else:
                self.statusBar().showMessage("Error loading replay data")
            
        except Exception as e:
            self.statusBar().showMessage(f"Error: {str(e)}")
    
    def replay_next(self):
        """Step forward in replay."""
        if not self.replay:
            return
        
        result = self.replay.step_forward()
        if result:
            self.update_replay_display(result)
    
    def replay_prev(self):
        """Step backward in replay."""
        if not self.replay:
            return
        
        result = self.replay.step_backward()
        if result:
            self.update_replay_display(result)
    
    def update_replay_display(self, result: Dict[str, Any]):
        """Update replay display with current state."""
        # Update time and price
        self.replay_time.setText(result["timestamp"].strftime("%H:%M:%S"))
        self.replay_price.setText(f"${result['price']:.2f}")
        
        # Update bias and confidence
        self.replay_bias.setText(f"Bias: {result['bias']['bias']}")
        self.replay_confidence.setText(f"Confidence: {result['bias']['confidence']}")
        
        # Update setup score
        setup = self.replay.analyze_setup(self.replay.current_index - 1)
        self.replay_score.setText(f"Setup Score: {setup['overall_score']:.2f}")
        
        # Update market alignment
        aligned = result["context"].get("market_aligned", False)
        self.replay_alignment.setText(f"Market Aligned: {'Yes' if aligned else 'No'}")
    
    def export_replay(self):
        """Export replay analysis to CSV."""
        if not self.replay:
            return
        
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Export Analysis",
            "",
            "CSV Files (*.csv)"
        )
        
        if file_name:
            success = self.replay.export_analysis(file_name)
            if success:
                self.statusBar().showMessage("Analysis exported")
            else:
                self.statusBar().showMessage("Error exporting analysis")
    
    def calculate_position(self):
        """Calculate position size and risk metrics."""
        try:
            # Get inputs
            entry = self.entry_input.value()
            stop = self.stop_input.value()
            target = self.target_input.value()
            
            # Calculate position size
            size, details = self.risk.calculate_position_size(entry, stop)
            
            # Calculate RR ratio
            rr = self.risk.calculate_rr_ratio(entry, stop, target)
            
            # Update display
            self.position_size.setText(f"Position Size: {size}")
            self.position_value.setText(f"Position Value: ${details['position_value']:.2f}")
            self.rr_ratio.setText(f"R:R Ratio: {rr['rr_ratio']:.2f}")
            self.risk_amount.setText(f"Risk Amount: ${details['dollar_risk']:.2f}")
            
            # Update daily stats
            self.update_risk_stats()
            
        except Exception as e:
            self.statusBar().showMessage(f"Error: {str(e)}")
    
    def update_risk_stats(self):
        """Update risk management statistics."""
        # Get red zone status
        red_zone = self.risk.check_red_zone()
        
        # Update display
        self.daily_pnl.setText(f"Daily P&L: ${red_zone['daily_pnl']:.2f}")
        self.current_dd.setText(f"Current DD: {red_zone['drawdown_pct']*100:.2f}%")
        self.trades_today.setText(f"Trades Today: {red_zone['trades_today']}")
        
        # Update red zone indicator
        if red_zone["in_red_zone"]:
            self.red_zone.setText("Red Zone: YES")
            self.red_zone.setStyleSheet("color: red")
        else:
            self.red_zone.setText("Red Zone: No")
            self.red_zone.setStyleSheet("color: green")
    
    def update_analytics_tab(self):
        """Update analytics charts with latest data."""
        try:
            # Get trade history
            trades = self.tbow.get_trade_history()
            if not trades:
                return
            
            # Calculate win rates by confidence
            confidence_scores = {}
            for trade in trades:
                score = trade.get("confidence", "DNP")
                if score not in confidence_scores:
                    confidence_scores[score] = {"wins": 0, "total": 0}
                confidence_scores[score]["total"] += 1
                if trade.get("result") == "win":
                    confidence_scores[score]["wins"] += 1
            
            # Update win rate chart
            winrates = []
            labels = []
            for score in ["A+", "B", "C", "DNP"]:
                if score in confidence_scores:
                    stats = confidence_scores[score]
                    winrate = (stats["wins"] / stats["total"]) * 100
                    winrates.append(winrate)
                    labels.append(f"{score} ({stats['total']})")
            
            self.winrate_chart.update_data(winrates, labels)
            
            # Calculate checklist compliance
            compliance_scores = []
            compliance_labels = []
            for trade in trades:
                if "checklist_score" in trade:
                    compliance_scores.append(trade["checklist_score"])
                    compliance_labels.append(trade["timestamp"].strftime("%m/%d"))
            
            self.compliance_chart.update_data(compliance_scores, compliance_labels)
            
            # Calculate trade durations
            durations = []
            duration_labels = []
            for trade in trades:
                if "duration" in trade:
                    durations.append(trade["duration"])
                    duration_labels.append(trade["timestamp"].strftime("%m/%d"))
            
            self.duration_chart.update_data(durations, duration_labels)
            
            # Calculate emotion profile
            emotions = {
                "Hesitant": 0,
                "Confident": 0,
                "Rushed": 0,
                "Patient": 0
            }
            
            for trade in trades:
                if "emotions" in trade:
                    for emotion in trade["emotions"]:
                        if emotion in emotions:
                            emotions[emotion] += 1
            
            self.emotion_chart.update_data(
                list(emotions.values()),
                list(emotions.keys())
            )
            
        except Exception as e:
            self.logger.error(f"Error updating analytics: {e}")

def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    dashboard = TBOWDashboard()
    dashboard.show()
    sys.exit(app.exec_()) 