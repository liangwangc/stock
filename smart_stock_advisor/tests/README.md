# 测试文档

## 测试结构

```
tests/
├── __init__.py
├── conftest.py           # pytest配置和fixtures
├── test_rate_limiter.py  # API限流器测试
├── test_data_quality.py  # 数据质量检查器测试
├── test_audit_log.py     # 操作审计日志测试
├── test_system_monitor.py # 系统监控器测试
└── test_automated_backtest.py # 自动化回测测试
```

## 运行测试

### 运行所有测试

```bash
pytest
```

### 运行特定测试文件

```bash
pytest tests/test_rate_limiter.py
```

### 运行特定测试类

```bash
pytest tests/test_rate_limiter.py::TestRateLimiter
```

### 运行特定测试函数

```bash
pytest tests/test_rate_limiter.py::TestRateLimiter::test_check_rate_limit_allowed
```

### 查看测试覆盖率

```bash
pytest --cov=utils --cov-report=html
```

测试覆盖率报告将生成在 `htmlcov/index.html`

### 运行带标记的测试

```bash
# 只运行单元测试
pytest -m unit

# 排除需要数据库的测试
pytest -m "not database"
```

## 测试标记

- `@pytest.mark.unit`: 单元测试
- `@pytest.mark.integration`: 集成测试
- `@pytest.mark.slow`: 慢速测试
- `@pytest.mark.database`: 需要数据库的测试

## 注意事项

1. **数据库测试**: 默认测试使用模拟数据库，不连接真实数据库。需要数据库的测试应该使用 `@pytest.mark.database` 标记。

2. **Mock**: 使用 `unittest.mock` 或 `pytest-mock` 来模拟外部依赖。

3. **Fixtures**: 常用的测试配置放在 `conftest.py` 中作为fixtures。

4. **覆盖率**: 目标覆盖率达到80%以上。

## 测试最佳实践

1. 每个测试函数应该只测试一个功能点
2. 测试名称应该清晰描述测试内容
3. 使用setup和teardown来准备和清理测试环境
4. 使用Mock来隔离外部依赖
5. 测试应该快速运行，慢速测试应该标记为 `@pytest.mark.slow`
