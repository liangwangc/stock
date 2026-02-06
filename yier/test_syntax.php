<?php
// 测试语法
require_once '扩展单词列表.php';
$lists = getWordLists();
echo "成功加载！共 " . count($lists) . " 个年级\n";
foreach ($lists as $grade => $words) {
    echo "$grade: " . count($words) . " 个单词\n";
}
