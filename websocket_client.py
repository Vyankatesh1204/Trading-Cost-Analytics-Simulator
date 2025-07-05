#websocket_client.py
import asyncio
import websockets
import json
import time
import os
import csv
from models import ModelManager

WS_URL = "wss://ws.gomarket-cpp.goquant.io/ws/l2-orderbook/okx/BTC-USDT-SWAP"

class WebSocketTrader:
    def __init__(self):
        self.model_manager = ModelManager()
        self.executed_trades = []

    async def connect_websocket(self):
        while True:
            try:
                async with websockets.connect(WS_URL) as websocket:
                    print("✅ Connected to WebSocket")
                    while True:
                        msg = await websocket.recv()
                        data = json.loads(msg)
                        self.process_orderbook(data)

            except websockets.ConnectionClosed:
                print("🔌 Connection closed, reconnecting in 2 seconds...")
                await asyncio.sleep(2)

            except Exception as e:
                print(f"⚠️ Error: {e}")
                await asyncio.sleep(1)

    def process_orderbook(self, data):
        timestamp = data.get("timestamp")
        exchange = data.get("exchange")
        symbol = data.get("symbol")
        asks = data.get("asks", [])
        bids = data.get("bids", [])

        if not asks or not bids:
            print("⚠️ Orderbook missing data.")
            return

        top_ask_price, top_ask_qty = asks[0]
        top_bid_price, top_bid_qty = bids[0]
        mid_price = (top_ask_price + top_bid_price) / 2
        price_impact_ratio = abs(top_ask_price - top_bid_price) / mid_price

        # 🧠 Predict maker/taker
        prediction = self.model_manager.predict_maker_taker(price_impact_ratio)
        maker_taker = "maker" if prediction == 1 else "taker"

        # 🧠 Strategy: Buy if spread < 0.1%
        spread = (top_ask_price - top_bid_price) / mid_price
        decision = "buy" if spread < 0.001 else "skip"

        if decision == "buy":
            trade = {
                "timestamp": timestamp,
                "exchange": exchange,
                "symbol": symbol,
                "action": decision,
                "maker_taker": maker_taker,
                "price": top_ask_price,
                "qty": top_ask_qty,
                "impact_ratio": price_impact_ratio
            }
            self.executed_trades.append(trade)
            print(f"🟢 Executed Trade: {trade}")
            self.save_trade_to_csv(trade)
        else:
            print("⏸️ Skipped trade due to spread")

    def save_trade_to_csv(self, trade, filename="executed_trades.csv"):
        file_exists = os.path.isfile(filename)
        with open(filename, mode='a', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=trade.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(trade)

# 🚀 Main entry point
if __name__ == "__main__":
    trader = WebSocketTrader()
    asyncio.run(trader.connect_websocket())
