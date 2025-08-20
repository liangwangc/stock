
C:.
│  data_processing.py  【数据处理，会生成hospital_info.csv、original_202209.csv、cleaned_202209.csv】
│  log.txt
│  main_0906.py  【运行主文件】
│  output_result_0906.py  【OE值计算，会生成again_cleaned_202209.csv】
│  README.txt
│  
├─data
│  ├─cleaned
│  │      cleaned_202209.csv
│  │      again_cleaned_202209.csv
│  │      
│  ├─original
│  │      hospital_info.csv  【从病案首页中提取最新（按照出院时间）的医院信息，由data_processing.py生成】
│  │      original_202209.csv
│  │      
│  └─other
│          level_jbbm_ssbm_20220831.csv  【E值结果，由output_result_0906.py中的level_jbbm_ssbm_mean()计算得出】
│          
├─docs
│      40家重点医院.xls
│      hospital.xlsx
│      hospital_id.xlsx
│      临床学科字典.xlsx
│      利用强化学习构建保险领域长期价值模型的分析和探讨.docx
│      区县字典.xlsx
│      
├─module
│      db_module.py
│      __init__.py
│      
└─result
    └─202209  【输出的结果，10张表，压缩后给到对接人】
