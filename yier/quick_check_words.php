<?php
/**
 * 快速检查单词库中的问题单词
 */

date_default_timezone_set('Asia/Shanghai');

// 数据库配置
$db_host = 'localhost';
$db_port = 3307;
$db_user = 'root';
$db_pass = 'root';
$db_name = 'word_app';

// 建立连接
$conn = new mysqli($db_host, $db_user, $db_pass, $db_name, $db_port);
if ($conn->connect_error) {
    die("数据库连接失败: " . $conn->connect_error);
}
$conn->set_charset("utf8mb4");

echo "========================================\n";
echo "单词库问题检查\n";
echo "========================================\n\n";

// 检查book单词
echo "检查 'book' 单词：\n";
$sql = "SELECT id, grade, word, meaning FROM word_bank WHERE LOWER(word) = 'book'";
$result = $conn->query($sql);
if ($result && $result->num_rows > 0) {
    while ($row = $result->fetch_assoc()) {
        echo "  ID: {$row['id']}, 年级: {$row['grade']}, 释义: {$row['meaning']}\n";
        if (stripos($row['meaning'], '预订') !== false || stripos($row['meaning'], '预约') !== false) {
            echo "  ⚠️ 问题：释义包含'预订'或'预约'，应该是'书'\n";
        }
    }
} else {
    echo "  未找到 'book' 单词\n";
}

echo "\n";

// 检查其他可能有问题的常见单词
$problemWords = ['run', 'play', 'read', 'write', 'make', 'do', 'get', 'take', 'go', 'come'];
echo "检查其他常见单词：\n";
foreach ($problemWords as $word) {
    $sql = "SELECT id, grade, word, meaning FROM word_bank WHERE LOWER(word) = ? LIMIT 5";
    $stmt = $conn->prepare($sql);
    $stmt->bind_param("s", $word);
    $stmt->execute();
    $result = $stmt->get_result();
    
    if ($result && $result->num_rows > 0) {
        while ($row = $result->fetch_assoc()) {
            $meaning = $row['meaning'];
            $hasIssue = false;
            $issue = '';
            
            // 检查是否有问题
            if ($word == 'run' && (stripos($meaning, '经营') !== false || stripos($meaning, '管理') !== false)) {
                $hasIssue = true;
                $issue = '包含"经营"或"管理"，低年级应该是"跑"';
            } elseif ($word == 'play' && (stripos($meaning, '播放') !== false || stripos($meaning, '演出') !== false)) {
                $hasIssue = true;
                $issue = '包含"播放"或"演出"，低年级应该是"玩"';
            } elseif ($word == 'read' && stripos($meaning, '阅读') !== false && stripos($meaning, '读') === false) {
                $hasIssue = true;
                $issue = '只有"阅读"，低年级应该包含"读"';
            } elseif ($word == 'write' && stripos($meaning, '写作') !== false && stripos($meaning, '写') === false) {
                $hasIssue = true;
                $issue = '只有"写作"，低年级应该包含"写"';
            }
            
            if ($hasIssue) {
                echo "  ⚠️ {$word} (ID: {$row['id']}, 年级: {$row['grade']}): {$meaning}\n";
                echo "     问题: {$issue}\n";
            }
        }
    }
}

echo "\n";

// 查找所有包含"预订"、"预约"、"订票"的单词
echo "查找包含'预订'、'预约'、'订票'的单词：\n";
$sql = "SELECT id, grade, word, meaning FROM word_bank WHERE meaning LIKE '%预订%' OR meaning LIKE '%预约%' OR meaning LIKE '%订票%'";
$result = $conn->query($sql);
if ($result && $result->num_rows > 0) {
    while ($row = $result->fetch_assoc()) {
        echo "  ID: {$row['id']}, 年级: {$row['grade']}, 单词: {$row['word']}, 释义: {$row['meaning']}\n";
    }
} else {
    echo "  未找到包含'预订'、'预约'、'订票'的单词\n";
}

echo "\n";

// 查找所有包含"v."开头的释义（可能是动词释义，需要检查是否合理）
echo "查找以'v.'开头的释义（可能是动词释义）：\n";
$sql = "SELECT id, grade, word, meaning FROM word_bank WHERE meaning LIKE 'v.%' OR meaning LIKE 'V.%' LIMIT 20";
$result = $conn->query($sql);
if ($result && $result->num_rows > 0) {
    while ($row = $result->fetch_assoc()) {
        echo "  ID: {$row['id']}, 年级: {$row['grade']}, 单词: {$row['word']}, 释义: {$row['meaning']}\n";
    }
} else {
    echo "  未找到以'v.'开头的释义\n";
}

$conn->close();

echo "\n检查完成！\n";
