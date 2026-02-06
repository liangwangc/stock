# 按日期批量获取优化方案

## 一、问题分析

**当前问题**：
- 按股票循环，每只股票调用一次API
- 5000只股票 × 5天 = 25000次API调用（daily + daily_basic）
- 即使有50次/分钟的限制，也需要500分钟（约8.3小时）

**Tushare API支持**：
- `pro.daily(trade_date='20180810')` - 可以获取**所有股票**在指定日期的数据
- `pro.daily_basic(ts_code='', trade_date='20180726')` - 可以获取**所有股票**在指定日期的基本面数据
- 单次最大返回6000条数据
- 基础积分每分钟内可调取500次

## 二、优化方案

**改为按日期循环**：
- 对于每个日期，调用一次API获取所有股票的数据
- 5天数据 = 5次API调用（daily）+ 5次API调用（daily_basic）= 10次
- 性能提升约2500倍！

## 三、实现步骤

1. **新增方法**：`fetch_all_stocks_by_date` - 按日期批量获取所有股票数据
2. **新增方法**：`fetch_all_stocks_daily_basic_by_date` - 按日期批量获取所有股票基本面数据
3. **重构主方法**：`fetch_and_save_missing_data` - 改为按日期循环处理

## 四、代码修改

### 4.1 新增按日期批量获取方法

```python
def fetch_all_stocks_by_date(self, trade_date: str) -> Optional[pd.DataFrame]:
    """
    按日期批量获取所有股票的数据（优化：一次API调用获取所有股票）
    
    Args:
        trade_date: 交易日期（YYYY-MM-DD格式）
    
    Returns:
        DataFrame或None
    """
    try:
        # 速率限制：等待直到可以发送请求
        wait_time = self.rate_limiter.wait_if_needed()
        if wait_time > 0:
            time.sleep(wait_time)
        
        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD
        trade_date_str = trade_date.replace('-', '')
        
        # 调用Tushare API：不传ts_code，只传trade_date，获取所有股票的数据
        df = self.pro.daily(trade_date=trade_date_str)
        
        if df is None or df.empty:
            return None
        
        return df
        
    except Exception as e:
        error_str = str(e).lower()
        is_rate_limit = any(keyword in error_str for keyword in [
            'rate limit', '429', 'too many requests', 
            '每分钟最多', '访问该接口', '权限的具体详情',
            '请求过于频繁', '访问频率', '请求次数'
        ])
        
        if is_rate_limit:
            self.logger.debug(f"速率限制: {trade_date}，跳过本次请求")
            return None
        else:
            self.logger.error(f"获取所有股票数据失败 {trade_date}: {str(e)}")
            return None

def fetch_all_stocks_daily_basic_by_date(self, trade_date: str) -> Optional[pd.DataFrame]:
    """
    按日期批量获取所有股票的基本面数据（优化：一次API调用获取所有股票）
    
    Args:
        trade_date: 交易日期（YYYY-MM-DD格式）
    
    Returns:
        DataFrame或None
    """
    try:
        # 速率限制：等待直到可以发送请求
        wait_time = self.rate_limiter.wait_if_needed()
        if wait_time > 0:
            time.sleep(wait_time)
        
        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD
        trade_date_str = trade_date.replace('-', '')
        
        # 调用Tushare API：不传ts_code，只传trade_date，获取所有股票的数据
        df = self.pro.daily_basic(ts_code='', trade_date=trade_date_str)
        
        if df is None or df.empty:
            return None
        
        return df
        
    except Exception as e:
        error_str = str(e).lower()
        is_rate_limit = any(keyword in error_str for keyword in [
            'rate limit', '429', 'too many requests', 
            '每分钟最多', '访问该接口', '权限的具体详情',
            '请求过于频繁', '访问频率', '请求次数'
        ])
        
        if is_rate_limit:
            self.logger.debug(f"daily_basic速率限制: {trade_date}，跳过本次请求")
            return None
        elif 'permission' in error_str or '权限' in error_str or '积分' in error_str or '2000' in error_str:
            self.logger.debug(f"daily_basic接口权限不足 {trade_date}: {str(e)} (需要至少2000积分)")
            return None
        else:
            self.logger.debug(f"获取daily_basic数据失败 {trade_date}: {str(e)}")
            return None
```

### 4.2 重构主方法

```python
def fetch_and_save_missing_data(self, start_date: str, end_date: str, 
                                 batch_size: int = 50, delay: float = 2.0,
                                 max_stocks: int = None, max_workers: int = 10,
                                 symbols: Optional[List[str]] = None) -> Dict:
    """
    获取并保存缺失的数据（优化：按日期批量获取）
    
    优化策略：
    - 改为按日期循环，而不是按股票循环
    - 对于每个日期，调用一次API获取所有股票的数据
    - 性能提升约2500倍（对于5000只股票，5天数据）
    """
    # 1. 生成日期列表
    # 2. 对于每个日期：
    #    a. 调用 fetch_all_stocks_by_date 获取所有股票数据
    #    b. 调用 fetch_all_stocks_daily_basic_by_date 获取所有股票基本面数据
    #    c. 处理数据并保存到数据库
    # 3. 返回统计结果
```

## 五、性能对比

| 方案 | API调用次数 | 耗时（估算） |
|------|------------|------------|
| **优化前**（按股票循环） | 25000次 | 500分钟（8.3小时） |
| **优化后**（按日期循环） | 10次 | 0.2分钟（12秒） |
| **性能提升** | **2500倍** | **2500倍** |

## 六、注意事项

1. **数据量限制**：单次最大返回6000条数据，如果股票数量超过6000，需要分批处理
2. **速率限制**：每分钟最多500次（基础积分），当前优化后只需要10次，完全满足
3. **兼容性**：保留原有的按股票循环方法，作为兜底方案
