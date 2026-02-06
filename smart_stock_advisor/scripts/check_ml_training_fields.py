"""
检查ML模型训练使用的字段数据完整性

检查 stock_history_data 表中ML训练使用的字段是否有数据
"""
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from utils.db_connection import DatabaseConnection
import pandas as pd

logger = get_logger(__name__)


def check_field_data_completeness():
    """检查ML训练使用的字段数据完整性"""
    try:
        db = DatabaseConnection()
        
        logger.info("=" * 80)
        logger.info("ML模型训练字段数据完整性检查")
        logger.info("=" * 80)
        
        # ML训练使用的所有字段（从ml_data_loader.py中的SQL查询提取）
        ml_fields = [
            # 基础价格字段（7个）
            'close_price', 'open_price', 'high_price', 'low_price', 
            'pre_close', 'change_pct', 'change_amount',
            # 成交字段（4个）
            'volume', 'amount', 'turnover_rate', 'volume_ratio',
            # 技术指标字段（9个）
            'ma5', 'ma10', 'ma20', 'ma60', 'rsi', 
            'macd', 'macd_signal', 'macd_hist', 'x2',
            # 资金流向字段（5个）
            'main_net_inflow', 'super_large_inflow', 'large_inflow', 
            'medium_inflow', 'small_inflow',
            # 估值字段（4个）
            'pe_ratio', 'pb_ratio', 'total_market_cap', 'float_market_cap',
            # 融资融券字段（3个）
            'margin_balance', 'short_balance', 'margin_ratio'
        ]
        
        # 1. 检查总记录数
        sql_total = "SELECT COUNT(*) as cnt FROM stock_history_data WHERE period_type = 'daily'"
        result = db.execute_query(sql_total)
        total_records = result[0]['cnt'] if result else 0
        logger.info(f"\n总记录数: {total_records:,}")
        
        if total_records == 0:
            logger.warning("数据库中没有数据，无法继续检查")
            return
        
        # 2. 检查每个字段的数据完整性
        logger.info("\n" + "=" * 80)
        logger.info("字段数据完整性统计")
        logger.info("=" * 80)
        logger.info(f"{'字段名':<25} {'非空数量':<15} {'非空率':<15} {'空值数量':<15} {'状态':<10}")
        logger.info("-" * 80)
        
        field_stats = []
        critical_fields = ['close_price', 'open_price', 'high_price', 'low_price', 'volume']  # 关键字段
        
        for field in ml_fields:
            # 检查非空记录数
            sql_non_null = f"""
                SELECT COUNT(*) as cnt 
                FROM stock_history_data 
                WHERE period_type = 'daily' 
                  AND {field} IS NOT NULL
            """
            
            # 检查NULL和0值的记录数（某些字段0值可能表示无数据）
            sql_null = f"""
                SELECT COUNT(*) as cnt 
                FROM stock_history_data 
                WHERE period_type = 'daily' 
                  AND ({field} IS NULL OR {field} = 0)
            """
            
            try:
                result_non_null = db.execute_query(sql_non_null)
                result_null = db.execute_query(sql_null)
                
                non_null_count = result_non_null[0]['cnt'] if result_non_null else 0
                null_count = result_null[0]['cnt'] if result_null else total_records
                non_null_rate = (non_null_count / total_records * 100) if total_records > 0 else 0
                
                # 判断状态
                if non_null_rate >= 90:
                    status = "[OK]"
                elif non_null_rate >= 50:
                    status = "[WARN]"
                elif non_null_rate >= 10:
                    status = "[POOR]"
                else:
                    status = "[MISSING]"
                
                field_stats.append({
                    'field': field,
                    'non_null_count': non_null_count,
                    'non_null_rate': non_null_rate,
                    'null_count': null_count,
                    'status': status,
                    'is_critical': field in critical_fields
                })
                
                logger.info(
                    f"{field:<25} {non_null_count:>14,} {non_null_rate:>14.2f}% {null_count:>14,} {status:<10}"
                )
                
            except Exception as e:
                logger.error(f"检查字段 {field} 失败: {str(e)}")
                field_stats.append({
                    'field': field,
                    'non_null_count': 0,
                    'non_null_rate': 0,
                    'null_count': total_records,
                    'status': '✗ 错误',
                    'is_critical': field in critical_fields
                })
        
        # 3. 汇总统计
        logger.info("\n" + "=" * 80)
        logger.info("汇总统计")
        logger.info("=" * 80)
        
        good_fields = [f for f in field_stats if f['non_null_rate'] >= 90]
        medium_fields = [f for f in field_stats if 50 <= f['non_null_rate'] < 90]
        poor_fields = [f for f in field_stats if 10 <= f['non_null_rate'] < 50]
        missing_fields = [f for f in field_stats if f['non_null_rate'] < 10]
        
        logger.info(f"✓ 数据完整（≥90%）: {len(good_fields)} 个字段")
        logger.info(f"⚠ 数据一般（50-90%）: {len(medium_fields)} 个字段")
        logger.info(f"✗ 数据较差（10-50%）: {len(poor_fields)} 个字段")
        logger.info(f"✗ 数据缺失（<10%）: {len(missing_fields)} 个字段")
        
        # 4. 关键字段检查
        logger.info("\n" + "=" * 80)
        logger.info("关键字段检查（必须有的字段）")
        logger.info("=" * 80)
        
        critical_issues = []
        for field in field_stats:
            if field['is_critical']:
                if field['non_null_rate'] < 90:
                    critical_issues.append(field)
                    logger.warning(
                        f"⚠ {field['field']}: 非空率仅 {field['non_null_rate']:.2f}%，可能影响训练"
                    )
                else:
                    logger.info(f"✓ {field['field']}: 非空率 {field['non_null_rate']:.2f}%")
        
        # 5. 建议字段（可能缺失但重要的字段）
        logger.info("\n" + "=" * 80)
        logger.info("建议检查的字段（数据完整率 < 50%）")
        logger.info("=" * 80)
        
        for field in field_stats:
            if not field['is_critical'] and field['non_null_rate'] < 50:
                logger.warning(
                    f"⚠ {field['field']}: 非空率 {field['non_null_rate']:.2f}%，"
                    f"建议检查是否需要在训练中使用"
                )
        
        # 6. 生成报告
        logger.info("\n" + "=" * 80)
        logger.info("优化建议")
        logger.info("=" * 80)
        
        if missing_fields:
            logger.warning("发现数据缺失严重的字段，建议：")
            for field in missing_fields:
                logger.warning(f"  - {field['field']}: 非空率 {field['non_null_rate']:.2f}%")
                logger.warning(f"    → 建议在训练中跳过此字段，或使用默认值")
        
        if poor_fields:
            logger.info("发现数据完整率较低的字段：")
            for field in poor_fields:
                logger.info(f"  - {field['field']}: 非空率 {field['non_null_rate']:.2f}%")
                logger.info(f"    → 建议检查数据处理逻辑，确保缺失值处理正确")
        
        # 7. 检查字段类型
        logger.info("\n" + "=" * 80)
        logger.info("字段类型检查")
        logger.info("=" * 80)
        
        sql_columns = """
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'stock_history_data'
              AND COLUMN_NAME IN ({})
            ORDER BY ORDINAL_POSITION
        """.format(','.join([f"'{f}'" for f in ml_fields]))
        
        try:
            columns = db.execute_query(sql_columns)
            logger.info(f"{'字段名':<25} {'数据类型':<15} {'允许NULL':<10} {'默认值':<15}")
            logger.info("-" * 65)
            for col in columns:
                logger.info(
                    f"{col['COLUMN_NAME']:<25} {col['DATA_TYPE']:<15} "
                    f"{col['IS_NULLABLE']:<10} {str(col.get('COLUMN_DEFAULT', 'NULL')):<15}"
                )
        except Exception as e:
            logger.warning(f"检查字段类型失败: {str(e)}")
        
        logger.info("\n" + "=" * 80)
        logger.info("检查完成")
        logger.info("=" * 80)
        
        return field_stats
        
    except Exception as e:
        logger.error(f"检查失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None


if __name__ == '__main__':
    check_field_data_completeness()
