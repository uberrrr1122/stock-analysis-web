from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import requests
import os

app = Flask(__name__)
CORS(app)

# 台股常用股票清單
TAIWAN_STOCKS = [
    {"code": "0050",  "name": "元大台灣50"},
    {"code": "0056",  "name": "元大高股息"},
    {"code": "00878", "name": "國泰永續高股息"},
    {"code": "1101",  "name": "台泥"},
    {"code": "1216",  "name": "統一"},
    {"code": "1301",  "name": "台塑"},
    {"code": "1303",  "name": "南亞"},
    {"code": "1326",  "name": "台化"},
    {"code": "1402",  "name": "遠東新"},
    {"code": "2002",  "name": "中鋼"},
    {"code": "2207",  "name": "和泰車"},
    {"code": "2301",  "name": "光寶科"},
    {"code": "2303",  "name": "聯電"},
    {"code": "2308",  "name": "台達電"},
    {"code": "2317",  "name": "鴻海"},
    {"code": "2327",  "name": "國巨"},
    {"code": "2330",  "name": "台積電"},
    {"code": "2345",  "name": "智邦"},
    {"code": "2347",  "name": "聯強"},
    {"code": "2357",  "name": "華碩"},
    {"code": "2379",  "name": "瑞昱"},
    {"code": "2382",  "name": "廣達"},
    {"code": "2395",  "name": "研華"},
    {"code": "2408",  "name": "南亞科"},
    {"code": "2409",  "name": "友達"},
    {"code": "2412",  "name": "中華電"},
    {"code": "2454",  "name": "聯發科"},
    {"code": "2474",  "name": "可成"},
    {"code": "2476",  "name": "技嘉"},
    {"code": "2498",  "name": "宏達電"},
    {"code": "2603",  "name": "長榮"},
    {"code": "2609",  "name": "陽明"},
    {"code": "2615",  "name": "萬海"},
    {"code": "2618",  "name": "長榮航"},
    {"code": "2633",  "name": "台灣高鐵"},
    {"code": "2880",  "name": "華南金"},
    {"code": "2881",  "name": "富邦金"},
    {"code": "2882",  "name": "國泰金"},
    {"code": "2883",  "name": "開發金"},
    {"code": "2884",  "name": "玉山金"},
    {"code": "2885",  "name": "元大金"},
    {"code": "2886",  "name": "兆豐金"},
    {"code": "2887",  "name": "台新金"},
    {"code": "2888",  "name": "新光金"},
    {"code": "2890",  "name": "永豐金"},
    {"code": "2891",  "name": "中信金"},
    {"code": "2892",  "name": "第一金"},
    {"code": "2912",  "name": "統一超"},
    {"code": "3008",  "name": "大立光"},
    {"code": "3034",  "name": "聯詠"},
    {"code": "3037",  "name": "欣興"},
    {"code": "3045",  "name": "台灣大"},
    {"code": "3231",  "name": "緯創"},
    {"code": "3443",  "name": "創意"},
    {"code": "3481",  "name": "群創"},
    {"code": "3711",  "name": "日月光投控"},
    {"code": "4904",  "name": "遠傳"},
    {"code": "4938",  "name": "和碩"},
    {"code": "5871",  "name": "中租-KY"},
    {"code": "5876",  "name": "上海商銀"},
    {"code": "5880",  "name": "合庫金"},
    {"code": "6446",  "name": "藥華藥"},
    {"code": "6505",  "name": "台塑化"},
    {"code": "6669",  "name": "緯穎"},
    {"code": "6770",  "name": "力積電"},
    {"code": "8046",  "name": "南電"},
]

US_STOCKS = [
    {"symbol": "AAPL",  "name": "Apple"},
    {"symbol": "MSFT",  "name": "Microsoft"},
    {"symbol": "GOOGL", "name": "Google"},
    {"symbol": "AMZN",  "name": "Amazon"},
    {"symbol": "NVDA",  "name": "NVIDIA"},
    {"symbol": "META",  "name": "Meta"},
    {"symbol": "TSLA",  "name": "Tesla"},
    {"symbol": "TSM",   "name": "TSMC ADR"},
    {"symbol": "AVGO",  "name": "Broadcom"},
    {"symbol": "AMD",   "name": "AMD"},
    {"symbol": "INTC",  "name": "Intel"},
    {"symbol": "QCOM",  "name": "Qualcomm"},
]


@app.route('/')
def home():
    return render_template('index.html', title='首页')


@app.route('/about')
def about():
    return render_template('about.html', title='关于我们')


@app.route('/api/search', methods=['GET'])
def search_stock():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])

    query_lower = query.lower()
    results = []

    for stock in TAIWAN_STOCKS:
        code = stock['code']
        name = stock['name']
        if query_lower in code or query_lower in name:
            results.append({
                'symbol': f"{code}.TW",
                'display': f"{code} - {name}"
            })

    for stock in US_STOCKS:
        if query_lower in stock['symbol'].lower() or query_lower in stock['name'].lower():
            results.append({
                'symbol': stock['symbol'],
                'display': f"{stock['symbol']} - {stock['name']}"
            })

    return jsonify(results[:10])


@app.route('/api/stock', methods=['GET'])
def get_stock_data():
    try:
        ticker = request.args.get('symbol')

        if not ticker:
            return jsonify({'error': '请提供股票代号 (symbol 参数)'}), 400

        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)

        stock = yf.Ticker(ticker)
        hist = stock.history(start=start_date, end=end_date)

        if hist.empty:
            return jsonify({'error': f'找不到股票代号: {ticker}'}), 404

        eps_current = 0.0
        eps_change_percent = 0.0
        company_name = ticker

        try:
            info = stock.info
            company_name = info.get('longName', ticker)

            if ticker.endswith('.TW') or ticker.endswith('.TWO'):
                stock_id = ticker.split('.')[0]
                token = os.getenv("FINMIND_TOKEN")

                res = requests.get("https://api.finmindtrade.com/api/v4/data", params={
                    "dataset": "TaiwanStockFinancialStatements",
                    "data_id": stock_id,
                    "start_date": (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d'),
                    "token": token
                }, timeout=5)

                if res.status_code == 200:
                    data_json = res.json()
                    if data_json.get('status') == 200 and data_json.get('data'):
                        df_fin = pd.DataFrame(data_json['data'])
                        df_eps = df_fin[df_fin['type'] == 'EPS'].copy()

                        if not df_eps.empty:
                            df_eps['value'] = pd.to_numeric(df_eps['value'], errors='coerce')
                            df_eps = df_eps.sort_values('date')

                            latest_4 = df_eps.tail(4)
                            eps_current = float(latest_4['value'].sum())

                            if len(df_eps) >= 8:
                                prev_4 = df_eps.iloc[-8:-4]
                                eps_prev = float(prev_4['value'].sum())
                                if eps_prev != 0:
                                    eps_change_percent = ((eps_current - eps_prev) / abs(eps_prev)) * 100

            else:
                q_financials = stock.quarterly_financials
                if q_financials is not None and not q_financials.empty:
                    eps_rows = [idx for idx in q_financials.index if 'Basic EPS' in str(idx)]
                    if eps_rows:
                        latest_data = q_financials.loc[eps_rows[0]].dropna()
                        if len(latest_data) >= 4:
                            eps_current = sum(latest_data.iloc[:4])
                            eps_prev = sum(latest_data.iloc[4:8]) if len(latest_data) >= 8 else 0.0
                            if eps_prev != 0:
                                eps_change_percent = ((eps_current - eps_prev) / abs(eps_prev)) * 100

        except Exception as financial_err:
            print(f"基本面計算警告: {str(financial_err)}")

        eps_current = round(float(eps_current), 2) if eps_current else 0.0
        eps_change_percent = round(float(eps_change_percent), 2) if eps_change_percent else 0.0

        hist['MA5'] = hist['Close'].rolling(window=5).mean()
        hist['MA20'] = hist['Close'].rolling(window=20).mean()
        hist['MA60'] = hist['Close'].rolling(window=60).mean()
        hist = hist.sort_index()
        hist = hist[hist['Volume'] > 0].dropna(subset=['Open', 'High', 'Low', 'Close'])

        candles = []
        for date, row in hist.iterrows():
            candles.append({
                'time': date.strftime('%Y-%m-%d'),
                'open': round(float(row['Open']), 2),
                'high': round(float(row['High']), 2),
                'low': round(float(row['Low']), 2),
                'close': round(float(row['Close']), 2),
                'ma5': round(float(row['MA5']), 2) if pd.notna(row['MA5']) else None,
                'ma20': round(float(row['MA20']), 2) if pd.notna(row['MA20']) else None,
                'ma60': round(float(row['MA60']), 2) if pd.notna(row['MA60']) else None
            })

        return jsonify({
            'symbol': ticker,
            'name': company_name,
            'eps': eps_current,
            'eps_growth': eps_change_percent,
            'candles': candles,
            'data_points': len(candles),
            'date_range': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            }
        }), 200

    except Exception as e:
        return jsonify({'error': f'发生错误: {str(e)}'}), 500


@app.route('/api/institutional', methods=['GET'])
def get_institutional_data():
    try:
        ticker = request.args.get('symbol')
        if not ticker:
            return jsonify({'error': '請提供股票代號'}), 400

        if not (ticker.endswith('.TW') or ticker.endswith('.TWO')):
            return jsonify({'error': '籌碼面資料僅支援台股'}), 400

        stock_id = ticker.split('.')[0]
        token = os.getenv("FINMIND_TOKEN")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)

        res = requests.get("https://api.finmindtrade.com/api/v4/data", params={
            "dataset": "TaiwanStockInstitutionalInvestorsBuySell",
            "data_id": stock_id,
            "start_date": start_date.strftime('%Y-%m-%d'),
            "token": token
        }, timeout=5)

        if res.status_code != 200:
            return jsonify({'error': 'FinMind API 請求失敗'}), 500

        data_json = res.json()
        if data_json.get('status') != 200 or not data_json.get('data'):
            return jsonify({'error': '查無籌碼資料'}), 404

        df = pd.DataFrame(data_json['data'])

        name_map = {
            'Foreign_Investor': 'foreign',
            'Investment_Trust': 'trust',
            'Dealer_self':      'dealer',
            'Dealer_Hedging':   'dealer'
        }

        result = {}
        for eng, key in name_map.items():
            sub = df[df['name'] == eng][['date', 'buy', 'sell']].copy()
            sub['net'] = pd.to_numeric(sub['buy'], errors='coerce') - pd.to_numeric(sub['sell'], errors='coerce')
            sub = sub.sort_values('date').tail(30)
            for _, row in sub.iterrows():
                d = row['date']
                if d not in result:
                    result[d] = {'date': d, 'foreign': 0, 'trust': 0, 'dealer': 0}
                result[d][key] += int(row['net'] // 1000)

        records = sorted(result.values(), key=lambda x: x['date'])
        return jsonify({'symbol': ticker, 'data': records}), 200

    except Exception as e:
        return jsonify({'error': f'發生錯誤: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
