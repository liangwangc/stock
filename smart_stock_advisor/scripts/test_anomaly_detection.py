"""
测试异常检测功能
验证停牌、ST股票、涨跌停等异常情况的检测和处理
"""
import sys
import os
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from predictor.stock_predictor import StockPredictor
from utils.logger import get_logger

logger = get_logger(__name__)


def test_anomaly_detection():
    """测试异常检测功能"""
    logger.info("=" * 60)
    logger.info("开始测试异常检测功能")
    logger.info("=" * 60)
    
    predictor = StockPredictor()
    
    # 测试股票列表（包含不同类型的股票）
    test_stocks = [
        # 正常股票
        {'symbol': '000001', 'name': '平安银行', 'expected_anomalies': []},
        # ST股票（示例：*ST股票）
        {'symbol': '000007', 'name': '全新好', 'expected_anomalies': ['st_stock']},
        # 其他测试股票
        {'symbol': '600519', 'name': '贵州茅台', 'expected_anomalies': []},
    ]
    
    results = []
    
    for test_case in test_stocks:
        symbol = test_case['symbol']
        name = test_case['name']
        expected_anomalies = test_case['expected_anomalies']
        
        logger.info("\n" + "-" * 60)
        logger.info(f"测试股票: {symbol} ({name})")
        logger.info(f"预期异常: {expected_anomalies}")
        logger.info("-" * 60)
        
        try:
            # 1. 测试异常检测方法
            logger.info("\n1. 测试 _detect_anomalies 方法...")
            anomaly_result = predictor._detect_anomalies(symbol)
            
            detected_anomalies = anomaly_result.get('anomalies', [])
            can_predict = anomaly_result.get('can_predict', True)
            details = anomaly_result.get('details', {})
            
            logger.info(f"   检测到的异常: {detected_anomalies}")
            logger.info(f"   是否可以预测: {can_predict}")
            logger.info(f"   异常详情: {details}")
            
            # 2. 测试完整预测流程
            logger.info("\n2. 测试完整预测流程...")
            prediction_result = predictor.predict(symbol)
            
            prediction_success = prediction_result.get('success', False)
            prediction_anomalies = prediction_result.get('anomalies', [])
            prediction_anomaly_details = prediction_result.get('anomaly_details', {})
            
            logger.info(f"   预测是否成功: {prediction_success}")
            logger.info(f"   预测结果中的异常: {prediction_anomalies}")
            logger.info(f"   预测结果中的异常详情: {prediction_anomaly_details}")
            
            # 3. 验证结果
            logger.info("\n3. 验证结果...")
            
            # 检查异常检测是否正确
            anomaly_detection_correct = True
            if expected_anomalies:
                # 如果预期有异常，检查是否检测到
                for expected_anomaly in expected_anomalies:
                    if expected_anomaly not in detected_anomalies:
                        logger.warning(f"   ⚠️ 预期异常 '{expected_anomaly}' 未被检测到")
                        anomaly_detection_correct = False
                    else:
                        logger.info(f"   ✓ 成功检测到预期异常: {expected_anomaly}")
            
            # 检查停牌股票是否被正确阻止预测
            if 'suspended' in detected_anomalies:
                if not can_predict:
                    logger.info("   ✓ 停牌股票正确阻止预测")
                else:
                    logger.warning("   ⚠️ 停牌股票应该阻止预测，但can_predict=True")
                    anomaly_detection_correct = False
                
                if not prediction_success:
                    logger.info("   ✓ 停牌股票在预测流程中被正确阻止")
                else:
                    logger.warning("   ⚠️ 停牌股票应该阻止预测，但预测返回success=True")
                    anomaly_detection_correct = False
            
            # 检查ST股票是否降低置信度
            if 'st_stock' in detected_anomalies:
                if prediction_success:
                    confidence = prediction_result.get('confidence', 0)
                    logger.info(f"   ✓ ST股票预测成功，置信度: {confidence:.2%}")
                    if confidence < 0.8:
                        logger.info("   ✓ ST股票置信度已降低（<80%）")
                    else:
                        logger.warning(f"   ⚠️ ST股票置信度未降低（{confidence:.2%}）")
                else:
                    logger.warning("   ⚠️ ST股票预测失败，但ST股票应该可以预测")
            
            # 检查预测结果中是否包含异常信息
            if detected_anomalies:
                if prediction_anomalies:
                    logger.info(f"   ✓ 预测结果中包含异常信息: {prediction_anomalies}")
                else:
                    logger.warning("   ⚠️ 检测到异常，但预测结果中未包含异常信息")
            
            # 记录测试结果
            test_result = {
                'symbol': symbol,
                'name': name,
                'expected_anomalies': expected_anomalies,
                'detected_anomalies': detected_anomalies,
                'can_predict': can_predict,
                'prediction_success': prediction_success,
                'anomaly_detection_correct': anomaly_detection_correct,
                'anomaly_info_in_result': bool(prediction_anomalies)
            }
            results.append(test_result)
            
        except Exception as e:
            logger.error(f"   测试失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            results.append({
                'symbol': symbol,
                'name': name,
                'error': str(e)
            })
    
    # 输出测试总结
    logger.info("\n" + "=" * 60)
    logger.info("测试总结")
    logger.info("=" * 60)
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r.get('anomaly_detection_correct', False) and not r.get('error'))
    failed_tests = total_tests - passed_tests
    
    logger.info(f"总测试数: {total_tests}")
    logger.info(f"通过: {passed_tests}")
    logger.info(f"失败: {failed_tests}")
    
    logger.info("\n详细结果:")
    for result in results:
        symbol = result.get('symbol', 'N/A')
        name = result.get('name', 'N/A')
        if 'error' in result:
            logger.info(f"  {symbol} ({name}): ❌ 错误 - {result['error']}")
        elif result.get('anomaly_detection_correct', False):
            logger.info(f"  {symbol} ({name}): ✓ 通过")
            logger.info(f"    检测到的异常: {result.get('detected_anomalies', [])}")
            logger.info(f"    预测成功: {result.get('prediction_success', False)}")
            logger.info(f"    异常信息在结果中: {result.get('anomaly_info_in_result', False)}")
        else:
            logger.info(f"  {symbol} ({name}): ❌ 失败")
            logger.info(f"    检测到的异常: {result.get('detected_anomalies', [])}")
            logger.info(f"    预期异常: {result.get('expected_anomalies', [])}")
    
    return results


if __name__ == '__main__':
    test_anomaly_detection()
