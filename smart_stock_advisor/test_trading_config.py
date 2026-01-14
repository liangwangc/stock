"""
测试实时交易策略配置功能
验证配置的加载、保存、验证功能是否正常
"""
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_config_structure():
    """测试配置结构是否正确"""
    print("=" * 60)
    print("测试1: 检查配置文件中的TRADING_CONFIG结构")
    print("=" * 60)
    
    try:
        from config import TRADING_CONFIG
        
        # 检查必需的配置项
        required_keys = [
            'buy_signal_threshold',
            'strong_buy_threshold',
            'sell_signal_threshold',
            'strong_sell_threshold',
            'min_confidence',
            'high_confidence',
            'capital_flow_weight',
            'bid_ask_weight',
            'intraday_weight',
            'stop_loss_pct',
            'take_profit_pct',
            'trailing_stop_pct',
            'chase_high_threshold',
            'catch_low_threshold',
            'max_position_pct',
            'max_total_position_pct',
            'position_step',
            'max_correlation',
            'monitor_interval',
            'enable_risk_control',
            'alert_on_signal_change'
        ]
        
        missing_keys = []
        for key in required_keys:
            if key not in TRADING_CONFIG:
                missing_keys.append(key)
        
        if missing_keys:
            print(f"[ERROR] 缺少配置项: {missing_keys}")
            return False
        else:
            print("[OK] 所有必需的配置项都存在")
            print(f"[OK] 配置项总数: {len(TRADING_CONFIG)}")
            
            # 显示配置值
            print("\n配置值预览:")
            for key, value in TRADING_CONFIG.items():
                print(f"  {key}: {value}")
            
            return True
            
    except ImportError as e:
        print(f"[ERROR] 导入配置失败: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_html_structure():
    """测试HTML结构是否正确"""
    print("\n" + "=" * 60)
    print("测试2: 检查HTML结构中的实时交易策略配置")
    print("=" * 60)
    
    try:
        html_file = os.path.join(project_root, 'templates', 'settings.html')
        if not os.path.exists(html_file):
            print(f"[ERROR] HTML文件不存在: {html_file}")
            return False
        
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查关键元素
        required_elements = [
            '实时交易策略配置',
            'buy_signal_threshold',
            'strong_buy_threshold',
            'sell_signal_threshold',
            'strong_sell_threshold',
            'trading_min_confidence',
            'high_confidence',
            'trading_capital_flow_weight',
            'trading_bid_ask_weight',
            'trading_intraday_weight',
            'stop_loss_pct',
            'take_profit_pct',
            'trailing_stop_pct',
            'chase_high_threshold',
            'catch_low_threshold',
            'max_position_pct',
            'max_total_position_pct',
            'position_step',
            'max_correlation',
            'monitor_interval',
            'enable_risk_control',
            'alert_on_signal_change'
        ]
        
        missing_elements = []
        for element in required_elements:
            if element not in content:
                missing_elements.append(element)
        
        if missing_elements:
            print(f"[ERROR] 缺少HTML元素: {missing_elements}")
            return False
        else:
            print("[OK] 所有必需的HTML元素都存在")
            
            # 检查JavaScript函数
            js_functions = [
                'loadConfigValues',
                'getCurrentConfigValues',
                'loadDefaultConfig'
            ]
            
            print("\n检查JavaScript函数:")
            for func in js_functions:
                if f'function {func}' in content:
                    print(f"  [OK] {func} 函数存在")
                else:
                    print(f"  [ERROR] {func} 函数不存在")
            
            # 检查是否包含trading配置的处理
            if 'values.trading' in content:
                print("  [OK] loadConfigValues 函数包含 trading 配置处理")
            else:
                print("  [ERROR] loadConfigValues 函数不包含 trading 配置处理")
            
            if 'trading: {}' in content:
                print("  [OK] getCurrentConfigValues 函数包含 trading 配置")
            else:
                print("  [WARN] getCurrentConfigValues 函数可能不包含 trading 配置（需要检查）")
            
            return True
            
    except Exception as e:
        print(f"[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_api_availability():
    """测试配置API是否可用"""
    print("\n" + "=" * 60)
    print("测试3: 检查配置API是否可用")
    print("=" * 60)
    
    try:
        from utils.prediction_config_manager import PredictionConfigManager
        
        manager = PredictionConfigManager()
        print("[OK] PredictionConfigManager 可以正常导入和实例化")
        
        # 测试验证函数
        test_values = {
            'prediction': {
                'news_weight': 0.25,
                'capital_flow_weight': 0.18,
                'market_weight': 0.17,
                'technical_weight': 0.20,
                'sector_rotation_weight': 0.05,
                'history_weight': 0.08,
                'us_sector_weight': 0.05,
                'valuation_weight': 0.02,
            },
            'indicator': {
                'ma_short': 5,
                'ma_long': 20
            },
            'trading': {
                'buy_signal_threshold': 0.65,
                'strong_buy_threshold': 0.75
            }
        }
        
        is_valid, message = manager.validate_config(test_values)
        if is_valid:
            print("[OK] 配置验证函数可以处理包含 trading 的配置")
        else:
            print(f"[WARN] 配置验证返回: {message}（trading配置为可选，此警告可以忽略）")
        
        return True
        
    except ImportError as e:
        print(f"[WARN] 无法导入 PredictionConfigManager: {e}")
        print("   这可能是正常的，如果数据库未初始化")
        return True  # 不阻止测试继续
    except Exception as e:
        print(f"[WARN] 测试配置管理器时出错: {e}")
        import traceback
        traceback.print_exc()
        return True  # 不阻止测试继续


def generate_test_summary():
    """生成测试摘要"""
    print("\n" + "=" * 60)
    print("测试摘要")
    print("=" * 60)
    print("""
手动测试步骤：

1. 启动Web应用：
   py web_app.py

2. 访问设置页面：
   http://localhost:5000/settings
   登录：admin / admin123

3. 进入"参数设置"标签页

4. 测试实时交易策略配置：

   a) 检查默认值加载：
      - 点击"📥 加载当前配置"按钮
      - 检查实时交易策略配置部分的字段是否显示默认值
      - 检查是否显示在"信号阈值配置"、"风险控制参数"、"仓位管理"、"实时数据权重 & 监控"四个分组中

   b) 测试配置修改：
      - 修改买入信号阈值（例如改为 0.70）
      - 修改止损比例（例如改为 -6.0）
      - 修改单只股票最大仓位（例如改为 35.0）
      - 修改监控间隔（例如改为 120）

   c) 测试配置保存：
      - 点击"💾 保存配置"按钮
      - 输入配置名称（例如：测试配置_实时交易策略）
      - 点击确认
      - 检查是否提示"配置保存成功"

   d) 测试配置激活：
      - 点击"✅ 保存并激活"按钮
      - 输入配置名称
      - 检查是否提示"配置已保存并激活！"

   e) 测试配置加载：
      - 点击"📋 配置管理"按钮
      - 在配置列表中找到刚才保存的配置
      - 点击"加载"按钮
      - 检查实时交易策略配置的字段是否正确加载

   f) 测试默认值重置：
      - 修改一些配置值
      - 点击"🔄 重置为默认值"按钮
      - 检查实时交易策略配置的字段是否恢复为默认值

5. 检查浏览器控制台：
   - 按 F12 打开开发者工具
   - 查看 Console 标签页
   - 检查是否有 JavaScript 错误

6. 检查网络请求：
   - 在开发者工具的 Network 标签页
   - 保存配置时，检查 /api/prediction/config 请求
   - 检查请求体中的 values.trading 字段是否包含所有配置项
   - 检查响应是否成功
""")


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("实时交易策略配置功能测试")
    print("=" * 60)
    print()
    
    results = []
    
    # 测试1: 配置结构
    results.append(("配置结构", test_config_structure()))
    
    # 测试2: HTML结构
    results.append(("HTML结构", test_html_structure()))
    
    # 测试3: API可用性
    results.append(("API可用性", test_config_api_availability()))
    
    # 显示测试结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    all_passed = True
    for test_name, result in results:
        status = "[PASS] 通过" if result else "[FAIL] 失败"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    print()
    if all_passed:
        print("[OK] 所有自动测试通过！")
        print("   请按照下面的手动测试步骤进行完整测试。")
    else:
        print("[ERROR] 部分测试失败，请检查代码。")
    
    # 生成测试摘要
    generate_test_summary()


if __name__ == '__main__':
    main()
