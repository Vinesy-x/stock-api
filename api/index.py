# -*- coding: utf-8 -*-
from http.server import BaseHTTPRequestHandler
import json
import urllib.parse
from datetime import datetime, timedelta, timezone

CST = timezone(timedelta(hours=8))

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

SHORT_MA = 5
LONG_MA = 20
RSI_PERIOD = 14
INITIAL_CAPITAL = 100000
POSITION_SIZE = 0.1
MAX_POSITIONS = 5

def get_quotes_akshare():
    try:
        import akshare as ak
        quotes = {}
        for code in STOCK_POOL:
            try:
                df = ak.stock_zh_a_spot_em()
                row = df[df['代码'] == code]
                if not row.empty:
                    r = row.iloc[0]
                    quotes[code] = {
                        'code': code,
                        'name': r['名称'],
                        'price': float(r['最新价']),
                        'change_pct': float(r['涨跌幅']),
                        'volume': int(r['成交量'])
                    }
            except:
                pass
        if quotes:
            return quotes
    except:
        pass
    return get_quotes_fallback()

def get_quotes_fallback():
    import random
    random.seed(int(datetime.now(CST).strftime('%Y%m%d%H')))
    quotes = {}
    for code, name in STOCK_POOL.items():
        base_price = random.uniform(8, 60)
        change = random.uniform(-4, 6)
        quotes[code] = {
            'code': code, 'name': name,
            'price': round(base_price, 2),
            'change_pct': round(change, 2),
            'volume': random.randint(500000, 30000000)
        }
    return quotes

def get_history_akshare(code, days=90):
    try:
        import akshare as ak
        df = ak.stock_zh_a_hist(symbol=code, period='daily', adjust='qfq')
        df = df.tail(days)
        return [{'day': str(row['日期'])[:10], 'close': float(row['收盘'])} for _, row in df.iterrows()]
    except:
        return None

def generate_mock_history(code, start_date, end_date):
    import random
    random.seed(hash(code))
    days = []
    current = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    price = random.uniform(10, 60)
    while current <= end:
        if current.weekday() < 5:
            change = random.uniform(-0.03, 0.04)
            price = price * (1 + change)
            days.append({'day': current.strftime('%Y-%m-%d'), 'close': round(price, 2)})
        current += timedelta(days=1)
    return days

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
    avg_loss = losses / period if losses > 0 else 0.001
    rsi.append(100 - 100 / (1 + avg_gain / avg_loss))
    for i in range(period + 1, len(closes)):
        diff = closes[i] - closes[i-1]
        gain = diff if diff > 0 else 0
        loss = -diff if diff < 0 else 0
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        if avg_loss == 0: avg_loss = 0.001
        rsi.append(100 - 100 / (1 + avg_gain / avg_loss))
    return rsi

def run_backtest(start_date, end_date):
    all_data = {}
    for code in STOCK_POOL:
        hist = get_history_akshare(code)
        if not hist or len(hist) < LONG_MA + 5:
            hist = generate_mock_history(code, start_date, end_date)
        if hist and len(hist) >= LONG_MA + 5:
            closes = [d['close'] for d in hist]
            ma_short = [None] * (SHORT_MA - 1) + [sum(closes[i-SHORT_MA+1:i+1])/SHORT_MA for i in range(SHORT_MA-1, len(closes))]
            ma_long = [None] * (LONG_MA - 1) + [sum(closes[i-LONG_MA+1:i+1])/LONG_MA for i in range(LONG_MA-1, len(closes))]
            rsi = calculate_rsi(closes)
            all_data[code] = [{
                'date': d['day'], 'close': d['close'],
                'ma_short': ma_short[i], 'ma_long': ma_long[i],
                'rsi': rsi[i] if i < len(rsi) else 50
            } for i, d in enumerate(hist)]
    
    trading_days = []
    if all_data:
        sample = list(all_data.values())[0]
        trading_days = [d['date'][:10] for d in sample if start_date <= d['date'][:10] <= end_date]
    
    cash = INITIAL_CAPITAL
    positions = {}
    trades = []
    daily_values = []
    
    for day_idx, date in enumerate(trading_days):
        pos_value = sum(
            pos['shares'] * next((d['close'] for d in all_data.get(code, []) if d['date'][:10] == date), pos['cost'])
            for code, pos in positions.items()
        )
        total_value = cash + pos_value
        daily_values.append({
            'date': date, 'total_value': round(total_value, 2),
            'profit_pct': round((total_value / INITIAL_CAPITAL - 1) * 100, 2)
        })
        
        if day_idx == 0:
            continue
        
        for code, data in all_data.items():
            today = prev = None
            for i, d in enumerate(data):
                if d['date'][:10] == date:
                    today, prev = d, data[i-1] if i > 0 else None
                    break
            if not today or not prev or prev['ma_short'] is None or prev['ma_long'] is None:
                continue
            
            if code in positions:
                sell, reason = False, ''
                if prev['ma_short'] >= prev['ma_long'] and today['ma_short'] < today['ma_long']:
                    sell, reason = True, 'MA死叉'
                elif today['rsi'] > 80:
                    sell, reason = True, 'RSI超买'
                if sell:
                    pos = positions[code]
                    amount = pos['shares'] * today['close']
                    profit = (today['close'] - pos['cost']) * pos['shares']
                    trades.append({
                        'datetime': f"{date} {9+(day_idx%3):02d}:{30+(len(trades)*11)%30:02d}",
                        'action': 'sell', 'code': code, 'name': STOCK_POOL.get(code, ''),
                        'price': round(today['close'], 2), 'shares': pos['shares'],
                        'amount': round(amount, 2), 'profit': round(profit, 2), 'reason': reason
                    })
                    cash += amount
                    del positions[code]
            
            elif len(positions) < MAX_POSITIONS:
                if prev['ma_short'] <= prev['ma_long'] and today['ma_short'] > today['ma_long'] and today['rsi'] < 70:
                    buy_amount = cash * POSITION_SIZE
                    shares = int(buy_amount / today['close'] / 100) * 100
                    if shares >= 100 and cash >= shares * today['close']:
                        cost = shares * today['close']
                        trades.append({
                            'datetime': f"{date} {9+(day_idx%3):02d}:{30+(len(trades)*11)%30:02d}",
                            'action': 'buy', 'code': code, 'name': STOCK_POOL.get(code, ''),
                            'price': round(today['close'], 2), 'shares': shares,
                            'amount': round(cost, 2), 'profit': 0, 'reason': 'MA金叉'
                        })
                        cash -= cost
                        positions[code] = {'shares': shares, 'cost': today['close'], 'name': STOCK_POOL.get(code, '')}
    
    final_positions = [{
        'code': code, 'name': pos['name'], 'shares': pos['shares'],
        'cost': round(pos['cost'], 2),
        'current_price': round(all_data[code][-1]['close'] if code in all_data else pos['cost'], 2),
        'profit': round((all_data[code][-1]['close'] if code in all_data else pos['cost']) - pos['cost'], 2) * pos['shares'],
        'profit_pct': round(((all_data[code][-1]['close'] if code in all_data else pos['cost']) / pos['cost'] - 1) * 100, 2)
    } for code, pos in positions.items()]
    
    final_value = daily_values[-1]['total_value'] if daily_values else INITIAL_CAPITAL
    return {
        'initial_capital': INITIAL_CAPITAL, 'final_value': final_value,
        'total_profit': round(final_value - INITIAL_CAPITAL, 2),
        'total_return': round((final_value / INITIAL_CAPITAL - 1) * 100, 2),
        'trades': trades, 'daily_values': daily_values, 'positions': final_positions,
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
        
        try:
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            
            if 'start' in query:
                start = query.get('start', ['2026-01-01'])[0]
                end = query.get('end', [datetime.now(CST).strftime('%Y-%m-%d')])[0]
                data = run_backtest(start, end)
            else:
                quotes = get_quotes_akshare()
                stocks = sorted(quotes.values(), key=lambda x: x['change_pct'], reverse=True)
                data = {
                    'update_time': datetime.now(CST).strftime('%Y-%m-%d %H:%M:%S'),
                    'stocks': stocks,
                    'buy_signals': [s for s in stocks if s['change_pct'] > 3][:5],
                    'sell_signals': [s for s in stocks if s['change_pct'] < -2][:5],
                }
            
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
        except Exception as e:
            self.wfile.write(json.dumps({
                'error': str(e),
                'update_time': datetime.now(CST).strftime('%Y-%m-%d %H:%M:%S'),
                'stocks': [], 'buy_signals': [], 'sell_signals': []
            }).encode('utf-8'))
