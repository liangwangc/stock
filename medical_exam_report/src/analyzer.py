from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import pandas as pd

from . import config


@dataclass
class OverviewStats:
    total_records: int
    total_visits: int
    first_date: pd.Timestamp
    last_date: pd.Timestamp
    institutions: List[str]
    check_types: List[str]


def compute_overview(df: pd.DataFrame) -> OverviewStats:
    """整体概况统计。"""
    total_records = len(df)

    # 用「日期 + 机构 + 检查类型」大致代表“一次检查”
    visit_keys = [
        config.DATE_COLUMN,
        config.INSTITUTION_COLUMN,
        config.CHECK_TYPE_COLUMN,
    ]
    visit_df = df.drop_duplicates(subset=visit_keys)
    total_visits = len(visit_df)

    first_date = df[config.DATE_COLUMN].min()
    last_date = df[config.DATE_COLUMN].max()

    institutions = sorted(
        {str(x) for x in df[config.INSTITUTION_COLUMN].dropna().unique()}
    )
    check_types = sorted(
        {str(x) for x in df[config.CHECK_TYPE_COLUMN].dropna().unique()}
    )

    return OverviewStats(
        total_records=total_records,
        total_visits=total_visits,
        first_date=first_date,
        last_date=last_date,
        institutions=institutions,
        check_types=check_types,
    )


def build_visit_timeline(df: pd.DataFrame) -> pd.DataFrame:
    """
    每次检查的时间线摘要。

    每一行代表一次检查（同一天、同机构、同类型合并）。
    """
    visit_keys = [
        config.DATE_COLUMN,
        config.INSTITUTION_COLUMN,
        config.CHECK_TYPE_COLUMN,
    ]

    # 每次检查里异常项目的数量
    abnormal_col = config.ABNORMAL_FLAG_COLUMN
    if abnormal_col in df.columns:
        abnormal_mask = df[abnormal_col] == "Y"
        abnormal_count = (
            df.assign(_abnormal=abnormal_mask)
            .groupby(visit_keys)["_abnormal"]
            .sum()
            .reset_index(name="abnormal_item_count")
        )
    else:
        abnormal_count = (
            df.groupby(visit_keys)[config.ITEM_NAME_COLUMN]
            .count()
            .reset_index(name="item_count")
        )
        abnormal_count["abnormal_item_count"] = None

    # 汇总项目数量
    item_count = (
        df.groupby(visit_keys)[config.ITEM_NAME_COLUMN]
        .count()
        .reset_index(name="total_item_count")
    )

    timeline = pd.merge(item_count, abnormal_count, on=visit_keys, how="left")
    timeline = timeline.sort_values(config.DATE_COLUMN).reset_index(drop=True)
    return timeline


def find_common_items_by_check_type(
    df: pd.DataFrame, min_coverage_ratio: float = 0.8
) -> Dict[Tuple[str], List[str]]:
    """
    找出“通用检查规则”：
    对于每一种检查类型（如：年度体检），统计在该类型的所有检查中，
    有哪些项目是“几乎每次都会做”的。

    min_coverage_ratio: 至少出现在该类型检查次数的多少比例以上，才认为是“通用项目”。
    """
    results: Dict[Tuple[str], List[str]] = {}

    # 每次检查的 key
    visit_keys = [
        config.DATE_COLUMN,
        config.INSTITUTION_COLUMN,
        config.CHECK_TYPE_COLUMN,
    ]

    # 在每一种检查类型内部做统计
    for check_type, group in df.groupby(config.CHECK_TYPE_COLUMN):
        # 一共进行了多少次这种类型的检查
        visit_df = group.drop_duplicates(subset=visit_keys)
        total_visits = len(visit_df)
        if total_visits == 0:
            continue

        # 统计每个项目在多少次检查中出现
        item_visit = (
            group.drop_duplicates(subset=visit_keys + [config.ITEM_NAME_COLUMN])
            .groupby(config.ITEM_NAME_COLUMN)[config.DATE_COLUMN]
            .count()
            .sort_values(ascending=False)
        )

        threshold = max(1, int(total_visits * min_coverage_ratio))
        common_items = [
            item_name
            for item_name, cnt in item_visit.items()
            if cnt >= threshold
        ]

        key = (check_type,)
        results[key] = common_items

    return results


def find_repeated_abnormal_items(
    df: pd.DataFrame, min_times: int = 2
) -> pd.DataFrame:
    """
    找出多次出现异常的项目，便于在汇报中说明“长期关注点”。
    """
    abnormal_col = config.ABNORMAL_FLAG_COLUMN
    if abnormal_col not in df.columns:
        return pd.DataFrame()

    abnormal_df = df[df[abnormal_col] == "Y"]
    if abnormal_df.empty:
        return pd.DataFrame()

    # 针对“项目 + 机构(可选)”，统计出现异常的次数
    group_cols = [config.ITEM_NAME_COLUMN]
    if config.INSTITUTION_COLUMN in abnormal_df.columns:
        group_cols.append(config.INSTITUTION_COLUMN)

    result = (
        abnormal_df.groupby(group_cols)[config.DATE_COLUMN]
        .count()
        .reset_index(name="abnormal_times")
        .sort_values("abnormal_times", ascending=False)
    )

    result = result[result["abnormal_times"] >= min_times]
    return result.reset_index(drop=True)


