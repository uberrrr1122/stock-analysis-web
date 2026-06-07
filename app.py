from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta
import yfinance as yf

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
        start_date = end_date - timedelta(days=30)
        
        stock = yf.Ticker(ticker)
        hist = stock.history(start=start_date, end=end_date)
        
        if hist.empty:
            return jsonify({
                'error': f'找不到股票代号: {ticker}'
            }), 404
        
        candles = []
        for date, row in hist.iterrows():
            candle = {
                'time': date.strftime('%Y-%m-%d'),
                'open': round(float(row['Open']), 2),
                'high': round(float(row['High']), 2),
                'low': round(float(row['Low']), 2),
                'close': round(float(row['Close']), 2)
            }
            candles.append(candle)
        
        data = {
            'symbol': ticker,
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
