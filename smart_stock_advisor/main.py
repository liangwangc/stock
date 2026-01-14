"""
Smart Stock Advisor 主程序
智能股票预测系统

支持三种模式：
1. 预测模式：分析股票并预测明天走势
2. 实时模式：开盘时间实时获取数据，给出买卖建议
3. 监控模式：持续监控股票，信号变化时提醒
"""
import sys
import os
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, '..', 'quant_trading_platform'))

# 确保可以导入模块
import importlib.util

# 导入data_source
data_source_spec = importlib.util.spec_from_file_location(
    "stock_data_source", 
    os.path.join(project_root, "data_source", "stock_data_source.py")
)
data_source_module = importlib.util.module_from_spec(data_source_spec)
data_source_spec.loader.exec_module(data_source_module)
StockDataSource = data_source_module.StockDataSource

# 导入predictor
from predictor.stock_predictor import StockPredictor

# 导入visualizer
from visualizer.prediction_visualizer import PredictionVisualizer

# 导入实时交易决策顾问
realtime_spec = importlib.util.spec_from_file_location(
    "realtime_trading_advisor",
    os.path.join(project_root, "predictor", "realtime_trading_advisor.py")
)
realtime_module = importlib.util.module_from_spec(realtime_spec)
realtime_spec.loader.exec_module(realtime_module)
RealtimeTradingAdvisor = realtime_module.RealtimeTradingAdvisor

# 导入logger
logger_spec = importlib.util.spec_from_file_location(
    "logger",
    os.path.join(project_root, "utils", "logger.py")
)
logger_module = importlib.util.module_from_spec(logger_spec)
logger_spec.loader.exec_module(logger_module)
get_logger = logger_module.get_logger

# 导入配置
config_spec = importlib.util.spec_from_file_location(
    "config",
    os.path.join(project_root, "config.py")
)
config_module = importlib.util.module_from_spec(config_spec)
config_spec.loader.exec_module(config_module)
BATCH_ANALYSIS_CONFIG = config_module.BATCH_ANALYSIS_CONFIG

logger = get_logger(__name__)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Smart Stock Advisor - 智能股票预测系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  预测模式（分析并预测明天走势）:
    py main.py --symbol 600519
    py main.py --symbol 600519 --simple
    py main.py --all --limit 10
    
  实时模式（开盘时间获取实时数据，给出买卖建议）:
    py main.py --realtime --symbol 600519
    py main.py --realtime --symbol 600519 --holding --cost 1800
    
  监控模式（持续监控，信号变化时提醒）:
    py main.py --monitor --symbol 600519 --interval 30
    py main.py --monitor --symbol 600519 --holding --cost 1800
    
  批量扫描（找出最佳买入机会）:
    py main.py --scan --limit 50
        """
    )
    
    # 基本参数
    parser.add_argument('--symbol', type=str, help='股票代码（如：600519）')
    
    # 预测模式参数
    parser.add_argument('--all', action='store_true', help='预测全部A股（非交互、仅保存CSV，不弹图）')
    parser.add_argument('--limit', type=int, default=0, help='批量预测/扫描限制数量（0表示不限制）')
    parser.add_argument('--simple', action='store_true', help='使用简化版可视化')
    
    # 实时交易模式参数
    parser.add_argument('--realtime', '-r', action='store_true', help='实时交易决策模式')
    parser.add_argument('--monitor', '-m', action='store_true', help='实时监控模式（持续运行）')
    parser.add_argument('--scan', action='store_true', help='批量扫描模式（找出最佳买入机会）')
    parser.add_argument('--interval', '-i', type=int, default=60, help='监控更新间隔（秒），默认60秒')
    
    # 持仓相关参数
    parser.add_argument('--holding', action='store_true', help='是否持有该股票')
    parser.add_argument('--cost', type=float, help='持仓成本价')
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("Smart Stock Advisor - 智能股票预测系统")
    logger.info("=" * 60)
    
    # =====================================================
    # 实时交易模式处理
    # =====================================================
    
    # 批量扫描模式
    if args.scan:
        logger.info("\n进入批量扫描模式：寻找最佳买入机会")
        advisor = RealtimeTradingAdvisor()
        data_source = StockDataSource()
        
        limit_val = args.limit if args.limit > 0 else 50
        stock_list = data_source.get_all_stock_list(limit=limit_val, sort_by_turnover=True)
        symbols = [s['symbol'] for s in stock_list]
        
        opportunities = advisor.batch_scan(symbols, top_n=10)
        
        logger.info(f"\n扫描完成，找到 {len(opportunities)} 个买入机会")
        return
    
    # 实时监控模式
    if args.monitor:
        if not args.symbol:
            logger.error("监控模式需要指定股票代码 (--symbol)")
            return
        
        logger.info(f"\n进入实时监控模式：{args.symbol}")
        advisor = RealtimeTradingAdvisor()
        advisor.monitor_realtime(
            symbol=args.symbol,
            interval_seconds=args.interval,
            holding=args.holding,
            cost_price=args.cost
        )
        return
    
    # 实时交易决策模式
    if args.realtime:
        if not args.symbol:
            logger.error("实时模式需要指定股票代码 (--symbol)")
            return
        
        logger.info(f"\n进入实时交易决策模式：{args.symbol}")
        advisor = RealtimeTradingAdvisor()
        result = advisor.get_realtime_decision(
            symbol=args.symbol,
            holding=args.holding,
            cost_price=args.cost,
            mode="realtime"
        )
        
        if result.get('success', False):
            logger.info("\n实时决策分析完成")
            
            # 生成可视化图表（包含实时数据）
            logger.info("\n正在生成可视化图表（包含实时数据）...")
            predictor = StockPredictor()
            visualizer = PredictionVisualizer()
            data_source = StockDataSource()
            
            # 执行预测分析
            prediction_result = predictor.predict(args.symbol)
            if prediction_result.get('success', False):
                # 获取股票数据
                stock_data = data_source.get_stock_data(args.symbol, days=60)
                
                # 准备实时数据
                realtime_data = {
                    'quote': result.get('realtime_quote', {}),
                    'capital_flow': result.get('capital_flow', {}),
                    'trading_time': result.get('trading_time', {}),
                    'decision': result.get('decision', {}),
                    'prediction': result.get('prediction', {}),
                    'signal_strength': result.get('signal_strength', 0)
                }
                
                # 生成可视化图表
                visualizer.visualize(prediction_result, stock_data, realtime_data)
        else:
            logger.error(f"实时决策分析失败: {result.get('message', '未知错误')}")
        return
    
    # =====================================================
    # 预测模式处理（原有逻辑）
    # =====================================================
    
    # 创建预测器/可视化器/数据源
    predictor = StockPredictor()
    visualizer = PredictionVisualizer()
    data_source = StockDataSource()

    # 批量预测：全部A股（非交互，不生成图表/报告，避免plt.show阻塞）
    if args.all:
        logger.info("\n进入批量预测模式：预测全部A股（仅保存CSV，不弹图）")
        try:
            # 获取股票列表，按成交额排序，如果设置了limit则只取前N只
            limit_val = args.limit if args.limit > 0 else None
            stock_list = data_source.get_all_stock_list(limit=limit_val, sort_by_turnover=True)
        except Exception as e:
            logger.error(f"获取股票列表失败: {str(e)}")
            return

        symbols = [str(item.get('symbol', '')).strip() for item in stock_list if str(item.get('symbol', '')).strip()]

        if not symbols:
            logger.error("股票列表为空，无法批量预测")
            return

        total_count = len(symbols)
        
        # 显示批量分析开始信息
        logger.info("\n" + "=" * 60)
        logger.info(f"开始批量分析股票，共 {total_count} 只股票")
        
        # 读取批量分析配置
        enable_parallel = BATCH_ANALYSIS_CONFIG.get('enable_parallel', True)
        max_workers = BATCH_ANALYSIS_CONFIG.get('max_workers', 3)
        
        if enable_parallel:
            logger.info(f"多线程并行分析模式：同时分析 {max_workers} 只股票")
        else:
            logger.info("单线程顺序分析模式")
        logger.info("=" * 60)
        
        # 线程安全的计数器
        success_count_lock = threading.Lock()
        fail_count_lock = threading.Lock()
        completed_count_lock = threading.Lock()
        progress_lock = threading.Lock()
        
        success_count = 0
        fail_count = 0
        completed_count = 0
        
        # 定义单只股票分析函数（用于多线程执行）
        def analyze_single_stock(symbol, index):
            """分析单只股票（线程安全）"""
            # 声明nonlocal变量（必须在函数开始处）
            nonlocal success_count, fail_count, completed_count
            
            # 每个线程创建独立的实例，避免竞争
            thread_predictor = StockPredictor()
            thread_visualizer = PredictionVisualizer()
            thread_data_source = StockDataSource()
            
            try:
                logger.info(f"[股票 {index}/{total_count}] 开始分析: {symbol}")
                
                # 执行预测
                result = thread_predictor.predict(symbol)
                if not result.get('success', False):
                    with fail_count_lock:
                        fail_count += 1
                    logger.warning(f"[股票 {index}/{total_count}] 预测失败: {symbol} - {result.get('message', '未知错误')}")
                    return False

                # 批量模式下也生成PNG和HTML报告（但不显示图表窗口）
                logger.info(f"[股票 {index}/{total_count}] {symbol} 正在生成图形报告和文字详情...")
                
                # 获取股票数据用于可视化
                stock_data = thread_data_source.get_stock_data(symbol, days=60)
                
                # 尝试获取实时数据（如果可用）
                realtime_data = None
                try:
                    realtime_quote = thread_data_source.get_realtime_quote(symbol)
                    capital_flow = thread_data_source.get_realtime_capital_flow(symbol)
                    trading_time = thread_data_source.is_trading_time()
                    if realtime_quote or capital_flow:
                        realtime_data = {
                            'quote': realtime_quote,
                            'capital_flow': capital_flow,
                            'trading_time': trading_time
                        }
                except Exception as e:
                    logger.debug(f"[股票 {index}/{total_count}] {symbol} 获取实时数据失败: {str(e)}")
                
                # 生成可视化文件（但不调用plt.show()，避免阻塞）
                try:
                    # 使用visualize_no_display_v2方法生成文件，但不显示窗口
                    # 这会生成：PNG文件、interactive.html、full_report.html
                    file_paths = thread_visualizer.visualize_no_display_v2(result, stock_data, realtime_data)
                    if file_paths:
                        png_file = file_paths.get('png_file')
                        interactive_html = file_paths.get('interactive_html')
                        full_report_html = file_paths.get('full_report_html')
                        logger.info(f"[股票 {index}/{total_count}] {symbol} 已生成报告文件:")
                        if png_file:
                            logger.info(f"    PNG图形报告: {png_file}")
                        if interactive_html:
                            logger.info(f"    交互式图表: {interactive_html}")
                        if full_report_html:
                            logger.info(f"    完整HTML报告: {full_report_html}")
                    else:
                        # 如果生成失败，只保存基本数据
                        thread_visualizer.save_stock_record(symbol, result, None, None, None)
                    
                    # 立即生成历史预测页面 history_{symbol}.html
                    try:
                        history_html = thread_visualizer.create_stock_history_page(symbol)
                        if history_html:
                            logger.info(f"[股票 {index}/{total_count}] {symbol} 历史预测页面已生成: {history_html}")
                    except Exception as e:
                        logger.warning(f"[股票 {index}/{total_count}] {symbol} 生成历史预测页面失败: {str(e)}")
                        # 不影响主流程，继续执行
                except Exception as e:
                    logger.warning(f"[股票 {index}/{total_count}] {symbol} 生成图形/文字报告失败: {str(e)}，仅保存CSV数据")
                    import traceback
                    logger.debug(traceback.format_exc())
                    # 即使生成失败，也保存基本预测数据
                    thread_visualizer.save_stock_record(symbol, result, None, None, None)
                
                # 线程安全地更新成功计数
                with success_count_lock:
                    success_count += 1
                
                with completed_count_lock:
                    completed_count += 1
                    current_completed = completed_count
                
                # 更新进度显示
                progress_pct = (current_completed / total_count) * 100
                logger.info(f"[进度: {current_completed}/{total_count}] ({progress_pct:.1f}%) | 成功: {success_count} | 失败: {fail_count}")
                logger.info(f"[股票 {index}/{total_count}] 股票 {symbol} 分析完成！")
                
                # 每完成一只股票预测后，立即更新股票列表页面（使用锁确保不会并发更新）
                try:
                    with progress_lock:
                        # 使用共享的 visualizer 实例更新页面（已加锁保护）
                        update_info = visualizer.create_stock_list_page()
                        if update_info.get('success', False):
                            logger.info(f"  [进度: {current_completed}/{total_count}] 股票列表页面已更新 - 总记录数: {update_info.get('total_records', 0)}, 总股票数: {update_info.get('total_stocks', 0)}")
                            latest_symbols = update_info.get('latest_symbols', [])
                            if latest_symbols:
                                logger.info(f"    最新更新的股票: {', '.join(latest_symbols[:3])}{' ...' if len(latest_symbols) > 3 else ''}")
                        else:
                            logger.warning(f"  [进度: {current_completed}/{total_count}] 股票列表页面更新失败")
                except Exception as e:
                    logger.warning(f"  [进度: {current_completed}/{total_count}] 更新股票列表页面失败: {str(e)}")
                    # 不影响后续处理，继续执行
                
                return True
            except Exception as e:
                # 线程安全地更新失败计数
                with fail_count_lock:
                    fail_count += 1
                
                with completed_count_lock:
                    completed_count += 1
                    current_completed = completed_count
                
                progress_pct = (current_completed / total_count) * 100
                logger.warning(f"[股票 {index}/{total_count}] ({progress_pct:.1f}%) 预测异常: {symbol} - {str(e)}")
                return False
        
        # 根据配置选择多线程或单线程模式
        if enable_parallel and max_workers > 1:
            # 多线程并行分析模式
            logger.info(f"\n使用多线程并行分析模式（并发数: {max_workers}）...")
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有任务
                future_to_symbol = {
                    executor.submit(analyze_single_stock, symbol, i+1): (symbol, i+1)
                    for i, symbol in enumerate(symbols)
                }
                
                # 等待所有任务完成
                for future in as_completed(future_to_symbol):
                    symbol, index = future_to_symbol[future]
                    try:
                        future.result()
                    except Exception as e:
                        logger.error(f"[股票 {index}/{total_count}] {symbol} 执行异常: {str(e)}")
        else:
            # 单线程顺序分析模式（保持原有逻辑）
            logger.info("\n使用单线程顺序分析模式...")
            for i, symbol in enumerate(symbols, start=1):
                analyze_single_stock(symbol, i)

        # 显示批量分析完成总结
        logger.info("\n" + "=" * 60)
        logger.info(f"批量分析完成！")
        logger.info(f"  总计: {total_count} 只股票")
        logger.info(f"  成功: {success_count} 只 ({(success_count/total_count*100):.1f}%)")
        logger.info(f"  失败: {fail_count} 只 ({(fail_count/total_count*100):.1f}%)")
        logger.info("=" * 60)

        # 最后再次生成/更新股票列表页面（确保最终状态是最新的）
        logger.info("\n正在生成股票列表页面（最终更新）...")
        try:
            update_info = visualizer.create_stock_list_page()
            if update_info.get('success', False):
                logger.info(f"股票列表页面最终更新完成 - 总记录数: {update_info.get('total_records', 0)}, 总股票数: {update_info.get('total_stocks', 0)}")
                latest_symbols = update_info.get('latest_symbols', [])
                if latest_symbols:
                    logger.info(f"最新更新的股票: {', '.join(latest_symbols)}")
            else:
                logger.warning(f"股票列表页面最终更新失败")
        except Exception as e:
            logger.warning(f"最终更新股票列表页面失败: {str(e)}")

        logger.info("\n" + "=" * 60)
        logger.info("批量预测完成！")
        logger.info("=" * 60)
        return

    # 单股模式：获取股票代码
    if args.symbol:
        symbol = args.symbol
    else:
        # 导入默认股票代码配置
        import config
        default_symbol = getattr(config, 'DEFAULT_STOCK_SYMBOL', None)

        if default_symbol:
            user_input = input(f"\n请输入股票代码（直接回车使用默认: {default_symbol}）: ").strip()
            symbol = user_input if user_input else default_symbol
        else:
            symbol = input("\n请输入股票代码（如：600519）: ").strip()

    if not symbol:
        logger.error("股票代码不能为空")
        return
    
    # 执行预测
    try:
        result = predictor.predict(symbol)
        
        if not result.get('success', False):
            logger.error(f"预测失败: {result.get('message', '未知错误')}")
            return
        
        # 预测完成后立即保存预测记录（不需要等待可视化）
        logger.info("\n正在保存预测记录...")
        visualizer.save_stock_record(symbol, result, None, None, None)  # 先保存基本预测数据，文件路径稍后更新
        
        # 可视化结果（可选，不影响数据保存）
        logger.info("\n正在生成可视化图表...")
        
        # 获取股票数据用于可视化
        stock_data = data_source.get_stock_data(symbol, days=60)
        
        # 尝试获取实时数据（如果可用）
        realtime_data = None
        try:
            realtime_quote = data_source.get_realtime_quote(symbol)
            capital_flow = data_source.get_realtime_capital_flow(symbol)
            trading_time = data_source.is_trading_time()
            if realtime_quote or capital_flow:
                realtime_data = {
                    'quote': realtime_quote,
                    'capital_flow': capital_flow,
                    'trading_time': trading_time
                }
        except Exception as e:
            logger.debug(f"获取实时数据失败: {str(e)}")
        
        png_file = None
        full_report_html = None
        
        if args.simple:
            # 简化版不生成PNG和HTML报告
            visualizer.visualize_simple(result)
            png_file = None
            full_report_html = None
        else:
            # visualize方法返回文件路径（内部会更新CSV记录）
            # 这会生成：PNG文件、interactive.html、full_report.html
            file_paths = visualizer.visualize(result, stock_data, realtime_data)
            if file_paths:
                png_file = file_paths.get('png_file')
                interactive_html = file_paths.get('interactive_html')
                full_report_html = file_paths.get('full_report_html')
                logger.info(f"已生成报告文件:")
                if png_file:
                    logger.info(f"  PNG图形报告: {png_file}")
                if interactive_html:
                    logger.info(f"  交互式图表: {interactive_html}")
                if full_report_html:
                    logger.info(f"  完整HTML报告: {full_report_html}")
                
                # 更新预测记录的文件路径
                visualizer.save_stock_record(symbol, result, png_file, full_report_html, interactive_html)
            else:
                png_file = None
                full_report_html = None
                # 即使文件生成失败，也保存基本预测数据
                visualizer.save_stock_record(symbol, result, None, None, None)
            
            # 立即生成历史预测页面 history_{symbol}.html
            try:
                logger.info(f"\n正在生成历史预测页面...")
                history_html = visualizer.create_stock_history_page(symbol)
                if history_html:
                    logger.info(f"历史预测页面已生成: {history_html}")
            except Exception as e:
                logger.warning(f"生成历史预测页面失败: {str(e)}")
                # 不影响主流程，继续执行
        
        # 生成/更新股票列表页面
        logger.info("\n正在生成股票列表页面...")
        try:
            update_info = visualizer.create_stock_list_page()
            if update_info.get('success', False):
                logger.info(f"股票列表页面已更新 - 总记录数: {update_info.get('total_records', 0)}, 总股票数: {update_info.get('total_stocks', 0)}")
            else:
                logger.warning(f"股票列表页面更新失败")
        except Exception as e:
            logger.warning(f"更新股票列表页面失败: {str(e)}")
        
        # 打印综合文字总结
        logger.info("\n" + "=" * 60)
        logger.info("明日走势综合总结")
        logger.info("=" * 60)
        summary = result.get('summary')
        if summary:
            logger.info(summary)
        else:
            logger.info("（暂无总结文本）")

        # 打印详细结果
        logger.info("\n" + "=" * 60)
        logger.info("详细预测结果")
        logger.info("=" * 60)
        
        factors = result['factors']
        logger.info("\n各因素分析:")
        logger.info(f"  技术指标: {factors['technical']['score']:.2f} ({factors['technical']['trend']})")
        logger.info(f"  新闻情感: {factors['news']['score']:.2f} ({factors['news']['sentiment']})")
        logger.info(f"  市场情绪: {factors['market']['score']:.2f} ({factors['market']['trend']})")
        logger.info(f"  历史模式: {factors['history']['score']:.2f}")
        
        logger.info("\n技术指标信号:")
        for signal_name, signal_value in factors['technical']['signals'].items():
            logger.info(f"  {signal_name}: {signal_value}")
        
        logger.info("\n" + "=" * 60)
        logger.info("预测完成！")
        logger.info("=" * 60)
        
    except KeyboardInterrupt:
        logger.info("\n用户中断")
    except Exception as e:
        logger.error(f"预测过程出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()

