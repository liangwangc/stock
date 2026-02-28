from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from . import config


@dataclass
class GjFileStats:
    path: Path
    rule_type: str  # 直接用文件名（去扩展名）作为规则类型说明
    total_rows: int
    institution_level_col: Optional[str] = None
    institution_levels: List[str] = field(default_factory=list)
    dimension_presence: Dict[str, bool] = field(default_factory=dict)


DIMENSION_KEYWORDS = {
    "性别": ["性别"],
    "年龄": ["年龄"],
    "儿童": ["儿童"],
    "机构级别": ["机构级别", "医疗机构级别"],
    "就医方式": ["就医方式"],
    "工伤": ["工伤"],
    "生育": ["生育"],
    "支付疗程": ["疗程", "支付疗程"],
    "频次": ["频次", "限次"],
}


def _detect_column(columns: List[str], keywords: List[str]) -> Optional[str]:
    """在列名中根据关键字列表尝试匹配一个列。"""
    for col in columns:
        for kw in keywords:
            if kw in str(col):
                return str(col)
    return None


def analyze_single_file(path: Path) -> GjFileStats:
    """
    分析单个国家规则 Excel：
    - 记录总行数
    - 识别“医疗机构级别”列以及出现的级别
    - 标记是否包含 性别 / 年龄 / 儿童 / 机构级别 / 就医方式 / 工伤 / 生育 / 支付疗程 / 频次 等限制维度
    """
    # 默认读取第一个工作表
    df = pd.read_excel(path)
    # 去掉完全空的行
    df = df.dropna(how="all")

    total_rows = len(df)
    cols = [str(c) for c in df.columns]

    # 机构级别列
    inst_col = _detect_column(cols, DIMENSION_KEYWORDS["机构级别"])
    if inst_col and inst_col in df.columns:
        levels = (
            df[inst_col]
            .dropna()
            .astype(str)
            .str.strip()
            .replace({"": None})
            .dropna()
            .unique()
        )
        institution_levels = sorted(set(levels))
    else:
        institution_levels = []

    # 其他维度存在性
    dimension_presence: Dict[str, bool] = {}
    for dim_name, kws in DIMENSION_KEYWORDS.items():
        if dim_name == "机构级别":
            # 已经单独处理过
            dimension_presence[dim_name] = inst_col is not None
        else:
            dimension_presence[dim_name] = _detect_column(cols, kws) is not None

    rule_type = path.stem  # 去掉扩展名后的文件名

    return GjFileStats(
        path=path,
        rule_type=rule_type,
        total_rows=total_rows,
        institution_level_col=inst_col,
        institution_levels=institution_levels,
        dimension_presence=dimension_presence,
    )


def scan_gj_rule_files(directory: Path | None = None) -> List[GjFileStats]:
    """
    扫描国家规则目录下的所有 Excel 文件，并逐个分析。
    """
    if directory is None:
        directory = config.GJ_RULES_DIR

    if not directory.exists():
        raise FileNotFoundError(f"国家规则目录不存在：{directory}")

    excel_paths = sorted(
        p for p in directory.iterdir() if p.suffix.lower() in {".xlsx", ".xls"}
    )
    if not excel_paths:
        raise FileNotFoundError(f"在目录 {directory} 下未找到任何 Excel 文件。")

    stats_list: List[GjFileStats] = []
    for path in excel_paths:
        stats = analyze_single_file(path)
        stats_list.append(stats)

    return stats_list


