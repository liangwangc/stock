import traceback
from datetime import datetime

import akshare as ak
import pandas as pd


def print_header(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def safe_show_df(df: pd.DataFrame, max_rows: int = 5) -> None:
    """安全打印 DataFrame 的前几行，避免内容太长。"""
    if df is None:
        print("DataFrame 为 None")
        return
    if len(df) == 0:
        print("返回空数据（0 行）")
        return

    print(f"总行数: {len(df)}")
    print(df.head(max_rows))


def test_cls_news():
    """测试：财联社新闻（你当前正式使用的接口）"""
    print_header("测试 财联社新闻 (ak.stock_info_global_cls)")
    try:
        df = ak.stock_info_global_cls(symbol="全部")
        safe_show_df(df)
        print("状态: ✅ 接口调用成功")
    except Exception as e:
        print("状态: ❌ 接口调用失败")
        print("错误类型:", type(e).__name__)
        print("错误信息:", e)
        traceback.print_exc()


def test_js_news():
    """测试：金十快讯 / 新闻 (ak.js_news)"""
    print_header("测试 金十新闻 (ak.js_news)")
    # 部分 AkShare 版本没有 js_news 接口，这里先做存在性检查，避免报 AttributeError
    if not hasattr(ak, "js_news"):
        print("状态: ⚠ 当前 AkShare 版本不包含 ak.js_news 接口，跳过金十新闻测试")
        print("如需使用金十新闻，请先执行: pip install -U akshare 升级到最新版本后再测试。")
        return
    try:
        # indicator 参数不同版本文档略有差异，这里使用常见的 '最新资讯'
        df = ak.js_news(indicator="最新资讯")
        safe_show_df(df)
        print("状态: ✅ 接口调用成功")
    except Exception as e:
        print("状态: ❌ 接口调用失败")
        print("错误类型:", type(e).__name__)
        print("错误信息:", e)
        traceback.print_exc()


def test_stock_news_em():
    """测试：东方财富个股新闻 (ak.stock_news_em)"""
    print_header("测试 东方财富个股新闻 (ak.stock_news_em)")

    # 可以根据自己数据库里常用的股票代码来改这里
    test_symbols = ["600000", "000001", "300750"]  # 测试几只常见股票

    for symbol in test_symbols:
        print(f"\n--- 测试股票代码: {symbol} ---")
        try:
            df = ak.stock_news_em(symbol=symbol)
            safe_show_df(df)
            print(f"状态: ✅ {symbol} 接口调用成功")
        except Exception as e:
            print(f"状态: ❌ {symbol} 接口调用失败")
            print("错误类型:", type(e).__name__)
            print("错误信息:", e)
            traceback.print_exc()


def main():
    print_header(f"AkShare 新闻接口连通性测试 - {datetime.now()}")

    # 1. 财联社（当前已在项目中使用）
    test_cls_news()

    # 2. 金十新闻 / 快讯
    test_js_news()

    # 3. 东方财富个股新闻
    test_stock_news_em()

    print("\n全部测试完成，可以根据打印结果判断哪些接口可用。")


if __name__ == "__main__":
    main()

