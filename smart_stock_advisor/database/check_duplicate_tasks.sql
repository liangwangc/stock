-- 检查重复的定时任务
-- 表名: scheduled_tasks

-- 1. 查看所有启用的任务
SELECT 
    id,
    task_name,
    task_type,
    schedule_type,
    schedule_time,
    schedule_weekdays,
    is_active,
    created_at
FROM scheduled_tasks
WHERE is_active = 1
ORDER BY task_type, schedule_type, schedule_time;

-- 2. 查找重复的任务（相同任务类型、调度类型、调度时间）
SELECT 
    task_type,
    schedule_type,
    schedule_time,
    schedule_weekdays,
    COUNT(*) as duplicate_count,
    GROUP_CONCAT(id ORDER BY id) as task_ids,
    GROUP_CONCAT(task_name ORDER BY id SEPARATOR ' | ') as task_names
FROM scheduled_tasks
WHERE is_active = 1
GROUP BY task_type, schedule_type, schedule_time, schedule_weekdays
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC, task_type;

-- 3. 详细查看重复任务
SELECT 
    t1.id,
    t1.task_name,
    t1.task_type,
    t1.schedule_type,
    t1.schedule_time,
    t1.schedule_weekdays,
    t1.created_at,
    t1.task_config
FROM scheduled_tasks t1
INNER JOIN (
    SELECT task_type, schedule_type, schedule_time, schedule_weekdays
    FROM scheduled_tasks
    WHERE is_active = 1
    GROUP BY task_type, schedule_type, schedule_time, schedule_weekdays
    HAVING COUNT(*) > 1
) t2 ON t1.task_type = t2.task_type 
    AND t1.schedule_type = t2.schedule_type 
    AND t1.schedule_time = t2.schedule_time
    AND (t1.schedule_weekdays = t2.schedule_weekdays OR (t1.schedule_weekdays IS NULL AND t2.schedule_weekdays IS NULL))
WHERE t1.is_active = 1
ORDER BY t1.task_type, t1.schedule_type, t1.schedule_time, t1.id;

-- 4. 禁用重复任务（保留ID最小的任务）
-- 注意：执行前请先备份数据！
-- UPDATE scheduled_tasks 
-- SET is_active = 0 
-- WHERE id IN (
--     SELECT id FROM (
--         SELECT t1.id
--         FROM scheduled_tasks t1
--         INNER JOIN (
--             SELECT task_type, schedule_type, schedule_time, schedule_weekdays, MIN(id) as min_id
--             FROM scheduled_tasks
--             WHERE is_active = 1
--             GROUP BY task_type, schedule_type, schedule_time, schedule_weekdays
--             HAVING COUNT(*) > 1
--         ) t2 ON t1.task_type = t2.task_type 
--             AND t1.schedule_type = t2.schedule_type 
--             AND t1.schedule_time = t2.schedule_time
--             AND (t1.schedule_weekdays = t2.schedule_weekdays OR (t1.schedule_weekdays IS NULL AND t2.schedule_weekdays IS NULL))
--         WHERE t1.is_active = 1 AND t1.id != t2.min_id
--     ) AS temp
-- );
