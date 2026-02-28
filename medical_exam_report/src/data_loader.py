from __future__ import annotations

from pathlib import Path
from typing import Sequence

import pandas as pd

from . import config


REQUIRED_COLUMNS: Sequence[str] = [
    config.DATE_COLUMN,
    config.INSTITUTION_COLUMN,
    config.CHECK_TYPE_COLUMN,
    config.ITEM_NAME_COLUMN,
    config.RESULT_COLUMN,
]


def load_medical_data(path: Path | None = None) -> pd.DataFrame:
    """
    读取医疗检查数据 CSV，并做基础清洗。

    要求至少包含 REQUIRED_COLUMNS 里定义的列。
    """
    if path is None:
        path = config.DATA_FILE

    if not path.exists():
        raise FileNotFoundError(
            f"未找到数据文件：{path}\n"
            "请在 data 目录下创建 medical_exams.csv，并参考 README 中给出的列格式。"
        )

    df = pd.read_csv(path, encoding="utf-8-sig")

    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            "数据文件中缺少必需的列："
            + ", ".join(missing)
            + "\n请参照 README 调整列名或补充数据。"
        )

    # 解析日期
    df[config.DATE_COLUMN] = pd.to_datetime(df[config.DATE_COLUMN], errors="coerce")
    if df[config.DATE_COLUMN].isna().any():
        raise ValueError(
            f"列 `{config.DATE_COLUMN}` 中存在无法解析的日期，请检查日期格式。"
        )

    # 去除明显空行
    df = df.dropna(subset=[config.DATE_COLUMN, config.ITEM_NAME_COLUMN], how="any")

    # 统一机构 / 检查类型两端空格
    for col in [config.INSTITUTION_COLUMN, config.CHECK_TYPE_COLUMN, config.ITEM_NAME_COLUMN]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    # 异常标记标准化为大写
    if config.ABNORMAL_FLAG_COLUMN in df.columns:
        df[config.ABNORMAL_FLAG_COLUMN] = (
            df[config.ABNORMAL_FLAG_COLUMN]
            .astype(str)
            .str.strip()
            .str.upper()
            .replace({"TRUE": "Y", "FALSE": "N"})
        )

    return df


