<?php
/**
 * 修复单词库中的错误释义
 * 根据年级和单词，修复不合理的释义
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
echo "单词库释义修复工具\n";
echo "========================================\n\n";

// 定义需要修复的单词（根据年级）
$fixRules = [
    // 低年级（1-3年级）应该使用简单词义
    'grade1' => [
        'book' => '书；书籍',
        'run' => '跑；跑步',
        'play' => '玩；游戏',
        'read' => '读；阅读',
        'write' => '写；书写',
        'make' => '做；制作',
        'do' => '做；干',
        'get' => '得到；获得',
        'take' => '拿；取',
        'go' => '去；走',
        'come' => '来；来到',
        'study' => '学习；读书',
        'learn' => '学习；学会',
        'work' => '工作；劳动',
    ],
    'grade2' => [
        'book' => '书；书籍',
        'run' => '跑；跑步',
        'play' => '玩；游戏',
        'read' => '读；阅读',
        'write' => '写；书写',
        'make' => '做；制作',
        'do' => '做；干',
        'get' => '得到；获得',
        'take' => '拿；取',
        'go' => '去；走',
        'come' => '来；来到',
        'study' => '学习；读书',
        'learn' => '学习；学会',
        'work' => '工作；劳动',
    ],
    'grade3' => [
        'book' => '书；书籍',
        'run' => '跑；跑步',
        'play' => '玩；游戏',
        'read' => '读；阅读',
        'write' => '写；书写',
        'make' => '做；制作',
        'do' => '做；干',
        'get' => '得到；获得',
        'take' => '拿；取',
        'go' => '去；走',
        'come' => '来；来到',
        'study' => '学习；读书',
        'learn' => '学习；学会',
        'work' => '工作；劳动',
    ],
    // 中年级（4-6年级）可以使用稍微复杂一点的词义
    'grade4' => [
        'book' => '书；书籍；预订',
        'run' => '跑；跑步；经营',
        'play' => '玩；游戏；演奏',
        'read' => '读；阅读',
        'write' => '写；书写；写作',
        'make' => '做；制作；制造',
        'do' => '做；干；执行',
        'get' => '得到；获得；拿到',
        'take' => '拿；取；带走',
        'go' => '去；走；前往',
        'come' => '来；来到',
        'study' => '学习；研究',
        'learn' => '学习；学会；得知',
        'work' => '工作；劳动；起作用',
    ],
    'grade5' => [
        'book' => '书；书籍；预订',
        'run' => '跑；跑步；经营',
        'play' => '玩；游戏；演奏；播放',
        'read' => '读；阅读',
        'write' => '写；书写；写作',
    ],
    'grade6' => [
        'book' => '书；书籍；预订',
        'run' => '跑；跑步；经营；管理',
        'play' => '玩；游戏；演奏；播放',
        'read' => '读；阅读',
        'write' => '写；书写；写作',
    ],
];

// 查找需要修复的单词
$toFix = [];

foreach ($fixRules as $grade => $words) {
    foreach ($words as $word => $correctMeaning) {
        $sql = "SELECT id, word, meaning FROM word_bank WHERE grade = ? AND LOWER(word) = ?";
        $stmt = $conn->prepare($sql);
        $stmt->bind_param("ss", $grade, $word);
        $stmt->execute();
        $result = $stmt->get_result();
        
        while ($row = $result->fetch_assoc()) {
            $currentMeaning = $row['meaning'] ?? '';
            
            // 检查是否需要修复
            $needsFix = false;
            
            // 特殊检查：book不应该只有"预订"
            if ($word == 'book' && (stripos($currentMeaning, '预订') !== false || stripos($currentMeaning, '预约') !== false)) {
                if (stripos($currentMeaning, '书') === false) {
                    $needsFix = true;
                }
            }
            
            // 特殊检查：run在低年级不应该只有"管理"
            if ($word == 'run' && in_array($grade, ['grade1', 'grade2', 'grade3'])) {
                if (stripos($currentMeaning, '管理') !== false || stripos($currentMeaning, '运营') !== false) {
                    if (stripos($currentMeaning, '跑') === false) {
                        $needsFix = true;
                    }
                }
            }
            
            // 检查当前释义是否与正确释义匹配
            $hasCorrectMeaning = false;
            $correctParts = explode('；', $correctMeaning);
            foreach ($correctParts as $part) {
                $part = trim($part);
                if (!empty($part) && stripos($currentMeaning, $part) !== false) {
                    $hasCorrectMeaning = true;
                    break;
                }
            }
            
            if (!$hasCorrectMeaning || $needsFix) {
                $toFix[] = [
                    'id' => $row['id'],
                    'grade' => $grade,
                    'word' => $row['word'],
                    'current' => $currentMeaning,
                    'correct' => $correctMeaning
                ];
            }
        }
    }
}

echo "发现需要修复的单词：" . count($toFix) . " 个\n\n";

if (count($toFix) == 0) {
    echo "没有需要修复的单词！\n";
    $conn->close();
    exit;
}

// 显示需要修复的单词
echo "需要修复的单词列表：\n";
echo str_repeat('-', 80) . "\n";
foreach ($toFix as $item) {
    $gradeName = [
        'grade1' => '一年级', 'grade2' => '二年级', 'grade3' => '三年级',
        'grade4' => '四年级', 'grade5' => '五年级', 'grade6' => '六年级',
        'grade7' => '初一', 'grade8' => '初二', 'grade9' => '初三',
        'grade10' => '高一', 'grade11' => '高二', 'grade12' => '高三'
    ][$item['grade']] ?? $item['grade'];
    
    echo "ID: {$item['id']} | 年级: {$gradeName} | 单词: {$item['word']}\n";
    echo "  当前: {$item['current']}\n";
    echo "  正确: {$item['correct']}\n\n";
}

echo "\n是否开始修复？(y/n，默认n): ";
if (php_sapi_name() === 'cli') {
    $confirm = trim(fgets(STDIN));
    if (strtolower($confirm) !== 'y') {
        echo "已取消修复。\n";
        $conn->close();
        exit;
    }
} else {
    $confirm = $_GET['confirm'] ?? 'n';
    if (strtolower($confirm) !== 'y') {
        echo "请在URL中添加 ?confirm=y 来确认修复\n";
        $conn->close();
        exit;
    }
}

echo "\n开始修复...\n\n";

$success = 0;
$failed = 0;

foreach ($toFix as $item) {
    $sql = "UPDATE word_bank SET meaning = ? WHERE id = ?";
    $stmt = $conn->prepare($sql);
    $stmt->bind_param("si", $item['correct'], $item['id']);
    
    if ($stmt->execute()) {
        echo "✓ ID {$item['id']} ({$item['word']}): {$item['current']} → {$item['correct']}\n";
        $success++;
    } else {
        echo "✗ ID {$item['id']} ({$item['word']}): 修复失败 - {$stmt->error}\n";
        $failed++;
    }
}

echo "\n========================================\n";
echo "修复完成！\n";
echo "成功：{$success} 个\n";
echo "失败：{$failed} 个\n";
echo "========================================\n";

$conn->close();
