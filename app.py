from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import requests  # 💡 確保有這行
from bs4 import BeautifulSoup  # 💡 確保有這行
import os  # 這行沒有！

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
            return jsonify({
                'error': '请提供股票代号 (symbol 参数)'
            }), 400
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        stock = yf.Ticker(ticker)
        hist = stock.history(start=start_date, end=end_date)
        
        if hist.empty:
            return jsonify({
                'error': f'找不到股票代号: {ticker}'
            }), 404
        
 
# --- 🚀 基本面數據撈取 - FinMind 真正動態完全體（數據對齊觀測站） ---
        eps_current = 0.0
        eps_change_percent = 0.0
        company_name = ticker

        try:
            info = stock.info
            company_name = info.get('longName', ticker)
            
            # 🎯 判斷如果是台股 (.TW 或 .TWO)
            if ticker.endswith('.TW') or ticker.endswith('.TWO'):
                stock_id = ticker.split('.')[0]
                
                # 🌐 直連 FinMind 官方介面
                token = os.getenv("FINMIND_TOKEN")
                url = "https://api.finmindtrade.com/api/v4/data"
                parameter = {
                    "dataset": "TaiwanStockFinancialStatements",
                    "data_id": stock_id,
                    "start_date": (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d'), # 抓兩年內季報
                    "token": token
                }
                
                res = requests.get(url, params=parameter, timeout=5)
                if res.status_code == 200:
                    data_json = res.json()
                    if data_json.get('status') == 200 and data_json.get('data'):
                        df_fin = pd.DataFrame(data_json['data'])
                        
                        # 🎯 關鍵修正：FinMind 的欄位名稱叫 'EPS'，不是中文！
                        df_eps = df_fin[df_fin['type'] == 'EPS'].copy()
                        
                        if not df_eps.empty:
                            # 🚨 核心修正 1：強制把 value 欄位轉成數字型態，不然 Pandas 算不出總和！
                            df_eps['value'] = pd.to_numeric(df_eps['value'], errors='coerce')
                            
                            # 依時間由舊到新排序
                            df_eps = df_eps.sort_values('date')
                            
                            
                            # 💡 真正動態：加總最新 4 季的真實 EPS
                            latest_4 = df_eps.tail(4)
                            eps_current = float(latest_4['value'].sum())

                            # 計算前 4 季 EPS（年增率）
                            if len(df_eps) >= 8:
                                prev_4 = df_eps.iloc[-8:-4]
                                eps_prev = float(prev_4['value'].sum())
                                if eps_prev != 0:
                                    eps_change_percent = ((eps_current - eps_prev) / abs(eps_prev)) * 100
          
            else:
                # 🇺🇸 美股世界 (AAPL) 保持穩定動態計算
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
            print(f"🔥 FinMind 動態計算嚴重警告: {str(financial_err)}")

        # 精準格式化到小數點後兩位
        eps_current = round(float(eps_current), 2) if eps_current else 0.0
        eps_change_percent = round(float(eps_change_percent), 2) if eps_change_percent else 0.0
        # -------------------------------------------------------------------------

        
        hist['MA5'] = hist['Close'].rolling(window=5).mean()
        hist['MA20'] = hist['Close'].rolling(window=20).mean()
        hist['MA60'] = hist['Close'].rolling(window=60).mean()
        
        # 確保按時間排序（從舊到新）
        hist = hist.sort_index()
        
        # 過濾掉沒有成交量或缺失數據的日期
        hist = hist[hist['Volume'] > 0].dropna(subset=['Open', 'High', 'Low', 'Close'])
        
        candles = []
        for date, row in hist.iterrows():
            candle = {
                'time': date.strftime('%Y-%m-%d'),
                'open': round(float(row['Open']), 2),
                'high': round(float(row['High']), 2),
                'low': round(float(row['Low']), 2),
                'close': round(float(row['Close']), 2),
                'ma5': round(float(row['MA5']), 2) if pd.notna(row['MA5']) else None,
                'ma20': round(float(row['MA20']), 2) if pd.notna(row['MA20']) else None,
                'ma60': round(float(row['MA60']), 2) if pd.notna(row['MA60']) else None
            }
            candles.append(candle)
        
        data = {
            'symbol': ticker,
            'name': company_name,
            'eps': eps_current,                         # 💡 丟給前端：當前 EPS
            'eps_growth': eps_change_percent,           # 💡 丟給前端：EPS 年增率 %
            'candles': candles,
            'data_points': len(candles),
            'date_range': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            }
        }
        
        return jsonify(data), 200
    
    except Exception as e:
        return jsonify({
            'error': f'发生错误: {str(e)}'
        }), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)