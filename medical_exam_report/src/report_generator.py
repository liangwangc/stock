from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Tuple

import pandas as pd

from .analyzer import OverviewStats
from . import config


def _format_date(dt: pd.Timestamp | None) -> str:
    if dt is None or pd.isna(dt):
        return "-"
    return dt.strftime("%Y-%m-%d")


def render_report(
    overview: OverviewStats,
    timeline: pd.DataFrame,
    common_items: Dict[Tuple[str], list[str]],
    repeated_abnormal: pd.DataFrame,
) -> str:
    """
    生成面向领导的 Markdown 报告文本。
    """
    lines: list[str] = []

    now_str = datetime.now().strftime("%Y-%m-%d")
    lines.append(f"## 个人医疗检查情况汇报（截止 {now_str}）")
    lines.append("")

    # 一、整体检查概况
    lines.append("### 一、整体检查概况")
    lines.append("")
    lines.append(f"- **检查记录总条数**：{overview.total_records} 条")
    lines.append(f"- **实际检查次数**：约 {overview.total_visits} 次")
    lines.append(
        f"- **检查时间跨度**：自 {_format_date(overview.first_date)} "
        f"至 {_format_date(overview.last_date)}"
    )
    lines.append(
        f"- **主要就诊机构**：{('、'.join(overview.institutions)) or '（无数据）'}"
    )
    lines.append(
        f"- **主要检查类型**：{('、'.join(overview.check_types)) or '（无数据）'}"
    )
    lines.append("")

    # 二、历次检查时间线及结果概览
    lines.append("### 二、历次检查时间线及结果概览")
    lines.append("")
    if timeline.empty:
        lines.append("目前尚未录入任何检查记录。")
    else:
        header = "| 日期 | 机构 | 检查类型 | 项目总数 | 异常项目数 |"
        sep = "| --- | --- | --- | --- | --- |"
        lines.append(header)
        lines.append(sep)
        for _, row in timeline.iterrows():
            date_str = _format_date(row[config.DATE_COLUMN])
            institution = str(row.get(config.INSTITUTION_COLUMN, ""))
            check_type = str(row.get(config.CHECK_TYPE_COLUMN, ""))
            total_items = row.get("total_item_count", "")
            abnormal_items = row.get("abnormal_item_count", "")
            lines.append(
                f"| {date_str} | {institution} | {check_type} | "
                f"{total_items} | {abnormal_items if abnormal_items == abnormal_items else ''} |"
            )
    lines.append("")

    # 三、各类检查的通用项目（通用检查规则）
    lines.append("### 三、各类检查的通用项目（通用检查规则）")
    lines.append("")
    if not common_items:
        lines.append("由于样本较少或项目差异较大，目前尚未能归纳出稳定的通用项目。")
    else:
        for key, items in common_items.items():
            check_type = key[0]
            lines.append(f"**检查类型：{check_type}**")
            if not items:
                lines.append("- 当前样本下尚未形成稳定的固定项目。")
            else:
                for item in items:
                    lines.append(f"- {item}")
            lines.append("")

    # 四、需要长期关注的指标（多次异常）
    lines.append("### 四、需要长期关注的指标（多次异常）")
    lines.append("")
    if repeated_abnormal is None or repeated_abnormal.empty:
        lines.append("根据当前录入的数据，尚未发现多次持续异常的项目。")
    else:
        headers: list[str] = [config.ITEM_NAME_COLUMN]
        if config.INSTITUTION_COLUMN in repeated_abnormal.columns:
            headers.append(config.INSTITUTION_COLUMN)
        headers.append("abnormal_times")

        header_row = "| " + " | ".join(headers) + " |"
        sep = "| " + " | ".join(["---"] * len(headers)) + " |"
        lines.append(header_row)
        lines.append(sep)

        for _, row in repeated_abnormal.iterrows():
            values: list[str] = []
            for col in headers:
                values.append(str(row.get(col, "")))
            lines.append("| " + " | ".join(values) + " |")
    lines.append("")

    # 五、个人说明与后续计划（留白，便于人工补充）
    lines.append("### 五、个人说明与后续计划（可根据需要补充）")
    lines.append("")
    lines.append("- 结合岗位职责，对当前健康状况的总体评价：")
    lines.append("- 针对重点异常指标，已采取或计划采取的干预措施：")
    lines.append("- 后续在定期体检、专项复查等方面的安排与建议：")
    lines.append("")

    return "\n".join(lines)


def save_report(content: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


