<?php
/**
 * 测试导入脚本 - 只导入一年级单词进行测试
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
    die("数据库连接失败: " . $conn->connect_error . "\n");
}
$conn->set_charset("utf8mb4");

echo "========================================\n";
echo "单词库导入测试（只导入一年级前5个单词）\n";
echo "========================================\n\n";

// 测试单词列表（只取前5个）
$testWords = ['hello', 'good', 'thank', 'yes', 'no'];
$grade = 'grade1';

/**
 * 获取单词信息
 */
function getWordInfo($word) {
    // 先尝试中文API
    $url = "https://api.52vmy.cn/api/wl/word?word=" . urlencode($word);
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    if ($httpCode === 200 && $response) {
        $data = json_decode($response, true);
        if ($data && isset($data['code']) && $data['code'] === 200) {
            $wordData = $data['data'] ?? [];
            return [
                'pronunciation' => $wordData['accent'] ?? '',
                'meaning' => $wordData['mean_cn'] ?? '',
                'example' => isset($wordData['sentence']) && !empty($wordData['sentence']) 
                    ? ($wordData['sentence'][0]['sentence'] ?? '') : ''
            ];
        }
    }
    
    // 如果中文API失败，使用Free Dictionary API
    $url = "https://api.dictionaryapi.dev/api/v2/entries/en/" . urlencode(strtolower($word));
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    if ($httpCode === 200 && $response) {
        $data = json_decode($response, true);
        if ($data && isset($data[0])) {
            $wordData = $data[0];
            $phonetic = $wordData['phonetic'] ?? '';
            if (empty($phonetic) && isset($wordData['phonetics'])) {
                foreach ($wordData['phonetics'] as $ph) {
                    if (isset($ph['text'])) {
                        $phonetic = $ph['text'];
                        break;
                    }
                }
            }
            
            $meanings = [];
            if (isset($wordData['meanings'])) {
                foreach ($wordData['meanings'] as $meaning) {
                    if (isset($meaning['definitions']) && !empty($meaning['definitions'])) {
                        $def = $meaning['definitions'][0];
                        if (isset($def['definition'])) {
                            $meanings[] = $def['definition'];
                        }
                    }
                }
            }
            $meaning = !empty($meanings) ? implode('; ', array_slice($meanings, 0, 3)) : '';
            
            $examples = [];
            if (isset($wordData['meanings'])) {
                foreach ($wordData['meanings'] as $meaning) {
                    if (isset($meaning['definitions'])) {
                        foreach ($meaning['definitions'] as $def) {
                            if (isset($def['example'])) {
                                $examples[] = $def['example'];
                            }
                        }
                    }
                }
            }
            $example = !empty($examples) ? $examples[0] : '';
            
            return [
                'pronunciation' => $phonetic,
                'meaning' => $meaning,
                'example' => $example
            ];
        }
    }
    
    return null;
}

// 开始导入
$success = 0;
$failed = 0;
$order = 1;

foreach ($testWords as $word) {
    echo "处理: {$word}...";
    
    // 检查是否已存在
    $stmt = $conn->prepare("SELECT id FROM word_bank WHERE grade = ? AND word = ?");
    $stmt->bind_param("ss", $grade, $word);
    $stmt->execute();
    if ($stmt->get_result()->num_rows > 0) {
        echo " [跳过] 已存在\n";
        continue;
    }
    
    // 获取单词信息
    $wordInfo = getWordInfo($word);
    
    if (!$wordInfo) {
        echo " [失败] API无数据\n";
        $failed++;
        continue;
    }
    
    // 插入数据库
    $stmt = $conn->prepare("INSERT INTO word_bank (grade, word, pronunciation, meaning, example, word_order) VALUES (?, ?, ?, ?, ?, ?)");
    $stmt->bind_param("sssssi", 
        $grade, 
        $word, 
        $wordInfo['pronunciation'], 
        $wordInfo['meaning'], 
        $wordInfo['example'], 
        $order
    );
    
    if ($stmt->execute()) {
        echo " [成功]\n";
        echo "   音标: " . ($wordInfo['pronunciation'] ?: '无') . "\n";
        echo "   词义: " . mb_substr($wordInfo['meaning'], 0, 50) . ($wordInfo['meaning'] ? '...' : '无') . "\n";
        $success++;
    } else {
        echo " [失败] " . $stmt->error . "\n";
        $failed++;
    }
    
    $order++;
    usleep(300000); // 0.3秒延迟
}

echo "\n========================================\n";
echo "测试完成！\n";
echo "成功: {$success}\n";
echo "失败: {$failed}\n";
echo "========================================\n";

// 显示导入结果
echo "\n查看导入的单词：\n";
$stmt = $conn->prepare("SELECT word, pronunciation, meaning FROM word_bank WHERE grade = ? ORDER BY word_order");
$stmt->bind_param("s", $grade);
$stmt->execute();
$result = $stmt->get_result();

while ($row = $result->fetch_assoc()) {
    echo "- {$row['word']}";
    if ($row['pronunciation']) {
        echo " [{$row['pronunciation']}]";
    }
    if ($row['meaning']) {
        echo " - " . mb_substr($row['meaning'], 0, 30);
    }
    echo "\n";
}

$conn->close();
