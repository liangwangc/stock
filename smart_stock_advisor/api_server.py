"""
简单的API服务器，提供股票预测数据接口
"""
import os
import sys
import json
import pandas as pd
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import webbrowser

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

class StockAPIHandler(BaseHTTPRequestHandler):
    """处理股票数据API请求"""
    
    def do_GET(self):
        """处理GET请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # CORS头
        self.send_cors_headers()
        
        if path == '/api/stocks':
            # 返回股票列表数据
            self.handle_get_stocks()
        elif path == '/api/stock':
            # 返回单个股票数据
            query_params = parse_qs(parsed_path.query)
            symbol = query_params.get('symbol', [None])[0]
            self.handle_get_stock(symbol)
        elif path.startswith('/'):
            # 静态文件服务
            self.handle_static_file(path)
        else:
            self.send_error(404, "Not Found")
    
    def send_cors_headers(self):
        """发送CORS头"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    
    def handle_get_stocks(self):
        """获取股票列表"""
        try:
            # 尝试使用数据库
            records = []
            try:
                from utils.stock_prediction_db import StockPredictionDB
                from config_db import USE_DATABASE
                
                if USE_DATABASE:
                    db = StockPredictionDB()
                    records = db.get_latest_predictions(limit=1000)
            except Exception as e:
                print(f"数据库读取失败，回退到CSV: {str(e)}")
            
            # CSV模式（如果数据库不可用或未启用）
            if not records:
                csv_file = os.path.join(project_root, 'stock_predictions.csv')
                
                if not os.path.exists(csv_file):
                    self.send_json_response({'success': False, 'message': 'CSV文件不存在', 'data': []})
                    return
                
                # 读取CSV
                df = pd.read_csv(csv_file, dtype={'symbol': str}, encoding='utf-8-sig')
                
                # 转换为字典列表
                for _, row in df.iterrows():
                    record = {}
                    for col in df.columns:
                        value = row[col]
                        if pd.isna(value):
                            if col in ['current_price', 'up_probability', 'down_probability', 'confidence']:
                                value = 0
                            else:
                                value = ''
                        elif col in ['current_price', 'up_probability', 'down_probability', 'confidence']:
                            try:
                                value = float(value)
                            except (ValueError, TypeError):
                                value = 0
                        record[col] = value
                    records.append(record)
                
                # 获取最新的记录（每个股票只保留最新的一条）
                latest_records = {}
                for record in records:
                    symbol = str(record.get('symbol', '')).strip()
                    if not symbol:
                        continue
                    
                    prediction_time = record.get('prediction_time', '')
                    if symbol not in latest_records or prediction_time > latest_records[symbol].get('prediction_time', ''):
                        latest_records[symbol] = record
                
                records = list(latest_records.values())
            
            self.send_json_response({
                'success': True,
                'data': records,
                'total': len(records)
            })
            
        except Exception as e:
            self.send_json_response({
                'success': False,
                'message': str(e),
                'data': []
            })
    
    def handle_get_stock(self, symbol):
        """获取单个股票数据"""
        try:
            if not symbol:
                self.send_json_response({'success': False, 'message': '缺少股票代码参数'})
                return
            
            # 尝试使用数据库
            records = []
            try:
                from utils.stock_prediction_db import StockPredictionDB
                from config_db import USE_DATABASE
                
                if USE_DATABASE:
                    db = StockPredictionDB()
                    records = db.get_predictions(symbol=symbol)
            except Exception as e:
                print(f"数据库读取失败，回退到CSV: {str(e)}")
            
            # CSV模式（如果数据库不可用或未启用）
            if not records:
                csv_file = os.path.join(project_root, 'stock_predictions.csv')
                
                if not os.path.exists(csv_file):
                    self.send_json_response({'success': False, 'message': 'CSV文件不存在'})
                    return
                
                # 读取CSV
                df = pd.read_csv(csv_file, dtype={'symbol': str}, encoding='utf-8-sig')
                
                # 筛选股票
                stock_df = df[df['symbol'] == str(symbol).strip()]
                
                if stock_df.empty:
                    self.send_json_response({'success': False, 'message': '未找到该股票数据'})
                    return
                
                # 转换为字典列表
                for _, row in stock_df.iterrows():
                    record = {}
                    for col in stock_df.columns:
                        value = row[col]
                        if pd.isna(value):
                            if col in ['current_price', 'up_probability', 'down_probability', 'confidence']:
                                value = 0
                            else:
                                value = ''
                        elif col in ['current_price', 'up_probability', 'down_probability', 'confidence']:
                            try:
                                value = float(value)
                            except (ValueError, TypeError):
                                value = 0
                        record[col] = value
                    records.append(record)
            
            if not records:
                self.send_json_response({'success': False, 'message': '未找到该股票数据'})
                return
            
            self.send_json_response({
                'success': True,
                'data': records
            })
            
        except Exception as e:
            self.send_json_response({
                'success': False,
                'message': str(e)
            })
    
    def handle_static_file(self, path):
        """处理静态文件请求"""
        try:
            if path == '/':
                path = '/stock_list.html'
            
            file_path = os.path.join(project_root, path.lstrip('/'))
            
            if not os.path.exists(file_path):
                self.send_error(404, "File Not Found")
                return
            
            # 读取文件
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # 确定MIME类型
            if file_path.endswith('.html'):
                content_type = 'text/html; charset=utf-8'
            elif file_path.endswith('.css'):
                content_type = 'text/css'
            elif file_path.endswith('.js'):
                content_type = 'application/javascript'
            elif file_path.endswith('.json'):
                content_type = 'application/json'
            elif file_path.endswith('.csv'):
                content_type = 'text/csv'
            else:
                content_type = 'application/octet-stream'
            
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(content)
            
        except Exception as e:
            self.send_error(500, f"Internal Server Error: {str(e)}")
    
    def send_json_response(self, data):
        """发送JSON响应"""
        json_data = json.dumps(data, ensure_ascii=False, indent=2)
        json_bytes = json_data.encode('utf-8')
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(json_bytes)))
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(json_bytes)
    
    def log_message(self, format, *args):
        """重写日志方法，使用更友好的格式"""
        print(f"[API] {args[0]} - {args[1] if len(args) > 1 else ''}")

def run_server(port=8888, open_browser=True):
    """运行API服务器"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, StockAPIHandler)
    
    print("=" * 60)
    print("🚀 股票预测数据API服务器已启动")
    print("=" * 60)
    print(f"📡 API地址: http://localhost:{port}/api/stocks")
    print(f"🌐 Web页面: http://localhost:{port}/stock_list.html")
    print("=" * 60)
    print("\n按 Ctrl+C 停止服务器\n")
    
    if open_browser:
        try:
            webbrowser.open(f'http://localhost:{port}/stock_list.html')
        except:
            pass
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n服务器已停止")
        httpd.shutdown()

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='股票预测数据API服务器')
    parser.add_argument('--port', type=int, default=8888, help='服务器端口（默认8888）')
    parser.add_argument('--no-browser', action='store_true', help='不自动打开浏览器')
    
    args = parser.parse_args()
    
    run_server(port=args.port, open_browser=not args.no_browser)
