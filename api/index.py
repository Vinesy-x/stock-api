# -*- coding: utf-8 -*-
from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone

# 北京时间 UTC+8
CST = timezone(timedelta(hours=8))
import re

# 股票�?STOCK_POOL = {
    '002174': '游族网络', '002517': '恺英网络', '002555': '三七互娱',
    '002558': '巨人网络', '002292': '奥飞娱乐', '603258': '电魂网络',
    '002460': '赣锋锂业', '002466': '天齐锂业', '600995': '南网储能',
    '601222': '林洋能源', '600905': '三峡能源', '002240': '盛新锂能',
    '600570': '恒生电子', '600877': '电科芯片', '603068': '博通集�?,
    '002138': '顺络电子', '603678': '火炬电子', '601231': '环旭电子',
    '000425': '徐工机械', '002031': '巨轮智能', '601615': '明阳智能',
    '002097': '山河智能', '603011': '合锻智能', '000977': '浪潮信息',
    '000988': '华工科技', '002230': '科大讯飞', '600588': '用友网络',
    '000555': '神州信息', '000733': '振华科技',
}

SHORT_MA = 5
LONG_MA = 20
RSI_PERIOD = 14
INITIAL_CAPITAL = 100000
POSITION_SIZE = 0.1
MAX_POSITIONS = 5

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
            'code': code, 'name': data[0], 'price': price,
            'change_pct': change_pct, 'volume': int(float(data[8])) if data[8] else 0,
        }
    return quotes

def get_history(code, days=90):
    symbol = get_sina_symbol(code)
    url = f'http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={symbol}&scale=240&ma=no&datalen={days}'
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        return data if data else None
    except:
        return None

def calculate_rsi(closes, period=14):
    if len(closes) < period + 1:
        return [50] * len(closes)
    rsi = [50] * period
    gains = losses = 0
    for i in range(1, period + 1):
        diff = closes[i] - closes[i-1]
        if diff > 0: gains += diff
        else: losses -= diff
    avg_gain = gains / period
    avg_loss = losses / period
    rs = avg_gain / avg_loss if avg_loss != 0 else 100
    rsi.append(100 - 100 / (1 + rs))
    for i in range(period + 1, len(closes)):
        diff = closes[i] - closes[i-1]
        gain = diff if diff > 0 else 0
        loss = -diff if diff < 0 else 0
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        rs = avg_gain / avg_loss if avg_loss != 0 else 100
        rsi.append(100 - 100 / (1 + rs))
    return rsi

def run_backtest(start_date, end_date):
    all_data = {}
    for code in STOCK_POOL:
        hist = get_history(code)
        if hist and len(hist) >= LONG_MA + 5:
            closes = [float(d['close']) for d in hist]
            ma_short = [None] * (SHORT_MA - 1) + [sum(closes[i-SHORT_MA+1:i+1])/SHORT_MA for i in range(SHORT_MA-1, len(closes))]
            ma_long = [None] * (LONG_MA - 1) + [sum(closes[i-LONG_MA+1:i+1])/LONG_MA for i in range(LONG_MA-1, len(closes))]
            rsi = calculate_rsi(closes, RSI_PERIOD)
            all_data[code] = [{
                'date': d['day'], 'close': float(d['close']),
                'ma_short': ma_short[i], 'ma_long': ma_long[i], 'rsi': rsi[i]
            } for i, d in enumerate(hist)]
    
    trading_days = []
    if all_data:
        sample = list(all_data.values())[0]
        for d in sample:
            dt = d['date'][:10]
            if start_date <= dt <= end_date:
                trading_days.append(dt)
    
    cash = INITIAL_CAPITAL
    positions = {}
    trades = []
    daily_values = []
    
    for day_idx, date in enumerate(trading_days):
        pos_value = 0
        for code, pos in positions.items():
            if code in all_data:
                for d in all_data[code]:
                    if d['date'][:10] == date:
                        pos_value += pos['shares'] * d['close']
                        break
        total_value = cash + pos_value
        daily_values.append({
            'date': date, 'total_value': round(total_value, 2),
            'cash': round(cash, 2), 'position_value': round(pos_value, 2),
            'profit': round(total_value - INITIAL_CAPITAL, 2),
            'profit_pct': round((total_value / INITIAL_CAPITAL - 1) * 100, 2)
        })
        
        if day_idx == 0:
            continue
        
        for code, data in all_data.items():
            today = prev = None
            for i, d in enumerate(data):
                if d['date'][:10] == date:
                    today = d
                    prev = data[i-1] if i > 0 else None
                    break
            if not today or not prev or prev['ma_short'] is None or prev['ma_long'] is None:
                continue
            
            # Sell signal
            if code in positions:
                sell = False
                reason = ''
                if prev['ma_short'] >= prev['ma_long'] and today['ma_short'] < today['ma_long']:
                    sell, reason = True, 'MA死叉'
                elif today['rsi'] > 80:
                    sell, reason = True, 'RSI超买'
                if sell:
                    pos = positions[code]
                    amount = pos['shares'] * today['close']
                    profit = (today['close'] - pos['cost']) * pos['shares']
                    now = datetime.now(CST)
                    trade_time = f"{date} {9 + (day_idx % 4)}:{30 + (len(trades) * 7) % 30:02d}"
                    trades.append({
                        'datetime': trade_time, 'action': 'sell', 'code': code,
                        'name': STOCK_POOL.get(code, ''), 'price': round(today['close'], 2),
                        'shares': pos['shares'], 'amount': round(amount, 2),
                        'profit': round(profit, 2), 'reason': reason
                    })
                    cash += amount
                    del positions[code]
            
            # Buy signal
            elif len(positions) < MAX_POSITIONS:
                if prev['ma_short'] <= prev['ma_long'] and today['ma_short'] > today['ma_long'] and today['rsi'] < 70:
                    buy_amount = cash * POSITION_SIZE
                    shares = int(buy_amount / today['close'] / 100) * 100
                    if shares >= 100 and cash >= shares * today['close']:
                        cost = shares * today['close']
                        trade_time = f"{date} {9 + (day_idx % 4)}:{30 + (len(trades) * 7) % 30:02d}"
                        trades.append({
                            'datetime': trade_time, 'action': 'buy', 'code': code,
                            'name': STOCK_POOL.get(code, ''), 'price': round(today['close'], 2),
                            'shares': shares, 'amount': round(cost, 2),
                            'profit': 0, 'reason': 'MA金叉'
                        })
                        cash -= cost
                        positions[code] = {'shares': shares, 'cost': today['close'], 'name': STOCK_POOL.get(code, '')}
    
    final_positions = []
    for code, pos in positions.items():
        current_price = pos['cost']
        if code in all_data and all_data[code]:
            current_price = all_data[code][-1]['close']
        profit = (current_price - pos['cost']) * pos['shares']
        final_positions.append({
            'code': code, 'name': pos['name'], 'shares': pos['shares'],
            'cost': round(pos['cost'], 2), 'current_price': round(current_price, 2),
            'profit': round(profit, 2), 'profit_pct': round((current_price/pos['cost']-1)*100, 2)
        })
    
    final_value = daily_values[-1]['total_value'] if daily_values else INITIAL_CAPITAL
    return {
        'initial_capital': INITIAL_CAPITAL,
        'final_value': final_value,
        'total_profit': round(final_value - INITIAL_CAPITAL, 2),
        'total_return': round((final_value / INITIAL_CAPITAL - 1) * 100, 2),
        'trades': trades,
        'daily_values': daily_values,
        'positions': final_positions,
        'trade_count': len(trades),
        'buy_count': len([t for t in trades if t['action'] == 'buy']),
        'sell_count': len([t for t in trades if t['action'] == 'sell']),
    }

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        path = self.path.split('?')[0]
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        
        if path == '/api/backtest' or 'start' in query:
            start = query.get('start', ['2026-02-02'])[0]
            end = query.get('end', [datetime.now(CST).strftime('%Y-%m-%d')])[0]
            data = run_backtest(start, end)
        else:
            quotes = get_quotes()
            stocks = sorted(quotes.values(), key=lambda x: x['change_pct'], reverse=True)
            buy_signals = [s for s in stocks if s['change_pct'] > 3][:3]
            sell_signals = [s for s in stocks if s['change_pct'] < -2][:3]
            data = {
                'update_time': datetime.now(CST).strftime('%Y-%m-%d %H:%M:%S'),
                'stocks': stocks, 'buy_signals': buy_signals, 'sell_signals': sell_signals,
            }
        
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
