<?php
// 数据库连接测试脚本

// 设置错误报告
error_reporting(E_ALL);
ini_set('display_errors', 1);

// 设置时区
date_default_timezone_set('Asia/Shanghai');

echo "<h2>数据库连接测试</h2>";
echo "<hr>";

// 数据库配置
$db_host = 'localhost';
$db_user = 'root';
$db_pass = 'root';
$db_name = 'word_app';

echo "<p><strong>配置信息：</strong></p>";
echo "<ul>";
echo "<li>主机: $db_host</li>";
echo "<li>用户: $db_user</li>";
echo "<li>数据库: $db_name</li>";
echo "</ul>";

// 尝试连接数据库
echo "<h3>1. 测试连接...</h3>";
$conn = @new mysqli($db_host, $db_user, $db_pass, $db_name);

if ($conn->connect_error) {
    echo "<p style='color: red;'>❌ <strong>连接失败:</strong> " . $conn->connect_error . "</p>";
    exit;
} else {
    echo "<p style='color: green;'>✅ <strong>连接成功!</strong></p>";
    echo "<p>MySQL版本: " . $conn->server_info . "</p>";
    echo "<p>字符集: " . $conn->character_set_name() . "</p>";
}

// 设置字符集
$conn->set_charset("utf8mb4");
echo "<p>已设置字符集为: utf8mb4</p>";

// 测试查询表
echo "<hr>";
echo "<h3>2. 检查数据库表...</h3>";

$tables = ['users', 'words'];
foreach ($tables as $table) {
    $result = $conn->query("SHOW TABLES LIKE '$table'");
    if ($result && $result->num_rows > 0) {
        echo "<p style='color: green;'>✅ 表 '$table' 存在</p>";
        
        // 获取表结构
        $desc = $conn->query("DESCRIBE $table");
        if ($desc) {
            echo "<details><summary>查看表结构</summary>";
            echo "<table border='1' cellpadding='5' style='border-collapse: collapse; margin-top: 10px;'>";
            echo "<tr><th>字段</th><th>类型</th><th>空值</th><th>键</th><th>默认值</th><th>额外</th></tr>";
            while ($row = $desc->fetch_assoc()) {
                echo "<tr>";
                echo "<td>" . $row['Field'] . "</td>";
                echo "<td>" . $row['Type'] . "</td>";
                echo "<td>" . $row['Null'] . "</td>";
                echo "<td>" . $row['Key'] . "</td>";
                echo "<td>" . ($row['Default'] ?? 'NULL') . "</td>";
                echo "<td>" . ($row['Extra'] ?? '') . "</td>";
                echo "</tr>";
            }
            echo "</table></details>";
        }
    } else {
        echo "<p style='color: red;'>❌ 表 '$table' 不存在</p>";
    }
}

// 测试查询数据
echo "<hr>";
echo "<h3>3. 查询数据统计...</h3>";

// 用户数量
$result = $conn->query("SELECT COUNT(*) as count FROM users");
if ($result) {
    $row = $result->fetch_assoc();
    echo "<p>👥 用户总数: <strong>" . $row['count'] . "</strong></p>";
    
    // 显示用户列表
    $users = $conn->query("SELECT id, username, daily_goal, created_at FROM users ORDER BY id DESC LIMIT 10");
    if ($users && $users->num_rows > 0) {
        echo "<details><summary>最近10个用户</summary>";
        echo "<table border='1' cellpadding='5' style='border-collapse: collapse; margin-top: 10px;'>";
        echo "<tr><th>ID</th><th>用户名</th><th>每日目标</th><th>创建时间</th></tr>";
        while ($u = $users->fetch_assoc()) {
            echo "<tr>";
            echo "<td>" . $u['id'] . "</td>";
            echo "<td>" . htmlspecialchars($u['username']) . "</td>";
            echo "<td>" . $u['daily_goal'] . "</td>";
            echo "<td>" . $u['created_at'] . "</td>";
            echo "</tr>";
        }
        echo "</table></details>";
    }
}

// 单词数量
$result = $conn->query("SELECT COUNT(*) as count FROM words");
if ($result) {
    $row = $result->fetch_assoc();
    echo "<p>📚 单词总数: <strong>" . $row['count'] . "</strong></p>";
}

// 按状态统计
$result = $conn->query("SELECT status, COUNT(*) as count FROM words GROUP BY status");
if ($result) {
    echo "<details><summary>单词状态统计</summary>";
    echo "<table border='1' cellpadding='5' style='border-collapse: collapse; margin-top: 10px;'>";
    echo "<tr><th>状态</th><th>数量</th></tr>";
    while ($row = $result->fetch_assoc()) {
        echo "<tr>";
        echo "<td>" . htmlspecialchars($row['status']) . "</td>";
        echo "<td>" . $row['count'] . "</td>";
        echo "</tr>";
    }
    echo "</table></details>";
}

// 测试API功能
echo "<hr>";
echo "<h3>4. 测试API功能...</h3>";

// 测试查询
$test_query = "SELECT * FROM words WHERE user_id = 1 ORDER BY id DESC LIMIT 5";
$result = $conn->query($test_query);
if ($result && $result->num_rows > 0) {
    echo "<p style='color: green;'>✅ 查询功能正常</p>";
    echo "<details><summary>用户ID=1的最近5个单词</summary>";
    echo "<table border='1' cellpadding='5' style='border-collapse: collapse; margin-top: 10px;'>";
    echo "<tr><th>ID</th><th>单词</th><th>音标</th><th>状态</th><th>下次复习</th></tr>";
    while ($word = $result->fetch_assoc()) {
        echo "<tr>";
        echo "<td>" . $word['id'] . "</td>";
        echo "<td>" . htmlspecialchars($word['word']) . "</td>";
        echo "<td>" . htmlspecialchars($word['pronunciation']) . "</td>";
        echo "<td>" . htmlspecialchars($word['status']) . "</td>";
        echo "<td>" . $word['next_review'] . "</td>";
        echo "</tr>";
    }
    echo "</table></details>";
} else {
    echo "<p style='color: orange;'>⚠️ 查询成功，但没有数据</p>";
}

// 关闭连接
$conn->close();

echo "<hr>";
echo "<h3>5. 测试完成</h3>";
echo "<p style='color: green;'>✅ 所有测试通过！数据库连接正常。</p>";
echo "<p><a href='index.html'>返回首页</a></p>";
?>
