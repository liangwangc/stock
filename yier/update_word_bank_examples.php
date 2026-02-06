<?php
/**
 * 更新单词库例句脚本
 * 更新现有单词的例句，确保包含英文+中文
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

// 引入API函数（需要先定义这些函数）
// 注意：这里需要包含import_all_grades.php中的API函数，但为了避免重复定义，我们直接在这里定义

/**
 * 使用 Free Dictionary API 获取单词信息
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
        foreach ($wordData['meanings'] as $meaningItem) {
            if (isset($meaningItem['definitions']) && !empty($meaningItem['definitions'])) {
                $def = $meaningItem['definitions'][0];
                if (isset($def['definition'])) {
                    $meanings[] = $def['definition'];
                }
            }
        }
    }
    $meaning = !empty($meanings) ? implode('; ', array_slice($meanings, 0, 3)) : '';
    
    // 提取例句（优先获取第一个有例句的定义）
    $example = '';
    if (isset($wordData['meanings'])) {
        foreach ($wordData['meanings'] as $meaningItem) {
            if (isset($meaningItem['definitions'])) {
                foreach ($meaningItem['definitions'] as $def) {
                    if (isset($def['example']) && !empty($def['example'])) {
                        $example = is_array($def['example']) ? implode(' ', $def['example']) : (string)$def['example'];
                        break 2; // 找到第一个例句就退出
                    }
                }
            }
        }
    }
    
    return [
        'word' => $word,
        'pronunciation' => $phonetic,
        'meaning' => $meaning,
        'example' => $example
    ];
}

/**
 * 使用中文API获取单词信息（备用）
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
    
    // 处理meaning字段（可能是数组或字符串）
    $meaning = '';
    if (isset($wordData['mean_cn'])) {
        if (is_array($wordData['mean_cn'])) {
            $meaning = implode('; ', $wordData['mean_cn']);
        } else {
            $meaning = (string)$wordData['mean_cn'];
        }
    }
    
    // 处理pronunciation字段（可能是数组或字符串）
    $pronunciation = '';
    if (isset($wordData['accent'])) {
        if (is_array($wordData['accent'])) {
            $pronunciation = implode(' ', $wordData['accent']);
        } else {
            $pronunciation = (string)$wordData['accent'];
        }
    }
    
    return [
        'word' => $word,
        'pronunciation' => $pronunciation,
        'meaning' => $meaning,
        'example' => $example
    ];
}

/**
 * 使用免费翻译API翻译英文句子为中文
 * 使用多个翻译API，确保成功率
 */
function translateToChinese($text, $debug = false) {
    if (empty($text) || !preg_match('/[a-zA-Z]/', $text)) {
        return ''; // 不是英文，不需要翻译
    }
    
    // 方法1：使用百度翻译免费接口（无需API Key，但可能不稳定）
    // 注意：这是非官方接口，可能随时失效
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
    curl_setopt($ch1, CURLOPT_USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');
    curl_setopt($ch1, CURLOPT_HTTPHEADER, [
        'Content-Type: application/x-www-form-urlencoded',
        'Referer: https://fanyi.baidu.com/',
        'Origin: https://fanyi.baidu.com'
    ]);
    
    $response1 = @curl_exec($ch1);
    $httpCode1 = curl_getinfo($ch1, CURLINFO_HTTP_CODE);
    $error1 = curl_error($ch1);
    curl_close($ch1);
    
    if ($httpCode1 === 200 && $response1 && !$error1) {
        $data1 = json_decode($response1, true);
        // 检查错误码
        if ($data1 && isset($data1['errno']) && $data1['errno'] == 0) {
            // 尝试多种可能的响应格式
            $translation1 = '';
            if (isset($data1['trans_result']['data'][0]['dst'])) {
                $translation1 = trim($data1['trans_result']['data'][0]['dst']);
            } elseif (isset($data1['trans_result']['data'][0]['result'][0][1])) {
                $translation1 = trim($data1['trans_result']['data'][0]['result'][0][1]);
            } elseif (isset($data1['trans_result']['data'][0])) {
                if (is_string($data1['trans_result']['data'][0])) {
                    $translation1 = trim($data1['trans_result']['data'][0]);
                } elseif (is_array($data1['trans_result']['data'][0]) && isset($data1['trans_result']['data'][0]['dst'])) {
                    $translation1 = trim($data1['trans_result']['data'][0]['dst']);
                }
            }
            
            if (!empty($translation1) && preg_match('/[\x{4e00}-\x{9fa5}]/u', $translation1)) {
                return $translation1;
            }
        }
    }
    
    // 等待一下再尝试第二个API
    usleep(500000); // 0.5秒
    
    // 方法2：使用有道翻译免费接口（无需API Key，但可能不稳定）
    // 注意：这是非官方接口，可能随时失效
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
    curl_setopt($ch2, CURLOPT_USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');
    curl_setopt($ch2, CURLOPT_HTTPHEADER, [
        'Content-Type: application/x-www-form-urlencoded',
        'Referer: https://fanyi.youdao.com/',
        'Origin: https://fanyi.youdao.com',
        'Cookie: OUTFOX_SEARCH_USER_ID=-' . rand(1000000000, 9999999999) . '@10.108.160.19'
    ]);
    
    $response2 = @curl_exec($ch2);
    $httpCode2 = curl_getinfo($ch2, CURLINFO_HTTP_CODE);
    $error2 = curl_error($ch2);
    curl_close($ch2);
    
    if ($httpCode2 === 200 && $response2 && !$error2) {
        $data2 = json_decode($response2, true);
        // 检查错误码
        if ($data2 && !isset($data2['errorCode'])) {
            // 尝试多种可能的响应格式
            $translation2 = '';
            if (isset($data2['translateResult'][0][0]['tgt'])) {
                $translation2 = trim($data2['translateResult'][0][0]['tgt']);
            } elseif (isset($data2['translateResult'][0]['tgt'])) {
                $translation2 = trim($data2['translateResult'][0]['tgt']);
            } elseif (isset($data2['smartResult']['entries'][0])) {
                $translation2 = trim($data2['smartResult']['entries'][0]);
            }
            
            if (!empty($translation2) && preg_match('/[\x{4e00}-\x{9fa5}]/u', $translation2)) {
                return $translation2;
            }
        }
    }
    
    // 所有翻译方法都失败
    if ($debug) {
        $debugInfo = "翻译失败详情: text=" . substr($text, 0, 50);
        if ($httpCode1 === 200 && $response1) {
            $data1 = json_decode($response1, true);
            $debugInfo .= ", 百度: HTTP $httpCode1";
            if ($data1 && isset($data1['errno'])) {
                $debugInfo .= " (errno: " . $data1['errno'] . ", errmsg: " . ($data1['errmsg'] ?? '') . ")";
            }
        } else {
            $debugInfo .= ", 百度: HTTP $httpCode1" . ($error1 ? " ($error1)" : "");
        }
        if ($httpCode2 === 200 && $response2) {
            $data2 = json_decode($response2, true);
            $debugInfo .= ", 有道: HTTP $httpCode2";
            if ($data2 && isset($data2['errorCode'])) {
                $debugInfo .= " (errorCode: " . $data2['errorCode'] . ")";
            }
        } else {
            $debugInfo .= ", 有道: HTTP $httpCode2" . ($error2 ? " ($error2)" : "");
        }
        error_log($debugInfo);
    }
    
    return ''; // 所有翻译方法都失败
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
        // 检查是否有完整例句（英文+中文，用句号或换行符分隔）
        $hasBoth = (strpos($example, "。") !== false || strpos($example, "\n") !== false) && $hasEnglish && $hasChinese;
        
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
                // 使用翻译API
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
        
        // 确保例句格式正确（英文。中文），统一格式
        if (!empty($example)) {
            // 如果有换行符，替换为句号
            if (strpos($example, "\n") !== false) {
                $example = str_replace("\n", "。", $example);
            }
            // 确保有英文和中文
            $hasEnglish = preg_match('/[a-zA-Z]/', $example);
            $hasChinese = preg_match('/[\x{4e00}-\x{9fa5}]/u', $example);
            $hasSeparator = strpos($example, "。") !== false;
            
            // 如果只有中文没有英文，从Free Dictionary API获取英文例句
            if (!$hasEnglish && $hasChinese) {
                $freeDictResult = fetchWordFromFreeDictionaryAPI($word);
                if ($freeDictResult && !empty($freeDictResult['example'])) {
                    $exampleEn = $freeDictResult['example'];
                    $example = $exampleEn . "。" . $example; // 英文在前，中文在后
                }
            }
            // 如果只有英文，强制翻译
            elseif ($hasEnglish && !$hasChinese) {
                $exampleEn = trim(preg_replace('/[\x{4e00}-\x{9fa5}]+.*/u', '', $example));
                if (empty($exampleEn)) {
                    $exampleEn = trim(preg_replace('/。.*/', '', $example));
                }
                if (!empty($exampleEn)) {
                    $exampleCn = translateToChinese($exampleEn);
                    if (!empty($exampleCn)) {
                        $example = $exampleEn . "。" . $exampleCn;
                    }
                }
            } elseif ($hasEnglish && $hasChinese && !$hasSeparator) {
                // 有英文和中文但没有分隔符，添加句号分隔
                if (preg_match('/^(.+?)([\x{4e00}-\x{9fa5}]+.*)$/u', $example, $matches)) {
                    $example = $matches[1] . "。" . $matches[2];
                }
            }
        } elseif (empty($example)) {
            // 完全没有例句，尝试从Free Dictionary API获取
            $freeDictResult = fetchWordFromFreeDictionaryAPI($word);
            if ($freeDictResult && !empty($freeDictResult['example'])) {
                $exampleEn = $freeDictResult['example'];
                $exampleCn = translateToChinese($exampleEn);
                if (!empty($exampleCn)) {
                    $example = $exampleEn . "。" . $exampleCn;
                } else {
                    $example = $exampleEn; // 至少保留英文
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
            } else {
                // 翻译失败，记录详细日志
                error_log("翻译失败: word=$word, example=$exampleEn");
                // 尝试再次翻译（使用调试模式）
                usleep(1000000); // 等待1秒
                $exampleCn = translateToChinese($exampleEn, true);
                if (!empty($exampleCn)) {
                    $result['example'] = $exampleEn . "。" . $exampleCn;
                } else {
                    // 最终失败，至少保留英文例句
                    $result['example'] = $exampleEn;
                }
            }
        }
    }
    
    return $result;
}

/**
 * 检查例句是否需要更新
 * 返回true表示需要更新
 */
function needsUpdate($example) {
    if (empty($example)) {
        return true; // 没有例句，需要更新
    }
    
    // 检查是否同时包含英文和中文
    $hasEnglish = preg_match('/[a-zA-Z]/', $example);
    $hasChinese = preg_match('/[\x{4e00}-\x{9fa5}]/u', $example);
    // 检查是否有分隔符（句号或换行符）
    $hasSeparator = (strpos($example, "。") !== false) || (strpos($example, "\n") !== false);
    $hasBoth = $hasSeparator && $hasEnglish && $hasChinese;
    
    // 如果只有英文或只有中文，需要更新
    if (($hasEnglish && !$hasChinese) || ($hasChinese && !$hasEnglish)) {
        return true;
    }
    
    // 如果同时有英文和中文但没有分隔符，需要更新（格式不统一）
    if ($hasEnglish && $hasChinese && !$hasSeparator) {
        return true;
    }
    
    return false; // 例句完整，不需要更新
}

/**
 * 更新单词信息
 */
function updateWord($conn, $id, $word, $pronunciation, $meaning, $example) {
    $stmt = $conn->prepare("UPDATE word_bank SET pronunciation = ?, meaning = ?, example = ? WHERE id = ?");
    $stmt->bind_param("sssi", $pronunciation, $meaning, $example, $id);
    return $stmt->execute();
}

echo "========================================\n";
echo "单词库例句更新工具\n";
echo "========================================\n\n";

// 询问更新模式
echo "请选择更新模式：\n";
echo "1. 只更新缺少例句的单词\n";
echo "2. 更新所有需要完善的单词（缺少例句或例句不完整）\n";
echo "3. 更新所有单词（强制更新）\n";
echo "\n输入选项 (1/2/3，默认2): ";

if (php_sapi_name() === 'cli') {
    $input = trim(fgets(STDIN));
    $mode = empty($input) ? '2' : $input;
} else {
    $mode = $_GET['mode'] ?? '2';
}

$updateMode = (int)$mode;
if ($updateMode < 1 || $updateMode > 3) {
    $updateMode = 2;
}

// 统计需要更新的单词
$sql = "SELECT id, grade, word, pronunciation, meaning, example FROM word_bank ORDER BY grade, word_order";
$result = $conn->query($sql);

if (!$result) {
    die("查询失败: " . $conn->error);
}

$totalWords = $result->num_rows;
$needUpdate = [];
$currentGrade = '';
$gradeCount = 0;

echo "\n正在分析单词库...\n";

while ($row = $result->fetch_assoc()) {
    $shouldUpdate = false;
    
    if ($updateMode == 1) {
        // 模式1：只更新缺少例句的
        $shouldUpdate = empty($row['example']);
    } elseif ($updateMode == 2) {
        // 模式2：更新需要完善的
        $shouldUpdate = needsUpdate($row['example']);
    } else {
        // 模式3：更新所有
        $shouldUpdate = true;
    }
    
    if ($shouldUpdate) {
        $needUpdate[] = $row;
    }
}

$totalNeedUpdate = count($needUpdate);
echo "总计单词：{$totalWords} 个\n";
echo "需要更新：{$totalNeedUpdate} 个\n";
echo "预计耗时：" . round($totalNeedUpdate * 0.2 / 60, 1) . " 分钟\n\n";

if ($totalNeedUpdate == 0) {
    echo "所有单词都已完整，无需更新！\n";
    exit;
}

echo "是否开始更新？(y/n，默认y): ";
if (php_sapi_name() === 'cli') {
    $confirm = trim(fgets(STDIN));
    if (strtolower($confirm) === 'n') {
        echo "已取消更新。\n";
        exit;
    }
}

echo "\n开始更新...\n\n";

$success = 0;
$failed = 0;
$skipped = 0;
$currentIndex = 0;

foreach ($needUpdate as $wordData) {
    $currentIndex++;
    $id = $wordData['id'];
    $word = $wordData['word'];
    $grade = $wordData['grade'];
    
    // 显示进度
    if ($currentGrade !== $grade) {
        $currentGrade = $grade;
        $gradeName = [
            'grade1' => '一年级', 'grade2' => '二年级', 'grade3' => '三年级',
            'grade4' => '四年级', 'grade5' => '五年级', 'grade6' => '六年级',
            'grade7' => '初一', 'grade8' => '初二', 'grade9' => '初三',
            'grade10' => '高一', 'grade11' => '高二', 'grade12' => '高三'
        ][$grade] ?? $grade;
        echo "\n========================================\n";
        echo "更新：{$gradeName} ({$grade})\n";
        echo "========================================\n";
    }
    
    echo "  [{$currentIndex}/{$totalNeedUpdate}] {$word}...";
    
        // 获取单词信息
        $wordInfo = getWordInfo($word);
        
        if (!$wordInfo) {
            echo " [失败：API无数据]\n";
            $failed++;
            continue;
        }
        
        // 检查例句是否完整（英文+中文）
        $example = $wordInfo['example'] ?? '';
        $hasEnglish = !empty($example) && preg_match('/[a-zA-Z]/', $example);
        $hasChinese = !empty($example) && preg_match('/[\x{4e00}-\x{9fa5}]/u', $example);
        $hasBoth = $hasEnglish && $hasChinese && (strpos($example, "。") !== false);
        
        if (!empty($example) && $hasEnglish && !$hasChinese) {
            // 只有英文没有中文，尝试再次翻译
            echo " [翻译中...]";
            $exampleEn = trim(preg_replace('/[\x{4e00}-\x{9fa5}]+.*/u', '', $example));
            if (empty($exampleEn)) {
                $exampleEn = trim(preg_replace('/\n.*/', '', $example));
            }
            if (!empty($exampleEn)) {
                usleep(500000); // 等待0.5秒
                $exampleCn = translateToChinese($exampleEn, true);
                if (!empty($exampleCn)) {
                    $wordInfo['example'] = $exampleEn . "。" . $exampleCn;
                    $hasBoth = true;
                }
            }
        }
        
        // 准备更新数据
        $pronunciation = (string)($wordInfo['pronunciation'] ?? $wordData['pronunciation'] ?? '');
        $meaning = (string)($wordInfo['meaning'] ?? $wordData['meaning'] ?? '');
        
        // 处理example字段
        $example = '';
        if (isset($wordInfo['example'])) {
            if (is_array($wordInfo['example'])) {
                $example = implode(' ', $wordInfo['example']);
            } else {
                $example = (string)$wordInfo['example'];
            }
        }
        
        // 确保例句格式正确（英文。中文）
        if (!empty($example)) {
            $hasEnglish = preg_match('/[a-zA-Z]/', $example);
            $hasChinese = preg_match('/[\x{4e00}-\x{9fa5}]/u', $example);
            $hasSeparator = (strpos($example, "。") !== false) || (strpos($example, "\n") !== false);
            
            // 如果只有英文，强制翻译
            if ($hasEnglish && !$hasChinese) {
                // 提取英文部分（去除可能的换行符）
                $exampleEn = trim(preg_replace('/[\x{4e00}-\x{9fa5}]+.*/u', '', $example));
                if (empty($exampleEn)) {
                    $exampleEn = trim(preg_replace('/\n.*/', '', $example));
                }
                if (!empty($exampleEn)) {
                    $exampleCn = translateToChinese($exampleEn);
                    if (!empty($exampleCn)) {
                        $example = $exampleEn . "。" . $exampleCn;
                    }
                }
            } elseif ($hasEnglish && $hasChinese && !$hasSeparator) {
                // 有英文和中文但没有分隔符，添加句号分隔
                if (preg_match('/^(.+?)([\x{4e00}-\x{9fa5}]+.*)$/u', $example, $matches)) {
                    $example = $matches[1] . "。" . $matches[2];
                }
            } elseif ($hasSeparator && strpos($example, "\n") !== false) {
                // 将换行符替换为句号
                $example = str_replace("\n", "。", $example);
            }
        }
    
    // 如果更新模式是3（强制更新），或者新例句比旧例句更完整，则更新
    if ($updateMode == 3 || !empty($example)) {
        // 检查新例句是否比旧例句更完整
        $oldExample = $wordData['example'] ?? '';
        $newIsBetter = false;
        
        if (empty($oldExample)) {
            $newIsBetter = !empty($example);
        } else {
            // 检查旧例句是否有完整格式（英文+中文+分隔符）
            $oldHasEnglish = preg_match('/[a-zA-Z]/', $oldExample);
            $oldHasChinese = preg_match('/[\x{4e00}-\x{9fa5}]/u', $oldExample);
            $oldHasSeparator = (strpos($oldExample, "。") !== false) || (strpos($oldExample, "\n") !== false);
            $oldHasBoth = $oldHasSeparator && $oldHasEnglish && $oldHasChinese;
            
            // 检查新例句是否有完整格式
            $newHasEnglish = preg_match('/[a-zA-Z]/', $example);
            $newHasChinese = preg_match('/[\x{4e00}-\x{9fa5}]/u', $example);
            $newHasSeparator = (strpos($example, "。") !== false) || (strpos($example, "\n") !== false);
            $newHasBoth = $newHasSeparator && $newHasEnglish && $newHasChinese;
            
            if (!$oldHasBoth && $newHasBoth) {
                $newIsBetter = true;
            }
        }
        
            if ($updateMode == 3 || $newIsBetter || empty($oldExample)) {
                // 检查最终例句是否完整
                $finalHasEnglish = preg_match('/[a-zA-Z]/', $example);
                $finalHasChinese = preg_match('/[\x{4e00}-\x{9fa5}]/u', $example);
                $finalHasBoth = $finalHasEnglish && $finalHasChinese && (strpos($example, "。") !== false);
                
                if (updateWord($conn, $id, $word, $pronunciation, $meaning, $example)) {
                    if ($finalHasBoth) {
                        echo " [成功：英文+中文]\n";
                    } elseif ($finalHasEnglish) {
                        echo " [成功：仅英文，翻译失败]\n";
                    } else {
                        echo " [成功]\n";
                    }
                    $success++;
                } else {
                    echo " [失败：数据库错误]\n";
                    $failed++;
                }
            } else {
                echo " [跳过：例句已完整]\n";
                $skipped++;
            }
    } else {
        echo " [跳过：无新例句]\n";
        $skipped++;
    }
    
    // 避免API请求过快（增加延迟以减少限流）
    usleep(2000000); // 2秒（从0.2秒增加到2秒，减少API限流）
}

echo "\n========================================\n";
echo "更新完成！\n";
echo "总计成功：{$success}\n";
echo "总计失败：{$failed}\n";
echo "总计跳过：{$skipped}\n";
echo "========================================\n";

$conn->close();
