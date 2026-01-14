"""
自动化定期回测模块
实现自动化的定期回测和性能评估，监控模型性能
"""
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import threading
import time

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection as DBConnection
from utils.model_performance_evaluator import ModelPerformanceEvaluator
from utils.backtest_engine import BacktestEngine
from utils.logger import get_logger
from config_db import USE_DATABASE

logger = get_logger(__name__)


class AutomatedBacktest:
    """自动化定期回测管理器"""
    
    def __init__(self):
        self.logger = logger
        self.db = DBConnection()
        self.use_database = USE_DATABASE
        self.evaluator = ModelPerformanceEvaluator()
        self.backtest_engine = BacktestEngine()
        self._monitoring = False
        self._monitor_thread = None
    
    def run_periodic_backtest(self, days: int = 30, save_to_db: bool = True) -> Dict:
        """
        执行定期回测和性能评估
        
        Args:
            days: 回测天数（默认30天）
            save_to_db: 是否保存到数据库
        
        Returns:
            回测结果字典
        """
        try:
            self.logger.info(f"开始执行定期回测，天数: {days}")
            
            # 1. 执行预测性能评估
            prediction_result = self.evaluator.evaluate_prediction_performance(days=days)
            
            # 2. 执行回测分析
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            backtest_result = self.backtest_engine.backtest_predictions(
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
                initial_capital=100000.0
            )
            
            # 3. 保存结果到数据库
            if save_to_db and self.use_database:
                self._save_backtest_result(prediction_result, backtest_result, days)
            
            # 4. 检查是否需要告警
            alerts = self._check_performance_alerts(prediction_result, backtest_result)
            
            result = {
                'success': True,
                'evaluation_date': end_date.strftime('%Y-%m-%d'),
                'days': days,
                'prediction_performance': prediction_result,
                'backtest_result': backtest_result,
                'alerts': alerts
            }
            
            self.logger.info(f"定期回测完成: 预测准确率={prediction_result.get('direction_accuracy', 0)*100:.2f}%")
            
            return result
            
        except Exception as e:
            self.logger.error(f"执行定期回测失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': str(e),
                'error': str(e)
            }
    
    def _save_backtest_result(self, prediction_result: Dict, backtest_result: Dict, days: int):
        """保存回测结果到数据库"""
        try:
            # 确保model_performance表存在
            check_sql = """
                SELECT COUNT(*) as cnt 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = 'model_performance'
            """
            result = self.db.execute_query(check_sql)
            
            if not result or result[0].get('cnt', 0) == 0:
                self.logger.warning("model_performance表不存在，跳过保存")
                return
            
            # 保存预测性能评估结果
            if prediction_result.get('success'):
                sql = """
                    INSERT INTO model_performance
                    (evaluation_type, evaluation_date, time_period,
                     direction_accuracy, magnitude_mae, calibration_score,
                     sample_count, market_condition, details, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                import json
                details_json = json.dumps(prediction_result, ensure_ascii=False)
                
                params = (
                    'prediction',
                    datetime.now().date(),
                    f'{days}d',
                    prediction_result.get('direction_accuracy', 0) * 100,
                    prediction_result.get('magnitude_mae', 0),
                    prediction_result.get('calibration_score', 0) * 100,
                    prediction_result.get('sample_count', 0),
                    prediction_result.get('market_condition', {}).get('condition', 'unknown'),
                    details_json,
                    datetime.now()
                )
                
                self.db.execute_update(sql, params)
                self.logger.info("预测性能评估结果已保存到数据库")
            
            # 保存回测结果
            if backtest_result.get('success'):
                sql = """
                    INSERT INTO model_performance
                    (evaluation_type, evaluation_date, time_period,
                     total_return, annual_return, max_drawdown, win_rate,
                     profit_loss_ratio, sample_count, details, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                import json
                details_json = json.dumps(backtest_result, ensure_ascii=False)
                
                params = (
                    'backtest',
                    datetime.now().date(),
                    f'{days}d',
                    backtest_result.get('total_return', 0),
                    backtest_result.get('annual_return', 0),
                    backtest_result.get('max_drawdown', 0),
                    backtest_result.get('win_rate', 0) * 100,
                    backtest_result.get('profit_loss_ratio', 0),
                    backtest_result.get('total_trades', 0),
                    details_json,
                    datetime.now()
                )
                
                self.db.execute_update(sql, params)
                self.logger.info("回测结果已保存到数据库")
            
        except Exception as e:
            self.logger.error(f"保存回测结果失败: {str(e)}")
    
    def _check_performance_alerts(self, prediction_result: Dict, backtest_result: Dict) -> List[Dict]:
        """
        检查性能告警
        
        Args:
            prediction_result: 预测性能评估结果
            backtest_result: 回测结果
        
        Returns:
            告警列表
        """
        alerts = []
        
        try:
            # 检查预测准确率
            direction_accuracy = prediction_result.get('direction_accuracy', 0) * 100
            if direction_accuracy > 0 and direction_accuracy < 50:
                alerts.append({
                    'level': 'warning',
                    'type': 'prediction_accuracy',
                    'metric': 'direction_accuracy',
                    'value': direction_accuracy,
                    'message': f'预测准确率较低: {direction_accuracy:.2f}%，建议检查模型参数',
                    'timestamp': datetime.now().isoformat()
                })
            
            # 检查回测收益率
            total_return = backtest_result.get('total_return', 0)
            if total_return < -10:
                alerts.append({
                    'level': 'critical',
                    'type': 'backtest_return',
                    'metric': 'total_return',
                    'value': total_return,
                    'message': f'回测总收益率为负: {total_return:.2f}%，模型表现不佳',
                    'timestamp': datetime.now().isoformat()
                })
            
            # 检查最大回撤
            max_drawdown = backtest_result.get('max_drawdown', 0)
            if abs(max_drawdown) > 20:
                alerts.append({
                    'level': 'warning',
                    'type': 'max_drawdown',
                    'metric': 'max_drawdown',
                    'value': max_drawdown,
                    'message': f'最大回撤较大: {abs(max_drawdown):.2f}%，风险较高',
                    'timestamp': datetime.now().isoformat()
                })
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"检查性能告警失败: {str(e)}")
            return []
    
    def start_periodic_backtest(self, interval_days: int = 7, backtest_days: int = 30):
        """
        启动定期回测（自动执行）
        
        Args:
            interval_days: 执行间隔（天数，默认7天）
            backtest_days: 回测天数（默认30天）
        """
        if self._monitoring:
            self.logger.warning("定期回测已在运行")
            return
        
        self._monitoring = True
        
        def backtest_loop():
            self.logger.info(f"定期回测已启动，间隔: {interval_days}天，回测天数: {backtest_days}天")
            
            while self._monitoring:
                try:
                    # 执行回测
                    result = self.run_periodic_backtest(days=backtest_days, save_to_db=True)
                    
                    if result.get('success'):
                        # 记录告警
                        alerts = result.get('alerts', [])
                        for alert in alerts:
                            if alert['level'] == 'critical':
                                self.logger.error(f"【严重告警】{alert['message']}")
                            else:
                                self.logger.warning(f"【告警】{alert['message']}")
                    
                except Exception as e:
                    self.logger.error(f"定期回测执行失败: {str(e)}")
                
                # 等待下次执行
                wait_seconds = interval_days * 24 * 3600
                wait_interval = 3600  # 每小时检查一次是否停止
                
                for _ in range(wait_seconds // wait_interval):
                    if not self._monitoring:
                        break
                    time.sleep(wait_interval)
            
            self.logger.info("定期回测已停止")
        
        self._monitor_thread = threading.Thread(target=backtest_loop, daemon=True, name="AutomatedBacktest")
        self._monitor_thread.start()
    
    def stop_periodic_backtest(self):
        """停止定期回测"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        self.logger.info("定期回测已停止")


# 全局自动化回测实例
_automated_backtest = None
_automated_backtest_lock = threading.Lock()


def get_automated_backtest() -> AutomatedBacktest:
    """获取全局自动化回测实例（单例模式）"""
    global _automated_backtest
    
    if _automated_backtest is None:
        with _automated_backtest_lock:
            if _automated_backtest is None:
                _automated_backtest = AutomatedBacktest()
    
    return _automated_backtest
