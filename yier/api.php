<?php
// /var/www/html/api.php

// --- 1. 环境与时区配置 (最优先执行) ---
// 允许跨域（方便调试）
header("Access-Control-Allow-Origin: *");
header("Content-Type: application/json; charset=utf-8");

// 开启错误显示以便调试 (生产环境可关闭)
ini_set('display_errors', 0);
error_reporting(E_ALL);

// 设置错误处理，确保返回JSON而不是HTML
set_error_handler(function($errno, $errstr, $errfile, $errline) {
    if (error_reporting() === 0) {
        return false;
    }
    http_response_code(500);
    echo json_encode([
        'error' => 'PHP Error',
        'message' => $errstr,
        'file' => basename($errfile),
        'line' => $errline
    ]);
    exit;
});

// 设置异常处理
set_exception_handler(function($exception) {
    http_response_code(500);
    echo json_encode([
        'error' => 'Exception',
        'message' => $exception->getMessage(),
        'file' => basename($exception->getFile()),
        'line' => $exception->getLine()
    ]);
    exit;
});

// 【核心修改】设置时区为亚洲/上海（即北京时间）
date_default_timezone_set('Asia/Shanghai'); 
$today = date('Y-m-d'); // 此时 $today 就是准确的北京日期

// --- 2. 数据库配置 ---
$db_host = 'localhost';
$db_port = 3307; // MySQL端口
$db_user = 'root';
$db_pass = 'root'; // 你的数据库密码
$db_name = 'word_app'; // 你的数据库名

// 建立连接
$conn = new mysqli($db_host, $db_user, $db_pass, $db_name, $db_port);

// 检查连接
if ($conn->connect_error) {
    die(json_encode(["error" => "Database Connection Failed: " . $conn->connect_error]));
}
$conn->set_charset("utf8mb4");

$action = $_GET['action'] ?? '';

// 辅助函数：安全执行预处理语句
function prepare_check($conn, $sql) {
    $stmt = $conn->prepare($sql);
    if (!$stmt) {
        die(json_encode(["error" => "SQL Prepare Failed: " . $conn->error]));
    }
    return $stmt;
}

// 辅助函数：获取学习日期列表（统一使用word_review_logs表）
function getLearningDates($conn, $user_id, $limit = 30) {
    // 检查word_review_logs表是否存在
    $check_table = $conn->query("SHOW TABLES LIKE 'word_review_logs'");
    $table_exists = ($check_table && $check_table->num_rows > 0);
    
    if ($table_exists) {
        // 使用word_review_logs表（更准确，基于实际学习日期）
        $stmt = $conn->prepare("SELECT DISTINCT review_date as date FROM word_review_logs WHERE user_id = ? ORDER BY review_date DESC LIMIT ?");
    } else {
        // 回退到旧逻辑（兼容性，使用words表的date_added）
        $stmt = $conn->prepare("SELECT DISTINCT date_added as date FROM words WHERE user_id = ? ORDER BY date_added DESC LIMIT ?");
    }
    $stmt->bind_param("ii", $user_id, $limit);
    $stmt->execute();
    $result = $stmt->get_result();
    
    $dates = [];
    while ($row = $result->fetch_assoc()) {
        $dates[] = $row['date'];
    }
    return $dates;
}

// 辅助函数：判断是否是第一次登录（基于实际学习记录）
function isFirstLogin($conn, $user_id, $today) {
    // 检查word_review_logs表是否存在
    $check_table = $conn->query("SHOW TABLES LIKE 'word_review_logs'");
    $table_exists = ($check_table && $check_table->num_rows > 0);
    
    if ($table_exists) {
        // 使用word_review_logs表判断（基于实际学习记录）
        $stmt = prepare_check($conn, "
            SELECT COUNT(*) as learning_count
            FROM word_review_logs
            WHERE user_id = ? AND review_date < ?
        ");
        $stmt->bind_param("is", $user_id, $today);
        $stmt->execute();
        $result = $stmt->get_result()->fetch_assoc();
        return (int)($result['learning_count'] ?? 0) == 0;
    } else {
        // 回退到旧逻辑（兼容性）
        $stmt = prepare_check($conn, "
            SELECT COUNT(*) as total_words, 
                   COUNT(CASE WHEN date_added < ? THEN 1 END) as words_before_today
            FROM words 
            WHERE user_id = ?
        ");
        $stmt->bind_param("si", $today, $user_id);
        $stmt->execute();
        $user_history = $stmt->get_result()->fetch_assoc();
        $total_words = (int)($user_history['total_words'] ?? 0);
        $words_before_today = (int)($user_history['words_before_today'] ?? 0);
        return ($total_words == 0) || ($words_before_today == 0 && $total_words > 0);
    }
}

// 辅助函数：计算总任务量（根据天数显示不同的总任务量）
function calculateTotalTask($conn, $uid, $daily_goal, $today) {
    // 使用新的isFirstLogin函数判断
    $is_first_login = isFirstLogin($conn, $uid, $today);
    
    if ($is_first_login) {
        return $daily_goal; // 第1天
    }
    
    // 检查学习天数（使用getLearningDates函数）
    $dates = getLearningDates($conn, $uid, 30);
    $distinct_days = count($dates);
    
    if ($distinct_days == 2) {
        return (int) round($daily_goal * 2); // 第2天，取整避免浮点长小数
    } elseif ($distinct_days >= 3) {
        return (int) round($daily_goal * 2.4); // 第3天及以后，取整避免浮点长小数
    }
    
    return (int) $daily_goal; // 默认
}

// 辅助函数：获取连续打卡的日期列表（使用getLearningDates函数）
function getStreakDates($conn, $user_id, $today) {
    $dates = getLearningDates($conn, $user_id, 30);
    
    if (empty($dates)) {
        return [];
    }
    
    $has_today = in_array($today, $dates);
    $check_date = $has_today ? $today : date('Y-m-d', strtotime("$today -1 day"));
    
    $streak_dates = [];
    $current_date = $check_date;
    
    foreach ($dates as $date) {
        if ($date === $current_date) {
            $streak_dates[] = $date;
            $current_date = date('Y-m-d', strtotime("$current_date -1 day"));
        } elseif ($date < $current_date) {
            break;
        }
    }
    
    return $streak_dates;
}

// 辅助函数：计算连续打卡天数（使用getLearningDates函数）
function calculateCheckInStreak($conn, $user_id, $today) {
    // 使用统一的getLearningDates函数获取学习日期
    $dates = getLearningDates($conn, $user_id, 30);
    
    if (empty($dates)) {
        return 0;
    }
    
    // 检查今天是否有学习记录
    $has_today = in_array($today, $dates);
    
    // 如果今天没有学习，从昨天开始计算
    $check_date = $has_today ? $today : date('Y-m-d', strtotime("$today -1 day"));
    
    $streak = 0;
    $current_date = $check_date;
    
    // 从今天（或昨天）往前计算连续天数
    foreach ($dates as $date) {
        if ($date === $current_date) {
            $streak++;
            $current_date = date('Y-m-d', strtotime("$current_date -1 day"));
        } elseif ($date < $current_date) {
            // 如果日期不连续，停止计算
            break;
        }
    }
    
    return $streak;
}

// 辅助函数：计算复习优先级（以听写为主）
function calculateReviewPriority($conn, $word_id, $today) {
    $word = [];
    $stmt = prepare_check($conn, "SELECT * FROM words WHERE id = ?");
    $stmt->bind_param("i", $word_id);
    $stmt->execute();
    $word = $stmt->get_result()->fetch_assoc();
    
    if (!$word) return 0;
    
    // 获取最近5次复习记录
    $stmt = prepare_check($conn, "
        SELECT * FROM word_review_logs 
        WHERE word_id = ? 
        ORDER BY review_date DESC, created_at DESC 
        LIMIT 5
    ");
    $stmt->bind_param("i", $word_id);
    $stmt->execute();
    $recentReviews = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
    
    // 分离听写模式和学习模式的记录
    $dictationReviews = array_filter($recentReviews, function($r) {
        return $r['review_mode'] == 'dictation';
    });
    $studyReviews = array_filter($recentReviews, function($r) {
        return $r['review_mode'] == 'study';
    });
    
    $priority = 0;
    
    // ===== 统一权重：两种模式权重相同 =====
    
    // 1. 听写模式连续忘记次数
    $dictationConsecutiveForgot = 0;
    foreach ($dictationReviews as $review) {
        if ($review['quality'] == 1) {
            $dictationConsecutiveForgot++;
        } else {
            break;
        }
    }
    $priority += $dictationConsecutiveForgot * 10; // 统一权重：10
    
    // 2. 听写模式连续模糊次数
    $dictationConsecutiveVague = 0;
    foreach ($dictationReviews as $review) {
        if ($review['quality'] == 3) {
            $dictationConsecutiveVague++;
        } else {
            break;
        }
    }
    $priority += $dictationConsecutiveVague * 6; // 统一权重：6
    
    // 3. 听写模式连续记住次数（降低优先级）
    $dictationConsecutiveRemembered = 0;
    foreach ($dictationReviews as $review) {
        if ($review['quality'] == 5 && $review['should_advance'] == 1) {
            $dictationConsecutiveRemembered++;
        } else {
            break;
        }
    }
    $priority -= $dictationConsecutiveRemembered * 3; // 统一权重：-3
    
    // 4. 听写模式总失败率
    $dictationTotal = count($dictationReviews);
    if ($dictationTotal > 0) {
        $dictationFailCount = count(array_filter($dictationReviews, function($r) {
            return $r['quality'] < 5;
        }));
        $dictationFailRate = $dictationFailCount / $dictationTotal;
        $priority += $dictationFailRate * 8; // 统一权重：8
    }
    
    // ===== 学习模式权重（与听写模式相同）=====
    
    // 5. 学习模式连续忘记次数（权重与听写相同）
    $studyConsecutiveForgot = 0;
    foreach ($studyReviews as $review) {
        if ($review['quality'] == 1) {
            $studyConsecutiveForgot++;
        } else {
            break;
        }
    }
    $priority += $studyConsecutiveForgot * 10; // 统一权重：10（与听写相同）
    
    // 6. 学习模式连续模糊次数
    $studyConsecutiveVague = 0;
    foreach ($studyReviews as $review) {
        if ($review['quality'] == 3) {
            $studyConsecutiveVague++;
        } else {
            break;
        }
    }
    $priority += $studyConsecutiveVague * 6; // 统一权重：6（与听写相同）
    
    // 7. 学习模式连续记住次数（降低优先级，权重与听写相同）
    $studyConsecutiveRemembered = 0;
    foreach ($studyReviews as $review) {
        if ($review['quality'] == 5 && $review['should_advance'] == 1) {
            $studyConsecutiveRemembered++;
        } else {
            break;
        }
    }
    $priority -= $studyConsecutiveRemembered * 3; // 统一权重：-3（与听写相同）
    
    // ===== 其他因素 =====
    
    // 8. 距离上次复习时间越长，优先级越高
    if ($word['last_review_date']) {
        $daysSince = (strtotime($today) - strtotime($word['last_review_date'])) / 86400;
        $priority += min($daysSince, 7) * 2;
    }
    
    // 9. ef_factor越低（越难），优先级越高
    $priority += (3.0 - ($word['ef_factor'] ?? 2.5)) * 3;
    
    // 10. 如果只有学习模式记录，没有听写记录，提高优先级（需要听写验证）
    if (count($dictationReviews) == 0 && count($studyReviews) > 0) {
        $priority += 8;
    }
    
    return max(0, (int)$priority);
}

// 辅助函数：更新单词统计（以听写为主）
function updateWordStats($conn, $word_id, $review_mode, $today) {
    try {
        // 获取最近5次复习记录
        $stmt = prepare_check($conn, "
            SELECT * FROM word_review_logs 
            WHERE word_id = ? 
            ORDER BY review_date DESC, created_at DESC 
            LIMIT 5
        ");
        if (!$stmt) {
            error_log("updateWordStats: SQL准备失败: " . $conn->error);
            return;
        }
        $stmt->bind_param("i", $word_id);
        if (!$stmt->execute()) {
            error_log("updateWordStats: SQL执行失败: " . $stmt->error);
            return;
        }
        $allReviews = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
        
        $dictationReviews = array_filter($allReviews, function($r) {
            return $r['review_mode'] == 'dictation';
        });
        $studyReviews = array_filter($allReviews, function($r) {
            return $r['review_mode'] == 'study';
        });
        
        // ===== 听写模式统计（主要）=====
        $dictationConsecutiveRemembered = 0;
        $dictationConsecutiveForgot = 0;
        
        foreach ($dictationReviews as $review) {
            if ($review['quality'] == 5 && $review['should_advance'] == 1) {
                $dictationConsecutiveRemembered++;
            } else {
                break;
            }
        }
        
        foreach ($dictationReviews as $review) {
            if ($review['quality'] == 1) {
                $dictationConsecutiveForgot++;
            } else {
                break;
            }
        }
        
        // ===== 学习模式统计（辅助）=====
        $studyConsecutiveRemembered = 0;
        $studyConsecutiveForgot = 0;
        
        foreach ($studyReviews as $review) {
            if ($review['quality'] == 5 && $review['should_advance'] == 1) {
                $studyConsecutiveRemembered++;
            } else {
                break;
            }
        }
        
        foreach ($studyReviews as $review) {
            if ($review['quality'] == 1) {
                $studyConsecutiveForgot++;
            } else {
                break;
            }
        }
        
        // ===== 综合统计（以听写为主）=====
        $consecutiveRemembered = count($dictationReviews) > 0 
            ? $dictationConsecutiveRemembered 
            : $studyConsecutiveRemembered;
        
        $consecutiveForgot = count($dictationReviews) > 0 
            ? $dictationConsecutiveForgot 
            : $studyConsecutiveForgot;
        
        // ===== 统计总点击次数（确保数据一致性）=====
        // 从word_review_logs表统计，确保与words表一致
        $stmt = prepare_check($conn, "
            SELECT 
                SUM(CASE WHEN quality = 1 THEN 1 ELSE 0 END) as total_forgot,
                SUM(CASE WHEN quality = 3 THEN 1 ELSE 0 END) as total_vague,
                SUM(CASE WHEN quality = 5 THEN 1 ELSE 0 END) as total_remembered
            FROM word_review_logs 
            WHERE word_id = ?
        ");
        if (!$stmt) {
            error_log("updateWordStats: SQL准备失败: " . $conn->error);
            return;
        }
        $stmt->bind_param("i", $word_id);
        if (!$stmt->execute()) {
            error_log("updateWordStats: SQL执行失败: " . $stmt->error);
            return;
        }
        $counts = $stmt->get_result()->fetch_assoc();
        
        $total_forgot = (int)($counts['total_forgot'] ?? 0);
        $total_vague = (int)($counts['total_vague'] ?? 0);
        $total_remembered = (int)($counts['total_remembered'] ?? 0);
        
        // 计算复习优先级
        $priority = calculateReviewPriority($conn, $word_id, $today);
        
        // 更新words表（包括点击次数统计，确保数据一致性）
        // 先检查哪些字段存在，只更新存在的字段
        $fields_to_update = [];
        $params = [];
        $types = "";
        
        // 检查字段是否存在
        $check_fields = ['last_review_date', 'last_review_mode', 'consecutive_remembered', 'consecutive_forgot', 'review_priority'];
        $existing_fields = [];
        $stmt_check = $conn->query("SHOW COLUMNS FROM words LIKE 'last_review_date'");
        if ($stmt_check && $stmt_check->num_rows > 0) {
            $existing_fields[] = 'last_review_date';
        }
        $stmt_check = $conn->query("SHOW COLUMNS FROM words LIKE 'last_review_mode'");
        if ($stmt_check && $stmt_check->num_rows > 0) {
            $existing_fields[] = 'last_review_mode';
        }
        $stmt_check = $conn->query("SHOW COLUMNS FROM words LIKE 'consecutive_remembered'");
        if ($stmt_check && $stmt_check->num_rows > 0) {
            $existing_fields[] = 'consecutive_remembered';
        }
        $stmt_check = $conn->query("SHOW COLUMNS FROM words LIKE 'consecutive_forgot'");
        if ($stmt_check && $stmt_check->num_rows > 0) {
            $existing_fields[] = 'consecutive_forgot';
        }
        $stmt_check = $conn->query("SHOW COLUMNS FROM words LIKE 'review_priority'");
        if ($stmt_check && $stmt_check->num_rows > 0) {
            $existing_fields[] = 'review_priority';
        }
        
        // 构建UPDATE语句，只包含存在的字段
        if (in_array('last_review_date', $existing_fields)) {
            $fields_to_update[] = "last_review_date = ?";
            $params[] = $today;
            $types .= "s";
        }
        if (in_array('last_review_mode', $existing_fields)) {
            $fields_to_update[] = "last_review_mode = ?";
            $params[] = $review_mode;
            $types .= "s";
        }
        if (in_array('consecutive_remembered', $existing_fields)) {
            $fields_to_update[] = "consecutive_remembered = ?";
            $params[] = $consecutiveRemembered;
            $types .= "i";
        }
        if (in_array('consecutive_forgot', $existing_fields)) {
            $fields_to_update[] = "consecutive_forgot = ?";
            $params[] = $consecutiveForgot;
            $types .= "i";
        }
        if (in_array('review_priority', $existing_fields)) {
            $fields_to_update[] = "review_priority = ?";
            $params[] = $priority;
            $types .= "i";
        }
        
        // 添加必填字段（这些字段应该存在）
        $fields_to_update[] = "forgot_count = ?";
        $params[] = $total_forgot;
        $types .= "i";
        
        $fields_to_update[] = "vague_count = ?";
        $params[] = $total_vague;
        $types .= "i";
        
        $fields_to_update[] = "remembered_count = ?";
        $params[] = $total_remembered;
        $types .= "i";
        
        // 添加WHERE条件参数
        $params[] = $word_id;
        $types .= "i";
        
        // 构建SQL语句
        $sql = "UPDATE words SET " . implode(", ", $fields_to_update) . " WHERE id = ?";
        
        $stmt = prepare_check($conn, $sql);
        if (!$stmt) {
            error_log("updateWordStats: SQL准备失败: " . $conn->error . " SQL: " . $sql);
            return; // 静默失败，不影响主流程
        }
        $stmt->bind_param($types, ...$params);
        if (!$stmt->execute()) {
            error_log("updateWordStats: SQL执行失败: " . $stmt->error . " SQL: " . $sql);
            return; // 静默失败，不影响主流程
        }
    } catch (Exception $e) {
        error_log("updateWordStats: 异常: " . $e->getMessage());
        return; // 静默失败，不影响主流程
    }
}

// 辅助函数：从单词库导入单词
function importWordBankWords($conn, $user_id, $grade, $today, $daily_goal) {
    // 检查今天是否已经导入过
    $stmt = $conn->prepare("SELECT COUNT(*) FROM words WHERE user_id = ? AND date_added = ? AND source = 'word_bank'");
    $stmt->bind_param("is", $user_id, $today);
    $stmt->execute();
    $today_imported = $stmt->get_result()->fetch_row()[0];
    
    // 检查今天手动录入的单词数量
    $stmt = $conn->prepare("SELECT COUNT(*) FROM words WHERE user_id = ? AND date_added = ? AND source = 'manual'");
    $stmt->bind_param("is", $user_id, $today);
    $stmt->execute();
    $today_manual = $stmt->get_result()->fetch_row()[0];
    
    // 计算还需要导入的数量（考虑手动录入的单词）
    $need_import = max(0, $daily_goal - $today_manual - $today_imported);
    
    // 如果今天已经导入足够数量，不再导入
    if ($need_import <= 0) {
        return ['imported' => 0, 'manual_count' => $today_manual, 'word_bank_count' => $today_imported];
    }
    
    // 查询用户已添加的所有单词（避免重复，不管来源）
    // 修复：检查所有单词，不仅仅是word_bank来源，避免与手动添加的单词重复
    $stmt = $conn->prepare("SELECT LOWER(word) as word FROM words WHERE user_id = ?");
    $stmt->bind_param("i", $user_id);
    $stmt->execute();
    $imported_words = [];
    $result = $stmt->get_result();
    while ($row = $result->fetch_assoc()) {
        $imported_words[] = strtolower($row['word']);
    }
    
    // 从单词库中获取未导入的单词
    if (!empty($imported_words)) {
        $placeholders = implode(',', array_fill(0, count($imported_words), '?'));
        $sql = "SELECT * FROM word_bank WHERE grade = ? AND LOWER(word) NOT IN ($placeholders) ORDER BY word_order ASC LIMIT ?";
        $stmt = $conn->prepare($sql);
        $params = array_merge([$grade], array_map('strtolower', $imported_words), [$need_import]);
        $types = 's' . str_repeat('s', count($imported_words)) . 'i';
        $stmt->bind_param($types, ...$params);
    } else {
        $stmt = $conn->prepare("SELECT * FROM word_bank WHERE grade = ? ORDER BY word_order ASC LIMIT ?");
        $stmt->bind_param("si", $grade, $need_import);
    }
    
    $stmt->execute();
    $bank_words = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
    
    // 导入单词到用户词库
    if (!empty($bank_words)) {
        $import_stmt = $conn->prepare("INSERT INTO words (user_id, word, pronunciation, meaning, example, date_added, next_review, status, source) VALUES (?, ?, ?, ?, ?, ?, ?, 'new', 'word_bank')");
        $imported = 0;
        foreach ($bank_words as $bw) {
            $pronunciation = $bw['pronunciation'] ?? '';
            $meaning = $bw['meaning'] ?? '';
            $example = $bw['example'] ?? '';
            $import_stmt->bind_param("issssss", $user_id, $bw['word'], $pronunciation, $meaning, $example, $today, $today);
            if ($import_stmt->execute()) {
                $imported++;
            } else {
                // 记录导入失败的错误
                error_log("单词库导入失败: " . $import_stmt->error . " 单词: " . $bw['word']);
            }
        }
        // 记录导入结果（用于调试）
        error_log("单词库导入: 用户ID=$user_id, 年级=$grade, 需要导入=$need_import, 实际导入=$imported");
        return ['imported' => $imported, 'manual_count' => $today_manual, 'word_bank_count' => $today_imported + $imported];
    } else {
        // 检查单词库中是否有该年级的单词
        $check_stmt = $conn->prepare("SELECT COUNT(*) as total FROM word_bank WHERE grade = ?");
        $check_stmt->bind_param("s", $grade);
        $check_stmt->execute();
        $check_result = $check_stmt->get_result()->fetch_assoc();
        $total_in_bank = (int)($check_result['total'] ?? 0);
        
        // 记录日志
        error_log("单词库导入: 用户ID=$user_id, 年级=$grade, 需要导入=$need_import, 单词库中该年级共有=$total_in_bank 个单词, 已导入=" . count($imported_words) . " 个");
        return ['imported' => 0, 'manual_count' => $today_manual, 'word_bank_count' => $today_imported, 'bank_empty' => ($total_in_bank == 0)];
    }
}

// ==========================================
//                 路由逻辑
// ==========================================

// [1] 用户登录（账号+密码）
if ($action === 'login') {
    $username = $_POST['username'] ?? '';
    $password = $_POST['password'] ?? '';
    
    if (!$username || !$password) {
        exit(json_encode(['error' => '用户名和密码不能为空']));
    }
    
    // 获取客户端IP和User-Agent
    $ip_address = $_SERVER['REMOTE_ADDR'] ?? 'unknown';
    $user_agent = $_SERVER['HTTP_USER_AGENT'] ?? 'unknown';
    
    // 查询用户
    $stmt = prepare_check($conn, "SELECT id, username, password, role, daily_goal, is_active, enable_word_bank, grade FROM users WHERE username = ?");
    $stmt->bind_param("s", $username);
    $stmt->execute();
    $user = $stmt->get_result()->fetch_assoc();
    
    // 记录登录尝试
    $login_status = 'failed';
    $fail_reason = null;
    
    if (!$user) {
        $fail_reason = '用户不存在';
    } elseif ($user['is_active'] == 0) {
        $fail_reason = '账户已被禁用';
    } elseif (md5($password) !== $user['password']) {
        $fail_reason = '密码错误';
    } else {
        $login_status = 'success';
        // 更新最后登录时间
        $stmt = prepare_check($conn, "UPDATE users SET last_login = NOW() WHERE id = ?");
        $stmt->bind_param("i", $user['id']);
        $stmt->execute();
    }
    
    // 记录登录日志（如果表存在，且不影响登录流程）
    try {
        // 检查login_logs表是否存在
        $check_table = $conn->query("SHOW TABLES LIKE 'login_logs'");
        if ($check_table && $check_table->num_rows > 0) {
            if ($user) {
                $user_id = $user['id'];
                $log_username = $user['username'];
            } else {
                // 对于登录失败的情况，user_id设为0
                $user_id = 0;
                $log_username = $username;
            }
            
            // 使用try-catch包裹，避免因外键约束等问题影响登录
            $stmt = $conn->prepare("INSERT INTO login_logs (user_id, username, ip_address, user_agent, login_status, fail_reason) VALUES (?, ?, ?, ?, ?, ?)");
            if ($stmt) {
                $stmt->bind_param("isssss", $user_id, $log_username, $ip_address, $user_agent, $login_status, $fail_reason);
                if (!$stmt->execute()) {
                    // 如果执行失败（可能是外键约束），尝试只在登录成功时记录
                    if ($login_status === 'success' && $user) {
                        $stmt->close();
                        $stmt = $conn->prepare("INSERT INTO login_logs (user_id, username, ip_address, user_agent, login_status, fail_reason) VALUES (?, ?, ?, ?, ?, ?)");
                        if ($stmt) {
                            $null_reason = null;
                            $stmt->bind_param("isssss", $user['id'], $user['username'], $ip_address, $user_agent, $login_status, $null_reason);
                            $stmt->execute();
                        }
                    }
                    // 如果还是失败，忽略错误继续执行（不影响登录流程）
                }
                if (isset($stmt)) $stmt->close();
            }
        }
    } catch (Exception $e) {
        // 忽略日志记录错误，不影响登录流程
        error_log("登录日志记录失败: " . $e->getMessage());
    } catch (Error $e) {
        // 忽略致命错误，不影响登录流程
        error_log("登录日志记录致命错误: " . $e->getMessage());
    }
    
    if ($login_status === 'success') {
        // 登录成功
        $result = [
            'id' => $user['id'],
            'username' => $user['username'],
            'role' => $user['role'],
            'daily_goal' => $user['daily_goal'],
            'enable_word_bank' => $user['enable_word_bank'] ?? 0,
            'grade' => $user['grade'] ?? null,
            'server_today' => $today
        ];
        echo json_encode($result);
    } else {
        // 登录失败
        exit(json_encode(['error' => $fail_reason ?: '登录失败']));
    }
}

// [2] 日历打卡数据（增强：返回学习数量和连续打卡信息）
elseif ($action === 'calendar_data') {
    try {
        $uid = (int)$_GET['uid'];
        $month = $_GET['month'] ?? '';
        
        if (!$month) {
            echo json_encode(['error' => '月份参数不能为空']);
            exit;
        }
        
        // 获取每天的学习数量
        $stmt = prepare_check($conn, "SELECT date_added, COUNT(*) as count FROM words WHERE user_id = ? AND date_added LIKE CONCAT(?, '%') GROUP BY date_added");
        $stmt->bind_param("is", $uid, $month);
        $stmt->execute();
        $data = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
        
        // 计算连续打卡的日期（用于高亮显示）
        $streak_dates = getStreakDates($conn, $uid, $today);
        
        echo json_encode([
            'dates' => $data ?: [],
            'streak_dates' => $streak_dates ?: []
        ]);
    } catch (Exception $e) {
        http_response_code(500);
        echo json_encode([
            'error' => '获取日历数据失败',
            'message' => $e->getMessage()
        ]);
    }
}

// [3] 每日详情（点击任意日期均返回三种分类：头天+复习+新单词）
elseif ($action === 'day_details') {
    // 参数校验
    if (!isset($_GET['uid']) || !isset($_GET['date'])) {
        echo json_encode(["error" => "缺少必要参数", "message" => "需要提供 uid 和 date 参数"]);
        exit;
    }
    $uid = (int)$_GET['uid'];
    $date = $_GET['date'];
    if ($uid <= 0) {
        echo json_encode(["error" => "参数错误", "message" => "uid 必须为正整数"]);
        exit;
    }
    if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $date) || strtotime($date) === false) {
        echo json_encode(["error" => "参数错误", "message" => "date 格式不正确，需要 YYYY-MM-DD"]);
        exit;
    }
    
    // 如果点击的是今天，返回学习队列的三种分类（头天+复习+新单词）
    if ($date === $today) {
        try {
            // 获取用户设置
            $stmt = prepare_check($conn, "SELECT daily_goal FROM users WHERE id = ?");
            if (!$stmt) {
                throw new Exception("获取用户设置失败: " . $conn->error);
            }
            $stmt->bind_param("i", $uid);
            if (!$stmt->execute()) {
                throw new Exception("执行用户设置查询失败: " . $stmt->error);
            }
            $user_settings = $stmt->get_result()->fetch_assoc();
            $daily_goal = $user_settings['daily_goal'] ?? 5;
            
            // 使用统一的isFirstLogin函数判断是否是第一次登录
            $is_first_login = isFirstLogin($conn, $uid, $today);
            
            // 1. 头天（昨天学习的单词）- 全量
            $yesterday_words = [];
            $yesterday_review_count = 0;
            if (!$is_first_login) {
                $yesterday = date('Y-m-d', strtotime("$today -1 day"));
                $stmt = prepare_check($conn, "
                    SELECT w.*, 'yesterday' as word_category
                    FROM words w
                    WHERE w.user_id = ? AND w.date_added = ?
                    ORDER BY w.id ASC
                ");
                if (!$stmt) {
                    throw new Exception("查询昨天单词失败: " . $conn->error);
                }
                $stmt->bind_param("is", $uid, $yesterday);
                if (!$stmt->execute()) {
                    throw new Exception("执行昨天单词查询失败: " . $stmt->error);
                }
                $yesterday_words = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
                $yesterday_review_count = count($yesterday_words);
            }
            
            // 2. 复习（以前学的单词根据权重进行复习）- 40%的daily_goal
            $review_words = [];
            $review_count_target = 0;
            if (!$is_first_login) {
                // 检查学习天数，判断是否是第2天
                $dates = getLearningDates($conn, $uid, 30);
                $dates_before_today = array_filter($dates, function($d) use ($today) {
                    return $d < $today;
                });
                $distinct_days_before_today = count($dates_before_today);
                
                if ($distinct_days_before_today > 1) {
                    // 第3天及以后：复习单词=40%（动态计算）
                    $review_count_target = max(1, ceil($daily_goal * 0.4));
                    $yesterday = date('Y-m-d', strtotime("$today -1 day"));
                    
                    // 检查word_review_logs表是否存在
                    $table_exists = false;
                    $check_table = $conn->query("SHOW TABLES LIKE 'word_review_logs'");
                    if ($check_table && $check_table->num_rows > 0) {
                        $table_exists = true;
                    }
                    
                    if ($table_exists) {
                        // 获取基于next_review的复习单词（根据权重排序）
                        $stmt = prepare_check($conn, "
                            SELECT w.*, 'review' as word_category,
                                   -- 计算优先级分数
                                   CASE 
                                       WHEN COUNT(CASE WHEN rl_dict.review_mode = 'dictation' AND rl_dict.quality = 1 THEN 1 END) >= 2 
                                       THEN 1000 + w.review_priority
                                       WHEN COUNT(CASE WHEN rl_dict.review_mode = 'dictation' AND rl_dict.quality < 5 THEN 1 END) > 0
                                       THEN 500 + w.review_priority
                                       WHEN COUNT(CASE WHEN rl_dict.review_mode = 'dictation' THEN 1 END) = 0
                                       AND COUNT(CASE WHEN rl_study.review_mode = 'study' AND rl_study.quality = 1 THEN 1 END) >= 2
                                       THEN 200 + w.review_priority
                                       ELSE w.review_priority
                                   END as calculated_priority
                            FROM words w
                            LEFT JOIN word_review_logs rl_dict ON w.id = rl_dict.word_id AND rl_dict.review_mode = 'dictation'
                            LEFT JOIN word_review_logs rl_study ON w.id = rl_study.word_id AND rl_study.review_mode = 'study'
                            WHERE w.user_id = ? 
                              AND w.status != 'new' 
                              AND w.next_review <= ?
                              AND w.date_added != ?
                              AND w.date_added < ?
                            GROUP BY w.id
                            ORDER BY calculated_priority DESC, w.next_review ASC
                            LIMIT ?
                        ");
                    } else {
                        // 如果word_review_logs表不存在，使用简化查询
                        $stmt = prepare_check($conn, "
                            SELECT w.*, 'review' as word_category, w.review_priority as calculated_priority
                            FROM words w
                            WHERE w.user_id = ? 
                              AND w.status != 'new' 
                              AND w.next_review <= ?
                              AND w.date_added != ?
                              AND w.date_added < ?
                            ORDER BY w.review_priority DESC, w.next_review ASC
                            LIMIT ?
                        ");
                    }
                    
                    if (!$stmt) {
                        throw new Exception("查询复习单词失败: " . $conn->error);
                    }
                    $stmt->bind_param("isssi", $uid, $today, $yesterday, $yesterday, $review_count_target);
                    if (!$stmt->execute()) {
                        throw new Exception("执行复习单词查询失败: " . $stmt->error);
                    }
                    $review_words = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
                }
            }
            
            // 3. 新单词（用户设置的数量）- 100%的daily_goal
            // 修改：查询今天学习过的新单词（通过word_review_logs表），排除yesterday_words和review_words
            $new_word_target = $daily_goal;
            $new_words = [];
            
            // 获取yesterday_words和review_words的ID列表，用于排除
            $yesterday_word_ids = array_column($yesterday_words, 'id');
            $review_word_ids = array_column($review_words, 'id');
            $exclude_ids = array_merge($yesterday_word_ids, $review_word_ids);
            
            // 检查word_review_logs表是否存在
            $table_exists = false;
            $check_table = $conn->query("SHOW TABLES LIKE 'word_review_logs'");
            if ($check_table && $check_table->num_rows > 0) {
                $table_exists = true;
            }
            
            if ($table_exists) {
                // 查询今天学习过的新单词（通过word_review_logs表），排除yesterday_words和review_words
                if (!empty($exclude_ids)) {
                    $placeholders = implode(',', array_fill(0, count($exclude_ids), '?'));
                    $stmt = prepare_check($conn, "
                        SELECT DISTINCT w.*, 'new' as word_category
                        FROM words w
                        INNER JOIN word_review_logs rl ON w.id = rl.word_id AND rl.user_id = ? AND rl.review_date = ?
                        WHERE w.user_id = ?
                        AND w.id NOT IN ($placeholders)
                        ORDER BY w.date_added ASC, w.id ASC
                        LIMIT ?
                    ");
                    if (!$stmt) {
                        throw new Exception("查询新单词失败: " . $conn->error);
                    }
                    $params = array_merge([$uid, $today, $uid], $exclude_ids, [$new_word_target]);
                    $types = 'isi' . str_repeat('i', count($exclude_ids)) . 'i';
                    $stmt->bind_param($types, ...$params);
                } else {
                    // 如果没有需要排除的单词，直接查询今天学习过的单词
                    $stmt = prepare_check($conn, "
                        SELECT DISTINCT w.*, 'new' as word_category
                        FROM words w
                        INNER JOIN word_review_logs rl ON w.id = rl.word_id AND rl.user_id = ? AND rl.review_date = ?
                        WHERE w.user_id = ?
                        ORDER BY w.date_added ASC, w.id ASC
                        LIMIT ?
                    ");
                    if (!$stmt) {
                        throw new Exception("查询新单词失败: " . $conn->error);
                    }
                    $stmt->bind_param("isii", $uid, $today, $uid, $new_word_target);
                }
                
                if (!$stmt->execute()) {
                    throw new Exception("执行新单词查询失败: " . $stmt->error);
                }
                $new_words_from_logs = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
                
                // 如果从word_review_logs查询到的单词不够，补充今天添加的单词（排除已查询的）
                if (count($new_words_from_logs) < $new_word_target) {
                    $remaining = $new_word_target - count($new_words_from_logs);
                    $all_exclude_ids = array_merge($exclude_ids, array_column($new_words_from_logs, 'id'));
                    if (!empty($all_exclude_ids)) {
                        $placeholders2 = implode(',', array_fill(0, count($all_exclude_ids), '?'));
                        $stmt = prepare_check($conn, "
                            SELECT *, 'new' as word_category 
                            FROM words 
                            WHERE user_id = ? AND date_added = ? 
                            AND id NOT IN ($placeholders2)
                            ORDER BY id ASC 
                            LIMIT ?
                        ");
                        if ($stmt) {
                            $params2 = array_merge([$uid, $today], $all_exclude_ids, [$remaining]);
                            $types2 = 'is' . str_repeat('i', count($all_exclude_ids)) . 'i';
                            $stmt->bind_param($types2, ...$params2);
                            if ($stmt->execute()) {
                                $new_words_from_today = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
                                $new_words = array_merge($new_words_from_logs, $new_words_from_today);
                            } else {
                                $new_words = $new_words_from_logs;
                            }
                        } else {
                            $new_words = $new_words_from_logs;
                        }
                    } else {
                        // 如果没有需要排除的，直接查询今天添加的单词
                        $stmt = prepare_check($conn, "
                            SELECT *, 'new' as word_category 
                            FROM words 
                            WHERE user_id = ? AND date_added = ? 
                            ORDER BY id ASC 
                            LIMIT ?
                        ");
                        if ($stmt) {
                            $stmt->bind_param("isi", $uid, $today, $remaining);
                            if ($stmt->execute()) {
                                $new_words_from_today = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
                                $new_words = array_merge($new_words_from_logs, $new_words_from_today);
                            } else {
                                $new_words = $new_words_from_logs;
                            }
                        } else {
                            $new_words = $new_words_from_logs;
                        }
                    }
                } else {
                    $new_words = $new_words_from_logs;
                }
            } else {
                // 如果word_review_logs表不存在，只查询今天添加的单词
                // 先获取今天手动录入的单词
                $stmt = prepare_check($conn, "SELECT *, 'new' as word_category FROM words WHERE user_id = ? AND date_added = ? AND source = 'manual' ORDER BY id ASC LIMIT ?");
                if (!$stmt) {
                    throw new Exception("查询手动录入单词失败: " . $conn->error);
                }
                $stmt->bind_param("isi", $uid, $today, $new_word_target);
                if (!$stmt->execute()) {
                    throw new Exception("执行手动录入单词查询失败: " . $stmt->error);
                }
                $list_manual = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
                
                // 计算还需要多少新单词
                $manual_count = count($list_manual);
                $remaining = max(0, $new_word_target - $manual_count);
                
                // 如果还有剩余，从单词库导入的单词中取
                $list_word_bank = [];
                if ($remaining > 0) {
                    $stmt = prepare_check($conn, "SELECT *, 'new' as word_category FROM words WHERE user_id = ? AND date_added = ? AND source = 'word_bank' ORDER BY id ASC LIMIT ?");
                    if (!$stmt) {
                        throw new Exception("查询单词库单词失败: " . $conn->error);
                    }
                    $stmt->bind_param("isi", $uid, $today, $remaining);
                    if (!$stmt->execute()) {
                        throw new Exception("执行单词库单词查询失败: " . $stmt->error);
                    }
                    $list_word_bank = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
                }
                
                $new_words = array_merge($list_manual, $list_word_bank);
            }
            
            if (count($new_words) > $new_word_target) {
                $new_words = array_slice($new_words, 0, $new_word_target);
            }
            
            // 返回三种分类
            echo json_encode([
                'yesterday_words' => $yesterday_words,  // 头天（昨天学习的单词）
                'review_words' => $review_words,        // 复习（以前学的单词根据权重）
                'new_words' => $new_words,              // 新单词（用户设置的数量）
                'stats' => [
                    'yesterday_count' => $yesterday_review_count,
                    'review_count' => count($review_words),
                    'new_word_count' => count($new_words),
                    'total_count' => $yesterday_review_count + count($review_words) + count($new_words)
                ]
            ]);
        } catch (Exception $e) {
            http_response_code(500);
            echo json_encode([
                'error' => '获取今天的学习队列失败',
                'message' => $e->getMessage()
            ]);
        }
    } else {
        // 如果点击的是其他日期，也返回三种分类：头天、复习、新单词（与今天格式一致）
        $yesterday = date('Y-m-d', strtotime("$date -1 day"));

        // 1. 头天（该日期的前一天添加的单词）
        $yesterday_words = [];
        $stmt = prepare_check($conn, "SELECT w.*, 'yesterday' as word_category FROM words w WHERE w.user_id = ? AND w.date_added = ? ORDER BY w.id ASC");
        if ($stmt) {
            $stmt->bind_param("is", $uid, $yesterday);
            if ($stmt->execute()) {
                $yesterday_words = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
            }
        }

        // 2. 复习（该日期复习过的、且 date_added < 前一天的单词）
        // 注意：需要 word_review_logs 表才能获取历史复习记录；若该表不存在则复习列表为空
        $review_words = [];
        $check_table = $conn->query("SHOW TABLES LIKE 'word_review_logs'");
        if ($check_table && $check_table->num_rows > 0) {
            $stmt = prepare_check($conn, "
                SELECT DISTINCT w.*, 'review' as word_category
                FROM words w
                INNER JOIN word_review_logs rl ON w.id = rl.word_id AND rl.user_id = ? AND rl.review_date = ?
                WHERE w.user_id = ? AND w.date_added < ?
                ORDER BY w.id ASC
            ");
            if ($stmt) {
                $stmt->bind_param("isis", $uid, $date, $uid, $yesterday);
                if ($stmt->execute()) {
                    $review_words = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
                }
            }
        }

        // 3. 新单词（该日期添加的单词）
        $new_words = [];
        $stmt = prepare_check($conn, "SELECT w.*, 'new' as word_category FROM words w WHERE w.user_id = ? AND w.date_added = ? ORDER BY w.id ASC");
        if ($stmt) {
            $stmt->bind_param("is", $uid, $date);
            if ($stmt->execute()) {
                $new_words = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
            }
        }

        $yesterday_count = count($yesterday_words);
        $review_count = count($review_words);
        $new_word_count = count($new_words);
        $has_review_logs = ($check_table && $check_table->num_rows > 0);
        echo json_encode([
            'yesterday_words' => $yesterday_words,
            'review_words' => $review_words,
            'new_words' => $new_words,
            'stats' => [
                'yesterday_count' => $yesterday_count,
                'review_count' => $review_count,
                'new_word_count' => $new_word_count,
                'total_count' => $yesterday_count + $review_count + $new_word_count,
                'has_review_logs' => $has_review_logs  // 若为false表示无word_review_logs表，复习数据可能不完整
            ]
        ]);
    }
}

// [4] 查词代理
elseif ($action === 'lookup') {
    $word = urlencode($_GET['word']);
    $url = "https://dict.youdao.com/jsonapi?q={$word}";
    $ctx = stream_context_create(["http"=>["header"=>"User-Agent: Mozilla/5.0"]]);
    $res = @file_get_contents($url, false, $ctx);
    echo $res ? $res : json_encode([]); 
}

// [5] 添加单词 (使用顶部定义的 $today，标记为手动录入)
elseif ($action === 'add_word') {
    $in = json_decode(file_get_contents('php://input'), true);
    $target_date = $in['date'] ?? $today;
    
    if ($target_date < $today) {
        $status = 'review';
        $next_review = date('Y-m-d', strtotime($target_date . ' +1 day'));
    } else {
        $status = 'new';
        $next_review = $target_date;
    }
    
    // 手动录入的单词，source标记为'manual'
    $stmt = prepare_check($conn, "INSERT INTO words (user_id, word, pronunciation, meaning, example, date_added, next_review, status, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'manual')");
    $ex = $in['example'] ?? '';
    $stmt->bind_param("isssssss", $in['uid'], $in['word'], $in['ipa'], $in['meaning'], $ex, $target_date, $next_review, $status);
    
    if ($stmt->execute()) echo json_encode(["status" => "ok"]);
    else echo json_encode(["error" => $stmt->error]);
}

// [6] 获取首页数据 (使用顶部定义的 $today，优化：优先显示待复习，支持单词库)
elseif ($action === 'get_home_data') {
    $uid = (int)$_GET['uid'];
    $limit = isset($_GET['limit']) ? (int)$_GET['limit'] : 100; 
    
    // 获取用户设置（是否启用单词库）
    $stmt = prepare_check($conn, "SELECT daily_goal, enable_word_bank, grade FROM users WHERE id = ?");
    $stmt->bind_param("i", $uid);
    $stmt->execute();
    $user_settings = $stmt->get_result()->fetch_assoc();
    $enable_word_bank = $user_settings['enable_word_bank'] ?? 0;
    $grade = $user_settings['grade'] ?? null;
    $daily_goal = $user_settings['daily_goal'] ?? 5;
    
    // 使用统一的isFirstLogin函数判断是否是第一次登录
    $is_first_login = isFirstLogin($conn, $uid, $today);
    
    // 计算总任务量（使用公共函数）
    $total_task = calculateTotalTask($conn, $uid, $daily_goal, $today);
    
    // 计算复习单词（40%）和昨天新单词
    $review_count_target = 0; // 复习单词（40%）
    $yesterday_review_count = 0; // 昨天新单词（全量）
    
    if (!$is_first_login) {
        // 昨天新单词（全量）
        $yesterday = date('Y-m-d', strtotime("$today -1 day"));
        $stmt = prepare_check($conn, "
            SELECT COUNT(*) as yesterday_count
            FROM words 
            WHERE user_id = ? AND date_added = ?
        ");
        $stmt->bind_param("is", $uid, $yesterday);
        $stmt->execute();
        $yesterday_result = $stmt->get_result()->fetch_assoc();
        $yesterday_review_count = (int)($yesterday_result['yesterday_count'] ?? 0);
        
        // 检查学习天数，判断是否是第2天（与prepare_study_queue保持一致）
        $dates = getLearningDates($conn, $uid, 30);
        $dates_before_today = array_filter($dates, function($date) use ($today) {
            return $date < $today;
        });
        $distinct_days_before_today = count($dates_before_today);
        
        if ($distinct_days_before_today == 1) {
            // 第2天：今天之前只有1个学习日期（昨天），今天是第2天
            $review_count_target = 0; // 第2天：复习单词=0个（第一天没有需要复习的）
        } else {
            // 第3天及以后：今天之前有2个或更多学习日期
            $review_count_target = max(1, ceil($daily_goal * 0.4)); // 40%的复习量（动态计算），至少1个
        }
    }
    
    // 要复习显示：复习单词（40%）+ 昨天新单词（全量）
    $review_display_count = $review_count_target + $yesterday_review_count;

    // B. 待学新词（优先手动录入，然后单词库）
    // 新需求：新单词数量为100%的每日目标
    $new_word_target = $daily_goal; // 100%的每日目标
    
    // 先获取手动录入的单词
    $stmt = prepare_check($conn, "SELECT * FROM words WHERE user_id = ? AND status = 'new' AND date_added <= ? AND source = 'manual' ORDER BY date_added ASC, id ASC");
    $stmt->bind_param("is", $uid, $today);
    $stmt->execute();
    $list_manual = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
    
    // 计算还需要多少单词（基于100%的每日目标）
    $manual_count = count($list_manual);
    $remaining = max(0, $new_word_target - $manual_count);
    
    // 如果还有剩余，从单词库导入的单词中取
    $list_word_bank = [];
    if ($remaining > 0) {
        $stmt = prepare_check($conn, "SELECT * FROM words WHERE user_id = ? AND status = 'new' AND date_added <= ? AND source = 'word_bank' ORDER BY date_added ASC, id ASC LIMIT ?");
        $stmt->bind_param("isi", $uid, $today, $remaining);
        $stmt->execute();
        $list_word_bank = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
    }
    
    // 合并：手动录入优先
    $list_new = array_merge($list_manual, $list_word_bank);

    // C. 统计
    $stmt = prepare_check($conn, "SELECT COUNT(*) FROM words WHERE user_id = ? AND status = 'new' AND date_added <= ?");
    $stmt->bind_param("is", $uid, $today);
    $stmt->execute();
    $count_current_pool = $stmt->get_result()->fetch_row()[0];

    $stmt = prepare_check($conn, "SELECT COUNT(*) FROM words WHERE user_id = ? AND status = 'new' AND date_added > ?");
    $stmt->bind_param("is", $uid, $today);
    $stmt->execute();
    $count_future = $stmt->get_result()->fetch_row()[0];

    // D. 计算连续打卡天数
    $streak = calculateCheckInStreak($conn, $uid, $today);
    
    // E. 计算今日实际学习的单词数（包括新学和复习）
    // 统一使用word_review_logs表统计实际学习过的单词，更准确
    // 先检查word_review_logs表是否存在
    $table_exists = false;
    $check_table = $conn->query("SHOW TABLES LIKE 'word_review_logs'");
    if ($check_table && $check_table->num_rows > 0) {
        $table_exists = true;
    }
    
    if ($table_exists) {
        // 使用word_review_logs表统计今天实际学习过的单词（包括新学和复习）
        $stmt = prepare_check($conn, "
            SELECT COUNT(DISTINCT word_id) as today_learned 
            FROM word_review_logs 
            WHERE user_id = ? AND review_date = ?
        ");
        $stmt->bind_param("is", $uid, $today);
        $stmt->execute();
        $today_learned_result = $stmt->get_result()->fetch_assoc();
        $today_learned_count = (int)($today_learned_result['today_learned'] ?? 0);
        
        // 分别统计新学和复习（用于显示）
        // 新学：今天添加的单词中，有学习记录的
        $stmt = prepare_check($conn, "
            SELECT COUNT(DISTINCT w.id) as today_new 
            FROM words w
            INNER JOIN word_review_logs rl ON w.id = rl.word_id
            WHERE w.user_id = ? AND w.date_added = ? AND rl.user_id = ? AND rl.review_date = ?
        ");
        $stmt->bind_param("isis", $uid, $today, $uid, $today);
        $stmt->execute();
        $today_new_result = $stmt->get_result()->fetch_assoc();
        $today_new_count = (int)($today_new_result['today_new'] ?? 0);
        
        // 复习：今天复习的单词（date_added不是今天）
        $today_reviewed_count = $today_learned_count - $today_new_count;
        
        // 统计今天已听写的单词数（review_mode='dictation'）
        $stmt = prepare_check($conn, "
            SELECT COUNT(DISTINCT word_id) as today_dictation 
            FROM word_review_logs 
            WHERE user_id = ? AND review_date = ? AND review_mode = 'dictation'
        ");
        $stmt->bind_param("is", $uid, $today);
        $stmt->execute();
        $today_dictation_result = $stmt->get_result()->fetch_assoc();
        $today_dictation_count = (int)($today_dictation_result['today_dictation'] ?? 0);
    } else {
        // 如果word_review_logs表不存在，回退到旧逻辑（兼容性）
        // 1. 统计今天新添加的单词
        $stmt = prepare_check($conn, "
            SELECT COUNT(*) as today_new 
            FROM words 
            WHERE user_id = ? AND date_added = ?
        ");
        $stmt->bind_param("is", $uid, $today);
        $stmt->execute();
        $today_new_result = $stmt->get_result()->fetch_assoc();
        $today_new_count = (int)($today_new_result['today_new'] ?? 0);
        $today_reviewed_count = 0;
        $today_learned_count = $today_new_count;
        $today_dictation_count = 0;
    }
    
    // 计算今日学习进度百分比（基于今天实际学习的单词数和实际总任务量）
    // 注意：$total_task已经在上面计算好了（第982-1002行），根据天数显示不同的总任务量
    $progress_percent = $total_task > 0 ? min(100, round(($today_learned_count / $total_task) * 100)) : 0;
    
    // F. 计算今日获得的星星（基于今天实际学习过的单词数）
    // 每个单词1颗星：今天新学的单词 + 今天复习的单词
    $today_stars = $today_learned_count; // 使用实际学习的单词数，而不是队列数量
    
    // 新单词目标数已经在上面计算过了（在B部分）
    
    // 统计今天已导入的新单词数量（包括手动录入和单词库）
    $stmt = prepare_check($conn, "
        SELECT COUNT(*) as today_new_words
        FROM words 
        WHERE user_id = ? AND status = 'new' AND date_added = ?
    ");
    $stmt->bind_param("is", $uid, $today);
    $stmt->execute();
    $today_new_words_result = $stmt->get_result()->fetch_assoc();
    $today_new_words_count = (int)($today_new_words_result['today_new_words'] ?? 0);
    
    // 新需求：新单词显示为100%的每日目标
    $display_new_count = $new_word_target; // 100%的每日目标
    
    echo json_encode([
        "stats" => [
            "review_count" => $review_display_count,  // 要复习：复习单词（40%）+ 昨天新单词（全量）
            "new_count"    => $display_new_count,   // 新单词：今天新单词（100%）
            "new_count_target" => $new_word_target,  // 新单词目标数（100%）
            "review_count_target" => $review_count_target,  // 复习单词（40%）
            "yesterday_review_count" => $yesterday_review_count,  // 昨天新单词（全量）
            "future_count" => $count_future,           
            "total_pending"=> (int) round($total_task),         // 今天任务（取整，避免前端显示长小数）
            "backlog_remaining" => max(0, $count_current_pool - count($list_new)),
            "manual_count" => $manual_count,
            "word_bank_count" => count($list_word_bank),
            "streak_days" => $streak,
            "progress_percent" => $progress_percent,
            "today_stars" => $today_stars,
            "today_learned_count" => $today_learned_count,
            "today_dictation_count" => $today_dictation_count ?? 0,  // 今天已听写的单词数
            "daily_goal" => $daily_goal,  // 添加每日目标到stats中
            "today_new_words_count" => $today_new_words_count,  // 今天实际导入的新单词数
            "enable_word_bank" => $enable_word_bank,  // 是否启用单词库
            "grade" => $grade,  // 年级
            "is_first_login" => $is_first_login  // 是否是第一次登录
        ]
    ]);
}

// [7] 提交复习（优化：记录复习日志，以听写为主）
elseif ($action === 'submit_review') {
    try {
        $raw_input = file_get_contents('php://input');
        $in = json_decode($raw_input, true);
        
        // 记录请求数据（用于调试）
        error_log("submit_review请求数据: " . $raw_input);
        
        if (!$in || !isset($in['id'])) {
            error_log("submit_review错误: 缺少必要参数，输入数据: " . $raw_input);
            echo json_encode(["status" => "error", "message" => "缺少必要参数: id"]);
            exit;
        }
        
        $id = (int)$in['id']; 
        $q = isset($in['quality']) ? (int)$in['quality'] : 0;
        $should_advance = isset($in['should_advance']) ? (bool)$in['should_advance'] : false;
        $review_mode = isset($in['review_mode']) ? $in['review_mode'] : 'study'; // 默认为学习模式
        
        error_log("submit_review参数: id=$id, quality=$q, should_advance=" . ($should_advance ? 'true' : 'false') . ", review_mode=$review_mode");
        
        // 验证review_mode
        if (!in_array($review_mode, ['study', 'dictation'])) {
            $review_mode = 'study';
        }
        
        $stmt = prepare_check($conn, "SELECT * FROM words WHERE id = ?");
        if (!$stmt) {
            $error_msg = "SQL准备失败: " . $conn->error;
            error_log("submit_review错误: " . $error_msg);
            echo json_encode(["status" => "error", "message" => $error_msg]);
            exit;
        }
        $stmt->bind_param("i", $id);
        if (!$stmt->execute()) {
            $error_msg = "SQL执行失败: " . $stmt->error;
            error_log("submit_review错误: " . $error_msg);
            echo json_encode(["status" => "error", "message" => $error_msg]);
            exit;
        }
        $w = $stmt->get_result()->fetch_assoc();
        
        if (!$w) {
            error_log("submit_review错误: 单词不存在，id=$id");
            echo json_encode(["status" => "error", "message" => "单词不存在: id=$id"]);
            exit;
        }
        
        error_log("submit_review: 找到单词，id=$id, word=" . ($w['word'] ?? 'N/A'));
        
        // 【新需求】检查是否重复学习（今天是否已有该模式的记录）
        $is_repeat = false;
        $other_mode_completed = false;
        $other_mode = ($review_mode === 'study') ? 'dictation' : 'study';
        
        // 检查今天是否已有该模式的记录
        $check_repeat_stmt = prepare_check($conn, "
            SELECT COUNT(*) as count 
            FROM word_review_logs 
            WHERE word_id = ? AND user_id = ? AND review_mode = ? AND DATE(review_date) = ?
        ");
        $user_id = (int)$w['user_id'];
        $check_repeat_stmt->bind_param("iiss", $id, $user_id, $review_mode, $today);
        $check_repeat_stmt->execute();
        $repeat_result = $check_repeat_stmt->get_result()->fetch_assoc();
        if ($repeat_result && (int)$repeat_result['count'] > 0) {
            $is_repeat = true;
            error_log("submit_review: 重复学习，word_id=$id, mode=$review_mode");
        }
        
        // 检查另一种模式今天是否已完成
        $check_other_stmt = prepare_check($conn, "
            SELECT COUNT(*) as count 
            FROM word_review_logs 
            WHERE word_id = ? AND user_id = ? AND review_mode = ? AND DATE(review_date) = ?
        ");
        $check_other_stmt->bind_param("iiss", $id, $user_id, $other_mode, $today);
        $check_other_stmt->execute();
        $other_result = $check_other_stmt->get_result()->fetch_assoc();
        if ($other_result && (int)$other_result['count'] > 0) {
            $other_mode_completed = true;
            error_log("submit_review: 另一种模式已完成，word_id=$id, other_mode=$other_mode");
        }
        
        // 记录复习前的状态（处理NULL值）
        $ef_before = (float)($w['ef_factor'] ?? 2.5); 
        $int_before = (int)($w['interval_days'] ?? 0); 
        $reps_before = (int)($w['repetitions'] ?? 0);
        
        $ef = $ef_before;
        $int = $int_before;
        $reps = $reps_before;
        
        // 获取当前的点击次数
        $forgot_count = (int)($w['forgot_count'] ?? 0);
        $vague_count = (int)($w['vague_count'] ?? 0);
        $remembered_count = (int)($w['remembered_count'] ?? 0);
        
        // 【新需求】如果是重复学习或另一种模式已完成，不计分（不更新点击次数）
        // 否则正常记录点击次数
        if (!$is_repeat && !$other_mode_completed) {
            // 根据quality记录点击次数
            if ($q == 1) {
                $forgot_count++;
            } elseif ($q == 3) {
                $vague_count++;
            } elseif ($q == 5) {
                $remembered_count++;
            }
        }
        
        // 【新需求】如果另一种模式已完成，当前模式也标记为完成但不计分
        // 如果重复学习，也不计分
        $should_update_score = !$is_repeat && !$other_mode_completed;
        
        // 判断是否需要更新复习计划
        // 1. 记住（quality=5）：总是更新
        // 2. 模糊（quality=3）且确认跳转：更新
        // 3. 忘记（quality=1）且确认跳转：第5次以后写错的情况，标记为重点复习
        if ($q == 5 || ($q == 3 && $should_advance) || ($q == 1 && $should_advance)) {
            if ($q == 5 || ($q == 3 && $should_advance)) {
                // 记住或模糊（确认跳转）：正常推进
                // 【新需求】如果另一种模式已完成或重复学习，不更新复习计划（保持原状态）
                if ($should_update_score) {
                    if ($reps == 0) {
                        $date_added = $w['date_added'] ?? $today;
                        $days_since = (new DateTime($date_added))->diff(new DateTime($today))->days;
                        if ($days_since > 2) { 
                            $int = $days_since; 
                            $ef += 0.2; 
                        } else { 
                            $int = 1; 
                        }
                    } elseif ($reps == 1) { 
                        $int = 6; 
                    } else { 
                        $int = round($int * $ef); 
                    }
                    $reps++; 
                    $ef = max(1.3, $ef + (0.1 - (5 - $q) * (0.08 + (5 - $q) * 0.02)));
                    
                    // 状态转换规则：
                    // - repetitions >= 5 且 ef_factor >= 2.5：已掌握（mastered）
                    // - repetitions >= 3：复习中（review）
                    // - 其他：学习中（learning）
                    if ($reps >= 5 && $ef >= 2.5) {
                        $status = 'mastered';
                    } elseif ($reps >= 3) {
                        $status = 'review';
                    } else {
                        $status = 'learning';
                    }
                    
                    // 计算下次复习日期
                    $next = date('Y-m-d', strtotime("$today +$int days"));
                } else {
                    // 另一种模式已完成或重复学习：不更新复习计划，保持原状态
                    $next = $w['next_review'] ?? $today;
                    $int = $int_before;
                    $ef = $ef_before;
                    $reps = $reps_before;
                    $status = $w['status'] ?? 'learning';
                    error_log("submit_review: 另一种模式已完成或重复学习，不更新复习计划，word_id=$id");
                }
            } else {
                // 忘记（quality=1）且确认跳转：第5次以后写错的情况，标记为重点复习
                // 【新需求】如果另一种模式已完成或重复学习，不更新复习计划
                if ($should_update_score) {
                    // 降低EF因子，缩短间隔，明天重点复习
                    $reps = 0; // 重置复习次数
                    $ef = max(1.3, $ef - 0.2); // 降低EF因子，标记为更困难
                    $int = 1; // 明天复习
                    $next = date('Y-m-d', strtotime("$today +1 day")); // 明天重点复习
                    $status = 'learning'; // 标记为学习中
                } else {
                    // 另一种模式已完成或重复学习：不更新复习计划
                    $next = $w['next_review'] ?? $today;
                    $int = $int_before;
                    $ef = $ef_before;
                    $reps = $reps_before;
                    $status = $w['status'] ?? 'learning';
                }
            }
            
            // 更新数据库（包括复习计划和点击次数）
            $stmt = prepare_check($conn, "UPDATE words SET next_review=?, interval_days=?, ef_factor=?, repetitions=?, status=?, forgot_count=?, vague_count=?, remembered_count=? WHERE id=?");
            if (!$stmt) {
                $error_msg = "SQL准备失败: " . $conn->error;
                error_log("submit_review错误: " . $error_msg);
                echo json_encode(["status" => "error", "message" => $error_msg]);
                exit;
            }
            $stmt->bind_param("sidsiiiii", $next, $int, $ef, $reps, $status, $forgot_count, $vague_count, $remembered_count, $id);
            if (!$stmt->execute()) {
                $error_msg = "更新单词失败: " . $stmt->error . " SQL: UPDATE words SET next_review='$next', interval_days=$int, ef_factor=$ef, repetitions=$reps, status='$status', forgot_count=$forgot_count, vague_count=$vague_count, remembered_count=$remembered_count WHERE id=$id";
                error_log("submit_review错误: " . $error_msg);
                echo json_encode(["status" => "error", "message" => "更新单词失败: " . $stmt->error]);
                exit;
            }
            
            error_log("submit_review: 更新单词成功，id=$id, status=$status, next_review=$next, is_repeat=" . ($is_repeat ? 'true' : 'false') . ", other_mode_completed=" . ($other_mode_completed ? 'true' : 'false'));
            
            // 【新需求】重复学习时不记录学习状态（不插入word_review_logs）
            if (!$is_repeat) {
                // 记录复习日志（复习前和复习后的状态）
                $stmt = prepare_check($conn, "
                    INSERT INTO word_review_logs 
                    (word_id, user_id, review_date, review_mode, quality, should_advance, 
                     ef_factor_before, ef_factor_after, interval_days_before, interval_days_after, 
                     repetitions_before, repetitions_after) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ");
                if (!$stmt) {
                    $error_msg = "SQL准备失败（插入日志）: " . $conn->error;
                    error_log("submit_review错误: " . $error_msg);
                    echo json_encode(["status" => "error", "message" => $error_msg]);
                    exit;
                }
                $user_id = (int)$w['user_id'];
                $should_advance_int = $should_advance ? 1 : 0;
                $stmt->bind_param("iisssiddiiii", 
                    $id, $user_id, $today, $review_mode, $q, $should_advance_int,
                    $ef_before, $ef, $int_before, $int, $reps_before, $reps
                );
                if (!$stmt->execute()) {
                    $error_msg = "记录复习日志失败: " . $stmt->error;
                    error_log("submit_review错误: " . $error_msg . " 参数: word_id=$id, user_id=$user_id, review_date=$today, review_mode=$review_mode, quality=$q");
                    echo json_encode(["status" => "error", "message" => $error_msg]);
                    exit;
                }
                
                error_log("submit_review: 记录复习日志成功");
            } else {
                error_log("submit_review: 重复学习，不记录学习状态，word_id=$id, mode=$review_mode");
            }
            
            // 更新单词统计（以听写为主）
            try {
                updateWordStats($conn, $id, $review_mode, $today);
            } catch (Exception $e) {
                error_log("submit_review警告: updateWordStats失败: " . $e->getMessage());
                // 不中断流程，继续执行
            }
            
            echo json_encode([
                "status" => "ok", 
                "advance" => true,
                "is_repeat" => $is_repeat,
                "other_mode_completed" => $other_mode_completed,
                "should_update_score" => $should_update_score,
                "counts" => [
                    "forgot" => $forgot_count,
                    "vague" => $vague_count,
                    "remembered" => $remembered_count
                ]
            ]);
        } else {
            // 忘记 或 模糊（不跳转）：只记录点击次数和复习日志，不更新复习计划
            // 【新需求】重复学习时不更新点击次数
            if (!$is_repeat && !$other_mode_completed) {
                $stmt = prepare_check($conn, "UPDATE words SET forgot_count=?, vague_count=?, remembered_count=? WHERE id=?");
                if (!$stmt) {
                    echo json_encode(["status" => "error", "message" => "SQL准备失败: " . $conn->error]);
                    exit;
                }
                $stmt->bind_param("iiii", $forgot_count, $vague_count, $remembered_count, $id);
                if (!$stmt->execute()) {
                    echo json_encode(["status" => "error", "message" => "更新单词失败: " . $stmt->error]);
                    exit;
                }
            }
            
            // 【新需求】重复学习时不记录学习状态（不插入word_review_logs）
            if (!$is_repeat) {
                // 记录复习日志（即使不跳转也记录）
                $stmt = prepare_check($conn, "
                    INSERT INTO word_review_logs 
                    (word_id, user_id, review_date, review_mode, quality, should_advance, 
                     ef_factor_before, ef_factor_after, interval_days_before, interval_days_after, 
                     repetitions_before, repetitions_after) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ");
                if (!$stmt) {
                    echo json_encode(["status" => "error", "message" => "SQL准备失败: " . $conn->error]);
                    exit;
                }
                // 将表达式结果赋值给变量，因为bind_param需要引用传递
                $should_advance_int = $should_advance ? 1 : 0;
                $user_id = (int)$w['user_id']; // 确保是整数类型
                $stmt->bind_param("iisssiddiiii", 
                    $id, $user_id, $today, $review_mode, $q, $should_advance_int,
                    $ef_before, $ef_before, $int_before, $int_before, $reps_before, $reps_before
                );
                if (!$stmt->execute()) {
                    echo json_encode(["status" => "error", "message" => "记录复习日志失败: " . $stmt->error]);
                    exit;
                }
                
                // 更新单词统计（以听写为主）
                updateWordStats($conn, $id, $review_mode, $today);
            } else {
                error_log("submit_review: 重复学习（不跳转），不记录学习状态，word_id=$id, mode=$review_mode");
            }
            
            echo json_encode([
                "status" => "ok", 
                "advance" => false,
                "is_repeat" => $is_repeat,
                "other_mode_completed" => $other_mode_completed,
                "should_update_score" => !$is_repeat && !$other_mode_completed,
                "counts" => [
                    "forgot" => $forgot_count,
                    "vague" => $vague_count,
                    "remembered" => $remembered_count
                ]
            ]);
        }
    } catch (Exception $e) {
        $error_msg = "服务器错误: " . $e->getMessage() . " 文件: " . $e->getFile() . " 行: " . $e->getLine();
        error_log("submit_review异常: " . $error_msg);
        error_log("submit_review异常堆栈: " . $e->getTraceAsString());
        echo json_encode([
            "status" => "error", 
            "message" => "服务器错误: " . $e->getMessage(),
            "file" => basename($e->getFile()),
            "line" => $e->getLine()
        ]);
    } catch (Error $e) {
        $error_msg = "PHP致命错误: " . $e->getMessage() . " 文件: " . $e->getFile() . " 行: " . $e->getLine();
        error_log("submit_review致命错误: " . $error_msg);
        error_log("submit_review错误堆栈: " . $e->getTraceAsString());
        echo json_encode([
            "status" => "error", 
            "message" => "服务器致命错误: " . $e->getMessage(),
            "file" => basename($e->getFile()),
            "line" => $e->getLine()
        ]);
    }
}

// [8] 设置
elseif ($action === 'update_settings') {
    $in = json_decode(file_get_contents('php://input'), true);
    $uid = (int)$in['uid'];
    $goal = isset($in['goal']) ? (int)$in['goal'] : null;
    $enable_word_bank = isset($in['enable_word_bank']) ? (int)$in['enable_word_bank'] : null;
    $grade = isset($in['grade']) ? $in['grade'] : null;
    
    $updates = [];
    if ($goal !== null) $updates[] = "daily_goal=$goal";
    if ($enable_word_bank !== null) $updates[] = "enable_word_bank=$enable_word_bank";
    if ($grade !== null) {
        $grade_escaped = $conn->real_escape_string($grade);
        $updates[] = "grade='$grade_escaped'";
    }
    
    if (!empty($updates)) {
        $sql = "UPDATE users SET " . implode(', ', $updates) . " WHERE id=$uid";
        if (!$conn->query($sql)) {
            echo json_encode(["status"=>"error", "message"=>"更新失败: " . $conn->error]);
            exit;
        }
        
        // 如果启用了单词库，立即触发一次导入（不等待get_home_data）
        if ($enable_word_bank == 1 && $grade) {
            importWordBankWords($conn, $uid, $grade, $today, $goal ?? 5);
        }
        
        // 返回更新后的用户信息
        $stmt = prepare_check($conn, "SELECT daily_goal, enable_word_bank, grade FROM users WHERE id = ?");
        $stmt->bind_param("i", $uid);
        $stmt->execute();
        $user_info = $stmt->get_result()->fetch_assoc();
        
        echo json_encode([
            "status"=>"ok",
            "user_info" => [
                "daily_goal" => (int)($user_info['daily_goal'] ?? 5),
                "enable_word_bank" => (int)($user_info['enable_word_bank'] ?? 0),
                "grade" => $user_info['grade'] ?? null
            ]
        ]);
    } else {
        echo json_encode(["status"=>"ok"]);
    }
}

// [9] 导出CSV（增强：支持内容筛选）
elseif ($action === 'export_csv') {
    $uid = (int)$_GET['uid'];
    $content = $_GET['content'] ?? 'all';
    
    $where = "user_id=$uid";
    if ($content === 'mastered') {
        $where .= " AND (status = 'mastered' OR repetitions >= 5)";
    } elseif ($content === 'review') {
        $where .= " AND status != 'new'";
    }
    
    $res = $conn->query("SELECT word, pronunciation, meaning, example, status, next_review FROM words WHERE $where");
    header('Content-Type: text/csv; charset=utf-8'); 
    header('Content-Disposition: attachment; filename="vocab_' . date('Ymd') . '.csv"');
    $out = fopen('php://output', 'w');
    // 添加BOM以支持Excel正确显示中文
    fprintf($out, chr(0xEF).chr(0xBB).chr(0xBF));
    fputcsv($out, ['Word','IPA','Meaning','Example','Status','Next Review']);
    while($r=$res->fetch_assoc()) fputcsv($out, $r);
    fclose($out); exit;
}

// [9.1] 导出JSON
elseif ($action === 'export_json') {
    $uid = (int)$_GET['uid'];
    $content = $_GET['content'] ?? 'all';
    
    $where = "user_id=$uid";
    if ($content === 'mastered') {
        $where .= " AND (status = 'mastered' OR repetitions >= 5)";
    } elseif ($content === 'review') {
        $where .= " AND status != 'new'";
    }
    
    $res = $conn->query("SELECT * FROM words WHERE $where");
    $data = [];
    while($r=$res->fetch_assoc()) {
        $data[] = $r;
    }
    
    header('Content-Type: application/json; charset=utf-8');
    header('Content-Disposition: attachment; filename="vocab_' . date('Ymd') . '.json"');
    echo json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
    exit;
}

// [10] 获取统计 (增强：添加学习趋势、效率指标、单词来源统计)
elseif ($action === 'get_stats') {
    $uid = (int)$_GET['uid'];
    $days = isset($_GET['days']) ? (int)$_GET['days'] : 30; // 默认30天
    
    // 1. 记忆熟练度分布
    $stmt = prepare_check($conn, "SELECT CASE WHEN ef_factor < 1.6 THEN 'hard' WHEN ef_factor BETWEEN 1.6 AND 2.5 THEN 'medium' ELSE 'easy' END as level, COUNT(*) as count FROM words WHERE user_id = ? GROUP BY level");
    $stmt->bind_param("i", $uid);
    $stmt->execute();
    $mastery = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);

    // 2. 未来7天复习压力
    $stmt = prepare_check($conn, "SELECT next_review, COUNT(*) as count FROM words WHERE user_id = ? AND next_review BETWEEN ? AND DATE_ADD(?, INTERVAL 6 DAY) GROUP BY next_review ORDER BY next_review ASC");
    $stmt->bind_param("iss", $uid, $today, $today);
    $stmt->execute();
    $forecast = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);

    // 3. 学习趋势（最近N天每日学习量）
    $start_date = date('Y-m-d', strtotime("-$days days"));
    // 检查word_review_logs表是否存在
    $check_table = $conn->query("SHOW TABLES LIKE 'word_review_logs'");
    $table_exists = ($check_table && $check_table->num_rows > 0);
    
    if ($table_exists) {
        // 使用word_review_logs表统计实际学习过的单词（更准确）
        $stmt = prepare_check($conn, "
            SELECT 
                review_date as date,
                COUNT(DISTINCT word_id) as total_words,
                COUNT(DISTINCT CASE WHEN w.status = 'new' AND w.date_added = rl.review_date THEN rl.word_id END) as new_words,
                COUNT(DISTINCT CASE WHEN w.status != 'new' OR w.date_added != rl.review_date THEN rl.word_id END) as review_words
            FROM word_review_logs rl
            LEFT JOIN words w ON rl.word_id = w.id
            WHERE rl.user_id = ? AND rl.review_date >= ?
            GROUP BY review_date
            ORDER BY review_date ASC
        ");
    } else {
        // 回退到旧逻辑（兼容性）
        $stmt = prepare_check($conn, "
            SELECT 
                date_added as date,
                COUNT(*) as total_words,
                COUNT(DISTINCT CASE WHEN status = 'new' THEN id END) as new_words,
                COUNT(DISTINCT CASE WHEN status != 'new' THEN id END) as review_words
            FROM words 
            WHERE user_id = ? AND date_added >= ?
            GROUP BY date_added
            ORDER BY date_added ASC
        ");
    }
    $stmt->bind_param("is", $uid, $start_date);
    $stmt->execute();
    $trend = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);

    // 4. 学习效率指标
    // 获取用户设置
    $stmt = prepare_check($conn, "SELECT daily_goal FROM users WHERE id = ?");
    $stmt->bind_param("i", $uid);
    $stmt->execute();
    $user_settings = $stmt->get_result()->fetch_assoc();
    $daily_goal = $user_settings['daily_goal'] ?? 5;
    
    // 计算最近30天的统计数据
    // 检查word_review_logs表是否存在
    if ($table_exists) {
        // 使用word_review_logs表统计实际学习过的单词（更准确）
        $stmt = prepare_check($conn, "
            SELECT 
                COUNT(DISTINCT DATE(rl.review_date)) as study_days,
                COUNT(DISTINCT rl.word_id) as total_words,
                COUNT(DISTINCT CASE WHEN w.status = 'new' AND w.date_added = rl.review_date THEN rl.word_id END) as new_words,
                COUNT(DISTINCT CASE WHEN w.status != 'new' OR w.date_added != rl.review_date THEN rl.word_id END) as review_words,
                COUNT(DISTINCT CASE WHEN w.status = 'mastered' OR w.repetitions >= 5 THEN rl.word_id END) as mastered_words
            FROM word_review_logs rl
            LEFT JOIN words w ON rl.word_id = w.id
            WHERE rl.user_id = ? AND rl.review_date >= ?
        ");
    } else {
        // 回退到旧逻辑（兼容性）
        $stmt = prepare_check($conn, "
            SELECT 
                COUNT(DISTINCT DATE(date_added)) as study_days,
                COUNT(*) as total_words,
                COUNT(DISTINCT CASE WHEN status = 'new' THEN id END) as new_words,
                COUNT(DISTINCT CASE WHEN status != 'new' THEN id END) as review_words,
                COUNT(DISTINCT CASE WHEN status = 'mastered' OR repetitions >= 5 THEN id END) as mastered_words
            FROM words 
            WHERE user_id = ? AND date_added >= ?
        ");
    }
    $stmt->bind_param("is", $uid, $start_date);
    $stmt->execute();
    $stats_30d = $stmt->get_result()->fetch_assoc();
    
    // 计算今天的完成率（更直观）
    // 统一使用word_review_logs表统计今天实际学习过的单词（包括新学和复习）
    if ($table_exists) {
        $stmt = prepare_check($conn, "
            SELECT COUNT(DISTINCT word_id) as today_studied
            FROM word_review_logs 
            WHERE user_id = ? AND review_date = ?
        ");
        $stmt->bind_param("is", $uid, $today);
        $stmt->execute();
        $today_stats = $stmt->get_result()->fetch_assoc();
        $today_studied_words = (int)($today_stats['today_studied'] ?? 0);
        // 这里无法准确区分新词与复习词，先用总学习数作为 today_total_words，today_new_words 置0
        $today_total_words = $today_studied_words;
        $today_new_words = 0;
    } else {
        // 回退到旧逻辑（兼容性），按words表统计今天新增单词数
        $stmt = prepare_check($conn, "
            SELECT COUNT(*) as today_total_words
            FROM words 
            WHERE user_id = ? AND date_added = ?
        ");
        $stmt->bind_param("is", $uid, $today);
        $stmt->execute();
        $today_stats = $stmt->get_result()->fetch_assoc();
        $today_total_words = (int)($today_stats['today_total_words'] ?? 0);
        $today_studied_words = $today_total_words;
        $today_new_words = $today_total_words;
    }
    
    // 计算复习准确率（记住次数/总复习次数）
    $stmt = prepare_check($conn, "
        SELECT 
            COUNT(*) as total_reviews,
            SUM(CASE WHEN repetitions > 0 THEN 1 ELSE 0 END) as remembered_reviews
        FROM words 
        WHERE user_id = ? AND status != 'new' AND repetitions > 0
    ");
    $stmt->bind_param("i", $uid);
    $stmt->execute();
    $review_stats = $stmt->get_result()->fetch_assoc();
    
    // 计算平均每日学习量
    $avg_daily_words = 0;
    if ($stats_30d['study_days'] > 0) {
        $avg_daily_words = round($stats_30d['total_words'] / $stats_30d['study_days'], 1);
    }
    
    // 计算学习完成率（优先显示今天的完成率）
    // 新需求：使用实际总任务量计算完成率
    $total_task = calculateTotalTask($conn, $uid, $daily_goal, $today);
    $completion_rate = 0;
    if ($total_task > 0) {
        // 优先使用今天的完成率（使用今天学习的总单词数，包括新学和复习）
        if ($today_studied_words > 0) {
            // 如果今天有学习记录，使用今天的完成率
            // 完成率 = (今天学习的单词数 / 实际总任务量) × 100%
            $completion_rate = round(min(100, ($today_studied_words / $total_task) * 100), 1);
        } elseif ($stats_30d['study_days'] > 0) {
            // 如果今天没有学习记录，使用30天平均完成率
            // 计算平均每日任务量
            $avg_daily_task = $daily_goal; // 默认第1天
            if ($stats_30d['study_days'] >= 3) {
                $avg_daily_task = $daily_goal * 2.4; // 第3天及以后
            } elseif ($stats_30d['study_days'] == 2) {
                $avg_daily_task = $daily_goal * 1.5; // 第2天
            }
            $expected_words = $avg_daily_task * $stats_30d['study_days'];
            if ($expected_words > 0) {
                $completion_rate = round(min(100, ($stats_30d['total_words'] / $expected_words) * 100), 1);
            }
        }
    }
    
    // 计算复习准确率
    $review_accuracy = 0;
    if ($review_stats['total_reviews'] > 0) {
        $review_accuracy = round(($review_stats['remembered_reviews'] / $review_stats['total_reviews']) * 100, 1);
    }
    
    // 计算掌握速度
    // 统计所有已掌握的单词（不限制时间范围），这样更准确
    $stmt = prepare_check($conn, "
        SELECT COUNT(*) as total_mastered_words
        FROM words 
        WHERE user_id = ? AND (status = 'mastered' OR repetitions >= 5)
    ");
    $stmt->bind_param("i", $uid);
    $stmt->execute();
    $mastered_result = $stmt->get_result()->fetch_assoc();
    $total_mastered_words = (int)($mastered_result['total_mastered_words'] ?? 0);
    
    // 获取总学习天数（不限制时间范围）
    // 检查word_review_logs表是否存在
    $check_table = $conn->query("SHOW TABLES LIKE 'word_review_logs'");
    $table_exists = ($check_table && $check_table->num_rows > 0);
    
    if ($table_exists) {
        // 使用word_review_logs表统计实际学习天数（更准确）
        $stmt = prepare_check($conn, "
            SELECT COUNT(DISTINCT DATE(review_date)) as total_study_days
            FROM word_review_logs 
            WHERE user_id = ?
        ");
    } else {
        // 回退到旧逻辑（兼容性）
        $stmt = prepare_check($conn, "
            SELECT COUNT(DISTINCT DATE(date_added)) as total_study_days
            FROM words 
            WHERE user_id = ?
        ");
    }
    $stmt->bind_param("i", $uid);
    $stmt->execute();
    $total_days_result = $stmt->get_result()->fetch_assoc();
    $total_study_days = (int)($total_days_result['total_study_days'] ?? 0);
    
    // 掌握速度 = 总掌握单词数 / 总学习天数
    $mastery_speed = 0;
    if ($total_study_days > 0) {
        $mastery_speed = round($total_mastered_words / $total_study_days, 1);
    } elseif ($total_mastered_words > 0) {
        // 如果有掌握单词但还没有学习天数，使用1天作为基准
        $mastery_speed = round($total_mastered_words / 1, 1);
    }
    
    $efficiency = [
        'avg_daily_words' => $avg_daily_words,
        'completion_rate' => $completion_rate,
        'review_accuracy' => $review_accuracy,
        'mastery_speed' => $mastery_speed,
        'total_mastered_words' => $total_mastered_words,
        'total_study_days' => $total_study_days,
        'today_new_words' => $today_new_words,
        'today_total_words' => $today_total_words,
        'today_studied_words' => $today_studied_words,
        'today_goal' => $daily_goal
    ];

    // 5. 单词来源统计
    $stmt = prepare_check($conn, "
        SELECT 
            source,
            COUNT(*) as count
        FROM words 
        WHERE user_id = ?
        GROUP BY source
    ");
    $stmt->bind_param("i", $uid);
    $stmt->execute();
    $source_stats = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
    
    // 6. 本周 vs 上周对比
    $monday_this_week = date('Y-m-d', strtotime('monday this week'));
    $monday_last_week = date('Y-m-d', strtotime('monday last week'));
    $sunday_last_week = date('Y-m-d', strtotime('sunday last week'));
    
    // 本周统计
    $stmt = prepare_check($conn, "
        SELECT COUNT(*) as words FROM words 
        WHERE user_id = ? AND date_added >= ?
    ");
    $stmt->bind_param("is", $uid, $monday_this_week);
    $stmt->execute();
    $this_week = $stmt->get_result()->fetch_assoc();
    
    // 上周统计
    $stmt = prepare_check($conn, "
        SELECT COUNT(*) as words FROM words 
        WHERE user_id = ? AND date_added BETWEEN ? AND ?
    ");
    $stmt->bind_param("iss", $uid, $monday_last_week, $sunday_last_week);
    $stmt->execute();
    $last_week = $stmt->get_result()->fetch_assoc();
    
    $comparison = [
        'this_week' => (int)($this_week['words'] ?? 0),
        'last_week' => (int)($last_week['words'] ?? 0),
        'change' => $last_week['words'] > 0 ? round((($this_week['words'] - $last_week['words']) / $last_week['words']) * 100, 1) : 0
    ];

    echo json_encode([
        "mastery" => $mastery, 
        "forecast" => $forecast,
        "trend" => $trend,
        "efficiency" => $efficiency,
        "source_stats" => $source_stats,
        "comparison" => $comparison
    ]);
}

// [11] 时光机：重置日期
elseif ($action === 'reset_date') {
    $in = json_decode(file_get_contents('php://input'), true);
    $uid = (int)$in['uid'];
    $target_date = $in['date']; 
    $type = $in['type']; 

    if ($type === 'new') {
        $stmt = prepare_check($conn, "UPDATE words SET status = 'new', repetitions = 0, interval_days = 0, next_review = date_added WHERE user_id = ? AND date_added = ?");
        $stmt->bind_param("is", $uid, $target_date);
    } elseif ($type === 'review') {
        $stmt = prepare_check($conn, "UPDATE words SET next_review = ? WHERE user_id = ? AND date_added < ? AND next_review > ? AND status != 'new'");
        $stmt->bind_param("siss", $target_date, $uid, $target_date, $target_date);
    }
    $stmt->execute();
    echo json_encode(["status" => "ok", "rows" => $stmt->affected_rows]);
}

// [12] 精准捞回
elseif ($action === 'rescue_words') {
    $in = json_decode(file_get_contents('php://input'), true);
    $uid = (int)$in['uid'];
    $target_review_date = $in['review_date']; 
    
    if (!empty($in['words_list'])) {
        $words = explode("\n", $in['words_list']);
        $count = 0;
        $stmt = prepare_check($conn, "UPDATE words SET next_review = ?, status = 'learning' WHERE user_id = ? AND word = ?");
        foreach ($words as $w) {
            $w = trim($w);
            if (empty($w)) continue;
            $stmt->bind_param("sis", $target_review_date, $uid, $w);
            $stmt->execute();
            $count += $stmt->affected_rows;
        }
        echo json_encode(["status" => "ok", "msg" => "成功捞回 $count 个指定单词"]);
    } elseif (!empty($in['added_date'])) {
        $added_date = $in['added_date'];
        $stmt = prepare_check($conn, "UPDATE words SET next_review = ?, status = 'review' WHERE user_id = ? AND date_added = ?");
        $stmt->bind_param("sis", $target_review_date, $uid, $added_date);
        $stmt->execute();
        echo json_encode(["status" => "ok", "msg" => "成功捞回 " . $stmt->affected_rows . " 个单词"]);
    } else {
        echo json_encode(["status" => "error", "msg" => "无效参数"]);
    }
}

// [13] 强力回滚
elseif ($action === 'rollback') {
    $in = json_decode(file_get_contents('php://input'), true);
    $uid = (int)$in['uid'];
    $rollback_date = $in['date'];
    
    // 重置新词
    $stmt1 = prepare_check($conn, "UPDATE words SET status = 'new', repetitions = 0, interval_days = 0, next_review = date_added WHERE user_id = ? AND date_added >= ?");
    $stmt1->bind_param("is", $uid, $rollback_date);
    $stmt1->execute();
    
    // 重置复习
    $stmt2 = prepare_check($conn, "UPDATE words SET next_review = ? WHERE user_id = ? AND date_added < ? AND next_review > ?");
    $stmt2->bind_param("siss", $rollback_date, $uid, $rollback_date, $rollback_date);
    $stmt2->execute();

    echo json_encode([
        "status" => "ok", 
        "msg" => "时间已倒流回 $rollback_date。\n新词重置: ".$stmt1->affected_rows."\n复习撤销: ".$stmt2->affected_rows
    ]);
}

// [14] 一键通过
elseif ($action === 'batch_pass') {
    $in = json_decode(file_get_contents('php://input'), true);
    $uid = (int)$in['uid'];
    
    // 安全处理日期，确保与系统 $today 逻辑兼容，如果有传参则用参，无则用 $today
    $raw_date = $in['date'] ?? $today;
    if (!DateTime::createFromFormat('Y-m-d', $raw_date)) {
        $raw_date = $today;
    }
    $today_date = $conn->real_escape_string($raw_date); 
    
    $target_words = [];
    
    if (!empty($in['words_list'])) {
        $list = explode("\n", $in['words_list']);
        foreach($list as $w) {
            $w = trim($w);
            if($w) $target_words[] = "'".$conn->real_escape_string($w)."'";
        }
        if(empty($target_words)) exit(json_encode(["status"=>"error","msg"=>"列表为空"]));
        $sql_where = "word IN (" . implode(",", $target_words) . ")";
    } else {
        $sql_where = "status != 'new' AND next_review <= '$today_date'";
    }

    $sql = "SELECT * FROM words WHERE user_id=$uid AND $sql_where";
    $res = $conn->query($sql);
    
    if (!$res) {
        exit(json_encode(["status"=>"error", "msg"=>"查询失败: " . $conn->error]));
    }

    $count = 0;
    while ($w = $res->fetch_assoc()) {
        $new_ef = $w['ef_factor'] + 0.1;
        $old_int = $w['interval_days'];
        if ($old_int == 0) $new_int = 1;
        elseif ($old_int == 1) $new_int = 6;
        else $new_int = ceil($old_int * $new_ef);
        
        $new_reps = $w['repetitions'] + 1;
        $new_date = date('Y-m-d', strtotime("$today_date +$new_int days"));
        
        $upd_sql = "UPDATE words SET next_review='$new_date', interval_days=$new_int, ef_factor=$new_ef, repetitions=$new_reps, status='review' WHERE id={$w['id']}";
        $conn->query($upd_sql);
        $count++;
    }

    echo json_encode(["status" => "ok", "msg" => "成功清洗了 $count 个单词。\n它们已标记为“已复习”，下次复习时间已推迟。"]);
}

// [15] 获取用户列表（管理员）
elseif ($action === 'get_users') {
    $uid = (int)$_GET['uid'];
    
    // 检查是否为管理员
    $stmt = prepare_check($conn, "SELECT role FROM users WHERE id = ?");
    $stmt->bind_param("i", $uid);
    $stmt->execute();
    $check = $stmt->get_result()->fetch_assoc();
    
    if (!$check || $check['role'] !== 'admin') {
        exit(json_encode(["error" => "无权限访问"]));
    }
    
    $stmt = prepare_check($conn, "SELECT id, username, role, daily_goal, is_active, created_at, last_login FROM users ORDER BY id DESC");
    $stmt->execute();
    $users = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
    
    echo json_encode($users);
}

// [16] 添加用户（管理员）
elseif ($action === 'add_user') {
    $uid = (int)$_POST['uid'];
    $username = $_POST['username'] ?? '';
    $password = $_POST['password'] ?? '';
    $role = $_POST['role'] ?? 'user';
    $daily_goal = (int)($_POST['daily_goal'] ?? 5);
    
    // 检查是否为管理员
    $stmt = prepare_check($conn, "SELECT role FROM users WHERE id = ?");
    $stmt->bind_param("i", $uid);
    $stmt->execute();
    $check = $stmt->get_result()->fetch_assoc();
    
    if (!$check || $check['role'] !== 'admin') {
        exit(json_encode(["error" => "无权限操作"]));
    }
    
    if (!$username || !$password) {
        exit(json_encode(["error" => "用户名和密码不能为空"]));
    }
    
    $password_md5 = md5($password);
    $stmt = prepare_check($conn, "INSERT INTO users (username, password, role, daily_goal, created_by) VALUES (?, ?, ?, ?, ?)");
    $stmt->bind_param("sssii", $username, $password_md5, $role, $daily_goal, $uid);
    
    if ($stmt->execute()) {
        echo json_encode(["status" => "ok", "msg" => "用户添加成功"]);
    } else {
        echo json_encode(["error" => "添加失败: " . $stmt->error]);
    }
}

// [17] 更新用户（管理员）
elseif ($action === 'update_user') {
    $uid = (int)$_POST['uid'];
    $target_id = (int)$_POST['target_id'];
    $username = $_POST['username'] ?? '';
    $password = $_POST['password'] ?? '';
    $role = $_POST['role'] ?? 'user';
    $daily_goal = (int)($_POST['daily_goal'] ?? 5);
    $is_active = (int)($_POST['is_active'] ?? 1);
    
    // 检查是否为管理员
    $stmt = prepare_check($conn, "SELECT role FROM users WHERE id = ?");
    $stmt->bind_param("i", $uid);
    $stmt->execute();
    $check = $stmt->get_result()->fetch_assoc();
    
    if (!$check || $check['role'] !== 'admin') {
        exit(json_encode(["error" => "无权限操作"]));
    }
    
    if (!$username) {
        exit(json_encode(["error" => "用户名不能为空"]));
    }
    
    // 如果提供了密码，则更新密码
    if ($password) {
        $password_md5 = md5($password);
        $stmt = prepare_check($conn, "UPDATE users SET username = ?, password = ?, role = ?, daily_goal = ?, is_active = ? WHERE id = ?");
        $stmt->bind_param("sssiii", $username, $password_md5, $role, $daily_goal, $is_active, $target_id);
    } else {
        $stmt = prepare_check($conn, "UPDATE users SET username = ?, role = ?, daily_goal = ?, is_active = ? WHERE id = ?");
        $stmt->bind_param("ssiii", $username, $role, $daily_goal, $is_active, $target_id);
    }
    
    if ($stmt->execute()) {
        echo json_encode(["status" => "ok", "msg" => "用户更新成功"]);
    } else {
        echo json_encode(["error" => "更新失败: " . $stmt->error]);
    }
}

// [18] 删除用户（管理员）
elseif ($action === 'delete_user') {
    $uid = (int)$_POST['uid'];
    $target_id = (int)$_POST['target_id'];
    
    // 检查是否为管理员
    $stmt = prepare_check($conn, "SELECT role FROM users WHERE id = ?");
    $stmt->bind_param("i", $uid);
    $stmt->execute();
    $check = $stmt->get_result()->fetch_assoc();
    
    if (!$check || $check['role'] !== 'admin') {
        exit(json_encode(["error" => "无权限操作"]));
    }
    
    // 不能删除自己
    if ($uid == $target_id) {
        exit(json_encode(["error" => "不能删除自己的账户"]));
    }
    
    $stmt = prepare_check($conn, "DELETE FROM users WHERE id = ?");
    $stmt->bind_param("i", $target_id);
    
    if ($stmt->execute()) {
        echo json_encode(["status" => "ok", "msg" => "用户删除成功"]);
    } else {
        echo json_encode(["error" => "删除失败: " . $stmt->error]);
    }
}

// [19] 获取登录日志（管理员）
elseif ($action === 'get_login_logs') {
    $uid = (int)$_GET['uid'];
    $page = (int)($_GET['page'] ?? 1);
    $limit = (int)($_GET['limit'] ?? 50);
    $offset = ($page - 1) * $limit;
    
    // 检查是否为管理员
    $stmt = prepare_check($conn, "SELECT role FROM users WHERE id = ?");
    $stmt->bind_param("i", $uid);
    $stmt->execute();
    $check = $stmt->get_result()->fetch_assoc();
    
    if (!$check || $check['role'] !== 'admin') {
        exit(json_encode(["error" => "无权限访问"]));
    }
    
    // 获取总数
    $stmt = prepare_check($conn, "SELECT COUNT(*) as total FROM login_logs");
    $stmt->execute();
    $total = $stmt->get_result()->fetch_assoc()['total'];
    
    // 获取日志列表
    $stmt = prepare_check($conn, "SELECT * FROM login_logs ORDER BY login_time DESC LIMIT ? OFFSET ?");
    $stmt->bind_param("ii", $limit, $offset);
    $stmt->execute();
    $logs = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
    
    echo json_encode([
        "logs" => $logs,
        "total" => $total,
        "page" => $page,
        "limit" => $limit
    ]);
}

// [20] 获取用户学习报告（管理员）
elseif ($action === 'get_learning_report') {
    $uid = (int)$_GET['uid']; // 管理员ID
    $target_user_id = isset($_GET['target_user_id']) ? (int)$_GET['target_user_id'] : 0; // 0表示全部用户
    $start_date = $_GET['start_date'] ?? date('Y-m-d', strtotime('-30 days'));
    $end_date = $_GET['end_date'] ?? date('Y-m-d');
    
    // 检查是否为管理员
    $stmt = prepare_check($conn, "SELECT role FROM users WHERE id = ?");
    $stmt->bind_param("i", $uid);
    $stmt->execute();
    $check = $stmt->get_result()->fetch_assoc();
    
    if (!$check || $check['role'] !== 'admin') {
        exit(json_encode(["error" => "无权限操作"]));
    }
    
    // 构建查询条件（word_review_logs用rl前缀，words单表不用前缀）
    $user_condition_rl = $target_user_id > 0 ? "AND rl.user_id = $target_user_id" : "";
    $user_condition_w = $target_user_id > 0 ? "AND user_id = $target_user_id" : "";
    
    // 1. 每日学习统计（按日期分组）
    // 检查word_review_logs表是否存在
    $check_table = $conn->query("SHOW TABLES LIKE 'word_review_logs'");
    $table_exists = ($check_table && $check_table->num_rows > 0);
    
    if ($table_exists) {
        // 使用word_review_logs表统计实际学习行为（更准确）
        $stmt = prepare_check($conn, "
            SELECT 
                rl.review_date as date,
                COUNT(DISTINCT rl.user_id) as user_count,
                COUNT(DISTINCT rl.word_id) as word_count,
                COUNT(DISTINCT CASE WHEN w.status != 'new' OR w.date_added != rl.review_date THEN rl.word_id END) as review_count,
                COUNT(DISTINCT CASE WHEN w.status = 'new' AND w.date_added = rl.review_date THEN rl.word_id END) as new_count
            FROM word_review_logs rl
            LEFT JOIN words w ON rl.word_id = w.id
            WHERE rl.review_date BETWEEN ? AND ?
            $user_condition_rl
            GROUP BY rl.review_date
            ORDER BY rl.review_date ASC
        ");
    } else {
        // 回退到旧逻辑（兼容性）
        $stmt = prepare_check($conn, "
            SELECT 
                date_added as date,
                COUNT(DISTINCT user_id) as user_count,
                COUNT(*) as word_count,
                COUNT(DISTINCT CASE WHEN status != 'new' THEN id END) as review_count,
                COUNT(DISTINCT CASE WHEN status = 'new' THEN id END) as new_count
            FROM words 
            WHERE date_added BETWEEN ? AND ?
            $user_condition_w
            GROUP BY date_added
            ORDER BY date_added ASC
        ");
    }
    $stmt->bind_param("ss", $start_date, $end_date);
    $stmt->execute();
    $daily_stats = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
    
    // 2. 用户学习汇总（如果查询全部用户）
    // 检查word_review_logs表是否存在
    $check_table = $conn->query("SHOW TABLES LIKE 'word_review_logs'");
    $table_exists = ($check_table && $check_table->num_rows > 0);
    
    $user_summary = [];
    if ($target_user_id == 0) {
        if ($table_exists) {
            // 使用word_review_logs表统计实际学习过的单词（更准确）
            $stmt = prepare_check($conn, "
                SELECT 
                    u.id,
                    u.username,
                    COUNT(DISTINCT DATE(rl.review_date)) as study_days,
                    COUNT(DISTINCT rl.word_id) as total_words,
                    COUNT(DISTINCT CASE WHEN w.status = 'mastered' OR w.repetitions >= 5 THEN rl.word_id END) as mastered_words,
                    MAX(rl.review_date) as last_study_date,
                    MIN(rl.review_date) as first_study_date
                FROM users u
                LEFT JOIN word_review_logs rl ON u.id = rl.user_id AND rl.review_date BETWEEN ? AND ?
                LEFT JOIN words w ON rl.word_id = w.id
                WHERE u.role = 'user'
                GROUP BY u.id, u.username
                HAVING total_words > 0 OR study_days > 0
                ORDER BY total_words DESC
            ");
        } else {
            // 回退到旧逻辑（兼容性）
            $stmt = prepare_check($conn, "
                SELECT 
                    u.id,
                    u.username,
                    COUNT(DISTINCT DATE(w.date_added)) as study_days,
                    COUNT(w.id) as total_words,
                    COUNT(DISTINCT CASE WHEN w.status = 'mastered' OR w.repetitions >= 5 THEN w.id END) as mastered_words,
                    MAX(w.date_added) as last_study_date,
                    MIN(w.date_added) as first_study_date
                FROM users u
                LEFT JOIN words w ON u.id = w.user_id AND w.date_added BETWEEN ? AND ?
                WHERE u.role = 'user'
                GROUP BY u.id, u.username
                ORDER BY total_words DESC
            ");
        }
        $stmt->bind_param("ss", $start_date, $end_date);
        $stmt->execute();
        $user_summary = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
    } else {
        // 单个用户的详细统计
        if ($table_exists) {
            // 使用word_review_logs表统计实际学习过的单词（更准确）
            $stmt = prepare_check($conn, "
                SELECT 
                    COUNT(DISTINCT DATE(rl.review_date)) as study_days,
                    COUNT(DISTINCT rl.word_id) as total_words,
                    COUNT(DISTINCT CASE WHEN w.status = 'mastered' OR w.repetitions >= 5 THEN rl.word_id END) as mastered_words,
                    COUNT(DISTINCT CASE WHEN w.status = 'new' AND w.date_added = rl.review_date THEN rl.word_id END) as new_words,
                    COUNT(DISTINCT CASE WHEN w.status != 'new' OR w.date_added != rl.review_date THEN rl.word_id END) as review_words,
                    MAX(rl.review_date) as last_study_date,
                    MIN(rl.review_date) as first_study_date,
                    AVG(CASE WHEN w.ef_factor < 1.6 THEN 1 WHEN w.ef_factor BETWEEN 1.6 AND 2.5 THEN 2 ELSE 3 END) as avg_difficulty
                FROM word_review_logs rl
                LEFT JOIN words w ON rl.word_id = w.id
                WHERE rl.user_id = ? AND rl.review_date BETWEEN ? AND ?
            ");
        } else {
            // 回退到旧逻辑（兼容性）
            $stmt = prepare_check($conn, "
                SELECT 
                    COUNT(DISTINCT DATE(date_added)) as study_days,
                    COUNT(*) as total_words,
                    COUNT(DISTINCT CASE WHEN status = 'mastered' OR repetitions >= 5 THEN id END) as mastered_words,
                    COUNT(DISTINCT CASE WHEN status = 'new' THEN id END) as new_words,
                    COUNT(DISTINCT CASE WHEN status != 'new' THEN id END) as review_words,
                    MAX(date_added) as last_study_date,
                    MIN(date_added) as first_study_date,
                    AVG(CASE WHEN ef_factor < 1.6 THEN 1 WHEN ef_factor BETWEEN 1.6 AND 2.5 THEN 2 ELSE 3 END) as avg_difficulty
                FROM words 
                WHERE user_id = ? AND date_added BETWEEN ? AND ?
            ");
        }
        $stmt->bind_param("iss", $target_user_id, $start_date, $end_date);
        $stmt->execute();
        $user_detail = $stmt->get_result()->fetch_assoc();
        
        // 获取用户信息
        $stmt = prepare_check($conn, "SELECT id, username FROM users WHERE id = ?");
        $stmt->bind_param("i", $target_user_id);
        $stmt->execute();
        $user_info = $stmt->get_result()->fetch_assoc();
        
        $user_summary = [[
            'id' => $user_info['id'],
            'username' => $user_info['username'],
            'study_days' => $user_detail['study_days'] ?? 0,
            'total_words' => $user_detail['total_words'] ?? 0,
            'mastered_words' => $user_detail['mastered_words'] ?? 0,
            'new_words' => $user_detail['new_words'] ?? 0,
            'review_words' => $user_detail['review_words'] ?? 0,
            'last_study_date' => $user_detail['last_study_date'],
            'first_study_date' => $user_detail['first_study_date'],
            'avg_difficulty' => round($user_detail['avg_difficulty'] ?? 0, 2)
        ]];
    }
    
    // 3. 单词掌握度分布
    $mastery_distribution = [];
    if ($target_user_id > 0) {
        $stmt = prepare_check($conn, "
            SELECT 
                CASE 
                    WHEN ef_factor < 1.6 THEN '困难'
                    WHEN ef_factor BETWEEN 1.6 AND 2.5 THEN '良好'
                    ELSE '掌握'
                END as level,
                COUNT(*) as count
            FROM words 
            WHERE user_id = ? AND date_added BETWEEN ? AND ?
            GROUP BY level
        ");
        $stmt->bind_param("iss", $target_user_id, $start_date, $end_date);
        $stmt->execute();
        $mastery_distribution = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
    }
    
    echo json_encode([
        'daily_stats' => $daily_stats,
        'user_summary' => $user_summary,
        'mastery_distribution' => $mastery_distribution,
        'date_range' => [
            'start' => $start_date,
            'end' => $end_date
        ]
    ]);
}

// [21] 获取学习统计（用于主页显示）
elseif ($action === 'get_learning_stats') {
    try {
        $uid = (int)$_GET['uid'];
        
        // 检查word_review_logs表是否存在
        $table_exists = false;
        $check_table = $conn->query("SHOW TABLES LIKE 'word_review_logs'");
        if ($check_table && $check_table->num_rows > 0) {
            $table_exists = true;
        }
        
        // 本周统计（周一到今天）
        // 计算本周一（周一是一周的第一天）
        $day_of_week = date('w', strtotime($today)); // 0=周日, 1=周一, ..., 6=周六
        $day_of_week = $day_of_week == 0 ? 7 : $day_of_week; // 将周日转为7
        $monday = date('Y-m-d', strtotime("$today -" . ($day_of_week - 1) . " days"));
        
        if ($table_exists) {
            // 使用word_review_logs表统计实际学习过的单词（包括新学和复习）
            $stmt = prepare_check($conn, "
                SELECT 
                    COUNT(DISTINCT review_date) as days,
                    COUNT(DISTINCT word_id) as words
                FROM word_review_logs 
                WHERE user_id = ? AND review_date >= ? AND review_date <= ?
            ");
            $stmt->bind_param("iss", $uid, $monday, $today);
            $stmt->execute();
            $week_result = $stmt->get_result();
            $week_stats = $week_result->fetch_assoc();
            if (!$week_stats) {
                $week_stats = ['days' => 0, 'words' => 0];
            }
        } else {
            // 如果word_review_logs表不存在，回退到使用words表的date_added（兼容性）
            $stmt = prepare_check($conn, "SELECT COUNT(DISTINCT date_added) as days, COUNT(*) as words FROM words WHERE user_id = ? AND date_added >= ? AND date_added <= ?");
            $stmt->bind_param("iss", $uid, $monday, $today);
            $stmt->execute();
            $week_result = $stmt->get_result();
            $week_stats = $week_result->fetch_assoc();
            if (!$week_stats) {
                $week_stats = ['days' => 0, 'words' => 0];
            }
        }
        
        // 本月统计（本月1号到今天）
        $first_day = date('Y-m-01', strtotime($today));
        
        if ($table_exists) {
            // 使用word_review_logs表统计实际学习过的单词（包括新学和复习）
            $stmt = prepare_check($conn, "
                SELECT 
                    COUNT(DISTINCT review_date) as days,
                    COUNT(DISTINCT word_id) as words
                FROM word_review_logs 
                WHERE user_id = ? AND review_date >= ? AND review_date <= ?
            ");
            $stmt->bind_param("iss", $uid, $first_day, $today);
            $stmt->execute();
            $month_result = $stmt->get_result();
            $month_stats = $month_result->fetch_assoc();
            if (!$month_stats) {
                $month_stats = ['days' => 0, 'words' => 0];
            }
        } else {
            // 如果word_review_logs表不存在，回退到使用words表的date_added（兼容性）
            $stmt = prepare_check($conn, "SELECT COUNT(DISTINCT date_added) as days, COUNT(*) as words FROM words WHERE user_id = ? AND date_added >= ? AND date_added <= ?");
            $stmt->bind_param("iss", $uid, $first_day, $today);
            $stmt->execute();
            $month_result = $stmt->get_result();
            $month_stats = $month_result->fetch_assoc();
            if (!$month_stats) {
                $month_stats = ['days' => 0, 'words' => 0];
            }
        }
        
        // 总学习天数（所有时间）
        // 检查word_review_logs表是否存在
        if ($table_exists) {
            // 使用word_review_logs表统计实际学习天数（更准确）
            $stmt = prepare_check($conn, "SELECT COUNT(DISTINCT DATE(review_date)) as total_days FROM word_review_logs WHERE user_id = ?");
        } else {
            // 回退到旧逻辑（兼容性）
            $stmt = prepare_check($conn, "SELECT COUNT(DISTINCT date_added) as total_days FROM words WHERE user_id = ?");
        }
        $stmt->bind_param("i", $uid);
        $stmt->execute();
        $total_result = $stmt->get_result();
        $total_row = $total_result->fetch_assoc();
        $total_days = (int)($total_row['total_days'] ?? 0);
        
        // 已掌握单词数（status='mastered'或repetitions>=5）
        $stmt = prepare_check($conn, "SELECT COUNT(*) as mastered FROM words WHERE user_id = ? AND (status = 'mastered' OR repetitions >= 5)");
        $stmt->bind_param("i", $uid);
        $stmt->execute();
        $mastered_result = $stmt->get_result();
        $mastered_row = $mastered_result->fetch_assoc();
        $mastered_count = (int)($mastered_row['mastered'] ?? 0);
        
        // 连续打卡天数
        $streak = calculateCheckInStreak($conn, $uid, $today);
        
        echo json_encode([
            'status' => 'ok',
            'week' => [
                'days' => (int)($week_stats['days'] ?? 0),
                'words' => (int)($week_stats['words'] ?? 0)
            ],
            'month' => [
                'days' => (int)($month_stats['days'] ?? 0),
                'words' => (int)($month_stats['words'] ?? 0)
            ],
            'total_days' => $total_days,
            'mastered_count' => $mastered_count,
            'streak_days' => (int)$streak
        ]);
    } catch (Exception $e) {
        http_response_code(500);
        echo json_encode([
            'status' => 'error',
            'error' => '获取学习统计失败: ' . $e->getMessage()
        ]);
    }
}

// [21] 获取排行榜数据
elseif ($action === 'get_rankings') {
    try {
        $uid = isset($_GET['uid']) ? (int)$_GET['uid'] : 0;
        $period = isset($_GET['period']) ? $_GET['period'] : 'day';
        $sort_by = isset($_GET['sort_by']) ? $_GET['sort_by'] : 'total_words';
        $date = isset($_GET['date']) ? $_GET['date'] : $today;
        
        // 映射period参数
        $period_map = [
            'day' => 'daily',
            'week' => 'weekly',
            'month' => 'monthly',
            'year' => 'yearly',
            'all' => 'all'
        ];
        $period_type = $period_map[$period] ?? 'daily';
        
        // 计算周期范围
        $period_start = $date;
        $period_end = $date;
        
        if ($period_type === 'all') {
            // 全部时间：不限制日期范围（使用一个很早的日期）
            $period_start = '1970-01-01';
            $period_end = $today;
        } elseif ($period_type === 'weekly') {
            // 本周一
            $day_of_week = date('w', strtotime($date));
            $day_of_week = $day_of_week == 0 ? 7 : $day_of_week; // 周日转为7
            $period_start = date('Y-m-d', strtotime("$date -" . ($day_of_week - 1) . " days"));
            $period_end = date('Y-m-d', strtotime("$period_start +6 days"));
        } elseif ($period_type === 'monthly') {
            // 本月第一天和最后一天
            $period_start = date('Y-m-01', strtotime($date));
            $period_end = date('Y-m-t', strtotime($date));
        } elseif ($period_type === 'yearly') {
            // 本年第一天和最后一天
            $period_start = date('Y-01-01', strtotime($date));
            $period_end = date('Y-12-31', strtotime($date));
        }
        
        // 获取所有用户在该周期内的学习数据
        // 注意：应该统计"实际学习过的单词"（通过word_review_logs表），而不是"添加的单词"（words表的date_added）
        // 先检查word_review_logs表是否存在且有数据
        $table_exists = false;
        $table_has_data = false;
        $check_table = $conn->query("SHOW TABLES LIKE 'word_review_logs'");
        if ($check_table && $check_table->num_rows > 0) {
            $table_exists = true;
            // 检查表中是否有数据
            $check_data = $conn->query("SELECT COUNT(*) as cnt FROM word_review_logs LIMIT 1");
            if ($check_data && $row = $check_data->fetch_assoc()) {
                $table_has_data = ($row['cnt'] > 0);
            }
        }
        
        if ($table_exists && $table_has_data) {
            // 使用word_review_logs表统计实际学习过的单词（表存在且有数据）
            $rankings_query = "
                SELECT 
                    u.id as user_id,
                    u.username,
                    u.daily_goal,
                    COUNT(DISTINCT DATE(rl.review_date)) as study_days,
                    COUNT(DISTINCT rl.word_id) as total_words,
                    COUNT(DISTINCT CASE WHEN w.status = 'mastered' OR w.repetitions >= 5 THEN rl.word_id END) as mastered_words
                FROM users u
                LEFT JOIN word_review_logs rl ON u.id = rl.user_id 
                    AND DATE(rl.review_date) >= ? 
                    AND DATE(rl.review_date) <= ?
                LEFT JOIN words w ON rl.word_id = w.id
                WHERE u.id > 0
                GROUP BY u.id, u.username, u.daily_goal
                HAVING total_words > 0 OR study_days > 0
                ORDER BY total_words DESC, mastered_words DESC, study_days DESC
            ";
        } else {
            // 如果word_review_logs表不存在或没有数据，回退到使用words表的date_added（兼容旧数据）
            $rankings_query = "
                SELECT 
                    u.id as user_id,
                    u.username,
                    u.daily_goal,
                    COUNT(DISTINCT DATE(w.date_added)) as study_days,
                    COUNT(DISTINCT w.id) as total_words,
                    SUM(CASE WHEN w.status = 'mastered' OR w.repetitions >= 5 THEN 1 ELSE 0 END) as mastered_words
                FROM users u
                LEFT JOIN words w ON u.id = w.user_id 
                    AND DATE(w.date_added) >= ? 
                    AND DATE(w.date_added) <= ?
                WHERE u.id > 0
                GROUP BY u.id, u.username, u.daily_goal
                HAVING total_words > 0 OR study_days > 0
                ORDER BY total_words DESC, mastered_words DESC, study_days DESC
            ";
        }
        
        $stmt = prepare_check($conn, $rankings_query);
        if (!$stmt) {
            throw new Exception('准备查询失败: ' . $conn->error);
        }
        
        $stmt->bind_param("ss", $period_start, $period_end);
        
        if (!$stmt->execute()) {
            throw new Exception('查询排行榜数据失败: ' . $stmt->error . ' SQL: ' . $rankings_query);
        }
        
        $result = $stmt->get_result();
        if (!$result) {
            throw new Exception('获取查询结果失败: ' . $stmt->error);
        }
        
        $rankings = [];
        $rank = 1;
        
        while ($row = $result->fetch_assoc()) {
            // 计算连续打卡天数（通过函数计算，不在users表中）
            $streak_days = calculateCheckInStreak($conn, $row['user_id'], $today);
            
            // 获取前一天排名（用于计算排名变化）
            $previous_date = date('Y-m-d', strtotime("$date -1 day"));
            $rank_change = 'new'; // 默认值：新上榜
            
            // 查询前一天的历史排名（如果表存在）
            try {
                // 检查表是否存在
                $check_table = $conn->query("SHOW TABLES LIKE 'user_ranking_history'");
                if ($check_table && $check_table->num_rows > 0) {
                    $history_stmt = prepare_check($conn, "
                        SELECT rank_position 
                        FROM user_ranking_history 
                        WHERE user_id = ? AND ranking_date = ? AND period_type = ?
                        ORDER BY created_at DESC LIMIT 1
                    ");
                    $history_stmt->bind_param("iss", $row['user_id'], $previous_date, $period_type);
                    $history_stmt->execute();
                    $history_result = $history_stmt->get_result();
                    
                    if ($history_row = $history_result->fetch_assoc()) {
                        $previous_rank = (int)$history_row['rank_position'];
                        $change = $previous_rank - $rank;
                        if ($change > 0) {
                            $rank_change = 'up';
                        } elseif ($change < 0) {
                            $rank_change = 'down';
                        } else {
                            $rank_change = 'same';
                        }
                    }
                }
            } catch (Exception $e) {
                // 如果表不存在或其他错误，使用默认值 'new'
                $rank_change = 'new';
            }
            
            // 计算完成率：周期内平均每日学习数 / 平均每日任务量
            // 注意：total_words现在是"实际学习过的单词数"，不是"添加的单词数"
            // 新需求：总任务量是变化的
            // 第1天：daily_goal
            // 第2天：daily_goal * 2
            // 第3天及以后：daily_goal * 2.4
            $daily_goal = (int)($row['daily_goal'] ?? 5);
            $study_days = (int)$row['study_days'];
            $total_words = (int)$row['total_words'];
            $completion_rate = 0;
            
            if ($study_days > 0 && $daily_goal > 0) {
                // 平均每日学习数 = 总学习单词数 / 学习天数
                $avg_daily_words = $total_words / $study_days;
                
                // 计算平均每日任务量（根据学习天数）
                // 第1天：daily_goal
                // 第2天：daily_goal * 1.5（(daily_goal + daily_goal * 2) / 2）
                // 第3天及以后：daily_goal * 2.4
                $avg_daily_task = $daily_goal; // 默认第1天
                if ($study_days >= 3) {
                    // 第3天及以后：使用固定任务量
                    $avg_daily_task = $daily_goal * 2.4;
                } elseif ($study_days == 2) {
                    // 第2天：平均任务量
                    $avg_daily_task = $daily_goal * 1.5; // (daily_goal + daily_goal * 2) / 2
                }
                
                $completion_rate = round(min(100, ($avg_daily_words / $avg_daily_task) * 100), 1);
            } elseif ($total_words > 0 && $daily_goal > 0) {
                // 如果只有1天数据，直接计算：今天学习的单词数 / 每日目标（第1天）
                $completion_rate = round(min(100, ($total_words / $daily_goal) * 100), 1);
            }
            // 如果total_words为0，completion_rate保持为0（表示还没学习）
            
            $rankings[] = [
                'user_id' => (int)$row['user_id'],
                'username' => $row['username'],
                'rank' => $rank,
                'rank_change' => $rank_change,
                'total_words' => $total_words,
                'study_days' => $study_days,
                'streak_days' => (int)$streak_days,
                'mastered_words' => (int)$row['mastered_words'],
                'completion_rate' => $completion_rate,
                'is_current_user' => ($row['user_id'] == $uid)
            ];
            
            $rank++;
        }
        
        // 对排名进行重新排序（因为streak_days是在PHP中计算的，不在SQL中）
        // 根据用户选择的排序方式排序
        usort($rankings, function($a, $b) use ($sort_by) {
            // 主排序：根据用户选择的指标
            $a_val = $a[$sort_by] ?? 0;
            $b_val = $b[$sort_by] ?? 0;
            
            if ($a_val != $b_val) {
                return $b_val - $a_val; // 降序排列
            }
            
            // 次排序（固定）：总单词数 > 已掌握单词数 > 连续打卡天数 > 学习天数
            if ($a['total_words'] != $b['total_words']) {
                return $b['total_words'] - $a['total_words'];
            }
            if ($a['mastered_words'] != $b['mastered_words']) {
                return $b['mastered_words'] - $a['mastered_words'];
            }
            if ($a['streak_days'] != $b['streak_days']) {
                return $b['streak_days'] - $a['streak_days'];
            }
            return $b['study_days'] - $a['study_days'];
        });
        
        // 重新分配排名（排序后）- 支持并列排名
        // 如果所有排序值都相同，显示相同的排名
        $current_rank = 1;
        $prev_values = null; // 存储上一个用户的所有排序值
        
        foreach ($rankings as $index => &$ranking) {
            // 获取当前用户的所有排序值（用于比较是否并列）
            $current_values = [
                'sort_by' => $ranking[$sort_by] ?? 0,
                'total_words' => $ranking['total_words'] ?? 0,
                'mastered_words' => $ranking['mastered_words'] ?? 0,
                'streak_days' => $ranking['streak_days'] ?? 0,
                'study_days' => $ranking['study_days'] ?? 0
            ];
            
            // 如果是第一个用户，或者当前用户的所有排序值与上一个用户不同，更新排名
            if ($prev_values === null || 
                $current_values['sort_by'] != $prev_values['sort_by'] ||
                $current_values['total_words'] != $prev_values['total_words'] ||
                $current_values['mastered_words'] != $prev_values['mastered_words'] ||
                $current_values['streak_days'] != $prev_values['streak_days'] ||
                $current_values['study_days'] != $prev_values['study_days']) {
                // 排名不同，更新排名（使用index+1，因为数组从0开始）
                $current_rank = $index + 1;
            }
            
            // 分配排名（如果所有值都相同，会使用相同的排名，实现并列）
            $ranking['rank'] = $current_rank;
            $prev_values = $current_values;
        }
        unset($ranking);
        
        // 保存当前排名到历史表（用于下次计算排名变化）
        // 注意：如果表不存在，跳过保存操作
        // 【新需求】"全部"时间段不保存历史记录（因为历史记录是按日期保存的）
        if ($period_type !== 'all') {
            try {
                $check_table = $conn->query("SHOW TABLES LIKE 'user_ranking_history'");
                if ($check_table && $check_table->num_rows > 0) {
                    foreach ($rankings as $ranking) {
                        $save_stmt = prepare_check($conn, "
                            INSERT INTO user_ranking_history (user_id, ranking_date, period_type, rank_position, total_words)
                            VALUES (?, ?, ?, ?, ?)
                            ON DUPLICATE KEY UPDATE 
                                rank_position = VALUES(rank_position),
                                total_words = VALUES(total_words)
                        ");
                        $save_stmt->bind_param(
                            "issii",
                            $ranking['user_id'],
                            $date,
                            $period_type,
                            $ranking['rank'],
                            $ranking['total_words']
                        );
                        $save_stmt->execute();
                    }
                }
            } catch (Exception $e) {
                // 如果表不存在或其他错误，忽略保存操作
                // 不影响排行榜数据的返回
            }
        }
        
        echo json_encode([
            'status' => 'ok',
            'period' => $period_type,
            'date' => $date,
            'rankings' => $rankings,
            'total_users' => count($rankings)
        ]);
    } catch (Exception $e) {
        http_response_code(500);
        error_log('PK排行榜错误: ' . $e->getMessage() . ' 文件: ' . $e->getFile() . ' 行: ' . $e->getLine());
        echo json_encode([
            'status' => 'error',
            'message' => '获取排行榜失败: ' . $e->getMessage(),
            'error_details' => [
                'file' => basename($e->getFile()),
                'line' => $e->getLine()
            ]
        ]);
    } catch (Error $e) {
        http_response_code(500);
        error_log('PK排行榜致命错误: ' . $e->getMessage() . ' 文件: ' . $e->getFile() . ' 行: ' . $e->getLine());
        echo json_encode([
            'status' => 'error',
            'message' => '获取排行榜失败: ' . $e->getMessage(),
            'error_details' => [
                'file' => basename($e->getFile()),
                'line' => $e->getLine()
            ]
        ]);
    }
}

// [20] 开始学习时导入单词（手动触发）
elseif ($action === 'import_words_for_study') {
    $uid = (int)$_GET['uid'];
    
    // 获取用户设置
    $stmt = prepare_check($conn, "SELECT daily_goal, enable_word_bank, grade FROM users WHERE id = ?");
    $stmt->bind_param("i", $uid);
    $stmt->execute();
    $user_settings = $stmt->get_result()->fetch_assoc();
    $enable_word_bank = $user_settings['enable_word_bank'] ?? 0;
    $grade = $user_settings['grade'] ?? null;
    $daily_goal = $user_settings['daily_goal'] ?? 5;
    
    // 检查今天手动录入的单词数量
    $stmt = prepare_check($conn, "SELECT COUNT(*) as count FROM words WHERE user_id = ? AND date_added = ? AND source = 'manual'");
    $stmt->bind_param("is", $uid, $today);
    $stmt->execute();
    $manual_result = $stmt->get_result()->fetch_assoc();
    $manual_count = (int)($manual_result['count'] ?? 0);
    
    // 检查今天单词库导入的单词数量
    $stmt = prepare_check($conn, "SELECT COUNT(*) as count FROM words WHERE user_id = ? AND date_added = ? AND source = 'word_bank'");
    $stmt->bind_param("is", $uid, $today);
    $stmt->execute();
    $word_bank_result = $stmt->get_result()->fetch_assoc();
    $word_bank_count = (int)($word_bank_result['count'] ?? 0);
    
    $result = [
        'manual_count' => $manual_count,
        'word_bank_count' => $word_bank_count,
        'daily_goal' => $daily_goal,
        'enable_word_bank' => $enable_word_bank,
        'grade' => $grade,
        'imported' => 0
    ];
    
    // 如果启用了单词库，执行导入
    if ($enable_word_bank == 1 && $grade) {
        $import_result = importWordBankWords($conn, $uid, $grade, $today, $daily_goal);
        if ($import_result) {
            $result['imported'] = $import_result['imported'] ?? 0;
            $result['manual_count'] = $import_result['manual_count'] ?? $manual_count;
            $result['word_bank_count'] = $import_result['word_bank_count'] ?? $word_bank_count;
            if (isset($import_result['bank_empty'])) {
                $result['bank_empty'] = $import_result['bank_empty'];
            }
        }
    }
    
    echo json_encode($result);
}

// [21] 准备学习队列（在点击"开始学习"时调用，计算复习单词+新单词）
elseif ($action === 'prepare_study_queue') {
    $uid = (int)$_GET['uid'];
    
    // 获取用户设置
    $stmt = prepare_check($conn, "SELECT daily_goal, enable_word_bank, grade FROM users WHERE id = ?");
    $stmt->bind_param("i", $uid);
    $stmt->execute();
    $user_settings = $stmt->get_result()->fetch_assoc();
    $daily_goal = $user_settings['daily_goal'] ?? 5;
    
    // 使用统一的isFirstLogin函数判断是否是第一次登录
    $is_first_login = isFirstLogin($conn, $uid, $today);
    
    // A. 智能复习抽取（如果不是第一次登录）
    $list_reviews = [];
    $total_review_count = 0;
    $yesterday_review_count = 0; // 前一天学习的新单词数量
    
    // 新需求：复习单词40%（动态计算）+ 昨天新单词（全量）+ 今天新单词（100%）
    // 如果是第一次登录，新单词100%（全部新单词）
    if ($is_first_login) {
        $review_count_target = 0; // 第一次登录，没有复习单词
        $new_word_target = $daily_goal; // 第一次登录，全部是新单词
    } else {
        // A1. 获取前一天学习的所有新单词（date_added = 昨天）
        // 这是新增的逻辑：第二天开始，每天都会复习前一天学习的所有新单词
        $yesterday = date('Y-m-d', strtotime("$today -1 day"));
        $stmt = prepare_check($conn, "
            SELECT w.*
            FROM words w
            WHERE w.user_id = ? AND w.date_added = ?
            ORDER BY w.id ASC
        ");
        $stmt->bind_param("is", $uid, $yesterday);
        $stmt->execute();
        $yesterday_words = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
        $yesterday_review_count = count($yesterday_words);
        
        // 检查学习天数，判断是否是第2天
        // 第2天：复习单词=0个（第一天没有需要复习的）
        // 第3天及以后：复习单词=40%（动态计算）
        $dates = getLearningDates($conn, $uid, 30);
        
        // 检查今天之前的学习日期数（不包括今天）
        $dates_before_today = array_filter($dates, function($date) use ($today) {
            return $date < $today;
        });
        $distinct_days_before_today = count($dates_before_today);
        
        if ($distinct_days_before_today == 1) {
            // 第2天：今天之前只有1个学习日期（昨天），今天是第2天
            $review_count_target = 0; // 第2天：复习单词=0个（第一天没有需要复习的）
        } else {
            // 第3天及以后：今天之前有2个或更多学习日期
            $review_count_target = max(1, ceil($daily_goal * 0.4)); // 40%的复习量（动态计算），至少1个
        }
        
        $new_word_target = $daily_goal; // 100%的新单词量（修改：从60%改为100%）
    }
    
    // 计算理论总任务量（用于返回）
    $theoretical_total_task = $review_count_target + $yesterday_review_count + $new_word_target;
    
    // 初始化变量
    $list_reviews_by_next_review = [];
    
    if (!$is_first_login) {
        // A2. 获取基于next_review的复习单词（新需求：固定40%，从前面所有天抽取）
        // 注意：yesterday_words和yesterday_review_count已经在上面计算好了
        // 复习单词数量固定为daily_goal * 0.4，从前面所有天（不包括昨天）中抽取
        // 第2天：review_count_target=0，不会执行此查询
        if ($review_count_target > 0) {
            // 优化：使用单一查询，通过LEFT JOIN和聚合函数计算优先级分数
            $stmt = prepare_check($conn, "
                SELECT w.*,
                       -- 统计听写模式忘记次数
                       COUNT(CASE WHEN rl_dict.review_mode = 'dictation' AND rl_dict.quality = 1 THEN 1 END) as dictation_forgot_count,
                       -- 统计听写模式失败次数（quality < 5）
                       COUNT(CASE WHEN rl_dict.review_mode = 'dictation' AND rl_dict.quality < 5 THEN 1 END) as dictation_fail_count,
                       -- 是否有听写记录
                       COUNT(CASE WHEN rl_dict.review_mode = 'dictation' THEN 1 END) > 0 as has_dictation_record,
                       -- 统计学习模式忘记次数
                       COUNT(CASE WHEN rl_study.review_mode = 'study' AND rl_study.quality = 1 THEN 1 END) as study_forgot_count,
                       -- 计算优先级分数（分数越高，优先级越高）
                       CASE 
                           -- 优先级1：听写模式连续忘记2次以上（分数：1000+）
                           WHEN COUNT(CASE WHEN rl_dict.review_mode = 'dictation' AND rl_dict.quality = 1 THEN 1 END) >= 2 
                           THEN 1000 + w.review_priority
                           -- 优先级2：听写模式有失败记录但少于2次（分数：500+）
                           WHEN COUNT(CASE WHEN rl_dict.review_mode = 'dictation' AND rl_dict.quality < 5 THEN 1 END) > 0
                           THEN 500 + w.review_priority
                           -- 优先级3：没有听写记录，但学习模式表现差（分数：200+）
                           WHEN COUNT(CASE WHEN rl_dict.review_mode = 'dictation' THEN 1 END) = 0
                           AND COUNT(CASE WHEN rl_study.review_mode = 'study' AND rl_study.quality = 1 THEN 1 END) >= 2
                           THEN 200 + w.review_priority
                           -- 优先级4：正常复习（分数：review_priority）
                           ELSE w.review_priority
                       END as calculated_priority
                FROM words w
                LEFT JOIN word_review_logs rl_dict ON w.id = rl_dict.word_id AND rl_dict.review_mode = 'dictation'
                LEFT JOIN word_review_logs rl_study ON w.id = rl_study.word_id AND rl_study.review_mode = 'study'
                WHERE w.user_id = ? 
                  AND w.status != 'new' 
                  AND w.next_review <= ?  -- SM-2算法依据
                  AND w.date_added != ?  -- 排除前一天学习的单词（已经在yesterday_words中）
                  AND w.date_added < ?   -- 只从前面所有天抽取（新需求）
                GROUP BY w.id
                ORDER BY calculated_priority DESC, w.next_review ASC
                LIMIT ?
            ");
            $stmt->bind_param("isssi", $uid, $today, $yesterday, $yesterday, $review_count_target);
            $stmt->execute();
            $list_reviews_by_next_review = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
        }
        
        // A3. 合并复习单词：前一天学习的单词 + 基于next_review的复习单词
        // 前一天学习的单词优先级最高（先复习）
        // 注意：第2天时，$list_reviews_by_next_review为空数组
        $list_reviews = array_merge($yesterday_words, $list_reviews_by_next_review);
        
        // 统计今天需要复习的所有单词数量（用于显示，不限制数量）
        $stmt = prepare_check($conn, "
            SELECT COUNT(*) as total_review_count
            FROM words 
            WHERE user_id = ? AND status != 'new' AND next_review <= ?
        ");
        $stmt->bind_param("is", $uid, $today);
        $stmt->execute();
        $total_review_result = $stmt->get_result()->fetch_assoc();
        $total_review_count = (int)($total_review_result['total_review_count'] ?? 0);
    } else {
        // 第一次登录，没有复习单词
        $list_reviews = [];
        $total_review_count = 0;
        $yesterday_review_count = 0;
    }
    
    // B. 待学新词（优先手动录入，然后单词库）
    // 新需求：新单词数量为100%的每日目标（修改：从60%改为100%）
    // 先获取今天手动录入的单词（只查询今天添加的，确保数量准确）
    $stmt = prepare_check($conn, "SELECT * FROM words WHERE user_id = ? AND status = 'new' AND date_added = ? AND source = 'manual' ORDER BY id ASC LIMIT ?");
    $stmt->bind_param("isi", $uid, $today, $new_word_target);
    $stmt->execute();
    $list_manual = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
    
    // 计算还需要多少新单词（基于100%）
    // 如果手动录入的单词已经够100%，就不需要从单词库导入
    $manual_count = count($list_manual);
    $remaining = max(0, $new_word_target - $manual_count);
    
    // 如果还有剩余，从单词库导入的单词中取（只查询今天添加的）
    $list_word_bank = [];
    if ($remaining > 0) {
        $stmt = prepare_check($conn, "SELECT * FROM words WHERE user_id = ? AND status = 'new' AND date_added = ? AND source = 'word_bank' ORDER BY id ASC LIMIT ?");
        $stmt->bind_param("isi", $uid, $today, $remaining);
        $stmt->execute();
        $list_word_bank = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
    }
    
    // 合并：手动录入优先
    $list_new = array_merge($list_manual, $list_word_bank);
    
    // 限制新单词数量不超过目标（100%）
    if (count($list_new) > $new_word_target) {
        $list_new = array_slice($list_new, 0, $new_word_target);
    }
    
    // 合并队列：优先显示待复习（不会的多练），然后是新词
    $final_queue = array_merge($list_reviews, $list_new);
    
    // 返回队列和统计信息
    echo json_encode([
        'queue' => $final_queue,
        'review_count' => count($list_reviews_by_next_review), // 复习单词数量（40%，从前面所有天抽取，不包括昨天新单词）
        'new_count' => count($list_new), // 今天新单词数量（100%）
        'total_review_count' => $total_review_count, // 所有需要复习的单词数（用于显示）
        'review_count_target' => $review_count_target, // 复习目标数量（40%，动态计算：daily_goal * 0.4）
        'new_word_target' => $new_word_target, // 新单词目标数量（100%，修改：从60%改为100%）
        'yesterday_review_count' => $yesterday_review_count, // 前一天学习的新单词数量（全量强制复习）
        'is_first_login' => $is_first_login,
        'total_task' => $theoretical_total_task, // 理论总任务量（复习单词40% + 昨天新单词 + 今天新单词100%）
        'actual_queue_length' => count($final_queue) // 实际队列长度（可能少于理论总任务量）
    ]);
}

// [22] 获取今天学习过的单词（用于听写）
elseif ($action === 'get_today_learned_words_for_dictation') {
    try {
        $uid = (int)$_GET['uid'];
        
        // 1. 检查今天是否学习过（包括新学和复习）
        // 先检查word_review_logs表是否存在
        $table_exists = false;
        $check_table = $conn->query("SHOW TABLES LIKE 'word_review_logs'");
        if ($check_table && $check_table->num_rows > 0) {
            $table_exists = true;
        }
        
        // 统计今天学习过的单词（通过word_review_logs表，这是最准确的方法）
        $today_learned_count = 0;
        $today_new_count = 0;
        $today_reviewed_count = 0;
        
        if ($table_exists) {
            // 统计今天学习过的所有单词（通过word_review_logs表）
            $stmt = prepare_check($conn, "
                SELECT COUNT(DISTINCT word_id) as today_learned 
                FROM word_review_logs 
                WHERE user_id = ? AND review_date = ?
            ");
            if ($stmt) {
                $stmt->bind_param("is", $uid, $today);
                if ($stmt->execute()) {
                    $today_learned_result = $stmt->get_result()->fetch_assoc();
                    $today_learned_count = (int)($today_learned_result['today_learned'] ?? 0);
                }
            }
            
            // 统计今天新添加的单词（date_added = 今天）
            $stmt = prepare_check($conn, "
                SELECT COUNT(*) as today_new 
                FROM words 
                WHERE user_id = ? AND date_added = ?
            ");
            if ($stmt) {
                $stmt->bind_param("is", $uid, $today);
                if ($stmt->execute()) {
                    $today_new_result = $stmt->get_result()->fetch_assoc();
                    $today_new_count = (int)($today_new_result['today_new'] ?? 0);
                }
            }
            
            // 统计今天复习的单词（今天学习过但不是今天添加的）
            $today_reviewed_count = max(0, $today_learned_count - $today_new_count);
        } else {
            // 如果word_review_logs表不存在，只统计今天新添加的单词
            $stmt = prepare_check($conn, "
                SELECT COUNT(*) as today_new 
                FROM words 
                WHERE user_id = ? AND date_added = ?
            ");
            if (!$stmt) {
                echo json_encode(["error" => "SQL准备失败: " . $conn->error]);
                exit;
            }
            $stmt->bind_param("is", $uid, $today);
            if (!$stmt->execute()) {
                echo json_encode(["error" => "SQL执行失败: " . $stmt->error]);
                exit;
            }
            $today_new_result = $stmt->get_result()->fetch_assoc();
            $today_new_count = (int)($today_new_result['today_new'] ?? 0);
            $today_learned_count = $today_new_count;
        }
        
        // 如果今天还没有学习过，返回空队列
        if ($today_learned_count == 0) {
            echo json_encode([
                'queue' => [],
                'today_learned_count' => 0,
                'today_new_count' => 0,
                'today_reviewed_count' => 0,
                'has_learned' => false
            ]);
            exit;
        }
        
        // 2. 获取今天学习过的所有单词（用于听写）
        // 包括：今天新添加的单词 + 今天复习过的单词
        if ($table_exists) {
            // 如果word_review_logs表存在，使用完整查询
            $stmt = prepare_check($conn, "
                SELECT DISTINCT w.*
                FROM words w
                WHERE w.user_id = ?
                AND (
                    -- 今天新添加的单词
                    (w.date_added = ?)
                    OR
                    -- 今天复习过的单词（通过word_review_logs表）
                    EXISTS (
                        SELECT 1 
                        FROM word_review_logs rl 
                        WHERE rl.word_id = w.id 
                        AND rl.user_id = ? 
                        AND rl.review_date = ?
                    )
                )
                ORDER BY 
                    -- 优先显示今天复习过的单词（需要更多练习）
                    CASE WHEN EXISTS (
                        SELECT 1 FROM word_review_logs rl2 
                        WHERE rl2.word_id = w.id AND rl2.user_id = ? AND rl2.review_date = ?
                    ) THEN 0 ELSE 1 END,
                    w.date_added ASC, w.id ASC
            ");
            if (!$stmt) {
                echo json_encode(["error" => "SQL准备失败: " . $conn->error]);
                exit;
            }
            // 修正：参数类型字符串应该是 "isisis" (6个参数：i, s, i, s, i, s)
            $stmt->bind_param("isisis", $uid, $today, $uid, $today, $uid, $today);
        } else {
            // 如果word_review_logs表不存在，只查询今天新添加的单词
            $stmt = prepare_check($conn, "
                SELECT DISTINCT w.*
                FROM words w
                WHERE w.user_id = ? AND w.date_added = ?
                ORDER BY w.date_added ASC, w.id ASC
            ");
            if (!$stmt) {
                echo json_encode(["error" => "SQL准备失败: " . $conn->error]);
                exit;
            }
            $stmt->bind_param("is", $uid, $today);
        }
        
        if (!$stmt->execute()) {
            echo json_encode(["error" => "SQL执行失败: " . $stmt->error]);
            exit;
        }
        $today_learned_words = $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
        
        echo json_encode([
            'queue' => $today_learned_words,
            'today_learned_count' => $today_learned_count,
            'today_new_count' => $today_new_count,
            'today_reviewed_count' => $today_reviewed_count,
            'has_learned' => true
        ]);
    } catch (Exception $e) {
        echo json_encode([
            "error" => "服务器错误: " . $e->getMessage(),
            "file" => basename($e->getFile()),
            "line" => $e->getLine()
        ]);
    } catch (Error $e) {
        echo json_encode([
            "error" => "PHP致命错误: " . $e->getMessage(),
            "file" => basename($e->getFile()),
            "line" => $e->getLine()
        ]);
    }
}

else {
    echo json_encode(["error" => "Invalid Action: " . htmlspecialchars($action)]);
}
?>