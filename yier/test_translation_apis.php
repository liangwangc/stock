<?php
/**
 * 测试翻译API脚本
 * 用于测试各个翻译API是否可用
 */

date_default_timezone_set('Asia/Shanghai');

$testText = "Hello, everyone.";

echo "========================================\n";
echo "翻译API测试工具\n";
echo "========================================\n\n";
echo "测试文本: {$testText}\n";
echo "期望结果: 大家好。\n\n";

// 测试函数
function testTranslation($name, $callback) {
    echo "测试 {$name}...\n";
    $start = microtime(true);
    try {
        $result = $callback();
        $time = round((microtime(true) - $start) * 1000, 0);
        if (!empty($result) && preg_match('/[\x{4e00}-\x{9fa5}]/u', $result)) {
            echo "  ✅ 成功: {$result} (耗时: {$time}ms)\n\n";
            return true;
        } else {
            echo "  ❌ 失败: 返回结果不包含中文\n";
            echo "  返回内容: " . substr($result, 0, 100) . "\n\n";
            return false;
        }
    } catch (Exception $e) {
        $time = round((microtime(true) - $start) * 1000, 0);
        echo "  ❌ 异常: " . $e->getMessage() . " (耗时: {$time}ms)\n\n";
        return false;
    }
}

// 1. Google Translate
testTranslation("Google Translate", function() use ($testText) {
    $url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=zh-CN&dt=t&q=" . urlencode($testText);
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 15);
    curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36');
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Accept: */*',
        'Referer: https://translate.google.com/'
    ]);
    $response = @curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $error = curl_error($ch);
    curl_close($ch);
    
    echo "  HTTP状态: {$httpCode}\n";
    if ($error) echo "  错误: {$error}\n";
    if ($response) echo "  响应长度: " . strlen($response) . " 字节\n";
    if ($response && strlen($response) < 500) echo "  响应内容: " . substr($response, 0, 200) . "\n";
    
    if ($httpCode === 200 && $response && !$error) {
        $data = json_decode($response, true);
        if ($data && isset($data[0]) && is_array($data[0])) {
            $translation = '';
            foreach ($data[0] as $item) {
                if (isset($item[0]) && !empty($item[0])) {
                    $translation .= $item[0];
                }
            }
            return trim($translation);
        }
    }
    return '';
});

// 2. MyMemory
testTranslation("MyMemory", function() use ($testText) {
    $url = "https://api.mymemory.translated.net/get?q=" . urlencode($testText) . "&langpair=en|zh";
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 15);
    curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    $response = @curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $error = curl_error($ch);
    curl_close($ch);
    
    echo "  HTTP状态: {$httpCode}\n";
    if ($error) echo "  错误: {$error}\n";
    if ($response && strlen($response) < 500) echo "  响应内容: " . substr($response, 0, 200) . "\n";
    
    if ($httpCode === 200 && $response) {
        $data = json_decode($response, true);
        if ($data && isset($data['responseData']['translatedText'])) {
            return trim($data['responseData']['translatedText']);
        }
    }
    return '';
});

// 3. LibreTranslate
testTranslation("LibreTranslate", function() use ($testText) {
    $url = "https://libretranslate.com/translate";
    $postData = json_encode(['q' => $testText, 'source' => 'en', 'target' => 'zh', 'format' => 'text']);
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $postData);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 15);
    curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
    $response = @curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $error = curl_error($ch);
    curl_close($ch);
    
    echo "  HTTP状态: {$httpCode}\n";
    if ($error) echo "  错误: {$error}\n";
    if ($response && strlen($response) < 500) echo "  响应内容: " . substr($response, 0, 200) . "\n";
    
    if ($httpCode === 200 && $response) {
        $data = json_decode($response, true);
        if ($data && isset($data['translatedText'])) {
            return trim($data['translatedText']);
        }
    }
    return '';
});

// 4. 百度翻译（修复版）
testTranslation("百度翻译", function() use ($testText) {
    // 尝试使用百度翻译网页版接口
    $url = "https://fanyi.baidu.com/transapi";
    $postData = http_build_query([
        'from' => 'en',
        'to' => 'zh',
        'query' => $testText
    ]);
    
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $postData);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36');
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Content-Type: application/x-www-form-urlencoded',
        'Referer: https://fanyi.baidu.com/'
    ]);
    $response = @curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    echo "  HTTP状态: {$httpCode}\n";
    echo "  响应内容: " . substr($response, 0, 200) . "\n";
    
    if ($httpCode === 200 && $response) {
        $data = json_decode($response, true);
        if ($data && isset($data['errno']) && $data['errno'] == 0) {
            if (isset($data['trans_result']['data'][0]['dst'])) {
                return trim($data['trans_result']['data'][0]['dst']);
            }
        } else {
            echo "  错误码: " . ($data['errno'] ?? 'unknown') . "\n";
            echo "  错误信息: " . ($data['errmsg'] ?? 'unknown') . "\n";
        }
    }
    return '';
});

// 5. 有道翻译（修复版）
testTranslation("有道翻译", function() use ($testText) {
    $salt = time() . rand(1000, 9999);
    $signStr = "fanyideskweb" . $testText . $salt . "Ygy_4c=r#e#4EX^NUGUc5";
    $sign = md5($signStr);
    $url = "https://fanyi.youdao.com/translate_o?smartresult=dict&smartresult=rule";
    $postData = http_build_query([
        'i' => $testText,
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
    
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $postData);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36');
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Content-Type: application/x-www-form-urlencoded',
        'Referer: https://fanyi.youdao.com/',
        'Origin: https://fanyi.youdao.com'
    ]);
    $response = @curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    echo "  HTTP状态: {$httpCode}\n";
    echo "  响应内容: " . substr($response, 0, 200) . "\n";
    
    if ($httpCode === 200 && $response) {
        $data = json_decode($response, true);
        if ($data && !isset($data['errorCode'])) {
            if (isset($data['translateResult'][0][0]['tgt'])) {
                return trim($data['translateResult'][0][0]['tgt']);
            }
        } else {
            echo "  错误码: " . ($data['errorCode'] ?? 'unknown') . "\n";
        }
    }
    return '';
});

// 6. 尝试使用Google Translate的其他端点
testTranslation("Google Translate (备用端点1)", function() use ($testText) {
    $url = "https://translate.google.com/translate_a/single?client=gtx&sl=en&tl=zh-CN&dt=t&q=" . urlencode($testText);
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 15);
    curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36');
    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Referer: https://translate.google.com/']);
    $response = @curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $error = curl_error($ch);
    curl_close($ch);
    
    echo "  HTTP状态: {$httpCode}\n";
    if ($error) echo "  错误: {$error}\n";
    if ($response && strlen($response) < 500) echo "  响应内容: " . substr($response, 0, 200) . "\n";
    
    if ($httpCode === 200 && $response && !$error) {
        $data = json_decode($response, true);
        if ($data && isset($data[0]) && is_array($data[0])) {
            $translation = '';
            foreach ($data[0] as $item) {
                if (isset($item[0]) && !empty($item[0])) {
                    $translation .= $item[0];
                }
            }
            return trim($translation);
        }
    }
    return '';
});

// 7. 尝试使用Google Translate的clients5端点
testTranslation("Google Translate (备用端点2)", function() use ($testText) {
    $url = "https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=en&tl=zh-CN&q=" . urlencode($testText);
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 15);
    curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36');
    $response = @curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $error = curl_error($ch);
    curl_close($ch);
    
    echo "  HTTP状态: {$httpCode}\n";
    if ($error) echo "  错误: {$error}\n";
    if ($response && strlen($response) < 500) echo "  响应内容: " . substr($response, 0, 200) . "\n";
    
    if ($httpCode === 200 && $response && !$error) {
        $data = json_decode($response, true);
        if ($data && is_array($data)) {
            if (isset($data[0][0][0])) {
                return trim($data[0][0][0]);
            } elseif (isset($data[0])) {
                return is_array($data[0]) ? (isset($data[0][0]) ? trim($data[0][0]) : '') : trim($data[0]);
            }
        }
    }
    return '';
});

echo "========================================\n";
echo "测试完成\n";
echo "========================================\n";
