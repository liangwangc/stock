import akshare as ak
import pandas as pd
import hashlib
import json
from datetime import datetime
from sqlalchemy import create_engine, text
import time

from ..config.config import DATABASE_URL
from .stock_mapper import StockMapper
from .simple_sentiment_analyzer import SimpleSentimentAnalyzer

# 初始化数据库引擎（与财联社脚本保持一致，直接写入 stock_data.news_articles）
engine = create_engine(DATABASE_URL)

# 初始化股票匹配器与情感分析器（与财联社脚本共用一套逻辑）
stock_mapper = StockMapper()
sentiment_analyzer = SimpleSentimentAnalyzer()


def generate_hash(row):
    """根据新闻标题和内容生成唯一哈希（与 get_cls_news 保持一致）"""
    combined = str(row.get("title", "")) + str(row.get("content", ""))
    return hashlib.md5(combined.encode("utf-8")).hexdigest()


def filter_new_hashes(df: pd.DataFrame) -> pd.DataFrame:
    """过滤掉 news_articles 中已经存在的 content_hash（与 get_cls_news 逻辑一致）"""
    if df is None or len(df) == 0:
        return df

    hashes = tuple(df["content_hash"].unique().tolist())
    if not hashes:
        return df

    existing_hashes = set()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT content_hash FROM news_articles WHERE content_hash IN :hashes"),
            {"hashes": hashes},
        )
        existing_hashes = {row[0] for row in result.fetchall()}

    return df[~df["content_hash"].isin(existing_hashes)]


def get_candidate_symbols(limit: int = 100) -> list:
    """
    从 smart_stock_advisor / stock_data 数据库里选一批股票代码
    用于调用东方财富个股新闻接口。

    默认取 stock_history_data 里按代码排序的前 N 只股票。
    """
    try:
        sql = """
            SELECT DISTINCT symbol
            FROM stock_history_data
            WHERE symbol IS NOT NULL AND symbol != ''
            ORDER BY symbol
            LIMIT :limit
        """
        with engine.connect() as conn:
            df = pd.read_sql(text(sql), conn, params={"limit": limit})
        symbols = sorted({str(s).strip().zfill(6) for s in df["symbol"].tolist() if s})
        print(f"从 stock_history_data 中获取到 {len(symbols)} 只股票用于东方财富新闻抓取")
        return symbols
    except Exception as e:
        print(f"从 stock_history_data 获取股票列表失败: {e}")
        return []


def fetch_and_store_em_stock_news(symbols: list = None, max_symbols: int = 100):
    """
    抓取东方财富个股新闻，并按与财联社相同的流程入库到 news_articles。

    - 如果未指定 symbols，则自动从 stock_history_data 里取前 max_symbols 只股票。
    - 字段统一映射为 title / content / publish_time / source / source_url 等。
    """
    print(f"[{datetime.now()}] 开始抓取东方财富个股新闻...")

    # 准备股票列表
    if symbols is None:
        symbols = get_candidate_symbols(limit=max_symbols)
    else:
        # 清洗股票代码格式
        symbols = [str(s).strip().zfill(6) for s in symbols if s]

    if not symbols:
        print("未获取到可用的股票代码，终止抓取。")
        return

    all_news_list = []

    for idx, symbol in enumerate(symbols, start=1):
        try:
            print(f"({idx}/{len(symbols)}) 正在获取 {symbol} 的新闻...")
            df = ak.stock_news_em(symbol=symbol)
            if df is not None and len(df) > 0:
                # 东方财富返回字段说明（常见字段）：
                # 关键词, 新闻标题, 新闻内容, 发布时间, 文章来源, 新闻链接
                df["symbol"] = symbol  # 显式补充股票代码
                all_news_list.append(df)
                print(f"  获取到 {len(df)} 条新闻")
            else:
                print("  未获取到新闻")

            # 简单控制一下请求节奏，避免过快
            time.sleep(0.2)
        except Exception as e:
            print(f"  获取 {symbol} 新闻失败: {e}")

    if not all_news_list:
        print("未从东方财富获取到任何新闻。")
        return

    # 合并所有股票的新闻
    news_df = pd.concat(all_news_list, ignore_index=True)
    # 去重：标题 + 内容
    if {"新闻标题", "新闻内容"} <= set(news_df.columns):
        news_df = news_df.drop_duplicates(subset=["新闻标题", "新闻内容"], keep="first")
    print(f"东方财富新闻合并后共 {len(news_df)} 条（去重后）")

    # 字段重命名到统一格式
    rename_map = {}
    if "新闻标题" in news_df.columns:
        rename_map["新闻标题"] = "title"
    if "新闻内容" in news_df.columns:
        rename_map["新闻内容"] = "content"
    if "发布时间" in news_df.columns:
        rename_map["发布时间"] = "raw_publish_time"
    if "新闻链接" in news_df.columns:
        rename_map["新闻链接"] = "source_url"
    if "关键词" in news_df.columns:
        rename_map["关键词"] = "symbol_hint"  # 一般是股票代码

    news_df = news_df.rename(columns=rename_map)

    # 统一处理发布时间为 datetime
    def parse_publish_time(val):
        if pd.isna(val):
            return None
        try:
            return pd.to_datetime(val)
        except Exception:
            try:
                return pd.to_datetime(str(val).split(".")[0])
            except Exception:
                return None

    if "raw_publish_time" in news_df.columns:
        news_df["publish_time"] = news_df["raw_publish_time"].apply(parse_publish_time)
    else:
        news_df["publish_time"] = None

    # 标题 / 内容 兜底
    news_df["title"] = news_df.get("title", "").fillna("").astype(str)
    news_df["content"] = news_df.get("content", "").fillna("").astype(str)

    # 添加 hash、抓取时间、创建时间
    news_df["content_hash"] = news_df.apply(generate_hash, axis=1)
    news_df["fetch_time"] = datetime.now()
    news_df["created_at"] = datetime.now()

    # 过滤掉数据库中已有的 hash
    new_news_df = filter_new_hashes(news_df).copy()
    if len(new_news_df) == 0:
        print("东方财富新闻中没有需要写入的新记录（全部为重复）。")
        return

    # 添加默认字段（与财联社脚本保持风格一致）
    new_news_df.loc[:, "source"] = "东方财富个股新闻"
    # source_url 已在前面填充（如果有），否则为 NaN，这里统一转 None 交给插入时处理
    new_news_df.loc[:, "news_type"] = "stock"

    # 初始化股票关联字段
    new_news_df.loc[:, "sector"] = None
    new_news_df.loc[:, "industry"] = None
    new_news_df.loc[:, "concept"] = None

    # 如果 symbol 列为空，尝试用 symbol_hint 补一遍
    if "symbol" not in new_news_df.columns:
        new_news_df["symbol"] = None
    if "symbol_hint" in new_news_df.columns:
        mask_empty = new_news_df["symbol"].isna() | (new_news_df["symbol"] == "")
        new_news_df.loc[mask_empty, "symbol"] = (
            new_news_df.loc[mask_empty, "symbol_hint"].astype(str).str.zfill(6)
        )

    # 股票匹配（与财联社逻辑相同，但如果接口本身已经提供 symbol，则优先使用接口提供的）
    print(f"开始股票匹配（东方财富新闻），共 {len(new_news_df)} 条...")
    matched_count = 0
    stock_relations_map = {}

    for idx, row in new_news_df.iterrows():
        try:
            title = str(row.get("title", ""))
            content = str(row.get("content", ""))

            stock_info = stock_mapper.map_news_to_stocks(title=title, content=content)

            # 如果本身已有 symbol，则将其也并入 symbols 列表
            base_symbol = str(row.get("symbol") or "").strip()
            if base_symbol:
                if stock_info.get("primary_symbol") is None:
                    stock_info["primary_symbol"] = base_symbol
                if "symbols" not in stock_info or not stock_info["symbols"]:
                    stock_info["symbols"] = [base_symbol]
                elif base_symbol not in stock_info["symbols"]:
                    stock_info["symbols"].insert(0, base_symbol)

            if stock_info.get("primary_symbol"):
                new_news_df.at[idx, "symbol"] = stock_info.get("primary_symbol")
                new_news_df.at[idx, "sector"] = stock_info.get("sector")
                new_news_df.at[idx, "industry"] = stock_info.get("industry")
                matched_count += 1

                content_hash = row.get("content_hash")
                if content_hash:
                    relations = []
                    for symbol in stock_info.get("symbols", []):
                        symbol_info = stock_mapper.get_stock_industry_sector(symbol)
                        relations.append(
                            {
                                "symbol": symbol,
                                "relevance_score": stock_info.get(
                                    "relevance_score", 1.0
                                ),
                                "relation_type": "direct"
                                if symbol == stock_info.get("primary_symbol")
                                else "related",
                            }
                        )
                    stock_relations_map[content_hash] = relations
        except Exception as e:
            print(f"股票匹配失败（索引 {idx}）: {e}")

    print(f"股票匹配完成: {matched_count}/{len(new_news_df)} 条东方财富新闻匹配到股票")

    # 情感分析（与财联社脚本保持一致）
    print("开始情感分析（东方财富新闻）...")
    sentiment_results = []
    for idx, row in new_news_df.iterrows():
        try:
            title = str(row.get("title", ""))
            content = str(row.get("content", ""))
            sentiment_result = sentiment_analyzer.analyze(title, content)
            sentiment_results.append(sentiment_result)
        except Exception as e:
            print(f"情感分析失败（索引 {idx}）: {e}")
            sentiment_results.append(
                {
                    "sentiment": "neutral",
                    "sentiment_score": 0.0,
                    "sentiment_confidence": 0.0,
                    "keywords": [],
                    "is_positive": 0,
                    "is_negative": 0,
                    "is_policy": 0,
                    "relevance_type": "market",
                    "relevance_score": 0.5,
                }
            )

    for idx, result in enumerate(sentiment_results):
        new_news_df.at[new_news_df.index[idx], "sentiment"] = result["sentiment"]
        new_news_df.at[new_news_df.index[idx], "sentiment_score"] = result[
            "sentiment_score"
        ]
        new_news_df.at[new_news_df.index[idx], "sentiment_confidence"] = result[
            "sentiment_confidence"
        ]
        new_news_df.at[new_news_df.index[idx], "is_positive"] = result["is_positive"]
        new_news_df.at[new_news_df.index[idx], "is_negative"] = result["is_negative"]
        new_news_df.at[new_news_df.index[idx], "is_policy"] = result["is_policy"]
        new_news_df.at[new_news_df.index[idx], "keywords"] = (
            json.dumps(result["keywords"], ensure_ascii=False)
            if result["keywords"]
            else None
        )
        new_news_df.at[new_news_df.index[idx], "relevance_type"] = result[
            "relevance_type"
        ]
        new_news_df.at[new_news_df.index[idx], "relevance_score"] = result[
            "relevance_score"
        ]

    # 有 symbol / 行业 / 板块 的新闻，提升相关性类型和得分
    for idx, row in new_news_df.iterrows():
        if pd.notna(row.get("symbol")) and str(row.get("symbol")).strip():
            new_news_df.at[idx, "relevance_type"] = "direct"
            new_news_df.at[idx, "relevance_score"] = 1.0
        elif pd.notna(row.get("industry")) or pd.notna(row.get("sector")):
            new_news_df.at[idx, "relevance_type"] = "industry"
            new_news_df.at[idx, "relevance_score"] = 0.7

    print(
        f"情感分析完成: {sum(1 for r in sentiment_results if r['sentiment'] != 'neutral')}/{len(sentiment_results)} 条新闻有明确情感倾向"
    )

    # 处理空标题：避免唯一索引 / 展示问题
    new_news_df.loc[:, "title"] = new_news_df["title"].fillna("").astype(str)
    empty_title_mask = new_news_df["title"].str.strip() == ""
    new_news_df.loc[empty_title_mask, "title"] = new_news_df.loc[
        empty_title_mask, "content"
    ].str[:50]

    # 准备写入 news_articles 表的字段（与 get_cls_news 一致）
    columns_to_write = [
        "title",
        "content",
        "publish_time",
        "fetch_time",
        "source",
        "source_url",
        "news_type",
        "symbol",
        "sector",
        "industry",
        "concept",
        "content_hash",
        "created_at",
        "sentiment",
        "sentiment_score",
        "sentiment_confidence",
        "is_positive",
        "is_negative",
        "is_policy",
        "keywords",
        "relevance_type",
        "relevance_score",
    ]

    for col in columns_to_write:
        if col not in new_news_df.columns:
            new_news_df.loc[:, col] = None

    write_df = new_news_df[columns_to_write].copy()

    inserted_count = 0
    skipped_count = 0

    with engine.connect() as conn:
        for idx, row in write_df.iterrows():
            try:
                check_sql = text(
                    "SELECT COUNT(*) FROM news_articles WHERE content_hash = :hash"
                )
                result = conn.execute(check_sql, {"hash": row["content_hash"]})
                if result.fetchone()[0] > 0:
                    skipped_count += 1
                    continue

                insert_sql = text(
                    """
                    INSERT INTO news_articles 
                    (title, content, publish_time, fetch_time, source, source_url,
                     news_type, symbol, sector, industry, concept, content_hash, created_at,
                     sentiment, sentiment_score, sentiment_confidence,
                     is_positive, is_negative, is_policy, keywords,
                     relevance_type, relevance_score)
                    VALUES (:title, :content, :publish_time, :fetch_time, :source, :source_url,
                            :news_type, :symbol, :sector, :industry, :concept, :content_hash, :created_at,
                            :sentiment, :sentiment_score, :sentiment_confidence,
                            :is_positive, :is_negative, :is_policy, :keywords,
                            :relevance_type, :relevance_score)
                """
                )

                params = {
                    "title": str(row["title"])[:500] if pd.notna(row["title"]) else "",
                    "content": str(row["content"]) if pd.notna(row["content"]) else None,
                    "publish_time": row["publish_time"]
                    if pd.notna(row["publish_time"])
                    else None,
                    "fetch_time": row["fetch_time"],
                    "source": str(row["source"]),
                    "source_url": str(row["source_url"])
                    if pd.notna(row["source_url"])
                    else None,
                    "news_type": str(row["news_type"]),
                    "symbol": str(row["symbol"])
                    if pd.notna(row["symbol"])
                    else None,
                    "sector": str(row["sector"])
                    if pd.notna(row["sector"])
                    else None,
                    "industry": str(row["industry"])
                    if pd.notna(row["industry"])
                    else None,
                    "concept": str(row["concept"])
                    if pd.notna(row["concept"])
                    else None,
                    "content_hash": str(row["content_hash"]),
                    "created_at": row["created_at"],
                    "sentiment": str(row.get("sentiment", "neutral"))
                    if pd.notna(row.get("sentiment"))
                    else "neutral",
                    "sentiment_score": float(row.get("sentiment_score", 0.0))
                    if pd.notna(row.get("sentiment_score"))
                    else 0.0,
                    "sentiment_confidence": float(
                        row.get("sentiment_confidence", 0.0)
                    )
                    if pd.notna(row.get("sentiment_confidence"))
                    else 0.0,
                    "is_positive": int(row.get("is_positive", 0))
                    if pd.notna(row.get("is_positive"))
                    else 0,
                    "is_negative": int(row.get("is_negative", 0))
                    if pd.notna(row.get("is_negative"))
                    else 0,
                    "is_policy": int(row.get("is_policy", 0))
                    if pd.notna(row.get("is_policy"))
                    else 0,
                    "keywords": str(row.get("keywords"))
                    if pd.notna(row.get("keywords"))
                    else None,
                    "relevance_type": str(row.get("relevance_type", "market"))
                    if pd.notna(row.get("relevance_type"))
                    else "market",
                    "relevance_score": float(row.get("relevance_score", 0.5))
                    if pd.notna(row.get("relevance_score"))
                    else 0.5,
                }

                conn.execute(insert_sql, params)
                conn.commit()
                inserted_count += 1
            except Exception as e:
                if "Duplicate entry" in str(e) or "1062" in str(e):
                    skipped_count += 1
                else:
                    print(f"插入东方财富新闻失败（索引 {idx}）: {e}")
                conn.rollback()

    print(f"成功写入 {inserted_count} 条东方财富新新闻到 news_articles 表")
    if skipped_count > 0:
        print(f"跳过 {skipped_count} 条重复新闻（根据 content_hash 判断）")

    # 保存股票关联关系到 news_stock_relation（如果存在该表）
    try:
        with engine.connect() as conn:
            check_table_sql = """
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                  AND table_name = 'news_stock_relation'
            """
            table_exists = conn.execute(text(check_table_sql)).fetchone()[0] > 0

        if not table_exists:
            print("提示: news_stock_relation 表不存在，跳过东方财富股票关联关系保存")
            print("   股票关联信息已保存在 news_articles 表的 symbol 字段中")
        else:
            sql = """
                SELECT id, content_hash
                FROM news_articles
                WHERE content_hash IN :hashes
                  AND fetch_time >= :fetch_time_start
                ORDER BY id DESC
            """
            hashes = tuple(new_news_df["content_hash"].tolist())
            fetch_time_start = new_news_df["fetch_time"].min()
            with engine.connect() as conn:
                result = conn.execute(
                    text(sql),
                    {"hashes": hashes, "fetch_time_start": fetch_time_start},
                )
                news_id_map = {row[1]: row[0] for row in result.fetchall()}

            relations = []
            for idx, row in new_news_df.iterrows():
                news_id = news_id_map.get(row["content_hash"])
                content_hash = row["content_hash"]
                if news_id and content_hash in stock_relations_map:
                    for rel_info in stock_relations_map[content_hash]:
                        relations.append(
                            {
                                "news_id": news_id,
                                "symbol": rel_info["symbol"],
                                "relevance_score": rel_info["relevance_score"],
                                "relation_type": rel_info["relation_type"],
                            }
                        )

            if relations:
                # 按 (news_id, symbol) 去重，并用 INSERT IGNORE 避免 uk_news_symbol 重复报错
                seen = set()
                unique_relations = []
                for r in relations:
                    key = (r["news_id"], r["symbol"])
                    if key not in seen:
                        seen.add(key)
                        unique_relations.append(r)
                insert_sql = text("""
                    INSERT IGNORE INTO news_stock_relation (news_id, symbol, relevance_score, relation_type)
                    VALUES (:news_id, :symbol, :relevance_score, :relation_type)
                """)
                with engine.connect() as conn:
                    conn.execute(insert_sql, unique_relations)
                    conn.commit()
                print(
                    f"成功保存 {len(unique_relations)} 条东方财富股票关联关系到 news_stock_relation 表"
                )
    except Exception as e:
        print(f"保存东方财富股票关联关系失败: {e}")
        print("提示: 股票关联信息已保存在 news_articles 表的 symbol 字段中")


if __name__ == "__main__":
    # 默认从 stock_history_data 中选取最多 100 只股票，抓取东方财富个股新闻
    fetch_and_store_em_stock_news()

