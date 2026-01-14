"""
测试全部功能
"""
import sys
import os
import pandas as pd
from datetime import datetime

# 添加项目路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_data_storage():
    """测试数据存储功能"""
    print("\n" + "="*60)
    print("测试1: 数据存储功能")
    print("="*60)
    
    try:
        from utils.data_storage import DataStorage
        
        storage = DataStorage(base_dir="data")
        print("[OK] 数据存储模块初始化成功")
        
        # 检查数据文件是否存在
        data_files = [
            'north_bound_capital_data.csv',
            'margin_trading_data.csv',
            'main_force_capital_data.csv',
            'sector_rotation_data.csv',
            'technical_indicators_data.csv',
            'news_sentiment_data.csv',
            'market_sentiment_data.csv',
            'prediction_factors_data.csv'
        ]
        
        data_dir = os.path.join(project_root, 'data')
        for filename in data_files:
            filepath = os.path.join(data_dir, filename)
            if os.path.exists(filepath):
                df = pd.read_csv(filepath, encoding='utf-8-sig')
                print(f"[OK] {filename}: {len(df)} 条记录")
            else:
                print(f"[--] {filename}: 文件不存在（首次运行时会创建）")
        
        return True
    except Exception as e:
        print(f"[FAIL] 数据存储测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_prediction_save():
    """测试预测记录保存"""
    print("\n" + "="*60)
    print("测试2: 预测记录保存功能")
    print("="*60)
    
    try:
        csv_file = os.path.join(project_root, 'stock_predictions.csv')
        
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file, dtype={'symbol': str}, encoding='utf-8-sig')
            print(f"[OK] CSV文件存在: {csv_file}")
            print(f"[OK] 共有 {len(df)} 条预测记录")
            
            if len(df) > 0:
                # 检查字段
                required_fields = [
                    'symbol', 'name', 'prediction_date', 'target_date',
                    'prediction', 'up_probability', 'down_probability',
                    'actual_price', 'actual_change_pct', 'prediction_hit'
                ]
                missing_fields = [f for f in required_fields if f not in df.columns]
                if missing_fields:
                    print(f"[--] 缺少字段: {missing_fields}")
                else:
                    print("[OK] 所有必需字段都存在")
                
                # 显示最新几条记录
                print("\n最新3条预测记录:")
                latest = df.tail(3)
                for idx, row in latest.iterrows():
                    symbol = row.get('symbol', '')
                    name = row.get('name', '')
                    pred_date = row.get('prediction_date', '')
                    target_date = row.get('target_date', '')
                    prediction = row.get('prediction', '')
                    hit = row.get('prediction_hit', '')
                    print(f"  {symbol} {name}: {pred_date} -> {target_date}, 预测:{prediction}, 结果:{hit}")
        else:
            print("[--] CSV文件不存在（首次运行后会创建）")
        
        return True
    except Exception as e:
        print(f"[FAIL] 预测记录保存测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_html_files():
    """测试HTML文件生成"""
    print("\n" + "="*60)
    print("测试3: HTML文件生成")
    print("="*60)
    
    try:
        # 检查主要HTML文件
        html_files = {
            'stock_list.html': '股票列表页面',
            'reports/': '预测结果目录'
        }
        
        stock_list = os.path.join(project_root, 'stock_list.html')
        if os.path.exists(stock_list):
            size = os.path.getsize(stock_list)
            print(f"[OK] stock_list.html 存在 ({size} 字节)")
            
            # 读取文件检查路径引用
            with open(stock_list, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'reports/' in content:
                    print("[OK] HTML中正确引用了reports目录")
                else:
                    print("[--] HTML中未找到reports目录引用")
        else:
            print("[--] stock_list.html 不存在")
        
        # 检查reports目录
        reports_dir = os.path.join(project_root, 'reports')
        if os.path.exists(reports_dir):
            files = os.listdir(reports_dir)
            png_files = [f for f in files if f.endswith('.png')]
            html_files = [f for f in files if f.endswith('.html')]
            print(f"[OK] reports目录存在")
            print(f"  - PNG文件: {len(png_files)} 个")
            print(f"  - HTML文件: {len(html_files)} 个")
        else:
            print("[--] reports目录不存在（首次生成预测结果时会创建）")
        
        # 检查历史页面
        history_files = [f for f in os.listdir(project_root) if f.startswith('history_') and f.endswith('.html')]
        if history_files:
            print(f"[OK] 历史预测页面: {len(history_files)} 个")
        else:
            print("[--] 历史预测页面: 0 个")
        
        return True
    except Exception as e:
        print(f"[FAIL] HTML文件测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_predictor():
    """测试预测器初始化"""
    print("\n" + "="*60)
    print("测试4: 预测器模块")
    print("="*60)
    
    try:
        from predictor.stock_predictor import StockPredictor
        
        predictor = StockPredictor()
        print("[OK] 预测器初始化成功")
        
        # 测试获取目标日期
        target_date, desc = predictor.get_target_date()
        print(f"[OK] 目标日期计算: {target_date} ({desc})")
        
        return True
    except Exception as e:
        print(f"[FAIL] 预测器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_source():
    """测试数据源"""
    print("\n" + "="*60)
    print("测试5: 数据源模块")
    print("="*60)
    
    try:
        import sys
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "stock_data_source",
            os.path.join(project_root, "data_source", "stock_data_source.py")
        )
        stock_data_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stock_data_module)
        StockDataSource = stock_data_module.StockDataSource
        
        data_source = StockDataSource()
        print("[OK] 数据源初始化成功")
        
        # 测试获取股票信息
        try:
            info = data_source.get_stock_info('600362')
            if info:
                print(f"[OK] 股票信息获取成功: {info.get('name', '未知')}")
        except Exception as e:
            print(f"[--] 股票信息获取失败（可能是网络问题）: {e}")
        
        return True
    except Exception as e:
        print(f"[FAIL] 数据源测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_visualizer():
    """测试可视化器"""
    print("\n" + "="*60)
    print("测试6: 可视化器模块")
    print("="*60)
    
    try:
        from visualizer.prediction_visualizer import PredictionVisualizer
        
        visualizer = PredictionVisualizer()
        print("[OK] 可视化器初始化成功")
        
        # 检查reports目录是否已创建
        reports_dir = os.path.join(project_root, 'reports')
        if os.path.exists(reports_dir):
            print(f"[OK] reports目录已创建: {reports_dir}")
        else:
            print("[--] reports目录未创建（首次使用时会自动创建）")
        
        return True
    except Exception as e:
        print(f"[FAIL] 可视化器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """运行所有测试"""
    print("="*60)
    print("Smart Stock Advisor - 全部功能测试")
    print("="*60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # 运行各项测试
    results.append(("数据存储功能", test_data_storage()))
    results.append(("预测记录保存", test_prediction_save()))
    results.append(("HTML文件生成", test_html_files()))
    results.append(("预测器模块", test_predictor()))
    results.append(("数据源模块", test_data_source()))
    results.append(("可视化器模块", test_visualizer()))
    
    # 输出总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "[OK] 通过" if result else "[FAIL] 失败"
        print(f"{status}: {name}")
    
    print(f"\n总计: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("\n[SUCCESS] 所有测试通过！")
        return 0
    else:
        print(f"\n[WARN]  有 {total - passed} 项测试失败")
        return 1

if __name__ == '__main__':
    sys.exit(main())

