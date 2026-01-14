"""
分析数据库写入性能瓶颈
测试批量INSERT的性能，找出慢的原因
"""
import os
import sys
import time
from datetime import datetime, timedelta

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from utils.stock_history_storage import StockHistoryStorage
from utils.db_connection import DatabaseConnection

logger = get_logger(__name__)


def test_batch_insert_performance():
    """测试批量INSERT的性能"""
    print("=" * 80)
    print("数据库批量写入性能测试")
    print("=" * 80)
    
    storage = StockHistoryStorage()
    db = DatabaseConnection()
    
    # 准备测试数据
    symbol = '000001'
    test_data = []
    base_date = datetime.now() - timedelta(days=100)
    
    print(f"\n准备测试数据...")
    for i in range(100):  # 100条测试数据
        date = (base_date + timedelta(days=i)).strftime('%Y-%m-%d')
        data = {
            'symbol': symbol,
            'name': '测试股票',
            'trade_date': date,
            'period_type': 'daily',
            'open_price': 10.0 + i * 0.01,
            'close_price': 10.5 + i * 0.01,
            'high_price': 11.0 + i * 0.01,
            'low_price': 9.5 + i * 0.01,
            'pre_close': 10.0 + i * 0.01,
            'change_amount': 0.5,
            'change_pct': 5.0,
            'volume': 1000000,
            'amount': 10000000,
            'volume_ratio': 1.0,
            'cost_distribution': None,
            'cost_distribution_history': None,
            'pe_ratio': 10.0,
            'pb_ratio': 1.0,
            'limit_up': 11.0,
            'limit_down': 9.0,
            'limit_pct': 10.0,
            'is_limit_up': False,
            'is_limit_down': False,
            'amplitude': 5.0,
            'price_range': 1.5,
            'ma5': 10.2,
            'ma10': 10.1,
            'ma20': 10.0,
            'ma60': 9.9,
            'rsi': 50.0,
            'macd': 0.1,
            'macd_signal': 0.05,
            'macd_hist': 0.05,
            'x2': 50.0,
            'margin_balance': None,
            'short_balance': None,
            'margin_ratio': None,
            'extra_data': None,
            'data_source': 'test',
            'data_quality_score': 1.0,
            'is_valid': True
        }
        test_data.append((symbol, date, data))
    
    print(f"准备完成：{len(test_data)} 条测试数据")
    print()
    
    # 测试1: 批量INSERT（当前实现）
    print("测试1: 批量INSERT（当前实现）")
    print("-" * 80)
    try:
        start_time = time.time()
        result = storage.save_stock_daily_data_batch(test_data, batch_size=100)
        duration = time.time() - start_time
        
        print(f"  成功: {result['success_count']}/{result['total_count']}")
        print(f"  失败: {result['fail_count']}")
        print(f"  耗时: {duration:.2f}秒")
        print(f"  速度: {result['success_count'] / duration:.2f} 条/秒" if duration > 0 else "  速度: N/A")
    except Exception as e:
        print(f"  测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print()
    
    # 测试2: 检查SQL语句长度
    print("测试2: SQL语句长度分析")
    print("-" * 80)
    try:
        # 构建一条SQL语句看看长度
        sql_base = """
            INSERT INTO stock_history_data 
            (symbol, name, trade_date, period_type, open_price, close_price, high_price, low_price, pre_close,
             change_amount, change_pct, volume, amount, volume_ratio,
             cost_distribution, cost_distribution_history, pe_ratio, pb_ratio,
             limit_up, limit_down, limit_pct, is_limit_up, is_limit_down,
             amplitude, price_range, ma5, ma10, ma20, ma60, rsi, macd, macd_signal, macd_hist, x2,
             margin_balance, short_balance, margin_ratio,
             extra_data, data_source, data_quality_score, is_valid)
            VALUES 
        """
        
        # 模拟100条数据的SQL
        values_part = "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        values_parts = [values_part] * 100
        sql = sql_base + ", ".join(values_parts)
        
        sql_length = len(sql)
        print(f"  100条数据的SQL长度: {sql_length:,} 字符")
        print(f"  500条数据的SQL长度: {sql_length * 5:,} 字符（预估）")
        print(f"  1000条数据的SQL长度: {sql_length * 10:,} 字符（预估）")
        
        # MySQL的max_allowed_packet默认是4MB或16MB
        max_packet = 4 * 1024 * 1024  # 4MB
        print(f"  MySQL max_allowed_packet: {max_packet:,} 字符（4MB）")
        
        if sql_length * 10 > max_packet:
            print(f"  ⚠️  警告: 1000条数据的SQL可能超过max_allowed_packet限制")
        else:
            print(f"  ✓ SQL长度在限制范围内")
    except Exception as e:
        print(f"  测试失败: {str(e)}")
    
    print()
    
    # 测试3: 检查数据库索引
    print("测试3: 检查数据库索引")
    print("-" * 80)
    try:
        # 检查表结构
        sql = "SHOW INDEX FROM stock_history_data"
        indexes = db.execute_query(sql)
        
        if indexes:
            print(f"  找到 {len(indexes)} 个索引:")
            for idx in indexes[:10]:  # 只显示前10个
                print(f"    - {idx.get('Key_name', 'N/A')}: {idx.get('Column_name', 'N/A')} ({idx.get('Index_type', 'N/A')})")
            
            # 检查唯一索引
            unique_indexes = [idx for idx in indexes if idx.get('Non_unique', 1) == 0]
            if unique_indexes:
                print(f"\n  唯一索引数量: {len(unique_indexes)}")
                print(f"  ⚠️  唯一索引会影响INSERT ... ON DUPLICATE KEY UPDATE的性能")
        else:
            print(f"  未找到索引信息")
    except Exception as e:
        print(f"  检查失败: {str(e)}")
    
    print()
    
    # 测试4: 检查表结构
    print("测试4: 检查表结构")
    print("-" * 80)
    try:
        sql = "DESCRIBE stock_history_data"
        columns = db.execute_query(sql)
        
        if columns:
            print(f"  表字段数量: {len(columns)}")
            
            # 检查JSON字段
            json_fields = [col for col in columns if 'json' in col.get('Type', '').lower() or 'text' in col.get('Type', '').lower()]
            if json_fields:
                print(f"  JSON/TEXT字段数量: {len(json_fields)}")
                print(f"  ⚠️  JSON/TEXT字段会影响写入性能")
            
            # 检查索引字段
            indexed_fields = [col for col in columns if col.get('Key', '') != '']
            if indexed_fields:
                print(f"  有索引的字段数量: {len(indexed_fields)}")
    except Exception as e:
        print(f"  检查失败: {str(e)}")
    
    print()
    
    # 测试5: 测试逐条插入的性能（对比）
    print("测试5: 逐条插入性能（对比）")
    print("-" * 80)
    try:
        # 只测试10条，避免太慢
        test_data_small = test_data[:10]
        start_time = time.time()
        
        for symbol, date, data in test_data_small:
            storage.save_stock_daily_data(symbol, date, data)
        
        duration = time.time() - start_time
        print(f"  10条数据逐条插入耗时: {duration:.2f}秒")
        print(f"  速度: {10 / duration:.2f} 条/秒" if duration > 0 else "  速度: N/A")
        print(f"  预估100条数据耗时: {duration * 10:.2f}秒")
    except Exception as e:
        print(f"  测试失败: {str(e)}")
    
    print()
    
    # 总结和建议
    print("=" * 80)
    print("性能分析和优化建议")
    print("=" * 80)
    
    print("\n可能的性能瓶颈:")
    print("1. SQL语句过长：批量INSERT的SQL语句可能很长，影响解析和执行")
    print("2. 唯一索引：ON DUPLICATE KEY UPDATE需要检查唯一索引，影响性能")
    print("3. JSON字段序列化：每条数据都要序列化JSON字段")
    print("4. 数据库连接：每次操作都要获取连接")
    print("5. 事务提交：每条数据都提交（如果autocommit=True）")
    
    print("\n优化建议:")
    print("1. 减小批次大小：从500改为100-200，避免SQL语句过长")
    print("2. 禁用唯一索引检查：如果数据不重复，可以先禁用唯一索引，插入后再启用")
    print("3. 使用LOAD DATA INFILE：MySQL的LOAD DATA INFILE比INSERT快10-100倍")
    print("4. 批量提交：关闭autocommit，批量提交事务")
    print("5. 优化索引：只保留必要的索引，减少索引数量")
    print("6. 使用executemany：使用cursor.executemany()而不是构建长SQL")


if __name__ == '__main__':
    test_batch_insert_performance()
