<?php
/**
 * 单词库批量导入脚本
 * 使用免费API获取单词详情并导入数据库
 */

// 设置时区
date_default_timezone_set('Asia/Shanghai');

// 数据库配置（与api.php保持一致）
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

/**
 * 使用 Free Dictionary API 获取单词信息
 * API: https://api.dictionaryapi.dev/api/v2/entries/en/{word}
 */
function fetchWordFromFreeDictionaryAPI($word) {
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
    
    // 提取中文释义（Free Dictionary API没有中文，使用英文释义）
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
        'word' => $word,
        'pronunciation' => $phonetic,
        'meaning' => $meaning,
        'example' => $example
    ];
}

/**
 * 使用中文API获取单词信息（备用）
 * API: https://api.52vmy.cn/api/wl/word
 */
function fetchWordFromChineseAPI($word) {
    $url = "https://api.52vmy.cn/api/wl/word?word=" . urlencode($word);
    
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
    if (!$data || $data['code'] !== 200) {
        return null;
    }
    
    $wordData = $data['data'] ?? [];
    
    // 提取例句（英文+中文）
    $example = '';
    if (isset($wordData['sentence']) && is_array($wordData['sentence']) && !empty($wordData['sentence'])) {
        // 优先查找有翻译的例句
        $foundComplete = false;
        foreach ($wordData['sentence'] as $sentence) {
            $exampleEn = $sentence['sentence'] ?? '';
            $exampleCn = $sentence['translation'] ?? '';
            
            if (!empty($exampleEn) && !empty($exampleCn)) {
                $example = $exampleEn . "。" . $exampleCn; // 使用句号分隔
                $foundComplete = true;
                break;
            } elseif (!empty($exampleEn) && empty($example)) {
                // 至少保存一个英文例句
                $example = $exampleEn;
            }
        }
        
        // 如果所有例句都没有翻译，使用第一个英文例句
        if (!$foundComplete && empty($example) && !empty($wordData['sentence'][0]['sentence'])) {
            $example = $wordData['sentence'][0]['sentence'];
        }
    }
    
    return [
        'word' => $word,
        'pronunciation' => $wordData['accent'] ?? '',
        'meaning' => $wordData['mean_cn'] ?? '',
        'example' => $example
    ];
}

/**
 * 使用免费翻译API翻译英文句子为中文
 */
function translateToChinese($text) {
    if (empty($text) || !preg_match('/[a-zA-Z]/', $text)) {
        return '';
    }
    
    // 方法1：使用百度翻译免费接口（无需API Key，但可能不稳定）
    $url1 = "https://fanyi.baidu.com/transapi";
    $postData1 = http_build_query([
        'from' => 'en',
        'to' => 'zh',
        'query' => $text,
        'transtype' => 'translang',
        'simple_means_flag' => '3'
    ]);
    
    $ch1 = curl_init();
    curl_setopt($ch1, CURLOPT_URL, $url1);
    curl_setopt($ch1, CURLOPT_POST, true);
    curl_setopt($ch1, CURLOPT_POSTFIELDS, $postData1);
    curl_setopt($ch1, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch1, CURLOPT_TIMEOUT, 15);
    curl_setopt($ch1, CURLOPT_CONNECTTIMEOUT, 10);
    curl_setopt($ch1, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch1, CURLOPT_USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36');
    curl_setopt($ch1, CURLOPT_HTTPHEADER, [
        'Content-Type: application/x-www-form-urlencoded',
        'Referer: https://fanyi.baidu.com/'
    ]);
    
    $response1 = @curl_exec($ch1);
    $httpCode1 = curl_getinfo($ch1, CURLINFO_HTTP_CODE);
    curl_close($ch1);
    
    if ($httpCode1 === 200 && $response1) {
        $data1 = json_decode($response1, true);
        if ($data1 && isset($data1['errno']) && $data1['errno'] == 0) {
            if (isset($data1['trans_result']['data'][0]['dst'])) {
                $translation = trim($data1['trans_result']['data'][0]['dst']);
                if (!empty($translation) && preg_match('/[\x{4e00}-\x{9fa5}]/u', $translation)) {
                    return $translation;
                }
            }
        }
    }
    
    // 等待一下再尝试第二个API
    usleep(500000); // 0.5秒
    
    // 方法2：使用有道翻译免费接口（无需API Key，但可能不稳定）
    $salt = time() . rand(1000, 9999);
    $signStr = "fanyideskweb" . $text . $salt . "Ygy_4c=r#e#4EX^NUGUc5";
    $sign = md5($signStr);
    $url2 = "https://fanyi.youdao.com/translate_o?smartresult=dict&smartresult=rule";
    $postData2 = http_build_query([
        'i' => $text,
        'from' => 'en',
        'to' => 'zh-CHS',
        'smartresult' => 'dict',
        'client' => 'fanyideskweb',
        'salt' => $salt,
        'sign' => $sign,
        'lts' => time() * 1000,
        'bv' => md5('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'),
        'doctype' => 'json',
        'version' => '2.1',
        'keyfrom' => 'fanyi.web',
        'action' => 'FY_BY_REALTIME'
    ]);
    
    $ch2 = curl_init();
    curl_setopt($ch2, CURLOPT_URL, $url2);
    curl_setopt($ch2, CURLOPT_POST, true);
    curl_setopt($ch2, CURLOPT_POSTFIELDS, $postData2);
    curl_setopt($ch2, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch2, CURLOPT_TIMEOUT, 15);
    curl_setopt($ch2, CURLOPT_CONNECTTIMEOUT, 10);
    curl_setopt($ch2, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch2, CURLOPT_USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36');
    curl_setopt($ch2, CURLOPT_HTTPHEADER, [
        'Content-Type: application/x-www-form-urlencoded',
        'Referer: https://fanyi.youdao.com/'
    ]);
    
    $response2 = @curl_exec($ch2);
    $httpCode2 = curl_getinfo($ch2, CURLINFO_HTTP_CODE);
    curl_close($ch2);
    
    if ($httpCode2 === 200 && $response2) {
        $data2 = json_decode($response2, true);
        if ($data2 && !isset($data2['errorCode'])) {
            if (isset($data2['translateResult'][0][0]['tgt'])) {
                $translation = trim($data2['translateResult'][0][0]['tgt']);
                if (!empty($translation) && preg_match('/[\x{4e00}-\x{9fa5}]/u', $translation)) {
                    return $translation;
                }
            }
        }
    }
    
    return '';
}

/**
 * 获取单词信息（优先使用中文API，失败则使用Free Dictionary API）
 * 确保最终返回的例句包含英文和中文
 */
function getWordInfo($word) {
    // 先尝试中文API
    $result = fetchWordFromChineseAPI($word);
    if ($result && !empty($result['meaning'])) {
        // 检查例句是否完整（包含英文和中文）
        $example = $result['example'] ?? '';
        $hasEnglish = !empty($example) && preg_match('/[a-zA-Z]/', $example);
        $hasChinese = !empty($example) && preg_match('/[\x{4e00}-\x{9fa5}]/u', $example);
        $hasBoth = strpos($example, "\n") !== false && $hasEnglish && $hasChinese;
        
        // 如果例句不完整，尝试补充
        if (empty($example) || !$hasBoth) {
            // 如果只有中文没有英文，或者完全没有例句，尝试从Free Dictionary API获取英文例句
            if (!$hasEnglish) {
                $freeDictResult = fetchWordFromFreeDictionaryAPI($word);
                if ($freeDictResult && !empty($freeDictResult['example'])) {
                    $exampleEn = $freeDictResult['example'];
                    // 如果已有中文翻译，组合；否则翻译英文例句
                    if ($hasChinese) {
                        $example = $exampleEn . "。" . $example; // 使用句号分隔
                    } else {
                        // 翻译英文例句为中文
                        $exampleCn = translateToChinese($exampleEn);
                        if (!empty($exampleCn)) {
                            $example = $exampleEn . "。" . $exampleCn; // 使用句号分隔
                        } else {
                            // 翻译失败，重试一次
                            usleep(500000); // 等待0.5秒
                            $exampleCn = translateToChinese($exampleEn);
                            if (!empty($exampleCn)) {
                                $example = $exampleEn . "。" . $exampleCn;
                            } else {
                                $example = $exampleEn; // 翻译失败，至少保留英文
                            }
                        }
                    }
                }
            } elseif ($hasEnglish && !$hasChinese) {
                // 只有英文没有中文，尝试翻译
                $exampleEn = $example;
                $exampleCn = translateToChinese($exampleEn);
                if (!empty($exampleCn)) {
                    $example = $exampleEn . "。" . $exampleCn; // 使用句号分隔
                } else {
                    // 翻译失败，重试一次
                    usleep(500000); // 等待0.5秒
                    $exampleCn = translateToChinese($exampleEn);
                    if (!empty($exampleCn)) {
                        $example = $exampleEn . "。" . $exampleCn;
                    }
                }
            }
        }
        
        $result['example'] = $example;
        return $result;
    }
    
    // 如果中文API失败，使用Free Dictionary API
    $result = fetchWordFromFreeDictionaryAPI($word);
    if ($result && !empty($result['example'])) {
        // Free Dictionary只有英文，需要翻译成中文
        $exampleEn = $result['example'];
        $exampleCn = translateToChinese($exampleEn);
        if (!empty($exampleCn)) {
            $result['example'] = $exampleEn . "。" . $exampleCn; // 使用句号分隔
        } else {
            // 翻译失败，重试一次
            usleep(500000); // 等待0.5秒
            $exampleCn = translateToChinese($exampleEn);
            if (!empty($exampleCn)) {
                $result['example'] = $exampleEn . "。" . $exampleCn;
            }
        }
    }
    
    return $result;
}

/**
 * 导入单词到数据库
 */
function importWord($conn, $grade, $word, $order) {
    // 检查是否已存在
    $stmt = $conn->prepare("SELECT id FROM word_bank WHERE grade = ? AND word = ?");
    $stmt->bind_param("ss", $grade, $word);
    $stmt->execute();
    $result = $stmt->get_result();
    if ($result->num_rows > 0) {
        echo "  [跳过] {$word} 已存在\n";
        return false;
    }
    
    // 获取单词信息
    echo "  [获取] {$word}...";
    $wordInfo = getWordInfo($word);
    
    if (!$wordInfo) {
        echo " 失败（API无数据）\n";
        return false;
    }
    
    // 插入数据库
    $stmt = $conn->prepare("INSERT INTO word_bank (grade, word, pronunciation, meaning, example, word_order) VALUES (?, ?, ?, ?, ?, ?)");
    $stmt->bind_param("sssssi", 
        $grade, 
        $wordInfo['word'], 
        $wordInfo['pronunciation'], 
        $wordInfo['meaning'], 
        $wordInfo['example'], 
        $order
    );
    
    if ($stmt->execute()) {
        echo " ✓\n";
        return true;
    } else {
        echo " ✗ 错误: " . $stmt->error . "\n";
        return false;
    }
}

/**
 * 各年级单词列表（示例数据）
 * 实际使用时可以从文件读取或从其他数据源获取
 */
$wordLists = [
    'grade1' => [
        'hello', 'good', 'thank', 'yes', 'no', 'please', 'sorry', 'bye', 'morning', 'afternoon',
        'evening', 'night', 'day', 'week', 'month', 'year', 'today', 'tomorrow', 'yesterday',
        'apple', 'banana', 'orange', 'water', 'milk', 'bread', 'rice', 'egg', 'fish', 'chicken'
    ],
    'grade2' => [
        'book', 'pen', 'pencil', 'school', 'teacher', 'student', 'class', 'desk', 'chair', 'bag',
        'friend', 'family', 'father', 'mother', 'brother', 'sister', 'grandfather', 'grandmother',
        'dog', 'cat', 'bird', 'rabbit', 'elephant', 'tiger', 'lion', 'monkey', 'panda', 'bear'
    ],
    'grade3' => [
        'happy', 'sad', 'angry', 'tired', 'hungry', 'thirsty', 'hot', 'cold', 'warm', 'cool',
        'big', 'small', 'tall', 'short', 'long', 'new', 'old', 'young', 'beautiful', 'ugly',
        'red', 'blue', 'green', 'yellow', 'black', 'white', 'orange', 'pink', 'purple', 'brown'
    ],
    'grade4' => [
        'play', 'read', 'write', 'draw', 'sing', 'dance', 'run', 'jump', 'walk', 'swim',
        'eat', 'drink', 'sleep', 'wake', 'study', 'learn', 'teach', 'help', 'work', 'rest',
        'house', 'room', 'bedroom', 'kitchen', 'bathroom', 'garden', 'park', 'zoo', 'library', 'hospital'
    ],
    'grade5' => [
        'weather', 'sunny', 'rainy', 'cloudy', 'windy', 'snowy', 'storm', 'rainbow', 'season', 'spring',
        'summer', 'autumn', 'winter', 'holiday', 'vacation', 'travel', 'trip', 'journey', 'adventure', 'explore',
        'country', 'city', 'village', 'mountain', 'river', 'lake', 'ocean', 'beach', 'forest', 'island'
    ],
    'grade6' => [
        'science', 'math', 'history', 'geography', 'art', 'music', 'sport', 'game', 'hobby', 'interest',
        'subject', 'lesson', 'homework', 'exam', 'test', 'grade', 'score', 'result', 'success', 'fail',
        'computer', 'internet', 'email', 'website', 'phone', 'mobile', 'tablet', 'camera', 'video', 'photo'
    ],
    'grade7' => [
        'important', 'necessary', 'possible', 'impossible', 'difficult', 'easy', 'simple', 'complex', 'different', 'same',
        'special', 'common', 'normal', 'strange', 'interesting', 'boring', 'exciting', 'amazing', 'wonderful', 'terrible',
        'decide', 'choose', 'plan', 'prepare', 'organize', 'manage', 'control', 'improve', 'develop', 'create'
    ],
    'grade8' => [
        'environment', 'pollution', 'protect', 'recycle', 'waste', 'energy', 'resource', 'nature', 'wildlife', 'species',
        'culture', 'tradition', 'custom', 'festival', 'celebration', 'ceremony', 'religion', 'belief', 'value', 'respect',
        'society', 'community', 'population', 'government', 'law', 'right', 'duty', 'responsibility', 'freedom', 'justice'
    ],
    'grade9' => [
        'achieve', 'accomplish', 'succeed', 'fail', 'challenge', 'obstacle', 'difficulty', 'problem', 'solution', 'method',
        'opportunity', 'chance', 'advantage', 'disadvantage', 'benefit', 'risk', 'danger', 'safety', 'security', 'protection',
        'career', 'profession', 'job', 'work', 'employ', 'employee', 'employer', 'salary', 'income', 'expense'
    ],
    'grade10' => [
        'analyze', 'evaluate', 'compare', 'contrast', 'examine', 'investigate', 'research', 'study', 'experiment', 'discover',
        'theory', 'hypothesis', 'evidence', 'proof', 'fact', 'opinion', 'argument', 'debate', 'discuss', 'conclude',
        'philosophy', 'psychology', 'sociology', 'anthropology', 'economics', 'politics', 'democracy', 'republic', 'monarchy', 'government'
    ],
    'grade11' => [
        'literature', 'novel', 'poetry', 'drama', 'fiction', 'nonfiction', 'author', 'writer', 'character', 'plot',
        'theme', 'symbol', 'metaphor', 'imagery', 'narrative', 'dialogue', 'description', 'analysis', 'interpretation', 'criticism',
        'academic', 'scholar', 'research', 'thesis', 'dissertation', 'essay', 'article', 'journal', 'publication', 'citation'
    ],
    'grade12' => [
        'university', 'college', 'academic', 'scholarship', 'tuition', 'degree', 'bachelor', 'master', 'doctor', 'professor',
        'admission', 'application', 'interview', 'recommendation', 'transcript', 'diploma', 'certificate', 'qualification', 'expertise', 'specialization',
        'career', 'profession', 'vocation', 'occupation', 'employment', 'internship', 'apprenticeship', 'mentorship', 'leadership', 'management'
    ]
];

// 主程序
echo "========================================\n";
echo "单词库批量导入工具\n";
echo "========================================\n\n";

// 选择要导入的年级
echo "请选择要导入的年级（输入年级编号，多个用逗号分隔，或输入 all 导入全部）：\n";
echo "1. 一年级 (grade1)\n";
echo "2. 二年级 (grade2)\n";
echo "3. 三年级 (grade3)\n";
echo "4. 四年级 (grade4)\n";
echo "5. 五年级 (grade5)\n";
echo "6. 六年级 (grade6)\n";
echo "7. 初一 (grade7)\n";
echo "8. 初二 (grade8)\n";
echo "9. 初三 (grade9)\n";
echo "10. 高一 (grade10)\n";
echo "11. 高二 (grade11)\n";
echo "12. 高三 (grade12)\n";
echo "\n输入: ";

// 如果是命令行运行，读取输入
if (php_sapi_name() === 'cli') {
    $input = trim(fgets(STDIN));
} else {
    // Web界面运行，使用GET参数
    $input = $_GET['grade'] ?? 'all';
}

$gradesToImport = [];
if ($input === 'all') {
    $gradesToImport = array_keys($wordLists);
} else {
    $gradeNumbers = explode(',', $input);
    $gradeMap = [
        '1' => 'grade1', '2' => 'grade2', '3' => 'grade3', '4' => 'grade4',
        '5' => 'grade5', '6' => 'grade6', '7' => 'grade7', '8' => 'grade8',
        '9' => 'grade9', '10' => 'grade10', '11' => 'grade11', '12' => 'grade12'
    ];
    foreach ($gradeNumbers as $num) {
        $num = trim($num);
        if (isset($gradeMap[$num])) {
            $gradesToImport[] = $gradeMap[$num];
        }
    }
}

if (empty($gradesToImport)) {
    die("错误：未选择有效的年级\n");
}

// 开始导入
$totalSuccess = 0;
$totalFailed = 0;

foreach ($gradesToImport as $grade) {
    if (!isset($wordLists[$grade])) {
        echo "警告：年级 {$grade} 没有单词列表\n";
        continue;
    }
    
    $words = $wordLists[$grade];
    $gradeName = [
        'grade1' => '一年级', 'grade2' => '二年级', 'grade3' => '三年级',
        'grade4' => '四年级', 'grade5' => '五年级', 'grade6' => '六年级',
        'grade7' => '初一', 'grade8' => '初二', 'grade9' => '初三',
        'grade10' => '高一', 'grade11' => '高二', 'grade12' => '高三'
    ][$grade] ?? $grade;
    
    echo "\n========================================\n";
    echo "开始导入：{$gradeName} ({$grade})\n";
    echo "单词数量：" . count($words) . "\n";
    echo "========================================\n";
    
    $success = 0;
    $failed = 0;
    $order = 1;
    
    foreach ($words as $word) {
        if (importWord($conn, $grade, $word, $order)) {
            $success++;
        } else {
            $failed++;
        }
        $order++;
        
        // 避免API请求过快，稍作延迟
        usleep(200000); // 0.2秒
    }
    
    echo "\n{$gradeName} 导入完成：成功 {$success}，失败 {$failed}\n";
    $totalSuccess += $success;
    $totalFailed += $failed;
}

echo "\n========================================\n";
echo "全部导入完成！\n";
echo "总计成功：{$totalSuccess}\n";
echo "总计失败：{$totalFailed}\n";
echo "========================================\n";

$conn->close();
