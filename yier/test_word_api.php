<?php
/**
 * 测试单词API是否可用
 */

echo "========================================\n";
echo "单词API测试工具\n";
echo "========================================\n\n";

// 测试单词
$testWords = ['hello', 'good', 'thank', 'apple', 'book'];

foreach ($testWords as $word) {
    echo "测试单词: {$word}\n";
    echo "----------------------------------------\n";
    
    // 测试 Free Dictionary API
    echo "1. Free Dictionary API:\n";
    $url = "https://api.dictionaryapi.dev/api/v2/entries/en/" . urlencode($word);
    echo "   URL: {$url}\n";
    
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
            echo "   ✓ 成功\n";
            echo "   音标: " . ($wordData['phonetic'] ?? '无') . "\n";
            if (isset($wordData['meanings'][0]['definitions'][0]['definition'])) {
                echo "   释义: " . substr($wordData['meanings'][0]['definitions'][0]['definition'], 0, 50) . "...\n";
            }
        } else {
            echo "   ✗ 失败：数据格式错误\n";
        }
    } else {
        echo "   ✗ 失败：HTTP {$httpCode}\n";
    }
    
    echo "\n";
    
    // 测试中文API
    echo "2. 中文单词API:\n";
    $url = "https://api.52vmy.cn/api/wl/word?word=" . urlencode($word);
    echo "   URL: {$url}\n";
    
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
            echo "   ✓ 成功\n";
            echo "   音标: " . ($wordData['accent'] ?? '无') . "\n";
            echo "   中文: " . ($wordData['mean_cn'] ?? '无') . "\n";
        } else {
            echo "   ✗ 失败：数据格式错误\n";
        }
    } else {
        echo "   ✗ 失败：HTTP {$httpCode}\n";
    }
    
    echo "\n";
    echo "========================================\n\n";
    
    sleep(1); // 避免请求过快
}

echo "测试完成！\n";
