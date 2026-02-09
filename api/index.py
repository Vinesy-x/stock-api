# -*- coding: utf-8 -*-
from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import time
from datetime import datetime

# 股票池
STOCK_POOL = {
    '002174': '游族网络', '002517': '恺英网络', '002555': '三七互娱',
    '002558': '巨人网络', '002292': '奥飞娱乐', '603258': '电魂网络',
    '002460': '赣锋锂业', '002466': '天齐锂业', '600995': '南网储能',
    '601222': '林洋能源', '600905': '三峡能源', '002240': '盛新锂能',
    '600570': '恒生电子', '600877': '电科芯片', '603068': '博通集成',
    '002138': '顺络电子', '603678': '火炬电子', '601231': '环旭电子',
    '000425': '徐工机械', '002031': '巨轮智能', '601615': '明阳智能',
    '002097': '山河智能', '603011': '合锻智能', '000977': '浪潮信息',
    '000988': '华工科技', '002230': '科大讯飞', '600588': '用友网络',
    '000555': '神州信息', '000733': '振华科技',
}

def get_sina_symbol(code):
    return f'sh{code}' if code.startswith('6') else f'sz{code}'

def get_quotes():
    symbols = ','.join([get_sina_symbol(c) for c in STOCK_POOL.keys()])
    url = f'http://hq.sinajs.cn/list={symbols}'
    
    req = urllib.request.Request(url, headers={'Referer': 'http://finance.sina.com.cn'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            text = resp.read().decode('gbk')
    except:
        return {}
    
    quotes = {}
    for line in text.strip().split('\n'):
        if '=' not in line:
            continue
        parts = line.split('=')
        code = parts[0].split('_')[-1][2:]
        data = parts[1].strip('"').split(',')
        if len(data) < 10 or not data[3]:
            continue
        
        prev_close = float(data[2]) if data[2] else 0
        price = float(data[3])
        change_pct = round((price - prev_close) / prev_close * 100, 2) if prev_close else 0
        
        quotes[code] = {
            'code': code,
            'name': data[0],
            'price': price,
            'change_pct': change_pct,
            'high': float(data[4]) if data[4] else 0,
            'low': float(data[5]) if data[5] else 0,
            'volume': int(float(data[8])) if data[8] else 0,
        }
    return quotes

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        quotes = get_quotes()
        stocks = sorted(quotes.values(), key=lambda x: x['change_pct'], reverse=True)
        
        # 模拟信号（实际需要历史数据计算）
        buy_signals = [s for s in stocks if s['change_pct'] > 3][:3]
        sell_signals = [s for s in stocks if s['change_pct'] < -2][:3]
        
        data = {
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_value': 100000,
            'cash_balance': 50000,
            'stocks': stocks,
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
            'positions': [],
            'trades': [],
            'daily_values': []
        }
        
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
