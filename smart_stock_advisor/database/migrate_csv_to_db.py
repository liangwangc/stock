"""
将CSV数据迁移到数据库
"""
import os
import sys
import pandas as pd
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    from config_db import DB_CONFIG, USE_DATABASE
    from utils.db_storage import DatabaseStorage
    from utils.stock_prediction_db import StockPredictionDB
    from utils.db_connection import DatabaseConnection
except ImportError as e:
    print(f"导入失败: {e}")
    print("请确保已安装pymysql: pip install pymysql")
    sys.exit(1)


def migrate_stock_predictions():
    """迁移stock_predictions.csv到数据库"""
    csv_file = os.path.join(project_root, 'stock_predictions.csv')
    
    if not os.path.exists(csv_file):
        print(f"CSV文件不存在: {csv_file}")
        return 0
    
    try:
        df = pd.read_csv(csv_file, dtype={'symbol': str}, encoding='utf-8-sig')
        if df.empty:
            print("CSV文件为空")
            return 0
        
        db = StockPredictionDB()
        count = 0
        
        for idx, row in df.iterrows():
            try:
                # 构建prediction_result字典
                prediction_result = {
                    'name': str(row.get('name', '')),
                    'prediction_date': str(row.get('prediction_date', '')),
                    'target_date': str(row.get('target_date', '')),
                    'current_price': float(row.get('current_price', 0)) if pd.notna(row.get('current_price')) else 0,
                    'prediction': str(row.get('prediction', '震荡')),
                    'up_probability': float(row.get('up_probability', 0)) if pd.notna(row.get('up_probability')) else 0,
                    'down_probability': float(row.get('down_probability', 0)) if pd.notna(row.get('down_probability')) else 0,
                    'confidence': float(row.get('confidence', 0)) if pd.notna(row.get('confidence')) else 0,
                    'final_score': 0,
                    'prediction_time': str(row.get('prediction_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))),
                    'summary': str(row.get('summary', ''))
                }
                
                symbol = str(row.get('symbol', '')).strip()
                png_file = str(row.get('png_file', '')) if pd.notna(row.get('png_file')) else None
                full_report_html = str(row.get('full_report_html', '')) if pd.notna(row.get('full_report_html')) else None
                
                # 保存到数据库
                if db.save_prediction(symbol, prediction_result, png_file, None, full_report_html):
                    # 如果有实际数据，更新
                    if pd.notna(row.get('actual_price')):
                        db.update_prediction_actual(
                            symbol,
                            str(row.get('target_date', '')),
                            float(row.get('actual_price', 0)),
                            float(row.get('actual_change_pct', 0)) if pd.notna(row.get('actual_change_pct')) else 0,
                            str(row.get('actual_direction', '')),
                            str(row.get('prediction_hit', ''))
                        )
                    count += 1
            except Exception as e:
                print(f"迁移记录 {idx} 失败: {str(e)}")
        
        print(f"成功迁移 {count}/{len(df)} 条预测记录到数据库")
        return count
        
    except Exception as e:
        print(f"迁移失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return 0


def migrate_data_files():
    """迁移data目录下的CSV文件到数据库"""
    data_dir = os.path.join(project_root, 'data')
    
    if not os.path.exists(data_dir):
        print(f"数据目录不存在: {data_dir}")
        return 0
    
    db_storage = DatabaseStorage()
    total_count = 0
    
    # 迁移各类数据文件
    data_files = {
        'north_bound_capital': 'north_bound_capital',
        'margin_trading': 'margin_trading',
        'main_force_capital': 'main_force_capital',
        'sector_rotation': 'sector_rotation',
        'technical_indicators': 'technical_indicators',
        'news_sentiment': 'news_sentiment',
        'market_sentiment': 'market_sentiment',
        'prediction_factors': 'prediction_factors',
        'cost_distribution': 'cost_distribution',
        'realtime_trading_decisions': 'realtime_trading_decisions'
    }
    
    for file_key, table_name in data_files.items():
        csv_file = os.path.join(data_dir, f"{file_key}_data.csv")
        if not os.path.exists(csv_file):
            print(f"跳过: {csv_file} 不存在")
            continue
        
        try:
            df = pd.read_csv(csv_file, encoding='utf-8-sig')
            if df.empty:
                continue
            
            count = 0
            print(f"\n迁移 {file_key}...")
            
            for idx, row in df.iterrows():
                try:
                    # 这里需要根据不同的数据类型调用不同的保存方法
                    # 由于数据结构复杂，这里只做示例
                    # 实际使用时需要根据CSV结构构建相应的数据字典
                    count += 1
                except Exception as e:
                    print(f"  记录 {idx} 失败: {str(e)}")
            
            print(f"  {file_key}: {count}/{len(df)} 条记录")
            total_count += count
            
        except Exception as e:
            print(f"迁移 {file_key} 失败: {str(e)}")
    
    return total_count


def main():
    """主函数"""
    print("=" * 60)
    print("CSV数据迁移到数据库")
    print("=" * 60)
    
    if not USE_DATABASE:
        print("错误: 数据库未启用，请在 config_db.py 中设置 USE_DATABASE = True")
        return
    
    # 测试数据库连接
    try:
        db = DatabaseConnection()
        db.get_connection()
        print("✓ 数据库连接成功")
    except Exception as e:
        print(f"✗ 数据库连接失败: {str(e)}")
        print("请检查 config_db.py 中的数据库配置")
        return
    
    # 迁移stock_predictions.csv
    print("\n1. 迁移股票预测记录...")
    count1 = migrate_stock_predictions()
    
    # 迁移data目录下的数据文件
    print("\n2. 迁移数据文件...")
    print("注意: 数据文件的迁移需要根据具体的数据结构实现")
    print("建议: 使用现有的保存方法重新保存数据")
    
    print("\n" + "=" * 60)
    print(f"迁移完成！共迁移 {count1} 条预测记录")
    print("=" * 60)


if __name__ == '__main__':
    main()
