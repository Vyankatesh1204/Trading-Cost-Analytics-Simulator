#gui.py
from PyQt5.QtWidgets import (
    QMainWindow, QLabel, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QTextEdit, QLineEdit, QComboBox, QTableWidget,
    QTableWidgetItem, QGroupBox, QFormLayout, QProgressBar, QMessageBox
)
from PyQt5.QtCore import pyqtSignal, Qt, QTimer
import asyncio
import threading
import websockets
import json
import time
import numpy as np
from collections import deque
from cost_model import CostRegressionModel
from models import ModelManager
from impact_model import AlmgrenChrissModel

class MainWindow(QMainWindow):
    update_price_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Trading Cost Analytics Simulator")
        self.setGeometry(100, 100, 1100, 640)
        self.setStyleSheet(self.load_stylesheet())
        self.init_ui()
        self.update_price_signal.connect(self.update_price_label)
        self.latest_price = None
        self.top_bid_price = None
        self.top_ask_price = None
        self.price_history = deque(maxlen=100)
        self.volatility = 0.02

        try:
            self.cost_model = CostRegressionModel()
            self.model_mgr = ModelManager()
            self.append_log("✅ Models loaded successfully.")
        except FileNotFoundError as e:
            self.cost_model = None
            self.append_log(f"⚠️ Warning: {str(e)}")

    def load_stylesheet(self):
        return '''
        QWidget {
            background-color: #1e1e1e;
            color: #dddddd;
            font-family: Consolas;
            font-size: 11pt;
        }
        QLineEdit, QComboBox, QTextEdit {
            background-color: #2e2e2e;
            border: 1px solid #555;
            padding: 4px;
        }
        QPushButton {
            background-color: #007acc;
            color: white;
            padding: 6px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #005999;
        }
        QGroupBox {
            border: 1px solid #555;
            margin-top: 10px;
            padding: 10px;
            font-weight: bold;
        }
        QTableWidget {
            background-color: #2e2e2e;
            border: 1px solid #333;
        }
        QHeaderView::section {
            background-color: #444;
            color: white;
        }
        '''

    def init_ui(self):
        input_group = QGroupBox("🎯 Trade Inputs")
        input_layout = QFormLayout()

        self.symbol_input = QLineEdit("BTC-USDT-SWAP")
        self.side_input = QComboBox()
        self.side_input.addItems(["Buy", "Sell"])
        self.qty_input = QLineEdit("100")
        self.fee_input = QComboBox()
        self.fee_input.addItems(["Tier 1 (0.10%)", "Tier 2 (0.08%)", "Tier 3 (0.05%)"])

        self.order_button = QPushButton("Place Order")
        self.order_button.clicked.connect(self.place_order)
        self.start_button = QPushButton("Start WebSocket")
        self.start_button.clicked.connect(self.start_ws)

        input_layout.addRow("Symbol:", self.symbol_input)
        input_layout.addRow("Side:", self.side_input)
        input_layout.addRow("Quantity:", self.qty_input)
        input_layout.addRow("Fee Tier:", self.fee_input)
        input_layout.addRow(self.order_button)
        input_layout.addRow(self.start_button)
        input_group.setLayout(input_layout)

        output_layout = QVBoxLayout()
        self.price_label = QLabel("💰 Live Price: ---")
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        self.orders_table = QTableWidget(0, 6)
        self.orders_table.setHorizontalHeaderLabels(["Time", "Symbol", "Side", "Qty", "Price", "Status"])

        self.metrics_group = QGroupBox("📊 Performance Metrics")
        metrics_layout = QFormLayout()
        self.slippage_label = QLabel("---")
        self.fees_label = QLabel("---")
        self.impact_label = QLabel("---")
        self.net_cost_label = QLabel("---")
        self.maker_taker_label = QLabel("---")
        self.latency_label = QLabel("---")
        self.predicted_cost_label = QLabel("---")
        self.cost_bar = QProgressBar()
        self.cost_bar.setMinimum(0)
        self.cost_bar.setMaximum(1000)

        metrics_layout.addRow("Slippage:", self.slippage_label)
        metrics_layout.addRow("Fees:", self.fees_label)
        metrics_layout.addRow("Market Impact:", self.impact_label)
        metrics_layout.addRow("Net Cost:", self.net_cost_label)
        metrics_layout.addRow("Maker/Taker:", self.maker_taker_label)
        metrics_layout.addRow("Latency:", self.latency_label)
        metrics_layout.addRow("Predicted Cost:", self.predicted_cost_label)
        metrics_layout.addRow("Cost Visual:", self.cost_bar)
        self.metrics_group.setLayout(metrics_layout)

        output_layout.addWidget(self.price_label)
        output_layout.addWidget(self.log_output)
        output_layout.addWidget(self.orders_table)
        output_layout.addWidget(self.metrics_group)

        main_layout = QHBoxLayout()
        main_layout.addWidget(input_group)
        output_container = QWidget()
        output_container.setLayout(output_layout)
        main_layout.addWidget(output_container, stretch=2)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def place_order(self):
        try:
            start_time = time.perf_counter()
            symbol = self.symbol_input.text()
            side = self.side_input.currentText()
            quantity = self.qty_input.text()
            price = float(self.latest_price) if self.latest_price else 0.0

            if not symbol or not quantity or price == 0.0:
                self.append_log("❌ Invalid input.")
                return

            qty_float = float(quantity)
            if qty_float <= 0:
                self.append_log("❌ Quantity must be positive.")
                return

            row = self.orders_table.rowCount()
            self.orders_table.insertRow(row)
            self.orders_table.setItem(row, 0, QTableWidgetItem(time.strftime("%H:%M:%S")))
            self.orders_table.setItem(row, 1, QTableWidgetItem(symbol))
            self.orders_table.setItem(row, 2, QTableWidgetItem(side))
            self.orders_table.setItem(row, 3, QTableWidgetItem(quantity))
            self.orders_table.setItem(row, 4, QTableWidgetItem(f"{price:.2f}"))
            self.orders_table.setItem(row, 5, QTableWidgetItem("Pending"))

            self.reset_metrics_pending()
            QTimer.singleShot(1000, lambda: self.execute_order(row, qty_float, price, side, start_time))
        except Exception as e:
            self.append_log(f"❌ Error in placing order: {e}")

    def execute_order(self, row, quantity, order_price, side, start_time):
        try:
            if side.lower() == "buy":
                exec_price = float(self.top_ask_price) if self.top_ask_price else order_price
            else:
                exec_price = float(self.top_bid_price) if self.top_bid_price else order_price

            slippage = exec_price - order_price if side.lower() == "buy" else order_price - exec_price
            fee_map = {"Tier 1 (0.10%)": 0.0010, "Tier 2 (0.08%)": 0.0008, "Tier 3 (0.05%)": 0.0005}
            rate = fee_map[self.fee_input.currentText()]
            fees = exec_price * quantity * rate

            # Safeguard against fees exploding due to wrong quantity/price
            if fees > 0.1 * exec_price * quantity:
                self.append_log(f"⚠️ Warning: Fee unusually high. Check quantity input. Computed fee: {fees:.2f}")

            ac = AlmgrenChrissModel(X=quantity, N=10, sigma=self.volatility, eta=0.01, gamma=0.01, lambd=1e-6, T=1)
            impact_cost = ac.expected_cost()
            net_cost = slippage + fees + impact_cost
            latency_ms = (time.perf_counter() - start_time) * 1000

            spread = slippage / ((exec_price + order_price) / 2) if (exec_price + order_price) > 0 else 0
            maker_taker = "Maker" if self.model_mgr.predict_maker_taker(spread) == 1 else "Taker"

            time_of_day = float(time.strftime("%H")) / 24
            side_str = side.lower()
            predicted_cost = None
            if self.cost_model:
                try:
                    predicted_cost = self.cost_model.predict_cost(
                        quantity, exec_price, side_str, self.volatility, time_of_day
                    )
                except Exception as e:
                    self.append_log(f"❌ Prediction error: {e}")

            self.orders_table.setItem(row, 4, QTableWidgetItem(f"{exec_price:.2f}"))
            self.orders_table.setItem(row, 5, QTableWidgetItem("Executed"))

            self.slippage_label.setText(f"${slippage:.4f}")
            self.fees_label.setText(f"${fees:.4f}")
            self.impact_label.setText(f"${impact_cost:.4f}")
            self.net_cost_label.setText(f"${net_cost:.4f}")
            self.latency_label.setText(f"{latency_ms:.2f} ms")
            self.maker_taker_label.setText(maker_taker)
            if predicted_cost is not None:
                self.predicted_cost_label.setText(f"${predicted_cost:.4f}")
            self.cost_bar.setValue(min(int(net_cost), 1000))

            self.append_log(f"✅ Executed {side} {quantity} @ {exec_price:.2f}")

            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText(f"✅ Order Confirmed")
            msg.setInformativeText(f"{side} {quantity} units @ {exec_price:.2f}")
            msg.setWindowTitle("Trade Executed")
            msg.exec_()
        except Exception as e:
            self.append_log(f"❌ Execution error: {e}")

    def reset_metrics_pending(self):
        self.slippage_label.setText("---")
        self.fees_label.setText("---")
        self.impact_label.setText("---")
        self.net_cost_label.setText("---")
        self.maker_taker_label.setText("---")
        self.latency_label.setText("---")
        self.predicted_cost_label.setText("---")
        self.cost_bar.setValue(0)

    def start_ws(self):
        self.append_log("🔌 Connecting to GoQuant WebSocket...")
        thread = threading.Thread(target=self.run_ws_thread)
        thread.daemon = True
        thread.start()

    def run_ws_thread(self):
        asyncio.run(self.websocket_loop())

    async def websocket_loop(self):
        url = "wss://ws.gomarket-cpp.goquant.io/ws/l2-orderbook/okx/BTC-USDT-SWAP"
        try:
            async with websockets.connect(url, ping_interval=10, ping_timeout=5) as ws:
                self.append_log("📡 Subscribed to GoQuant orderbook")
                while True:
                    message = await ws.recv()
                    data = json.loads(message)
                    self.top_bid_price = float(data["bids"][0][0])
                    self.top_ask_price = float(data["asks"][0][0])
                    mid_price = (self.top_bid_price + self.top_ask_price) / 2

                    self.latest_price = f"{mid_price:.2f}"
                    self.update_price_signal.emit(self.latest_price)

                    self.price_history.append(mid_price)
                    if len(self.price_history) > 10:
                        log_returns = np.diff(np.log(self.price_history))
                        self.volatility = np.std(log_returns)

        except Exception as e:
            self.append_log(f"❌ WebSocket error: {e}")

    def append_log(self, text):
        self.log_output.append(text)

    def update_price_label(self, price):
        self.price_label.setText(f"💰 Live Price: {price}")