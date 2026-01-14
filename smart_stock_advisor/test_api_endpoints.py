"""
测试预测参数配置API端点
需要先启动web服务: py web_app.py
"""
import requests
import json
import sys

BASE_URL = "http://localhost:5000"

def test_api_login():
    """测试登录"""
    print("\n" + "=" * 60)
    print("测试API: 登录")
    print("=" * 60)
    
    session = requests.Session()
    try:
        # 先访问登录页面获取CSRF token（如果需要）
        response = session.post(
            f"{BASE_URL}/login",
            data={
                'username': 'admin',
                'password': 'admin@123'
            },
            allow_redirects=False
        )
        
        if response.status_code in [200, 302]:
            print("[OK] 登录成功")
            return session
        else:
            print(f"[ERROR] 登录失败: {response.status_code}")
            return None
    except Exception as e:
        print(f"[ERROR] 登录请求失败: {str(e)}")
        print("提示: 请确保web服务已启动 (py web_app.py)")
        return None


def test_get_configs(session):
    """测试获取配置列表"""
    print("\n" + "=" * 60)
    print("测试API: 获取配置列表")
    print("=" * 60)
    
    try:
        response = session.get(f"{BASE_URL}/api/prediction/configs")
        result = response.json()
        
        if result.get('success'):
            configs = result.get('data', [])
            print(f"[OK] 获取配置列表成功，共 {len(configs)} 个配置")
            for config in configs[:3]:
                print(f"   - {config.get('config_name')} (ID: {config.get('id')})")
            return True
        else:
            print(f"[ERROR] 获取配置列表失败: {result.get('message')}")
            return False
    except Exception as e:
        print(f"[ERROR] 请求失败: {str(e)}")
        return False


def test_get_active_config(session):
    """测试获取激活配置"""
    print("\n" + "=" * 60)
    print("测试API: 获取激活配置")
    print("=" * 60)
    
    try:
        response = session.get(f"{BASE_URL}/api/prediction/config/active")
        result = response.json()
        
        if result.get('success'):
            data = result.get('data', {})
            if data.get('info'):
                print(f"[OK] 获取激活配置成功: {data['info'].get('config_name')}")
                print(f"   - 配置ID: {data['info'].get('id')}")
                if data.get('values'):
                    print(f"   - 包含预测配置: {len(data['values'].get('prediction', {}))} 个参数")
                    print(f"   - 包含技术指标配置: {len(data['values'].get('indicator', {}))} 个参数")
            else:
                print("[OK] 当前没有激活的配置，使用config.py默认值")
            return True
        else:
            print(f"[ERROR] 获取激活配置失败: {result.get('message')}")
            return False
    except Exception as e:
        print(f"[ERROR] 请求失败: {str(e)}")
        return False


def test_validate_config(session):
    """测试配置验证"""
    print("\n" + "=" * 60)
    print("测试API: 验证配置")
    print("=" * 60)
    
    try:
        # 测试正确的配置
        valid_config = {
            'values': {
                'prediction': {
                    'news_weight': 0.25,
                    'capital_flow_weight': 0.18,
                    'market_weight': 0.17,
                    'technical_weight': 0.20,
                    'sector_rotation_weight': 0.05,
                    'history_weight': 0.08,
                    'us_sector_weight': 0.05,
                    'valuation_weight': 0.02
                },
                'indicator': {
                    'ma_short': 5,
                    'ma_long': 20
                }
            }
        }
        
        response = session.post(
            f"{BASE_URL}/api/prediction/config/validate",
            json=valid_config,
            headers={'Content-Type': 'application/json'}
        )
        result = response.json()
        
        if result.get('success') and result.get('is_valid'):
            print("[OK] 正确配置验证通过")
            
            # 测试错误的配置
            invalid_config = {
                'values': {
                    'prediction': {
                        'news_weight': 0.30,
                        'capital_flow_weight': 0.30,
                        'market_weight': 0.30,
                        'technical_weight': 0.20,
                        'sector_rotation_weight': 0.05,
                        'history_weight': 0.08,
                        'us_sector_weight': 0.05,
                        'valuation_weight': 0.02
                    }
                }
            }
            
            response2 = session.post(
                f"{BASE_URL}/api/prediction/config/validate",
                json=invalid_config,
                headers={'Content-Type': 'application/json'}
            )
            result2 = response2.json()
            
            if not result2.get('is_valid'):
                print(f"[OK] 错误配置验证失败（符合预期）: {result2.get('message')}")
                return True
            else:
                print("[ERROR] 错误配置验证通过（不符合预期）")
                return False
        else:
            print(f"[ERROR] 配置验证失败: {result.get('message')}")
            return False
    except Exception as e:
        print(f"[ERROR] 请求失败: {str(e)}")
        return False


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("预测参数配置API端点测试")
    print("=" * 60)
    print("\n注意: 请确保web服务已启动 (py web_app.py)")
    print("按Enter继续测试，或Ctrl+C退出...")
    
    try:
        input()
    except:
        print("\n测试已取消")
        return
    
    results = []
    
    # 测试登录
    session = test_api_login()
    results.append(('API登录', session is not None))
    
    if not session:
        print("\n[ERROR] 无法登录，后续测试无法进行")
        print("请检查:")
        print("1. Web服务是否已启动 (py web_app.py)")
        print("2. 用户名密码是否正确 (admin/admin@123)")
        return
    
    # 测试获取配置列表
    results.append(('获取配置列表', test_get_configs(session)))
    
    # 测试获取激活配置
    results.append(('获取激活配置', test_get_active_config(session)))
    
    # 测试配置验证
    results.append(('配置验证', test_validate_config(session)))
    
    # 输出测试结果汇总
    print("\n" + "=" * 60)
    print("API测试结果汇总")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "[OK] 通过" if result else "[ERROR] 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"总计: {len(results)} 个测试")
    print(f"通过: {passed} 个")
    print(f"失败: {failed} 个")
    print("=" * 60)
    
    if failed == 0:
        print("\n[OK] 所有API测试通过！")
    else:
        print("\n[ERROR] 部分API测试失败，请检查web服务是否正常运行")


if __name__ == '__main__':
    main()
