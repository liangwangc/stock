"""
机器学习特征工程模块
用于特征选择、特征变换、特征标准化等
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger

logger = get_logger(__name__)


class MLFeatureEngineering:
    """机器学习特征工程"""
    
    def __init__(self):
        self.logger = logger
        self.feature_columns = None  # 特征列名列表
        self.scaler = None  # 特征标准化器
    
    def prepare_features(self, df: pd.DataFrame, 
                        label_column: str = 'label_up',
                        exclude_columns: Optional[List[str]] = None,
                        filter_by_completeness: bool = True,
                        min_completeness: float = 0.5,
                        critical_fields: Optional[List[str]] = None) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
        """
        准备特征和标签（优化版：支持根据数据完整性过滤字段）
        
        Args:
            df: 数据DataFrame
            label_column: 标签列名
            exclude_columns: 需要排除的列（如symbol、target_date等）
            filter_by_completeness: 是否根据数据完整性过滤字段（默认True）
            min_completeness: 最低完整率阈值（低于此值的字段会被过滤，除非是关键字段）
            critical_fields: 关键字段列表（这些字段即使完整率低也会保留）
        
        Returns:
            (X, y, feature_names)
        """
        if df.empty:
            return pd.DataFrame(), pd.Series(), []
        
        # 机构级增强因子：横截面排名、指数、相对强弱（无未来函数，新增列自动参与后续 feature_columns）
        df = self._add_enhanced_factors(df)
        
        # 默认排除的列（元数据列和标签列，不应该作为特征）
        default_exclude = ['symbol', 'target_date', 'future_date', 'prediction_date', 
                          'label_direction', 'label_change_pct', 'label_up', 'label_up_probability',
                          'deviation_pct', 'absolute_deviation_pct', 'deviation_price']
        
        if exclude_columns:
            default_exclude.extend(exclude_columns)
        
        # 排除标签列和元数据列
        exclude_set = set(default_exclude)
        feature_columns = [col for col in df.columns if col not in exclude_set]
        
        # 根据数据完整性过滤字段（如果启用）
        if filter_by_completeness and len(df) > 0:
            if critical_fields is None:
                critical_fields = ['close_price', 'open_price', 'high_price', 'low_price', 'volume']
            
            filtered_columns = self._filter_fields_by_completeness(
                df, feature_columns, min_completeness, critical_fields
            )
            
            if len(filtered_columns) < len(feature_columns):
                removed_count = len(feature_columns) - len(filtered_columns)
                self.logger.info(
                    f"根据数据完整性过滤字段：从 {len(feature_columns)} 个特征中移除了 {removed_count} 个低质量字段，"
                    f"保留 {len(filtered_columns)} 个特征"
                )
                feature_columns = filtered_columns
        
        # 提取特征和标签
        X = df[feature_columns].copy()
        y = df[label_column].copy() if label_column in df.columns else pd.Series()
        
        # 处理缺失值
        X = self._handle_missing_values(X)
        
        # 处理无穷值
        X = self._handle_inf_values(X)
        
        # 性能优化：最后检查并移除object类型列（确保没有遗漏）
        # 虽然已经排除了元数据列，但可能还有其他object类型列（如字符串类型）
        object_cols = X.select_dtypes(include=['object']).columns.tolist()
        if object_cols:
            self.logger.warning(f"发现object类型列，将被排除: {object_cols}")
            X = X.drop(columns=object_cols)
            # 更新特征列名列表
            feature_columns = [col for col in feature_columns if col not in object_cols]
        
        # 记录特征列名
        self.feature_columns = feature_columns
        
        self.logger.info(f"准备特征完成：特征数 {len(feature_columns)}，样本数 {len(X)}")
        
        return X, y, feature_columns
    
    def _filter_fields_by_completeness(self, 
                                      df: pd.DataFrame,
                                      feature_columns: List[str],
                                      min_completeness: float = 0.5,
                                      critical_fields: Optional[List[str]] = None) -> List[str]:
        """
        根据数据完整性过滤字段（性能优化版：批量计算完整率）
        
        Args:
            df: 数据DataFrame
            feature_columns: 候选特征列名列表
            min_completeness: 最低完整率阈值
            critical_fields: 关键字段列表（这些字段即使完整率低也会保留）
        
        Returns:
            过滤后的特征列名列表
        """
        if critical_fields is None:
            critical_fields = []
        
        if len(df) == 0:
            return feature_columns
        
        critical_set = set(critical_fields)
        filtered_columns = []
        removed_fields = []
        
        # 性能优化：批量计算所有字段的完整率（避免逐列计算）
        feature_df = df[feature_columns]
        missing_counts = feature_df.isna().sum()  # 批量计算缺失值数量
        completeness_series = 1.0 - (missing_counts / len(df))  # 批量计算完整率
        
        for col in feature_columns:
            completeness = completeness_series[col]
            
            # 关键字段始终保留
            if col in critical_set:
                filtered_columns.append(col)
            # 完整率>=阈值的字段保留
            elif completeness >= min_completeness:
                filtered_columns.append(col)
            # 完整率<阈值的字段移除
            else:
                removed_fields.append({
                    'field': col,
                    'completeness': completeness
                })
        
        # 记录移除的字段（只记录前10个，避免日志过长）
        if removed_fields:
            removed_info = ', '.join([
                f"{f['field']}({f['completeness']:.1%})" 
                for f in removed_fields[:10]
            ])
            if len(removed_fields) > 10:
                removed_info += f" 等{len(removed_fields)}个字段"
            self.logger.debug(f"移除低质量字段: {removed_info}")
        
        return filtered_columns
    
    def _handle_missing_values(self, X: pd.DataFrame, method: str = 'smart_fill') -> pd.DataFrame:
        """
        处理缺失值（性能优化版：批量处理）
        
        Args:
            X: 特征DataFrame
            method: 处理方法
                - 'smart_fill': 智能填充（根据字段类型选择策略）
                - 'fill': 简单填充（用0填充）
                - 'drop': 删除缺失值
        
        Returns:
            处理后的DataFrame
        """
        if method == 'smart_fill':
            # 性能优化：批量识别需要处理的列
            cols_with_na = X.columns[X.isna().any()].tolist()
            if not cols_with_na:
                return X  # 没有缺失值，直接返回
            
            # 定义字段类型
            technical_fields = ['ma5', 'ma10', 'ma20', 'ma60', 'rsi', 'macd', 'macd_signal', 'macd_hist', 'x2']
            technical_rsi_x2 = ['rsi', 'x2']
            valuation_fields = ['pe_ratio', 'pb_ratio']
            capital_fields = ['main_net_inflow', 'super_large_inflow', 'large_inflow', 
                             'medium_inflow', 'small_inflow', 'margin_balance', 
                             'short_balance', 'margin_ratio']
            
            # 批量处理技术指标字段（性能优化：批量操作）
            technical_cols = [col for col in cols_with_na if col in technical_fields]
            if technical_cols:
                try:
                    # 使用ffill()方法（新版本pandas，更高效）
                    X[technical_cols] = X[technical_cols].ffill().bfill()
                    # RSI和X2使用50.0作为默认值
                    rsi_x2_cols = [col for col in technical_cols if col in technical_rsi_x2]
                    if rsi_x2_cols:
                        X[rsi_x2_cols] = X[rsi_x2_cols].fillna(50.0)
                    # 其他技术指标使用0.0
                    other_technical_cols = [col for col in technical_cols if col not in technical_rsi_x2]
                    if other_technical_cols:
                        X[other_technical_cols] = X[other_technical_cols].fillna(0.0)
                except AttributeError:
                    # 兼容旧版本pandas
                    for col in technical_cols:
                        X[col] = X[col].fillna(method='ffill').fillna(method='bfill')
                        if col in technical_rsi_x2:
                            X[col] = X[col].fillna(50.0)
                        else:
                            X[col] = X[col].fillna(0.0)
            
            # 批量处理估值指标字段
            valuation_cols = [col for col in cols_with_na if col in valuation_fields]
            if valuation_cols:
                for col in valuation_cols:
                    non_zero_values = X[col][X[col] > 0]
                    if len(non_zero_values) > 0:
                        median_val = non_zero_values.median()
                        X[col] = X[col].fillna(median_val)
                    else:
                        X[col] = X[col].fillna(0.0)
            
            # 批量处理资金流向和融资融券字段（性能优化：批量填充）
            capital_cols = [col for col in cols_with_na if col in capital_fields]
            if capital_cols:
                X[capital_cols] = X[capital_cols].fillna(0.0)
            
            # 处理其他数值字段（批量处理）
            numeric_cols = [col for col in cols_with_na 
                          if col not in technical_fields + valuation_fields + capital_fields
                          and X[col].dtype in [np.int64, np.float64, np.int32, np.float32]]
            if numeric_cols:
                X[numeric_cols] = X[numeric_cols].fillna(0.0)
            
            # 处理非数值字段
            non_numeric_cols = [col for col in cols_with_na 
                               if col not in technical_fields + valuation_fields + capital_fields + numeric_cols]
            if non_numeric_cols:
                try:
                    X[non_numeric_cols] = X[non_numeric_cols].ffill().fillna(0)
                except AttributeError:
                    for col in non_numeric_cols:
                        X[col] = X[col].fillna(method='ffill').fillna(0)
        
        elif method == 'fill':
            # 简单填充：所有数值列用0填充
            numeric_columns = X.select_dtypes(include=[np.number]).columns
            X[numeric_columns] = X[numeric_columns].fillna(0)
            
            # 非数值列：用前值填充
            non_numeric_columns = X.select_dtypes(exclude=[np.number]).columns
            X[non_numeric_columns] = X[non_numeric_columns].fillna(method='ffill').fillna(0)
        
        elif method == 'drop':
            X = X.dropna()
        
        return X
    
    def _handle_inf_values(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        处理无穷值
        
        Args:
            X: 特征DataFrame
        
        Returns:
            处理后的DataFrame
        """
        # 将无穷值替换为NaN，然后用0填充
        X = X.replace([np.inf, -np.inf], np.nan)
        X = X.fillna(0)
        
        return X
    
    def _add_enhanced_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        机构级增强因子：横截面排名、指数收益/波动、相对强弱。
        无未来函数（排名用当日截面，指数用 shift(1) 后 merge）。
        新增列自动处理 NaN（填 0 或 0.5）。
        """
        if df.empty or 'target_date' not in df.columns:
            return df
        try:
            # 1. 横截面排名（按 target_date 分组，pct=True 得 [0,1]）
            date_col = 'target_date'
            for col in ['volume', 'turnover_rate', 'amount', 'return_5d', 'return_20d']:
                if col not in df.columns:
                    continue
                rank_col = f'{col}_rank_all'
                df[rank_col] = df.groupby(date_col)[col].rank(pct=True)
                df[rank_col] = df[rank_col].fillna(0.5)
            
            # 2. 指数因子：从 market_indices 取沪深300，算收益/波动后 shift(1) 再 merge
            try:
                from utils.db_connection import DatabaseConnection
                db = DatabaseConnection()
                # 取 df 日期范围并外扩约 65 天以便算 20d/60d 指标
                dates = pd.to_datetime(df[date_col].dropna().astype(str))
                d_min, d_max = dates.min(), dates.max()
                start = (d_min - pd.Timedelta(days=65)).strftime('%Y-%m-%d')
                end = d_max.strftime('%Y-%m-%d')
                # 优先沪深300，其次上证指数，单指数保证每交易日一行
                rows = db.execute_query(
                    "SELECT trade_date, close_price FROM market_indices "
                    "WHERE index_code = %s AND trade_date >= %s AND trade_date <= %s ORDER BY trade_date",
                    ('sh000300', start, end)
                )
                if not rows:
                    rows = db.execute_query(
                        "SELECT trade_date, close_price FROM market_indices "
                        "WHERE index_code = %s AND trade_date >= %s AND trade_date <= %s ORDER BY trade_date",
                        ('sh000001', start, end)
                    )
                if rows:
                    idx_df = pd.DataFrame(rows)
                    idx_df['trade_date'] = pd.to_datetime(idx_df['trade_date']).dt.strftime('%Y-%m-%d')
                    idx_df = idx_df.sort_values('trade_date').drop_duplicates(subset=['trade_date'], keep='last')
                    idx_df['close_price'] = pd.to_numeric(idx_df['close_price'], errors='coerce').ffill()
                    idx_df['index_return_1d'] = idx_df['close_price'].pct_change(1).shift(1)
                    idx_df['index_return_5d'] = idx_df['close_price'].pct_change(5).shift(1)
                    idx_df['index_return_20d'] = idx_df['close_price'].pct_change(20).shift(1)
                    idx_df['index_volatility_20d'] = idx_df['close_price'].pct_change().rolling(20).std().shift(1)
                    idx_df = idx_df[['trade_date', 'index_return_1d', 'index_return_5d', 'index_return_20d', 'index_volatility_20d']]
                    df['_dt_key'] = pd.to_datetime(df[date_col]).dt.strftime('%Y-%m-%d')
                    df = df.merge(idx_df, left_on='_dt_key', right_on='trade_date', how='left')
                    df = df.drop(columns=['_dt_key', 'trade_date'], errors='ignore')
                    for c in ['index_return_1d', 'index_return_5d', 'index_return_20d', 'index_volatility_20d']:
                        if c in df.columns:
                            df[c] = df[c].fillna(0.0)
                    # 3. 相对强弱 = 个股 return_* - 指数 return_*
                    for period in ['5d', '20d', '60d']:
                        stock_col = f'return_{period}'
                        index_col = f'index_return_{period}'
                        if stock_col in df.columns and index_col in df.columns:
                            df[f'relative_strength_{period}'] = (df[stock_col] - df[index_col]).fillna(0.0)
                        elif stock_col in df.columns:
                            df[f'relative_strength_{period}'] = df[stock_col].fillna(0.0)
                else:
                    for c in ['index_return_1d', 'index_return_5d', 'index_return_20d', 'index_volatility_20d']:
                        df[c] = 0.0
                    for period in ['5d', '20d', '60d']:
                        if f'return_{period}' in df.columns:
                            df[f'relative_strength_{period}'] = df[f'return_{period}'].fillna(0.0)
            except Exception as e:
                self.logger.debug(f"指数/相对强弱因子加载失败，仅使用截面排名: {e}")
                for c in ['index_return_1d', 'index_return_5d', 'index_return_20d', 'index_volatility_20d']:
                    if c not in df.columns:
                        df[c] = 0.0
                for period in ['5d', '20d', '60d']:
                    if f'return_{period}' in df.columns and f'relative_strength_{period}' not in df.columns:
                        df[f'relative_strength_{period}'] = df[f'return_{period}'].fillna(0.0)
            
            # 4. 新增列统一 NaN 填 0（排名列已在上面填 0.5）
            new_cols = [c for c in df.columns if c.endswith('_rank_all') or c.startswith('index_') or c.startswith('relative_strength_')]
            for c in new_cols:
                if c in df.columns and c not in ['volume_rank_all', 'turnover_rank_all', 'amount_rank_all', 'return_5d_rank_all', 'return_20d_rank_all']:
                    df[c] = df[c].fillna(0.0)
                elif c in df.columns and c.endswith('_rank_all'):
                    df[c] = df[c].fillna(0.5)
        except Exception as e:
            self.logger.warning(f"增强因子计算异常，跳过: {e}")
        return df
    
    def normalize_features(self, X_train: pd.DataFrame, 
                          X_val: Optional[pd.DataFrame] = None,
                          X_test: Optional[pd.DataFrame] = None,
                          method: str = 'standard') -> Tuple[pd.DataFrame, Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        """
        特征标准化/归一化
        
        Args:
            X_train: 训练集特征
            X_val: 验证集特征（可选）
            X_test: 测试集特征（可选）
            method: 标准化方法（standard=标准化，minmax=最小最大归一化）
        
        Returns:
            (X_train_normalized, X_val_normalized, X_test_normalized)
        """
        from sklearn.preprocessing import StandardScaler, MinMaxScaler
        
        if method == 'standard':
            scaler = StandardScaler()
        elif method == 'minmax':
            scaler = MinMaxScaler()
        else:
            self.logger.warning(f"未知的标准化方法 {method}，使用标准化")
            scaler = StandardScaler()
        
        # 只在训练集上拟合
        X_train_normalized = pd.DataFrame(
            scaler.fit_transform(X_train),
            columns=X_train.columns,
            index=X_train.index
        )
        
        # 保存scaler供后续使用
        self.scaler = scaler
        
        # 转换验证集和测试集
        X_val_normalized = None
        if X_val is not None and not X_val.empty:
            X_val_normalized = pd.DataFrame(
                scaler.transform(X_val),
                columns=X_val.columns,
                index=X_val.index
            )
        
        X_test_normalized = None
        if X_test is not None and not X_test.empty:
            X_test_normalized = pd.DataFrame(
                scaler.transform(X_test),
                columns=X_test.columns,
                index=X_test.index
            )
        
        self.logger.info(f"特征标准化完成：方法={method}")
        
        return X_train_normalized, X_val_normalized, X_test_normalized
    
    def select_features(self, X: pd.DataFrame, y: pd.Series, 
                       method: str = 'importance',
                       n_features: int = 50) -> List[str]:
        """
        特征选择
        
        Args:
            X: 特征DataFrame
            y: 标签Series
            method: 选择方法（importance=重要性，correlation=相关性）
            n_features: 选择的特征数量
        
        Returns:
            选择的特征列名列表
        """
        if method == 'importance':
            # 使用随机森林计算特征重要性
            from sklearn.ensemble import RandomForestClassifier
            
            # 检查并移除object类型列（随机森林不支持）
            object_cols = X.select_dtypes(include=['object']).columns.tolist()
            if object_cols:
                self.logger.warning(f"特征选择：发现object类型列，将被排除: {object_cols}")
                X = X.drop(columns=object_cols).copy()
            
            rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
            rf.fit(X, y)
            
            # 获取特征重要性
            importances = rf.feature_importances_
            feature_importance = list(zip(X.columns, importances))
            feature_importance.sort(key=lambda x: x[1], reverse=True)
            
            # 选择前n_features个特征
            selected_features = [feat[0] for feat in feature_importance[:n_features]]
            
            self.logger.info(f"特征选择完成：从 {len(X.columns)} 个特征中选择 {len(selected_features)} 个")
            
            return selected_features
        
        elif method == 'correlation':
            # 使用相关性选择特征
            correlations = X.corrwith(y).abs().sort_values(ascending=False)
            selected_features = correlations.head(n_features).index.tolist()
            
            self.logger.info(f"特征选择完成：从 {len(X.columns)} 个特征中选择 {len(selected_features)} 个")
            
            return selected_features
        
        else:
            self.logger.warning(f"未知的特征选择方法 {method}，返回所有特征")
            return X.columns.tolist()
    
    def get_feature_importance(self, model, feature_names: List[str]) -> Dict[str, float]:
        """
        获取特征重要性
        
        Args:
            model: 训练好的模型（XGBoost、LightGBM等）
            feature_names: 特征名称列表
        
        Returns:
            特征重要性字典 {feature_name: importance_score}
        """
        try:
            if hasattr(model, 'feature_importances_'):
                # scikit-learn模型
                importances = model.feature_importances_
            elif hasattr(model, 'get_feature_importance'):
                # LightGBM sklearn API
                importances = model.get_feature_importance()
            elif hasattr(model, 'feature_importance'):
                # LightGBM Booster (lgb.train 返回)
                importances = model.feature_importance(importance_type='gain')
            elif hasattr(model, 'get_score'):
                # XGBoost模型（需要特殊处理）
                importances = []
                for i, feat_name in enumerate(feature_names):
                    try:
                        importance = model.get_score(importance_type='gain').get(f'f{i}', 0)
                        importances.append(importance)
                    except:
                        importances.append(0)
            else:
                self.logger.warning("模型不支持特征重要性提取")
                return {}
            
            # 构建特征重要性字典
            feature_importance = {}
            for i, feat_name in enumerate(feature_names):
                if i < len(importances):
                    feature_importance[feat_name] = float(importances[i])
            
            # 归一化（使总和为1）
            total = sum(feature_importance.values())
            if total > 0:
                feature_importance = {k: v / total for k, v in feature_importance.items()}
            
            return feature_importance
            
        except Exception as e:
            self.logger.error(f"获取特征重要性失败: {str(e)}")
            return {}
