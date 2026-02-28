from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable

from . import config
from .gj_rules_analyzer import GjFileStats


def render_gj_rules_report(stats_list: Iterable[GjFileStats]) -> str:
    """生成国家检查规则的汇总报告（Markdown）。"""
    stats_list = list(stats_list)
    now_str = datetime.now().strftime("%Y-%m-%d")

    lines: list[str] = []
    lines.append(f"## 国家医保检查规则汇总（截止 {now_str}）")
    lines.append("")
    lines.append(
        f"当前共整理国家规则文件 **{len(stats_list)}** 份，"
        f"存放于 `{config.GJ_RULES_DIR}` 目录。"
    )
    lines.append("")

    # 总览表：每个文件的基本情况
    lines.append("### 一、规则文件总体情况一览")
    lines.append("")
    lines.append("| 序号 | 规则名称（来源文件） | 记录条数 | 是否区分医疗机构级别 | 涉及主要限制维度 |")
    lines.append("| --- | --- | --- | --- | --- |")

    for idx, stats in enumerate(stats_list, start=1):
        has_inst = "是" if stats.institution_level_col else "否"
        # 选出为 True 的维度名称
        dims = [name for name, present in stats.dimension_presence.items() if present]
        dim_str = "、".join(dims) if dims else ""
        lines.append(
            f"| {idx} | {stats.rule_type} | {stats.total_rows} | "
            f"{has_inst} | {dim_str} |"
        )

    lines.append("")

    # 分文件详细说明
    lines.append("### 二、各规则文件明细说明")
    lines.append("")
    for idx, stats in enumerate(stats_list, start=1):
        lines.append(f"#### （{idx}）{stats.rule_type}")
        lines.append("")
        lines.append(f"- **来源文件路径**：`{stats.path}`")
        lines.append(f"- **记录条数**：{stats.total_rows}")

        # 医疗机构级别
        if stats.institution_level_col:
            if stats.institution_levels:
                level_str = "、".join(stats.institution_levels)
            else:
                level_str = "（列存在但当前数据中无有效级别值）"
            lines.append(
                f"- **区分医疗机构级别**：是（列名：`{stats.institution_level_col}`，"
                f"出现级别：{level_str}）"
            )
        else:
            lines.append("- **区分医疗机构级别**：否（未发现包含“医疗机构级别”字样的列）")

        # 限制维度
        dims_true = [name for name, present in stats.dimension_presence.items() if present]
        dims_false = [name for name, present in stats.dimension_presence.items() if not present]

        if dims_true:
            lines.append(
                "- **已识别的主要限制维度**：" + "、".join(dims_true)
            )
        else:
            lines.append("- **已识别的主要限制维度**：暂无明显限制维度列（仅做结构性记录）")

        if dims_false:
            lines.append(
                "- **当前未在结构化字段中体现的维度（可能以文字说明形式存在）**："
                + "、".join(dims_false)
            )

        lines.append("")

    # 结尾总结
    lines.append("### 三、可用于向领导汇报的要点建议")
    lines.append("")
    lines.append("- 各批次规则覆盖了性别、年龄、儿童专用、机构级别、就医方式、工伤/生育保险、疗程、频次等多个维度的限制要求。")
    lines.append("- 对于“限医疗机构级别”的规则，可重点说明不同级别机构在诊疗、用药方面的权限差异。")
    lines.append("- 对于“儿童专用、区分性别、限年龄”等规则，可作为解释精细化管理、风险防控的重要依据。")
    lines.append("- 后续可以在此基础上，进一步与个人检查记录做对照，说明个人检查是否严格遵守国家及医保规则。")
    lines.append("")

    return "\n".join(lines)


def save_gj_rules_report(content: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


