"""
模型学习系统功能测试脚本
用于验证所有模块是否正常工作
"""
import os
import sys
from datetime import datetime, timedelta

# 修复Windows控制台编码问题
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def print_section(title):
    """打印章节标题"""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)

def test_imports():
    """测试模块导入"""
    print_section("1. 测试模块导入")
    
    results = {}
    
    # 测试性能评估模块
    try:
        from utils.model_performance_evaluator import ModelPerformanceEvaluator
        results['ModelPerformanceEvaluator'] = True
        print("✓ ModelPerformanceEvaluator 导入成功")
    except Exception as e:
        results['ModelPerformanceEvaluator'] = False
        print(f"✗ ModelPerformanceEvaluator 导入失败: {str(e)}")
    
    # 测试回测引擎
    try:
        from utils.backtest_engine import BacktestEngine
        results['BacktestEngine'] = True
        print("✓ BacktestEngine 导入成功")
    except Exception as e:
        results['BacktestEngine'] = False
        print(f"✗ BacktestEngine 导入失败: {str(e)}")
    
    # 测试参数优化模块
    try:
        from utils.model_optimizer import ModelOptimizer
        results['ModelOptimizer'] = True
        print("✓ ModelOptimizer 导入成功")
    except Exception as e:
        results['ModelOptimizer'] = False
        print(f"✗ ModelOptimizer 导入失败: {str(e)}")
    
    # 测试参数更新模块
    try:
        from utils.model_parameter_updater import ModelParameterUpdater
        results['ModelParameterUpdater'] = True
        print("✓ ModelParameterUpdater 导入成功")
    except Exception as e:
        results['ModelParameterUpdater'] = False
        print(f"✗ ModelParameterUpdater 导入失败: {str(e)}")
    
    # 测试数据库连接
    try:
        from utils.db_connection import DatabaseConnection
        results['DatabaseConnection'] = True
        print("✓ DatabaseConnection 导入成功")
    except Exception as e:
        results['DatabaseConnection'] = False
        print(f"✗ DatabaseConnection 导入失败: {str(e)}")
    
    return results

def test_database_tables():
    """测试数据库表是否存在"""
    print_section("2. 测试数据库表")
    
    try:
        from utils.db_connection import DatabaseConnection
        db = DatabaseConnection()
        
        tables_to_check = [
            'model_performance',
            'parameter_optimization_history',
            'model_learning_tasks',
            'stock_predictions'
        ]
        
        results = {}
        for table in tables_to_check:
            try:
                sql = f"SELECT 1 FROM {table} LIMIT 1"
                db.execute_query(sql)
                results[table] = True
                print(f"✓ 表 {table} 存在")
            except Exception as e:
                results[table] = False
                print(f"✗ 表 {table} 不存在或无法访问: {str(e)}")
        
        return results
    except Exception as e:
        print(f"✗ 数据库连接失败: {str(e)}")
        return {}

def test_module_initialization():
    """测试模块初始化"""
    print_section("3. 测试模块初始化")
    
    results = {}
    
    # 测试性能评估模块初始化
    try:
        from utils.model_performance_evaluator import ModelPerformanceEvaluator
        evaluator = ModelPerformanceEvaluator()
        results['evaluator'] = True
        print("✓ ModelPerformanceEvaluator 初始化成功")
    except Exception as e:
        results['evaluator'] = False
        print(f"✗ ModelPerformanceEvaluator 初始化失败: {str(e)}")
    
    # 测试回测引擎初始化
    try:
        from utils.backtest_engine import BacktestEngine
        engine = BacktestEngine()
        results['engine'] = True
        print("✓ BacktestEngine 初始化成功")
    except Exception as e:
        results['engine'] = False
        print(f"✗ BacktestEngine 初始化失败: {str(e)}")
    
    # 测试参数优化模块初始化
    try:
        from utils.model_optimizer import ModelOptimizer
        optimizer = ModelOptimizer()
        results['optimizer'] = True
        print("✓ ModelOptimizer 初始化成功")
    except Exception as e:
        results['optimizer'] = False
        print(f"✗ ModelOptimizer 初始化失败: {str(e)}")
    
    # 测试参数更新模块初始化
    try:
        from utils.model_parameter_updater import ModelParameterUpdater
        updater = ModelParameterUpdater()
        results['updater'] = True
        print("✓ ModelParameterUpdater 初始化成功")
    except Exception as e:
        results['updater'] = False
        print(f"✗ ModelParameterUpdater 初始化失败: {str(e)}")
    
    return results

def test_basic_functionality():
    """测试基本功能"""
    print_section("4. 测试基本功能")
    
    results = {}
    
    # 测试查询优化历史（不需要实际数据）
    try:
        from utils.model_parameter_updater import ModelParameterUpdater
        updater = ModelParameterUpdater()
        history = updater.get_optimization_history(limit=5)
        results['get_history'] = True
        print(f"✓ 查询优化历史成功（返回 {len(history)} 条记录）")
    except Exception as e:
        results['get_history'] = False
        print(f"✗ 查询优化历史失败: {str(e)}")
    
    # 测试数据库查询（检查是否有历史数据）
    try:
        from utils.db_connection import DatabaseConnection
        db = DatabaseConnection()
        
        # 检查是否有预测数据
        sql = "SELECT COUNT(*) as cnt FROM stock_predictions"
        result = db.execute_query(sql)
        count = result[0]['cnt'] if result else 0
        results['check_data'] = True
        print(f"✓ 数据库查询成功，stock_predictions 表有 {count} 条记录")
    except Exception as e:
        results['check_data'] = False
        print(f"✗ 数据库查询失败: {str(e)}")
    
    return results

def test_web_api_endpoints():
    """测试Web API端点是否存在"""
    print_section("5. 测试Web API端点")
    
    try:
        import web_app
        
        endpoints = [
            ('api_model_evaluate', 'GET /api/model/evaluate'),
            ('api_model_optimize', 'POST /api/model/optimize'),
            ('api_get_optimization_history', 'GET /api/model/optimization-history'),
            ('api_apply_optimization', 'POST /api/model/apply-optimization/<id>')
        ]
        
        results = {}
        for func_name, endpoint in endpoints:
            if hasattr(web_app, func_name):
                results[endpoint] = True
                print(f"✓ {endpoint} 端点存在")
            else:
                results[endpoint] = False
                print(f"✗ {endpoint} 端点不存在")
        
        return results
    except Exception as e:
        print(f"✗ 无法检查Web API端点: {str(e)}")
        return {}

def test_web_interface():
    """测试Web界面文件是否存在"""
    print_section("6. 测试Web界面文件")
    
    files_to_check = [
        'templates/settings.html',
        'templates/graph_report.html',
        'templates/text_detail.html',
        'templates/history.html',
        'templates/realtime_strategy.html'
    ]
    
    results = {}
    for file_path in files_to_check:
        full_path = os.path.join(project_root, file_path)
        if os.path.exists(full_path):
            results[file_path] = True
            print(f"✓ {file_path} 存在")
            
            # 检查模型学习相关内容
            if file_path == 'templates/settings.html':
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'panel-model-learning' in content:
                        print("  ✓ 包含模型学习面板")
                    if 'runPerformanceEvaluation' in content:
                        print("  ✓ 包含性能评估函数")
                    if 'runParameterOptimization' in content:
                        print("  ✓ 包含参数优化函数")
        else:
            results[file_path] = False
            print(f"✗ {file_path} 不存在")
    
    return results

def generate_summary(all_results):
    """生成测试总结"""
    print_section("测试总结")
    
    total_tests = 0
    passed_tests = 0
    
    for category, results in all_results.items():
        if results:
            category_total = len(results)
            category_passed = sum(1 for v in results.values() if v)
            total_tests += category_total
            passed_tests += category_passed
            
            percentage = (category_passed / category_total * 100) if category_total > 0 else 0
            status = "✓" if category_passed == category_total else "⚠"
            print(f"{status} {category}: {category_passed}/{category_total} ({percentage:.1f}%)")
    
    overall_percentage = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    print(f"\n总体: {passed_tests}/{total_tests} ({overall_percentage:.1f}%)")
    
    if overall_percentage == 100:
        print("\n✓ 所有测试通过！系统可以正常使用。")
    elif overall_percentage >= 80:
        print("\n⚠ 大部分测试通过，部分功能可能不可用。")
    else:
        print("\n✗ 多项测试失败，请检查系统配置。")

def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print(" 模型学习系统功能测试")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_results = {}
    
    # 执行各项测试
    all_results['模块导入'] = test_imports()
    all_results['数据库表'] = test_database_tables()
    all_results['模块初始化'] = test_module_initialization()
    all_results['基本功能'] = test_basic_functionality()
    all_results['Web API端点'] = test_web_api_endpoints()
    all_results['Web界面文件'] = test_web_interface()
    
    # 生成总结
    generate_summary(all_results)
    
    print("\n" + "=" * 60)
    print(" 测试完成")
    print("=" * 60)

if __name__ == '__main__':
    main()
