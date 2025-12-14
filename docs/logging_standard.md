# 日志标准规范

## 日志级别使用标准

### DEBUG
**用途**: 详细的调试信息，帮助开发者追踪程序执行流程

**使用场景**:
- 变量值和中间计算结果
- 循环和条件分支的详细执行情况
- 算法的中间步骤（如图像匹配的候选结果）
- 函数参数和返回值

**示例**:
```python
logger.debug(f"[ImageMatcher] Skip low-quality match: cover={cover_name}, distance={distance}, gap={gap}")
logger.debug(f"[Cache] Processing level {level}, songs_count={len(songs)}")
```

### INFO
**用途**: 正常的业务操作信息，记录系统的重要状态变化

**使用场景**:
- 用户请求和操作（登录、查询、更新）
- 任务开始和完成
- 系统初始化和配置加载
- 资源创建和释放
- API 调用记录

**示例**:
```python
logger.info(f"[User] Login successful: user_id={user_id}, server={server}")
logger.info(f"[Cache] ✓ Generated cache for level {level}: {count} songs")
logger.info(f"[API] Request permission: token={token_id}, target_user={user_id}")
```

### WARNING
**用途**: 需要注意但不影响核心功能的情况

**使用场景**:
- 重试操作
- 降级处理（如备用方案）
- 资源不足但可继续
- 服务器维护模式
- 配置缺失使用默认值
- 速率限制触发

**示例**:
```python
logger.warning(f"[Maimai] ⚠ Server maintenance mode (503): {url}")
logger.warning(f"[RateLimit] ⚠ Rate limit exceeded: user_id={user_id}, task={task_type}")
logger.warning(f"[User] ⚠ User not found: user_id={user_id} (may have blocked bot)")
```

### ERROR
**用途**: 功能失败但程序可以继续运行

**使用场景**:
- API 调用失败
- 数据解析错误
- 文件读写失败
- 网络请求超时
- 图片加载失败
- 数据库操作失败

**示例**:
```python
logger.error(f"[ImageCache] ✗ Failed to download cover: url={url}, error={e}")
logger.error(f"[Maimai] ✗ Error fetching data: url={url}, error={e}")
logger.error(f"[API] ✗ User registration failed: user_id={user_id}, error={e}", exc_info=True)
```

**注意**: 重要错误添加 `exc_info=True` 以包含完整堆栈跟踪

### CRITICAL
**用途**: 严重错误，可能导致程序无法继续运行

**使用场景**:
- 数据库连接完全失败
- 关键配置文件损坏
- 系统资源耗尽

**示例**:
```python
logger.critical(f"[Database] ✗ Database connection lost, shutting down")
```

## 日志格式规范

### 1. 模块标识
所有日志应包含模块标识，格式：`[ModuleName]`

```python
logger.info(f"[User] Operation description")
logger.error(f"[ImageMatcher] Error description")
logger.warning(f"[Cache] Warning description")
```

### 2. 状态符号
使用 Unicode 符号标识操作状态：

- `✓` - 成功
- `✗` - 失败
- `→` - 进行中 / 阶段标识
- `⚠` - 警告

```python
logger.info(f"[Cache] ✓ Cache generated successfully")
logger.error(f"[API] ✗ Request failed")
logger.info(f"[Process] → Phase 1: Data loading")
logger.warning(f"[Server] ⚠ Maintenance mode detected")
```

### 3. 参数格式
重要参数使用键值对形式，便于搜索和分析：

```python
# 推荐
logger.info(f"[User] Login: user_id={user_id}, server={server}, status=success")
logger.error(f"[API] Failed: endpoint={endpoint}, code={status_code}, error={error}")

# 不推荐
logger.info(f"User {user_id} logged in to {server}")
logger.error(f"API request to {endpoint} failed with {status_code}")
```

### 4. 分隔符使用
使用分隔符标识重要的系统操作边界：

```python
logger.info("=" * 60)
logger.info("[System] Starting system check")
logger.info("=" * 60)
```

## 模块特定规范

### Image Matching
```python
logger.info("=" * 60)
logger.info("[ImageMatcher] → Starting recognition (hybrid strategy)")
logger.info("[ImageMatcher] → Phase 1: Hash matching")
logger.debug(f"[ImageMatcher] LSH candidates: count={len(candidates)}")
logger.info(f"[ImageMatcher] ✓ Match found: cover={cover_name}, confidence={confidence:.2f}%")
logger.warning("[ImageMatcher] ✗ No matching cover found")
logger.info("=" * 60)
```

### User Operations
```python
logger.info(f"[User] Login attempt: user_id={user_id}, server={server}")
logger.info(f"[User] ✓ Data updated: user_id={user_id}, records={count}")
logger.warning(f"[User] ⚠ User not found: user_id={user_id}")
logger.error(f"[User] ✗ Update failed: user_id={user_id}, error={e}")
```

### API Requests
```python
logger.info(f"[API] Request: endpoint={endpoint}, token={token_id}, user={user_id}")
logger.info(f"[API] ✓ Success: user_id={user_id}, action={action}")
logger.error(f"[API] ✗ Failed: endpoint={endpoint}, code={code}, error={error}")
```

### Cache Operations
```python
logger.info(f"[Cache] → Generating cache: level={level}, server={server}")
logger.info(f"[Cache] ✓ Cache generated: level={level}, songs={count}")
logger.warning(f"[Cache] ⚠ No songs found: level={level}")
logger.error(f"[Cache] ✗ Generation failed: level={level}, error={e}")
```

## 错误处理最佳实践

### 1. 异常捕获
```python
try:
    result = risky_operation()
    logger.info(f"[Module] ✓ Operation successful: result={result}")
except SpecificException as e:
    logger.error(f"[Module] ✗ Operation failed: error={e}", exc_info=True)
    # 处理错误
```

### 2. 重试逻辑
```python
for attempt in range(max_retries):
    try:
        result = operation()
        logger.info(f"[Module] ✓ Success on attempt {attempt + 1}")
        break
    except Exception as e:
        if attempt < max_retries - 1:
            logger.warning(f"[Module] ⚠ Retry {attempt + 1}/{max_retries}: error={e}")
        else:
            logger.error(f"[Module] ✗ All retries failed: attempts={max_retries}, error={e}")
```

### 3. 条件日志
```python
if important_condition:
    logger.info(f"[Module] Important event occurred: details={details}")
else:
    logger.debug(f"[Module] Normal flow: details={details}")
```

## 性能考虑

1. **避免在循环中使用 INFO 级别**：大量数据处理时使用 DEBUG
2. **延迟字符串格式化**：使用 f-string 或 % 格式化（Python 会自动优化）
3. **敏感信息脱敏**：密码、token 等敏感信息不要完整记录

```python
# 好
logger.debug(f"[Auth] Token: {token[:8]}...")

# 不好
logger.info(f"[Auth] Full token: {token}")
```

## 日志审查清单

更新日志时检查：
- [ ] 日志级别是否正确
- [ ] 是否包含模块标识 `[ModuleName]`
- [ ] 重要操作是否有状态符号（✓✗→⚠）
- [ ] 参数是否使用键值对格式
- [ ] ERROR 级别是否需要 `exc_info=True`
- [ ] 是否包含足够的上下文信息
- [ ] 是否避免了敏感信息泄露
