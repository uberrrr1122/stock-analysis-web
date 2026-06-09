from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import requests
import os

app = Flask(__name__)
CORS(app)


@app.route('/')
def home():
    return render_template('index.html', title='首页')


@app.route('/about')
def about():
    return render_template('about.html', title='关于我们')


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

        # --- 基本面數據 ---
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

        # --- K 線數據 ---
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
        start_date = end_date - timedelta(days=60)  # 多抓保險，取最近30交易日

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
        print("FinMind name 欄位有：", df['name'].unique())

        # 整理三大法人每天買賣超
        name_map = {
            'Foreign_Investor': 'foreign',
            'Investment_Trust': 'trust',
            'Dealer_self':      'dealer',
            'Dealer_Hedging':   'dealer'   # 自營商兩個都加到 dealer
        }
        unit_map = {
            'Foreign_Investor': 1000,
            'Investment_Trust': 1000,
            'Dealer_self':      1000,
            'Dealer_Hedging':   1000
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
                divisor = unit_map.get(eng, 1)
                result[d][key] += int(row['net'] // 1000)

        records = sorted(result.values(), key=lambda x: x['date'])

        return jsonify({'symbol': ticker, 'data': records}), 200

    except Exception as e:
        return jsonify({'error': f'發生錯誤: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
