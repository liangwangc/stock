@echo off
chcp 65001 >nul
echo ========================================
echo 数据库结构检查工具
echo ========================================
echo.

D:\xampp\php\php.exe -r "
\$conn = new mysqli('localhost', 'root', 'root', 'word_app', 3307);
if (\$conn->connect_error) {
    die('❌ 数据库连接失败: ' . \$conn->connect_error . PHP_EOL);
}

echo '正在检查数据库结构...' . PHP_EOL . PHP_EOL;

// 检查 users 表字段
echo '【检查 users 表】' . PHP_EOL;
\$res = \$conn->query(\"SHOW COLUMNS FROM users LIKE 'enable_word_bank'\");
echo (\$res && \$res->num_rows > 0) ? '  ✓ enable_word_bank 字段存在' : '  ✗ enable_word_bank 字段不存在' . PHP_EOL;

\$res = \$conn->query(\"SHOW COLUMNS FROM users LIKE 'grade'\");
echo (\$res && \$res->num_rows > 0) ? '  ✓ grade 字段存在' : '  ✗ grade 字段不存在' . PHP_EOL;

// 检查 words 表字段
echo PHP_EOL . '【检查 words 表】' . PHP_EOL;
\$res = \$conn->query(\"SHOW COLUMNS FROM words LIKE 'source'\");
echo (\$res && \$res->num_rows > 0) ? '  ✓ source 字段存在' : '  ✗ source 字段不存在' . PHP_EOL;

// 检查 word_bank 表
echo PHP_EOL . '【检查 word_bank 表】' . PHP_EOL;
\$res = \$conn->query(\"SHOW TABLES LIKE 'word_bank'\");
echo (\$res && \$res->num_rows > 0) ? '  ✓ word_bank 表存在' : '  ✗ word_bank 表不存在' . PHP_EOL;

echo PHP_EOL . '========================================' . PHP_EOL;
echo '检查完成！' . PHP_EOL;
echo PHP_EOL;
echo '如果所有项目都显示 ✓，则不需要修改数据库。' . PHP_EOL;
echo '如果有 ✗ 标记，请执行 word_bank_upgrade.sql' . PHP_EOL;
"

pause
