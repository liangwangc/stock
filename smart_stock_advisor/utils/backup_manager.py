"""
数据备份和恢复管理模块

本模块提供完整的数据库备份和恢复功能，支持：
- 自动/手动备份：支持使用mysqldump命令或Python方式创建数据库备份
- 备份管理：列出、删除备份文件，支持元数据管理
- 备份恢复：支持mysql命令或Python方式恢复备份
- 定时备份：可集成到定时任务管理系统，支持自动定期备份

使用示例：
    ```python
    from utils.backup_manager import BackupManager
    
    # 创建备份管理器实例
    manager = BackupManager()
    
    # 创建备份
    backup_info = manager.create_backup(backup_type='full', description='手动备份')
    
    # 列出所有备份
    backups = manager.list_backups(limit=50)
    
    # 恢复备份
    result = manager.restore_backup(backup_id=1)
    
    # 删除备份
    success = manager.delete_backup(backup_id=1)
    ```

作者：Smart Stock Advisor Team
创建日期：2024
最后更新：2024
"""
import os
import sys
import subprocess
from datetime import datetime
from typing import Dict, List, Optional
import json

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from config_db import DB_CONFIG, USE_DATABASE

logger = get_logger(__name__)


class BackupManager:
    """
    数据备份管理器
    
    负责数据库的备份、恢复和备份文件管理。支持多种备份方式：
    - mysqldump命令（优先，如果系统安装了MySQL客户端）
    - Python方式（回退方案，通用但性能较低）
    
    备份文件管理：
    - 备份文件保存在项目根目录下的 `backups/` 文件夹
    - 备份文件命名格式：`backup_YYYYMMDD_HHMMSS.sql`
    - 备份元数据存储在 `backups/backup_metadata.json` 中
    
    特性：
    - 自动创建备份目录
    - 元数据持久化存储
    - 支持备份文件验证
    - 错误处理和日志记录
    """
    
    def __init__(self):
        """
        初始化备份管理器
        
        初始化时会：
        1. 检查并创建备份目录（如果不存在）
        2. 加载备份元数据（如果存在）
        3. 初始化日志记录器
        
        功能说明：
        - 备份目录：项目根目录下的 backups/ 文件夹
        - 备份格式：SQL文件（使用mysqldump）或自定义格式
        - 备份命名：backup_YYYYMMDD_HHMMSS.sql
        
        Raises:
            OSError: 如果无法创建备份目录
        """
        self.logger = logger
        self.use_database = USE_DATABASE
        self.db_config = DB_CONFIG.copy()
        
        # 备份目录
        self.backup_dir = os.path.join(project_root, 'backups')
        self._ensure_backup_dir()
        
        # 备份文件元数据文件（存储备份信息）
        self.metadata_file = os.path.join(self.backup_dir, 'backup_metadata.json')
        self.metadata = self._load_metadata()
    
    def _ensure_backup_dir(self):
        """
        确保备份目录存在
        
        如果备份目录不存在，则创建该目录。如果创建失败，会记录错误并抛出异常。
        
        Raises:
            OSError: 如果无法创建备份目录
        """
        try:
            if not os.path.exists(self.backup_dir):
                os.makedirs(self.backup_dir)
                self.logger.info(f"创建备份目录: {self.backup_dir}")
        except Exception as e:
            self.logger.error(f"创建备份目录失败: {str(e)}")
            raise
    
    def _load_metadata(self) -> Dict:
        """
        加载备份元数据
        
        从备份元数据文件中加载备份信息。如果文件不存在或加载失败，
        返回默认的空元数据结构。
        
        Returns:
            Dict: 备份元数据字典，包含：
                - backups: 备份列表
                - last_backup_time: 最后备份时间
                - total_backups: 备份总数
        """
        try:
            if os.path.exists(self.metadata_file):
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.warning(f"加载备份元数据失败: {str(e)}")
        
        return {
            'backups': [],
            'last_backup_time': None,
            'total_backups': 0
        }
    
    def _save_metadata(self):
        """
        保存备份元数据到文件
        
        将当前内存中的备份元数据保存到JSON文件中。
        如果保存失败，会记录错误但不会抛出异常（避免影响主流程）。
        """
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存备份元数据失败: {str(e)}")
    
    def get_backup_info(self) -> Dict:
        """
        获取备份信息
        
        Returns:
            备份信息字典：包含备份目录、备份数量、最后备份时间等
        """
        try:
            backups = self.list_backups()
            last_backup = backups[0] if backups else None
            
            return {
                'backup_dir': self.backup_dir,
                'total_backups': len(backups),
                'last_backup_time': last_backup.get('created_at') if last_backup else None,
                'last_backup_file': last_backup.get('filename') if last_backup else None,
                'total_size': sum(b.get('size', 0) for b in backups)
            }
        except Exception as e:
            self.logger.error(f"获取备份信息失败: {str(e)}")
            return {
                'backup_dir': self.backup_dir,
                'total_backups': 0,
                'last_backup_time': None,
                'last_backup_file': None,
                'total_size': 0
            }
    
    def create_backup(self, backup_type: str = 'full', description: str = None) -> Optional[Dict]:
        """
        创建数据库备份
        
        Args:
            backup_type: 备份类型（'full'=全量备份，'incremental'=增量备份）
            description: 备份描述
        
        Returns:
            备份信息字典，如果失败返回None
        """
        if not self.use_database:
            self.logger.warning("数据库未启用，无法创建备份")
            return None
        
        try:
            # 生成备份文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"backup_{timestamp}.sql"
            filepath = os.path.join(self.backup_dir, filename)
            
            # 使用mysqldump进行备份（如果可用）
            backup_success = self._backup_with_mysqldump(filepath)
            
            if not backup_success:
                # 回退到Python导出方式
                self.logger.info("mysqldump不可用，使用Python导出方式")
                backup_success = self._backup_with_python(filepath)
            
            if not backup_success:
                self.logger.error("备份失败")
                return None
            
            # 获取文件大小
            file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
            
            # 创建备份记录（使用 max(id)+1 防止删除后ID冲突）
            existing_ids = [b.get('id', 0) for b in self.metadata.get('backups', [])]
            next_id = max(existing_ids, default=0) + 1
            backup_info = {
                'id': next_id,
                'filename': filename,
                'filepath': filepath,
                'size': file_size,
                'type': backup_type,
                'description': description or f'{backup_type}备份',
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'success'
            }
            
            # 添加到元数据
            if 'backups' not in self.metadata:
                self.metadata['backups'] = []
            self.metadata['backups'].insert(0, backup_info)  # 最新的在前面
            self.metadata['last_backup_time'] = backup_info['created_at']
            self.metadata['total_backups'] = len(self.metadata['backups'])
            self._save_metadata()
            
            self.logger.info(f"备份创建成功: {filename} (大小: {file_size / 1024 / 1024:.2f} MB)")
            return backup_info
            
        except Exception as e:
            self.logger.error(f"创建备份失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None
    
    def _backup_with_mysqldump(self, filepath: str) -> bool:
        """
        使用mysqldump命令进行备份（如果可用）
        
        Args:
            filepath: 备份文件路径
        
        Returns:
            是否成功
        """
        try:
            # 构建mysqldump命令
            cmd = [
                'mysqldump',
                f"--host={self.db_config['host']}",
                f"--port={self.db_config['port']}",
                f"--user={self.db_config['user']}",
                f"--password={self.db_config['password']}",
                '--single-transaction',  # 保证数据一致性
                '--routines',  # 包含存储过程和函数
                '--triggers',  # 包含触发器
                '--events',  # 包含事件
                '--hex-blob',  # 二进制数据使用十六进制
                self.db_config['database']
            ]
            
            # 执行mysqldump命令
            with open(filepath, 'w', encoding='utf-8') as f:
                result = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=3600  # 1小时超时
                )
            
            if result.returncode == 0:
                return True
            else:
                self.logger.warning(f"mysqldump执行失败: {result.stderr}")
                # 如果文件存在但命令失败，删除文件
                if os.path.exists(filepath):
                    os.remove(filepath)
                return False
                
        except FileNotFoundError:
            # mysqldump命令不存在
            return False
        except subprocess.TimeoutExpired:
            self.logger.error("mysqldump执行超时")
            if os.path.exists(filepath):
                os.remove(filepath)
            return False
        except Exception as e:
            self.logger.warning(f"使用mysqldump备份失败: {str(e)}")
            if os.path.exists(filepath):
                os.remove(filepath)
            return False
    
    def _backup_with_python(self, filepath: str) -> bool:
        """
        使用Python进行数据库备份（导出所有表结构数据）
        
        Args:
            filepath: 备份文件路径
        
        Returns:
            是否成功
        """
        try:
            import pymysql
            
            # 连接数据库（增加超时时间，避免大表查询超时）
            conn = pymysql.connect(
                host=self.db_config['host'],
                port=self.db_config['port'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                database=self.db_config['database'],
                charset=self.db_config.get('charset', 'utf8mb4'),
                connect_timeout=60,  # 连接超时60秒
                read_timeout=300,    # 读取超时300秒（5分钟）
                write_timeout=300    # 写入超时300秒（5分钟）
            )
            
            try:
                cursor = conn.cursor()
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    # 写入备份头部信息
                    f.write(f"-- 数据库备份文件\n")
                    f.write(f"-- 备份时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"-- 数据库: {self.db_config['database']}\n")
                    f.write(f"-- 主机: {self.db_config['host']}:{self.db_config['port']}\n")
                    f.write("-- ============================================\n\n")
                    f.write("SET FOREIGN_KEY_CHECKS=0;\n\n")
                    
                    # 获取所有表
                    cursor.execute("SHOW TABLES")
                    tables = [row[0] for row in cursor.fetchall()]
                    
                    for table in tables:
                        try:
                            # 导出表结构
                            try:
                                cursor.execute(f"SHOW CREATE TABLE `{table}`")
                                create_table = cursor.fetchone()
                                if create_table:
                                    f.write(f"\n-- ============================================\n")
                                    f.write(f"-- 表结构: {table}\n")
                                    f.write(f"-- ============================================\n")
                                    f.write(f"DROP TABLE IF EXISTS `{table}`;\n")
                                    f.write(f"{create_table[1]};\n\n")
                                else:
                                    self.logger.warning(f"表 {table} 结构查询返回空结果")
                                    f.write(f"\n-- 警告: 表 {table} 结构查询失败（返回空结果）\n\n")
                                    continue
                            except Exception as e:
                                self.logger.warning(f"导出表 {table} 结构失败: {str(e)}")
                                f.write(f"\n-- 警告: 表 {table} 结构导出失败: {str(e)}\n\n")
                                continue
                            
                            # 检查表是否存在数据
                            try:
                                cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                                row_count = cursor.fetchone()[0]
                                
                                if row_count == 0:
                                    f.write(f"-- 表数据: {table} (0 行，跳过数据导出)\n\n")
                                    continue
                                
                                # 获取列名
                                cursor.execute(f"DESCRIBE `{table}`")
                                columns = [col[0] for col in cursor.fetchall()]
                                
                                if not columns:
                                    self.logger.warning(f"表 {table} 列信息查询返回空结果")
                                    f.write(f"-- 警告: 表 {table} 列信息查询失败（返回空结果）\n\n")
                                    continue
                                
                                f.write(f"-- 表数据: {table} ({row_count} 行)\n")
                                
                                # 对于大表（超过10万行），使用流式查询分批导出
                                if row_count > 100000:
                                    self.logger.info(f"表 {table} 数据量较大 ({row_count} 行)，使用流式查询分批导出...")
                                    # 使用流式查询，分批获取数据
                                    cursor.execute(f"SELECT * FROM `{table}`")
                                    
                                    batch_size = 1000  # 大表使用更大的批次
                                    batch_count = 0
                                    first_batch = True
                                    
                                    while True:
                                        batch = cursor.fetchmany(batch_size)
                                        if not batch:
                                            break
                                        
                                        if first_batch:
                                            f.write(f"INSERT INTO `{table}` (`{'`, `'.join(columns)}`) VALUES\n")
                                            first_batch = False
                                        
                                        values_list = []
                                        for row in batch:
                                            values = []
                                            for val in row:
                                                if val is None:
                                                    values.append('NULL')
                                                elif isinstance(val, (int, float)):
                                                    values.append(str(val))
                                                else:
                                                    # 转义字符串
                                                    val_str = str(val).replace('\\', '\\\\').replace("'", "\\'")
                                                    values.append(f"'{val_str}'")
                                            values_list.append(f"({', '.join(values)})")
                                        
                                        f.write(',\n'.join(values_list))
                                        batch_count += len(batch)
                                        
                                        if batch_count < row_count:
                                            f.write(',\n')
                                        else:
                                            f.write(';\n\n')
                                        
                                        # 每处理一批后刷新文件缓冲区
                                        f.flush()
                                        
                                        # 每处理1万行打印一次进度
                                        if batch_count % 10000 == 0:
                                            self.logger.info(f"  已导出 {batch_count}/{row_count} 行...")
                                else:
                                    # 小表直接查询所有数据
                                    cursor.execute(f"SELECT * FROM `{table}`")
                                    rows = cursor.fetchall()
                                    
                                    if rows:
                                        f.write(f"INSERT INTO `{table}` (`{'`, `'.join(columns)}`) VALUES\n")
                                        
                                        # 导出数据（分批处理，避免SQL过长）
                                        batch_size = 100
                                        for i in range(0, len(rows), batch_size):
                                            batch = rows[i:i+batch_size]
                                            values_list = []
                                            
                                            for row in batch:
                                                values = []
                                                for val in row:
                                                    if val is None:
                                                        values.append('NULL')
                                                    elif isinstance(val, (int, float)):
                                                        values.append(str(val))
                                                    else:
                                                        # 转义字符串
                                                        val_str = str(val).replace('\\', '\\\\').replace("'", "\\'")
                                                        values.append(f"'{val_str}'")
                                                values_list.append(f"({', '.join(values)})")
                                            
                                            f.write(',\n'.join(values_list))
                                            if i + batch_size < len(rows):
                                                f.write(',\n')
                                            else:
                                                f.write(';\n\n')
                            except Exception as e:
                                error_msg = str(e)
                                # 检查是否是连接超时错误
                                if 'Lost connection' in error_msg or '2013' in error_msg:
                                    self.logger.warning(f"导出表 {table} 数据失败: 连接超时（表可能过大），尝试跳过数据导出")
                                    f.write(f"\n-- 警告: 表 {table} 数据导出失败: 连接超时（表可能过大，已跳过数据导出）\n\n")
                                else:
                                    self.logger.warning(f"导出表 {table} 数据失败: {error_msg}")
                                    f.write(f"\n-- 警告: 表 {table} 数据导出失败: {error_msg}\n\n")
                                
                        except Exception as e:
                            error_msg = str(e)
                            self.logger.warning(f"导出表 {table} 失败: {error_msg}")
                            f.write(f"\n-- 警告: 表 {table} 导出失败: {error_msg}\n\n")
                    
                    f.write("SET FOREIGN_KEY_CHECKS=1;\n")
                
                return True
                
            finally:
                conn.close()
                
        except Exception as e:
            self.logger.error(f"Python备份失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            if os.path.exists(filepath):
                os.remove(filepath)
            return False
    
    def list_backups(self, limit: int = 50) -> List[Dict]:
        """
        列出所有备份文件
        
        Args:
            limit: 返回数量限制
        
        Returns:
            备份列表（按时间倒序）
        """
        try:
            backups = []
            
            # 从元数据获取备份信息
            metadata_backups = self.metadata.get('backups', [])
            
            # 验证文件是否存在，更新文件大小
            for backup in metadata_backups[:limit]:
                filepath = backup.get('filepath') or os.path.join(self.backup_dir, backup.get('filename', ''))
                
                if os.path.exists(filepath):
                    # 更新文件大小
                    backup['size'] = os.path.getsize(filepath)
                    backup['filepath'] = filepath
                    backups.append(backup)
                else:
                    # 文件不存在，标记为无效
                    backup['status'] = 'missing'
            
            # 如果元数据中没有，尝试从文件系统扫描
            if len(backups) == 0:
                backups = self._scan_backup_files(limit)
            
            return backups
            
        except Exception as e:
            self.logger.error(f"列出备份失败: {str(e)}")
            return []
    
    def _scan_backup_files(self, limit: int = 50) -> List[Dict]:
        """从文件系统扫描备份文件，并将结果写入 metadata 使其可管理"""
        try:
            backups = []
            
            if not os.path.exists(self.backup_dir):
                return backups
            
            # 获取 metadata 中已有的文件名集合，避免重复
            existing_filenames = {b.get('filename') for b in self.metadata.get('backups', [])}
            existing_ids = [b.get('id', 0) for b in self.metadata.get('backups', [])]
            next_id = max(existing_ids, default=0) + 1
            
            # 扫描备份目录
            new_entries = []
            for filename in os.listdir(self.backup_dir):
                if filename.startswith('backup_') and filename.endswith('.sql'):
                    if filename in existing_filenames:
                        continue  # 已在 metadata 中，跳过
                    filepath = os.path.join(self.backup_dir, filename)
                    if os.path.isfile(filepath):
                        stat = os.stat(filepath)
                        entry = {
                            'id': next_id,
                            'filename': filename,
                            'filepath': filepath,
                            'size': stat.st_size,
                            'type': 'full',
                            'description': '自动扫描的备份',
                            'created_at': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                            'status': 'success'
                        }
                        new_entries.append(entry)
                        backups.append(entry)
                        next_id += 1
            
            # 将扫描到的新备份写入 metadata，使其可通过 ID 操作（删除/恢复）
            if new_entries:
                if 'backups' not in self.metadata:
                    self.metadata['backups'] = []
                self.metadata['backups'].extend(new_entries)
                self.metadata['total_backups'] = len(self.metadata['backups'])
                self._save_metadata()
                self.logger.info(f"扫描发现 {len(new_entries)} 个新备份文件，已写入元数据")
            
            # 合并 metadata 中已有的 + 新扫描的
            all_backups = self.metadata.get('backups', [])
            # 验证文件存在
            valid_backups = []
            for b in all_backups:
                fp = b.get('filepath') or os.path.join(self.backup_dir, b.get('filename', ''))
                if os.path.exists(fp):
                    b['filepath'] = fp
                    b['size'] = os.path.getsize(fp)
                    valid_backups.append(b)
            
            # 按时间倒序排序
            valid_backups.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            return valid_backups[:limit]
            
        except Exception as e:
            self.logger.error(f"扫描备份文件失败: {str(e)}")
            return []
    
    def delete_backup(self, backup_id: int = None, filename: str = None) -> bool:
        """
        删除备份文件
        
        Args:
            backup_id: 备份ID（从元数据）
            filename: 备份文件名
        
        Returns:
            是否成功
        """
        try:
            if backup_id:
                # 从元数据中查找
                backups = self.metadata.get('backups', [])
                backup = next((b for b in backups if b.get('id') == backup_id), None)
                if backup:
                    filename = backup.get('filename')
                    filepath = backup.get('filepath') or os.path.join(self.backup_dir, filename)
                else:
                    self.logger.error(f"备份ID {backup_id} 不存在")
                    return False
            elif filename:
                filepath = os.path.join(self.backup_dir, filename)
            else:
                self.logger.error("必须提供backup_id或filename")
                return False
            
            # 删除文件
            if os.path.exists(filepath):
                os.remove(filepath)
                self.logger.info(f"删除备份文件: {filename}")
            else:
                self.logger.warning(f"备份文件不存在: {filepath}")
            
            # 从元数据中移除
            if backup_id:
                self.metadata['backups'] = [b for b in self.metadata.get('backups', []) if b.get('id') != backup_id]
                self.metadata['total_backups'] = len(self.metadata['backups'])
                self._save_metadata()
            
            return True
            
        except Exception as e:
            self.logger.error(f"删除备份失败: {str(e)}")
            return False
    
    def restore_backup(self, backup_id: int = None, filename: str = None) -> Dict:
        """
        恢复备份
        
        Args:
            backup_id: 备份ID（从元数据）
            filename: 备份文件名
        
        Returns:
            恢复结果字典
        """
        if not self.use_database:
            return {
                'success': False,
                'message': '数据库未启用，无法恢复备份'
            }
        
        try:
            # 查找备份文件
            if backup_id:
                backups = self.metadata.get('backups', [])
                backup = next((b for b in backups if b.get('id') == backup_id), None)
                if backup:
                    filename = backup.get('filename')
                    filepath = backup.get('filepath') or os.path.join(self.backup_dir, filename)
                else:
                    return {
                        'success': False,
                        'message': f'备份ID {backup_id} 不存在'
                    }
            elif filename:
                filepath = os.path.join(self.backup_dir, filename)
            else:
                return {
                    'success': False,
                    'message': '必须提供backup_id或filename'
                }
            
            if not os.path.exists(filepath):
                return {
                    'success': False,
                    'message': f'备份文件不存在: {filepath}'
                }
            
            # 使用mysql命令恢复（如果可用）
            restore_success = self._restore_with_mysql(filepath)
            
            if not restore_success:
                # 回退到Python方式
                self.logger.info("mysql命令不可用，使用Python恢复方式")
                restore_success = self._restore_with_python(filepath)
            
            if restore_success:
                return {
                    'success': True,
                    'message': f'备份恢复成功: {filename}'
                }
            else:
                return {
                    'success': False,
                    'message': '备份恢复失败，请查看日志'
                }
                
        except Exception as e:
            self.logger.error(f"恢复备份失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f'恢复备份失败: {str(e)}'
            }
    
    def _restore_with_mysql(self, filepath: str) -> bool:
        """使用mysql命令恢复备份"""
        try:
            cmd = [
                'mysql',
                f"--host={self.db_config['host']}",
                f"--port={self.db_config['port']}",
                f"--user={self.db_config['user']}",
                f"--password={self.db_config['password']}",
                self.db_config['database']
            ]
            
            with open(filepath, 'r', encoding='utf-8') as f:
                result = subprocess.run(
                    cmd,
                    stdin=f,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=3600
                )
            
            if result.returncode == 0:
                return True
            else:
                self.logger.warning(f"mysql命令执行失败: {result.stderr}")
                return False
                
        except FileNotFoundError:
            return False
        except subprocess.TimeoutExpired:
            self.logger.error("mysql命令执行超时")
            return False
        except Exception as e:
            self.logger.warning(f"使用mysql命令恢复失败: {str(e)}")
            return False
    
    def _restore_with_python(self, filepath: str) -> bool:
        """使用Python恢复备份"""
        try:
            import pymysql
            
            # 连接数据库
            conn = pymysql.connect(
                host=self.db_config['host'],
                port=self.db_config['port'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                database=self.db_config['database'],
                charset=self.db_config.get('charset', 'utf8mb4')
            )
            
            try:
                cursor = conn.cursor()
                
                # 读取SQL文件
                with open(filepath, 'r', encoding='utf-8') as f:
                    sql_content = f.read()
                
                # 分割SQL语句（按分号分割，但要注意字符串中的分号）
                # 简单处理：按行分割，忽略注释
                statements = []
                current_statement = []
                
                for line in sql_content.split('\n'):
                    line = line.strip()
                    # 跳过注释和空行
                    if not line or line.startswith('--') or line.startswith('/*'):
                        continue
                    
                    current_statement.append(line)
                    
                    # 如果行以分号结尾，说明是一个完整的语句
                    if line.endswith(';'):
                        statement = ' '.join(current_statement)
                        if statement:
                            statements.append(statement)
                        current_statement = []
                
                # 执行SQL语句
                for i, statement in enumerate(statements):
                    try:
                        cursor.execute(statement)
                        if (i + 1) % 100 == 0:
                            self.logger.info(f"已执行 {i + 1}/{len(statements)} 条SQL语句")
                    except Exception as e:
                        self.logger.warning(f"执行SQL语句失败 (第{i+1}条): {str(e)}")
                        # 继续执行其他语句
                
                conn.commit()
                self.logger.info(f"备份恢复完成，共执行 {len(statements)} 条SQL语句")
                return True
                
            finally:
                conn.close()
                
        except Exception as e:
            self.logger.error(f"Python恢复失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False

