# -*- coding: utf-8 -*-
import pandas as pd
import os
import sys

# 设置输出编码
import codecs
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

def main():
    print("当前目录:", os.getcwd())
    print("\n目录中的文件:")
    files = os.listdir()
    for f in files:
        print(f)

    excel_files = [f for f in files if f.endswith('.xlsx')]
    print("\nExcel文件:")
    for f in excel_files:
        print(f)

    try:
        filename = excel_files[0]  # 使用第一个Excel文件
        print(f"\n尝试读取文件: {filename}")
        df = pd.read_excel(filename)
        print("成功读取文件")
        print("列名:", df.columns.tolist())
    except Exception as e:
        print("\n读取文件失败:", str(e))

if __name__ == "__main__":
    main() 