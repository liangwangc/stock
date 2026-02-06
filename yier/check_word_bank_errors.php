<?php
/**
 * 检查单词库中的错误释义
 * 检查常见单词的释义是否正确
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
echo "单词库错误检查工具\n";
echo "========================================\n\n";

// 定义常见单词的正确释义（用于对比检查）
$commonWords = [
    'book' => ['书', '书籍', '书本'],  // book应该是"书"，不是"预订"
    'run' => ['跑', '跑步', '运行'],
    'play' => ['玩', '游戏', '演奏'],
    'read' => ['读', '阅读', '读书'],
    'write' => ['写', '书写', '写作'],
    'eat' => ['吃', '吃饭'],
    'drink' => ['喝', '喝水', '饮料'],
    'sleep' => ['睡', '睡觉', '睡眠'],
    'walk' => ['走', '步行', '散步'],
    'jump' => ['跳', '跳跃'],
    'sit' => ['坐', '坐下'],
    'stand' => ['站', '站立', '站着'],
    'go' => ['去', '走', '前往'],
    'come' => ['来', '来到'],
    'see' => ['看', '看见', '看到'],
    'look' => ['看', '瞧', '看起来'],
    'hear' => ['听', '听到', '听见'],
    'say' => ['说', '讲', '说道'],
    'tell' => ['告诉', '说', '讲述'],
    'know' => ['知道', '了解', '认识'],
    'think' => ['想', '思考', '认为'],
    'get' => ['得到', '获得', '拿到'],
    'give' => ['给', '给予', '送给'],
    'take' => ['拿', '取', '带走'],
    'make' => ['做', '制作', '制造'],
    'do' => ['做', '干', '执行'],
    'have' => ['有', '拥有', '持有'],
    'be' => ['是', '在', '存在'],
    'good' => ['好', '好的', '良好'],
    'bad' => ['坏', '不好的', '糟糕'],
    'big' => ['大', '大的', '大型'],
    'small' => ['小', '小的', '小型'],
    'new' => ['新', '新的', '新近'],
    'old' => ['旧', '老的', '旧的'],
    'hot' => ['热', '热的', '炎热'],
    'cold' => ['冷', '冷的', '寒冷'],
    'happy' => ['高兴', '快乐', '开心'],
    'sad' => ['悲伤', '难过', '伤心'],
    'red' => ['红', '红色', '红的'],
    'blue' => ['蓝', '蓝色', '蓝的'],
    'green' => ['绿', '绿色', '绿的'],
    'yellow' => ['黄', '黄色', '黄的'],
    'black' => ['黑', '黑色', '黑的'],
    'white' => ['白', '白色', '白的'],
    'one' => ['一', '一个', '1'],
    'two' => ['二', '两个', '2'],
    'three' => ['三', '三个', '3'],
    'four' => ['四', '四个', '4'],
    'five' => ['五', '五个', '5'],
    'hello' => ['你好', '您好', '打招呼'],
    'thank' => ['谢谢', '感谢', '道谢'],
    'yes' => ['是', '是的', '对'],
    'no' => ['不', '不是', '否'],
    'apple' => ['苹果', '苹果'],
    'banana' => ['香蕉', '香蕉'],
    'water' => ['水', '水'],
    'milk' => ['牛奶', '奶', '乳'],
    'bread' => ['面包', '面包'],
    'rice' => ['米', '米饭', '大米'],
    'egg' => ['蛋', '鸡蛋', '蛋类'],
    'fish' => ['鱼', '鱼类', '鱼肉'],
    'chicken' => ['鸡', '鸡肉', '小鸡'],
    'cat' => ['猫', '猫咪'],
    'dog' => ['狗', '狗狗'],
    'bird' => ['鸟', '鸟类', '鸟儿'],
    'house' => ['房子', '房屋', '家'],
    'school' => ['学校', '学校'],
    'teacher' => ['老师', '教师', '教员'],
    'student' => ['学生', '学生'],
    'father' => ['父亲', '爸爸', '爹'],
    'mother' => ['母亲', '妈妈', '娘'],
    'friend' => ['朋友', '友人'],
    'family' => ['家庭', '家人', '家族'],
];

// 检查单词库中的错误
$errors = [];
$warnings = [];
$totalChecked = 0;

echo "正在检查单词库...\n\n";

// 查询所有单词
$sql = "SELECT id, grade, word, pronunciation, meaning, example FROM word_bank ORDER BY grade, word_order";
$result = $conn->query($sql);

if (!$result) {
    die("查询失败: " . $conn->error);
}

while ($row = $result->fetch_assoc()) {
    $totalChecked++;
    $word = strtolower(trim($row['word']));
    $meaning = $row['meaning'] ?? '';
    $id = $row['id'];
    $grade = $row['grade'];
    
    // 检查是否在常见单词列表中
    if (isset($commonWords[$word])) {
        $expectedMeanings = $commonWords[$word];
        $isCorrect = false;
        
        // 检查释义是否包含期望的含义
        foreach ($expectedMeanings as $expected) {
            if (stripos($meaning, $expected) !== false) {
                $isCorrect = true;
                break;
            }
        }
        
        if (!$isCorrect) {
            // 检查是否包含明显错误的释义
            $wrongPatterns = [
                'book' => ['预订', '预约', '订票', 'v.预订', 'v.预约'],  // book在小学阶段应该是"书"，不是"预订"
                'run' => ['经营', '管理', 'v.经营', 'v.管理'],  // run在小学阶段应该是"跑"
                'play' => ['播放', '演出', 'v.播放', 'v.演出'],  // play在小学阶段应该是"玩"
                'read' => ['阅读', 'v.阅读'],  // read在小学阶段应该是"读"
                'write' => ['写作', 'v.写作'],  // write在小学阶段应该是"写"
            ];
            
            $isWrong = false;
            $wrongPattern = '';
            if (isset($wrongPatterns[$word])) {
                foreach ($wrongPatterns[$word] as $pattern) {
                    if (stripos($meaning, $pattern) !== false) {
                        $isWrong = true;
                        $wrongPattern = $pattern;
                        break;
                    }
                }
            }
            
            if ($isWrong || !$isCorrect) {
                $errors[] = [
                    'id' => $id,
                    'grade' => $grade,
                    'word' => $row['word'],
                    'current_meaning' => $meaning,
                    'expected' => implode(' / ', $expectedMeanings),
                    'type' => $isWrong ? '错误（包含：' . $wrongPattern . '）' : '可能不正确'
                ];
            }
        }
    }
    
    // 检查其他常见问题
    // 1. 释义为空
    if (empty($meaning)) {
        $warnings[] = [
            'id' => $id,
            'grade' => $grade,
            'word' => $row['word'],
            'issue' => '释义为空'
        ];
    }
    
    // 2. 释义只有词性标记，没有实际含义
    if (preg_match('/^[nvadjadvprepconj]\.?\s*$/i', trim($meaning))) {
        $warnings[] = [
            'id' => $id,
            'grade' => $grade,
            'word' => $row['word'],
            'issue' => '释义只有词性标记，没有实际含义',
            'current_meaning' => $meaning
        ];
    }
    
    // 3. 释义包含明显的错误标记
    if (preg_match('/错误|不对|不正确/i', $meaning)) {
        $errors[] = [
            'id' => $id,
            'grade' => $grade,
            'word' => $row['word'],
            'current_meaning' => $meaning,
            'type' => '包含错误标记'
        ];
    }
    
    // 4. 检查常见单词的释义是否合理（针对不同年级）
    // 低年级（1-3年级）的单词不应该有复杂的词义
    if (in_array($grade, ['grade1', 'grade2', 'grade3'])) {
        $simpleWords = [
            'book' => ['预订', '预约', '订票'],  // 低年级book应该是"书"
            'run' => ['经营', '管理', '运行'],  // 低年级run应该是"跑"
            'play' => ['播放', '演出'],  // 低年级play应该是"玩"
            'read' => ['阅读'],  // 低年级read应该是"读"
            'write' => ['写作'],  // 低年级write应该是"写"
            'make' => ['制造', '制作'],  // 低年级make应该是"做"
            'do' => ['执行'],  // 低年级do应该是"做"
            'get' => ['获得', '得到'],  // 低年级get应该是"得到"
            'take' => ['带走'],  // 低年级take应该是"拿"
            'go' => ['前往'],  // 低年级go应该是"去"
            'come' => ['来到'],  // 低年级come应该是"来"
        ];
        
        if (isset($simpleWords[$word])) {
            foreach ($simpleWords[$word] as $wrongMeaning) {
                if (stripos($meaning, $wrongMeaning) !== false && stripos($meaning, $wrongMeaning) < 10) {
                    // 如果错误释义出现在前面（前10个字符），可能是主要释义
                    $errors[] = [
                        'id' => $id,
                        'grade' => $grade,
                        'word' => $row['word'],
                        'current_meaning' => $meaning,
                        'type' => '低年级单词使用了复杂词义（' . $wrongMeaning . '）'
                    ];
                    break;
                }
            }
        }
    }
}

echo "检查完成！\n";
echo "总计检查：{$totalChecked} 个单词\n";
echo "发现错误：" . count($errors) . " 个\n";
echo "发现警告：" . count($warnings) . " 个\n\n";

if (count($errors) > 0) {
    echo "========================================\n";
    echo "错误单词列表（共 " . count($errors) . " 个）\n";
    echo "========================================\n\n";
    
    // 按问题类型分组
    $errorsByType = [];
    foreach ($errors as $error) {
        $type = $error['type'] ?? '未知';
        if (!isset($errorsByType[$type])) {
            $errorsByType[$type] = [];
        }
        $errorsByType[$type][] = $error;
    }
    
    foreach ($errorsByType as $type => $typeErrors) {
        echo "\n【{$type}】\n";
        echo str_repeat('-', 50) . "\n";
        foreach ($typeErrors as $error) {
            $gradeName = [
                'grade1' => '一年级', 'grade2' => '二年级', 'grade3' => '三年级',
                'grade4' => '四年级', 'grade5' => '五年级', 'grade6' => '六年级',
                'grade7' => '初一', 'grade8' => '初二', 'grade9' => '初三',
                'grade10' => '高一', 'grade11' => '高二', 'grade12' => '高三'
            ][$error['grade']] ?? $error['grade'];
            
            echo "ID: {$error['id']} | 年级: {$gradeName} ({$error['grade']}) | 单词: {$error['word']}\n";
            echo "当前释义: {$error['current_meaning']}\n";
            if (isset($error['expected'])) {
                echo "期望释义: {$error['expected']}\n";
            }
            echo "\n";
        }
    }
}

if (count($warnings) > 0) {
    echo "\n========================================\n";
    echo "警告列表\n";
    echo "========================================\n\n";
    
    foreach ($warnings as $warning) {
        echo "ID: {$warning['id']}\n";
        echo "年级: {$warning['grade']}\n";
        echo "单词: {$warning['word']}\n";
        echo "问题: {$warning['issue']}\n";
        if (isset($warning['current_meaning'])) {
            echo "当前释义: {$warning['current_meaning']}\n";
        }
        echo "---\n";
    }
}

// 生成修复报告文件
if (count($errors) > 0) {
    $reportFile = 'word_bank_errors_report_' . date('Ymd_His') . '.txt';
    $report = "单词库错误报告\n";
    $report .= "生成时间: " . date('Y-m-d H:i:s') . "\n";
    $report .= "总计错误: " . count($errors) . " 个\n\n";
    
    foreach ($errors as $error) {
        $gradeName = [
            'grade1' => '一年级', 'grade2' => '二年级', 'grade3' => '三年级',
            'grade4' => '四年级', 'grade5' => '五年级', 'grade6' => '六年级',
            'grade7' => '初一', 'grade8' => '初二', 'grade9' => '初三',
            'grade10' => '高一', 'grade11' => '高二', 'grade12' => '高三'
        ][$error['grade']] ?? $error['grade'];
        
        $report .= "ID: {$error['id']}\n";
        $report .= "年级: {$gradeName} ({$error['grade']})\n";
        $report .= "单词: {$error['word']}\n";
        $report .= "当前释义: {$error['current_meaning']}\n";
        if (isset($error['expected'])) {
            $report .= "期望释义: {$error['expected']}\n";
        }
        $report .= "问题类型: {$error['type']}\n";
        $report .= "\n";
    }
    
    file_put_contents($reportFile, $report);
    echo "\n========================================\n";
    echo "错误报告已保存到: {$reportFile}\n";
    echo "========================================\n\n";
}

// 统计信息
echo "\n========================================\n";
echo "统计信息\n";
echo "========================================\n\n";

// 按年级统计
$gradeStats = [];
foreach ($errors as $error) {
    $grade = $error['grade'];
    if (!isset($gradeStats[$grade])) {
        $gradeStats[$grade] = 0;
    }
    $gradeStats[$grade]++;
}

if (count($gradeStats) > 0) {
    echo "各年级错误数量：\n";
    foreach ($gradeStats as $grade => $count) {
        $gradeName = [
            'grade1' => '一年级', 'grade2' => '二年级', 'grade3' => '三年级',
            'grade4' => '四年级', 'grade5' => '五年级', 'grade6' => '六年级',
            'grade7' => '初一', 'grade8' => '初二', 'grade9' => '初三',
            'grade10' => '高一', 'grade11' => '高二', 'grade12' => '高三'
        ][$grade] ?? $grade;
        echo "  {$gradeName} ({$grade}): {$count} 个\n";
    }
}

$conn->close();

echo "\n检查完成！\n";
