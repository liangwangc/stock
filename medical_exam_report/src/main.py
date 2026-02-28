from __future__ import annotations

from . import analyzer, config, data_loader, report_generator


def main() -> None:
    config.ensure_directories()

    # 1. 读取数据（支持 CSV/Excel）
    df = data_loader.load_medical_data()

    # 2. 各类分析
    overview = analyzer.compute_overview(df)
    timeline = analyzer.build_visit_timeline(df)
    common_items = analyzer.find_common_items_by_check_type(df, min_coverage_ratio=0.7)
    repeated_abnormal = analyzer.find_repeated_abnormal_items(df, min_times=2)

    # 3. 生成报告
    report_text = report_generator.render_report(
        overview=overview,
        timeline=timeline,
        common_items=common_items,
        repeated_abnormal=repeated_abnormal,
    )

    report_generator.save_report(report_text, config.REPORT_FILE)
    print(f"报告已生成：{config.REPORT_FILE}")


if __name__ == "__main__":
    main()

