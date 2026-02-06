<?php
/**
 * 更新单词库例句脚本（多进程并行版本）
 * 更新现有单词的例句，确保包含英文+中文
 * 支持多进程并行处理，大幅提升处理速度
 */

// 设置时区
date_default_timezone_set('Asia/Shanghai');

// 数据库配置（与api.php保持一致）
$db_host = 'localhost';
$db_port = 3307;
$db_user = 'root';
$db_pass = 'root';
$db_name = 'word_app';

// 并行处理配置
$max_processes = isset($argv[1]) ? (int)$argv[1] : 4; // 默认4个进程
if ($max_processes < 1 || $max_processes > 16) {
    $max_processes = 4; // 限制在1-16之间
}

echo "========================================\n";
echo "单词库例句更新工具（多进程并行版本）\n";
echo "并行进程数：{$max_processes}\n";
echo "========================================\n\n";

// 建立连接
$conn = new mysqli($db_host, $db_user, $db_pass, $db_name, $db_port);
if ($conn->connect_error) {
    die("数据库连接失败: " . $conn->connect_error);
}
$conn->set_charset("utf8mb4");

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

// 引入更新逻辑（从原文件复制函数）
require_once __DIR__ . '/update_word_bank_examples.php';

// 统计需要更新的单词
$sql = "SELECT id, grade, word, pronunciation, meaning, example FROM word_bank ORDER BY grade, word_order";
$result = $conn->query($sql);

if (!$result) {
    die("查询失败: " . $conn->error);
}

$totalWords = $result->num_rows;
$needUpdate = [];

echo "\n正在分析单词库...\n";

while ($row = $result->fetch_assoc()) {
    $shouldUpdate = false;
    
    if ($updateMode == 1) {
        $shouldUpdate = empty($row['example']);
    } elseif ($updateMode == 2) {
        $shouldUpdate = needsUpdate($row['example']);
    } else {
        $shouldUpdate = true;
    }
    
    if ($shouldUpdate) {
        $needUpdate[] = $row;
    }
}

$conn->close();

$totalNeedUpdate = count($needUpdate);
echo "总计单词：{$totalWords} 个\n";
echo "需要更新：{$totalNeedUpdate} 个\n";
echo "预计耗时（单进程）：" . round($totalNeedUpdate * 0.2 / 60, 1) . " 分钟\n";
echo "预计耗时（{$max_processes}进程）：" . round($totalNeedUpdate * 0.2 / 60 / $max_processes, 1) . " 分钟\n\n";

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

echo "\n开始并行更新...\n\n";

// 将单词列表分割成多个批次
$batchSize = ceil($totalNeedUpdate / $max_processes);
$batches = array_chunk($needUpdate, $batchSize);

// 创建临时文件存储批次数据
$tempDir = sys_get_temp_dir();
$batchFiles = [];
foreach ($batches as $index => $batch) {
    $batchFile = $tempDir . '/word_bank_batch_' . $index . '_' . getmypid() . '.json';
    file_put_contents($batchFile, json_encode($batch));
    $batchFiles[] = $batchFile;
}

// 创建工作脚本
$workerScript = __DIR__ . '/update_word_bank_worker.php';
if (!file_exists($workerScript)) {
    // 创建工作脚本
    $workerCode = <<<'PHP'
<?php
/**
 * 工作进程脚本（由主进程调用）
 */
date_default_timezone_set('Asia/Shanghai');

$batchFile = $argv[1] ?? '';
$processId = $argv[2] ?? 0;
$updateMode = $argv[3] ?? 2;

if (empty($batchFile) || !file_exists($batchFile)) {
    die("批次文件不存在: $batchFile\n");
}

// 加载批次数据
$batch = json_decode(file_get_contents($batchFile), true);
if (!$batch) {
    die("无法读取批次数据\n");
}

// 引入函数
require_once __DIR__ . '/update_word_bank_examples.php';

// 数据库配置
$db_host = 'localhost';
$db_port = 3307;
$db_user = 'root';
$db_pass = 'root';
$db_name = 'word_app';

$conn = new mysqli($db_host, $db_user, $db_pass, $db_name, $db_port);
if ($conn->connect_error) {
    die(json_encode(['error' => "数据库连接失败: " . $conn->connect_error]));
}
$conn->set_charset("utf8mb4");

$success = 0;
$failed = 0;
$skipped = 0;
$total = count($batch);

foreach ($batch as $index => $wordData) {
    $id = $wordData['id'];
    $word = $wordData['word'];
    $grade = $wordData['grade'];
    
    // 获取单词信息
    $wordInfo = getWordInfo($word);
    
    if (!$wordInfo) {
        $failed++;
        continue;
    }
    
    // 准备更新数据
    $pronunciation = (string)($wordInfo['pronunciation'] ?? $wordData['pronunciation'] ?? '');
    $meaning = (string)($wordInfo['meaning'] ?? $wordData['meaning'] ?? '');
    
    $example = '';
    if (isset($wordInfo['example'])) {
        $example = is_array($wordInfo['example']) ? implode(' ', $wordInfo['example']) : (string)$wordInfo['example'];
    }
    
    // 确保例句格式正确
    if (!empty($example)) {
        $hasEnglish = preg_match('/[a-zA-Z]/', $example);
        $hasChinese = preg_match('/[\x{4e00}-\x{9fa5}]/u', $example);
        $hasSeparator = (strpos($example, "。") !== false) || (strpos($example, "\n") !== false);
        
        if ($hasEnglish && !$hasChinese) {
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
            if (preg_match('/^(.+?)([\x{4e00}-\x{9fa5}]+.*)$/u', $example, $matches)) {
                $example = $matches[1] . "。" . $matches[2];
            }
        } elseif ($hasSeparator && strpos($example, "\n") !== false) {
            $example = str_replace("\n", "。", $example);
        }
    }
    
    // 更新数据库
    if ($updateMode == 3 || !empty($example)) {
        $oldExample = $wordData['example'] ?? '';
        $newIsBetter = false;
        
        if (empty($oldExample)) {
            $newIsBetter = !empty($example);
        } else {
            $oldHasEnglish = preg_match('/[a-zA-Z]/', $oldExample);
            $oldHasChinese = preg_match('/[\x{4e00}-\x{9fa5}]/u', $oldExample);
            $oldHasSeparator = (strpos($oldExample, "。") !== false) || (strpos($oldExample, "\n") !== false);
            $oldHasBoth = $oldHasSeparator && $oldHasEnglish && $oldHasChinese;
            
            $newHasEnglish = preg_match('/[a-zA-Z]/', $example);
            $newHasChinese = preg_match('/[\x{4e00}-\x{9fa5}]/u', $example);
            $newHasSeparator = (strpos($example, "。") !== false) || (strpos($example, "\n") !== false);
            $newHasBoth = $newHasSeparator && $newHasEnglish && $newHasChinese;
            
            if (!$oldHasBoth && $newHasBoth) {
                $newIsBetter = true;
            }
        }
        
        if ($updateMode == 3 || $newIsBetter || empty($oldExample)) {
            if (updateWord($conn, $id, $word, $pronunciation, $meaning, $example)) {
                $success++;
            } else {
                $failed++;
            }
        } else {
            $skipped++;
        }
    } else {
        $skipped++;
    }
    
    // 避免API请求过快（每个进程独立延迟）
    usleep(200000); // 0.2秒
}

$conn->close();

// 返回结果
echo json_encode([
    'process_id' => $processId,
    'total' => $total,
    'success' => $success,
    'failed' => $failed,
    'skipped' => $skipped
]) . "\n";

// 清理临时文件
@unlink($batchFile);
PHP;
    file_put_contents($workerScript, $workerCode);
}

// 启动多个进程
$processes = [];
$startTime = microtime(true);

foreach ($batchFiles as $index => $batchFile) {
    $processId = $index + 1;
    $command = sprintf(
        'php "%s" "%s" %d %d > "%s" 2>&1 &',
        escapeshellarg($workerScript),
        escapeshellarg($batchFile),
        $processId,
        $updateMode,
        $tempDir . '/worker_' . $processId . '_' . getmypid() . '.log'
    );
    
    if (strtoupper(substr(PHP_OS, 0, 3)) === 'WIN') {
        // Windows: 使用 start 命令后台运行
        $command = 'start /B ' . $command;
        pclose(popen($command, 'r'));
    } else {
        // Linux/Unix: 直接后台运行
        exec($command);
    }
    
    $processes[] = $processId;
    echo "启动进程 {$processId}...\n";
    usleep(100000); // 延迟0.1秒，避免同时启动造成资源竞争
}

echo "\n所有进程已启动，等待完成...\n\n";

// 等待所有进程完成
$allResults = [];
$completed = 0;
$maxWaitTime = 3600; // 最多等待1小时
$checkInterval = 2; // 每2秒检查一次
$elapsed = 0;

while ($completed < count($processes) && $elapsed < $maxWaitTime) {
    sleep($checkInterval);
    $elapsed += $checkInterval;
    
    // 检查进程日志文件
    foreach ($processes as $processId) {
        if (isset($allResults[$processId])) {
            continue; // 已处理
        }
        
        $logFile = $tempDir . '/worker_' . $processId . '_' . getmypid() . '.log';
        if (file_exists($logFile)) {
            $content = file_get_contents($logFile);
            // 检查是否包含JSON结果
            if (preg_match('/\{.*"process_id".*\}/', $content, $matches)) {
                $result = json_decode($matches[0], true);
                if ($result && isset($result['process_id'])) {
                    $allResults[$processId] = $result;
                    $completed++;
                    echo "进程 {$processId} 完成：成功 {$result['success']}, 失败 {$result['failed']}, 跳过 {$result['skipped']}\n";
                    @unlink($logFile); // 清理日志文件
                }
            }
        }
    }
    
    // 显示进度
    if ($elapsed % 10 == 0) {
        echo "等待中... ({$completed}/" . count($processes) . " 进程完成，已用时 {$elapsed} 秒)\n";
    }
}

// 汇总结果
$totalSuccess = 0;
$totalFailed = 0;
$totalSkipped = 0;

foreach ($allResults as $result) {
    $totalSuccess += $result['success'] ?? 0;
    $totalFailed += $result['failed'] ?? 0;
    $totalSkipped += $result['skipped'] ?? 0;
}

$endTime = microtime(true);
$duration = round($endTime - $startTime, 2);

echo "\n========================================\n";
echo "更新完成！\n";
echo "总计成功：{$totalSuccess}\n";
echo "总计失败：{$totalFailed}\n";
echo "总计跳过：{$totalSkipped}\n";
echo "总耗时：{$duration} 秒 (" . round($duration / 60, 1) . " 分钟)\n";
echo "平均速度：" . ($duration > 0 ? round($totalNeedUpdate / $duration, 1) : 0) . " 单词/秒\n";
echo "========================================\n";

// 清理临时文件
foreach ($batchFiles as $batchFile) {
    @unlink($batchFile);
}
