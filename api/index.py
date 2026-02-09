# -*- coding: utf-8 -*-
from http.server import BaseHTTPRequestHandler
import json
from datetime import datetime, timedelta
import os

# 注意：Vercel 免费版不支持 jqdatasdk（需要长连接）
# 这里用模拟数据，后续可以改用 akshare 或其他免费数据源

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        # 模拟数据 - 后续接入真实数据源
        data = {
            "update_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "total_value": 106800,
            "cash_balance": 50000,
            "total_profit": 6800,
            "total_profit_percent": 6.8,
            "positions": [
                {
                    "code": "600519",
                    "name": "贵州茅台",
                    "shares": 10,
                    "cost_price": 1680,
                    "current_price": 1720,
                    "profit": 400,
                    "profit_percent": 2.38
                },
                {
                    "code": "000858",
                    "name": "五粮液",
                    "shares": 100,
                    "cost_price": 158,
                    "current_price": 162,
                    "profit": 400,
                    "profit_percent": 2.53
                }
            ],
            "signals": [
                {
                    "code": "002594",
                    "name": "比亚迪",
                    "signal": "buy",
                    "price": 245.5,
                    "rsi": 28,
                    "reason": "MA5上穿MA20 + RSI超卖反弹"
                },
                {
                    "code": "600036",
                    "name": "招商银行",
                    "signal": "buy",
                    "price": 35.2,
                    "rsi": 32,
                    "reason": "MA5上穿MA20 + 成交量放大"
                }
            ],
            "trades": [
                {
                    "id": "1",
                    "date": "2026-02-07",
                    "code": "600519",
                    "name": "贵州茅台",
                    "action": "buy",
                    "price": 1680,
                    "shares": 10,
                    "amount": 16800
                },
                {
                    "id": "2",
                    "date": "2026-02-06",
                    "code": "000858",
                    "name": "五粮液",
                    "action": "buy",
                    "price": 158,
                    "shares": 100,
                    "amount": 15800
                }
            ],
            "daily_values": [
                {"date": "02-01", "value": 100000},
                {"date": "02-02", "value": 101200},
                {"date": "02-03", "value": 99800},
                {"date": "02-04", "value": 102500},
                {"date": "02-05", "value": 103200},
                {"date": "02-06", "value": 104800},
                {"date": "02-07", "value": 103500},
                {"date": "02-08", "value": 105200},
                {"date": "02-09", "value": 106800}
            ]
        }
        
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
        return
