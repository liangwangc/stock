<?php
/**
 * 从文件导入单词库
 * 支持CSV格式：word,pronunciation,meaning,example
 * 或纯文本格式：每行一个单词
 */

date_default_timezone_set('Asia/Shanghai');

// 数据库配置
$db_host = 'localhost';
$db_port = 3307;
$db_user = 'root';
$db_pass = 'root';
$db_name = 'word_app';

$conn = new mysqli($db_host, $db_user, $db_pass, $db_name, $db_port);
if ($conn->connect_error) {
    die("数据库连接失败: " . $conn->connect_error);
}
$conn->set_charset("utf8mb4");

/**
 * 从Free Dictionary API获取单词信息
 */
function fetchWordInfo($word) {
    $url = "https://api.dictionaryapi.dev/api/v2/entries/en/" . urlencode(strtolower($word));
    
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    if ($httpCode !== 200 || !$response) {
        return null;
    }
    
    $data = json_decode($response, true);
    if (!$data || !isset($data[0])) {
        return null;
    }
    
    $wordData = $data[0];
    
    // 提取音标
    $phonetic = '';
    if (isset($wordData['phonetic'])) {
        $phonetic = $wordData['phonetic'];
    } elseif (isset($wordData['phonetics']) && !empty($wordData['phonetics'])) {
        foreach ($wordData['phonetics'] as $ph) {
            if (isset($ph['text'])) {
                $phonetic = $ph['text'];
                break;
            }
        }
    }
    
    // 提取释义
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
    
    // 提取例句
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

/**
 * 导入单词
 */
function importWord($conn, $grade, $word, $pronunciation, $meaning, $example, $order) {
    // 检查是否已存在
    $stmt = $conn->prepare("SELECT id FROM word_bank WHERE grade = ? AND word = ?");
    $stmt->bind_param("ss", $grade, $word);
    $stmt->execute();
    if ($stmt->get_result()->num_rows > 0) {
        return false; // 已存在
    }
    
    // 如果缺少信息，尝试从API获取
    if (empty($pronunciation) || empty($meaning)) {
        $apiInfo = fetchWordInfo($word);
        if ($apiInfo) {
            if (empty($pronunciation)) $pronunciation = $apiInfo['pronunciation'];
            if (empty($meaning)) $meaning = $apiInfo['meaning'];
            if (empty($example)) $example = $apiInfo['example'];
        }
    }
    
    // 插入数据库
    $stmt = $conn->prepare("INSERT INTO word_bank (grade, word, pronunciation, meaning, example, word_order) VALUES (?, ?, ?, ?, ?, ?)");
    $stmt->bind_param("sssssi", $grade, $word, $pronunciation, $meaning, $example, $order);
    
    return $stmt->execute();
}

// 使用说明
echo "========================================\n";
echo "从文件导入单词库\n";
echo "========================================\n\n";
echo "使用方法：\n";
echo "1. 准备CSV文件，格式：word,pronunciation,meaning,example\n";
echo "2. 或准备纯文本文件，每行一个单词\n";
echo "3. 将文件放在此脚本同目录下\n";
echo "4. 运行：php import_word_bank_from_file.php <文件名> <年级>\n";
echo "\n年级选项：grade1-grade12\n";
echo "\n";

// 获取参数
if (php_sapi_name() === 'cli' && isset($argv[1]) && isset($argv[2])) {
    $filename = $argv[1];
    $grade = $argv[2];
    
    if (!file_exists($filename)) {
        die("错误：文件不存在 {$filename}\n");
    }
    
    if (!in_array($grade, ['grade1', 'grade2', 'grade3', 'grade4', 'grade5', 'grade6', 
                           'grade7', 'grade8', 'grade9', 'grade10', 'grade11', 'grade12'])) {
        die("错误：无效的年级 {$grade}\n");
    }
    
    echo "文件：{$filename}\n";
    echo "年级：{$grade}\n\n";
    
    $success = 0;
    $failed = 0;
    $order = 1;
    
    // 读取文件
    $lines = file($filename, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    
    foreach ($lines as $line) {
        $line = trim($line);
        if (empty($line)) continue;
        
        // 判断是CSV还是纯文本
        if (strpos($line, ',') !== false) {
            // CSV格式
            $parts = str_getcsv($line);
            $word = trim($parts[0]);
            $pronunciation = isset($parts[1]) ? trim($parts[1]) : '';
            $meaning = isset($parts[2]) ? trim($parts[2]) : '';
            $example = isset($parts[3]) ? trim($parts[3]) : '';
        } else {
            // 纯文本格式
            $word = $line;
            $pronunciation = '';
            $meaning = '';
            $example = '';
        }
        
        echo "导入: {$word}...";
        
        if (importWord($conn, $grade, $word, $pronunciation, $meaning, $example, $order)) {
            echo " ✓\n";
            $success++;
        } else {
            echo " ✗\n";
            $failed++;
        }
        
        $order++;
        usleep(200000); // 0.2秒延迟
    }
    
    echo "\n完成！成功：{$success}，失败：{$failed}\n";
} else {
    echo "请提供文件名和年级参数\n";
    echo "示例：php import_word_bank_from_file.php words.txt grade1\n";
}

$conn->close();
