from __future__ import annotations

from . import config, gj_rules_analyzer, gj_rules_report_generator


def main() -> None:
    # 不需要创建 gj 目录，假定你已经放好了文件
    stats_list = gj_rules_analyzer.scan_gj_rule_files()

    report_text = gj_rules_report_generator.render_gj_rules_report(stats_list)
    gj_rules_report_generator.save_gj_rules_report(
        report_text, config.GJ_RULES_REPORT_FILE
    )

    print(f"国家检查规则汇总报告已生成：{config.GJ_RULES_REPORT_FILE}")


if __name__ == "__main__":
    main()

