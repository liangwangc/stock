"""
自动化定期回测测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from utils.automated_backtest import AutomatedBacktest, get_automated_backtest


class TestAutomatedBacktest:
    """AutomatedBacktest测试类"""
    
    @patch('utils.automated_backtest.USE_DATABASE', False)
    def test_init(self):
        """测试初始化"""
        backtest = AutomatedBacktest()
        assert backtest.use_database is not None
        assert backtest.evaluator is not None
        assert backtest.backtest_engine is not None
    
    @patch('utils.automated_backtest.ModelPerformanceEvaluator')
    @patch('utils.automated_backtest.BacktestEngine')
    def test_run_periodic_backtest(self, mock_backtest_engine, mock_evaluator):
        """测试执行定期回测"""
        # 模拟评估结果
        mock_eval_result = {
            'success': True,
            'direction_accuracy': 0.6,
            'sample_count': 100
        }
        
        # 模拟回测结果
        mock_backtest_result = {
            'success': True,
            'total_return': 0.1,
            'max_drawdown': -0.05
        }
        
        mock_evaluator_instance = Mock()
        mock_evaluator_instance.evaluate_prediction_performance = Mock(return_value=mock_eval_result)
        mock_evaluator.return_value = mock_evaluator_instance
        
        mock_backtest_instance = Mock()
        mock_backtest_instance.backtest_predictions = Mock(return_value=mock_backtest_result)
        mock_backtest_engine.return_value = mock_backtest_instance
        
        backtest = AutomatedBacktest()
        backtest.evaluator = mock_evaluator_instance
        backtest.backtest_engine = mock_backtest_instance
        
        result = backtest.run_periodic_backtest(days=30, save_to_db=False)
        
        assert result['success'] is True
        assert 'prediction_performance' in result
        assert 'backtest_result' in result
        assert 'alerts' in result
    
    def test_check_performance_alerts(self):
        """测试检查性能告警"""
        backtest = AutomatedBacktest()
        
        # 正常性能（无告警）
        prediction_result = {
            'direction_accuracy': 0.55,  # 55%准确率
            'sample_count': 100
        }
        backtest_result = {
            'total_return': 0.05,  # 5%收益率
            'max_drawdown': -0.03  # 3%回撤
        }
        
        alerts = backtest._check_performance_alerts(prediction_result, backtest_result)
        assert isinstance(alerts, list)
        
        # 低准确率（应该有告警）
        prediction_result['direction_accuracy'] = 0.45  # 45%准确率
        alerts = backtest._check_performance_alerts(prediction_result, backtest_result)
        assert len(alerts) > 0
        assert any(a['type'] == 'prediction_accuracy' for a in alerts)
        
        # 负收益（应该有告警）
        backtest_result['total_return'] = -0.15  # -15%收益率
        alerts = backtest._check_performance_alerts(prediction_result, backtest_result)
        assert any(a['type'] == 'backtest_return' for a in alerts)
    
    def test_singleton(self):
        """测试单例模式"""
        backtest1 = get_automated_backtest()
        backtest2 = get_automated_backtest()
        assert backtest1 is backtest2
