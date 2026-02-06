#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
使用stock_history_data表全量数据训练模型
这是推荐的训练方式，使用10年历史数据直接训练
"""
import sys
import os
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from scripts.train_ml_models import train_models

if __name__ == '__main__':
    print("=" * 60)
    print("使用stock_history_data表全量数据训练模型")
    print("=" * 60)
    print()
    print("训练配置:")
    print("  - 数据源: stock_history_data表（全量历史数据）")
    print("  - 训练集: 2014-01-01 到 2022-12-31（9年）")
    print("  - 验证集: 2023-01-01 到 2023-12-31（1年）")
    print("  - 测试集: 2024-01-01 到 2024-12-31（1年）")
    print("  - 模型: XGBoost分类器 + LightGBM分类器")
    print()
    print("开始训练...")
    print()
    
    # 使用历史数据训练（默认方式）
    train_models(
        train_start_date='2014-01-01',
        train_end_date='2022-12-31',
        val_start_date='2023-01-01',
        val_end_date='2023-12-31',
        test_start_date='2024-01-01',
        test_end_date='2024-12-31',
        model_types=['xgb_classifier', 'lgb_classifier'],
        is_active=True,
        use_history_data=True  # 使用stock_history_data表
    )
