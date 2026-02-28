from __future__ import annotations

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

# 数据与输出路径
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

# 个人体检记录数据与报告
DATA_FILE = DATA_DIR / "medical_exams.csv"
REPORT_FILE = OUTPUT_DIR / "medical_report.md"

# 国家检查规则（国家规则）相关路径
GJ_RULES_DIR = DATA_DIR / "gj"
GJ_RULES_REPORT_FILE = OUTPUT_DIR / "gj_rules_report.md"

# 列名配置（如有需要，你可以根据自己的 CSV 调整这些名字）
DATE_COLUMN = "date"
INSTITUTION_COLUMN = "institution"
CHECK_TYPE_COLUMN = "check_type"  # 年度体检 / 入职体检 / 专项检查 等
ITEM_NAME_COLUMN = "item_name"  # 检查项目（血压、血糖、血脂等）
RESULT_COLUMN = "result"
UNIT_COLUMN = "unit"
REF_LOW_COLUMN = "ref_low"
REF_HIGH_COLUMN = "ref_high"
ABNORMAL_FLAG_COLUMN = "abnormal_flag"  # Y / N / 空


def ensure_directories() -> None:
    """确保数据与输出目录存在。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


