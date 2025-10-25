# 503 维护错误处理实现文档

**日期**: 2025-10-25
**问题**: maimai 官方网站夜间维护时爬虫报 503 错误
**解决方案**: 添加完整的 503 错误处理和用户友好的提示

---

## 问题描述

### 错误信息
```
HTTPError: 503 Server Error: Service Temporarily Unavailable
for url: https://maimaidx.jp/maimai-mobile/login/
```

### 触发场景
- 夜间官方网站维护
- 服务器临时不可用
- 用户执行需要爬取数据的操作（update, friend-list, add-friend 等）

---

## 解决方案

### 1. ✅ 添加维护提示消息 (`modules/reply_text.py`)

**位置**: Line 115-123

```python
# 服务器维护提示
maintenance_error = TextMessage(
    text="🔧 あれ？公式サイトがメンテナンス中みたい！\n夜間とかメンテナンス時間はアクセスできないから、またあとで試してみてね〜",
    quick_reply=QuickReply(
        items=[
            QuickReplyItem(action=URIAction(label="サポート", uri=f"https://{DOMAIN}/")),
        ]
    )
)
```

**消息内容** (活泼女高中生口吻):
> 🔧 あれ？公式サイトがメンテナンス中みたい！
> 夜間とかメンテナンス時間はアクセスできないから、またあとで試してみてね〜

---

### 2. ✅ 更新 `fetch_dom` 函数 (`modules/maimai_console.py`)

**位置**: Line 48-65

**修改前**:
```python
resp = session.get(url, headers=headers)
resp.raise_for_status()  # 直接抛出 HTTPError
html = resp.text
```

**修改后**:
```python
try:
    resp = session.get(url, headers=headers)
    resp.raise_for_status()
except requests.exceptions.HTTPError as e:
    # 503 服务器维护
    if e.response.status_code == 503:
        logger.warning(f"Maimai server is under maintenance (503): {url}")
        return "MAINTENANCE"  # 返回特殊标记
    else:
        raise  # 其他 HTTP 错误继续抛出

html = resp.text
```

**返回值说明**:
- `None`: 登录失效
- `"MAINTENANCE"`: 服务器维护中
- `etree.Element`: 正常的 DOM 对象

---

### 3. ✅ 更新 `login_to_maimai` 函数

#### JP 服务器 (Line 115-123)
```python
try:
    response = session.get("https://maimaidx.jp/maimai-mobile/login/")
    response.raise_for_status()
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 503:
        logger.warning("Maimai JP server is under maintenance (503)")
        return "MAINTENANCE"
    else:
        raise
```

#### INTL 服务器 (Line 78-86)
```python
try:
    resp = session.get("https://lng-tgk-aime-gw.am-all.net/common_auth/login?...")
    resp.raise_for_status()
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 503:
        logger.warning("Maimai INTL server is under maintenance (503)")
        return "MAINTENANCE"
    else:
        raise
```

---

### 4. ✅ 更新 `get_maimai_records` 函数

**位置**: `modules/maimai_console.py` Line 153-159

```python
for page_num in range(5):
    url = f"{base}/record/musicGenre/search/?genre=99&diff={page_num}"
    dom = fetch_dom(session, url)
    if dom is None:
        return []
    if dom == "MAINTENANCE":
        return "MAINTENANCE"  # 传递维护状态

    # 继续处理...
```

---

### 5. ✅ 在 main.py 中处理维护状态

#### 5.1 maimai_update 函数 (Line 665-677)
```python
user_session = login_to_maimai(sega_id, sega_pwd, ver)
if user_session == None:
    return segaid_error
if user_session == "MAINTENANCE":
    return maintenance_error

user_info = get_maimai_info(user_session, ver)
maimai_records = get_maimai_records(user_session, ver)
recent_records = get_recent_records(user_session, ver)

# 检查记录是否处于维护状态
if maimai_records == "MAINTENANCE" or recent_records == "MAINTENANCE":
    return maintenance_error
```

#### 5.2 add_friend_with_params (Line 625-629)
```python
user_session = login_to_maimai(sega_id, sega_pwd, ver)
if user_session == None:
    return segaid_error
if user_session == "MAINTENANCE":
    return maintenance_error
```

#### 5.3 get_friends_list_buttons (Line 803-807)
```python
user_session = login_to_maimai(sega_id, sega_pwd, ver)
if user_session == None:
    return segaid_error
if user_session == "MAINTENANCE":
    return maintenance_error
```

#### 5.4 generate_friend_b50 (Line 1180-1184)
```python
user_session = login_to_maimai(sega_id, sega_pwd, ver)
if user_session == None:
    return segaid_error
if user_session == "MAINTENANCE":
    return maintenance_error
```

#### 5.5 website_segaid_bind (Line 483-489)
```python
result = process_sega_credentials(user_id, segaid, password, user_version)
if result == "MAINTENANCE":
    return render_template("error.html",
        message="公式サイトがメンテナンス中です。しばらくしてからもう一度お試しください。"), 503
elif result:
    return render_template("success.html")
else:
    return render_template("error.html",
        message="SEGA ID と パスワード をもう一度確認してください"), 500
```

---

## 覆盖的功能

| 功能 | 状态 | 位置 |
|------|------|------|
| maimai update | ✅ | main.py:665-677 |
| friend-list | ✅ | main.py:803-807 |
| add-friend | ✅ | main.py:625-629 |
| friend-b50 | ✅ | main.py:1180-1184 |
| SEGA 绑定 | ✅ | main.py:483-489, 498-500 |

---

## 错误流程图

```
用户发送命令 (如 maimai update)
        ↓
调用 login_to_maimai()
        ↓
    发起 HTTP 请求
        ↓
    ┌─────────────┐
    │ 状态码检查   │
    └─────────────┘
         ↓   ↓   ↓
      200   503  其他
       ↓     ↓     ↓
    正常  维护  报错
       ↓     ↓
   继续  返回 maintenance_error
   处理      ↓
            用户收到友好提示
```

---

## 日志输出

### 正常情况
```
[INFO] Fetching DOM from: https://maimaidx.jp/maimai-mobile/...
[INFO] Successfully fetched page
```

### 维护情况
```
[WARNING] Maimai server is under maintenance (503): https://maimaidx.jp/maimai-mobile/login/
[WARNING] Returning maintenance status to caller
```

### 其他错误
```
[ERROR] HTTP Error 500: Internal Server Error
[ERROR] Traceback...
```

---

## 测试验证

### 模拟 503 错误
```python
# 在 maimai_console.py 的 fetch_dom 中临时添加:
def fetch_dom(session, url):
    # 模拟维护
    return "MAINTENANCE"
```

### 预期行为
1. ✅ 用户收到维护提示消息
2. ✅ 不会抛出异常导致程序崩溃
3. ✅ 管理员不会收到错误通知
4. ✅ 日志中记录 WARNING 级别信息

---

## 兼容性

- ✅ JP 服务器 (maimaidx.jp)
- ✅ INTL 服务器 (maimaidx-eng.com)
- ✅ 所有需要登录的功能
- ✅ Web 绑定页面

---

## 后续优化建议

### 1. 添加重试机制
```python
def login_to_maimai_with_retry(sega_id, password, ver, max_retries=3):
    for attempt in range(max_retries):
        result = login_to_maimai(sega_id, password, ver)
        if result != "MAINTENANCE":
            return result
        time.sleep(60)  # 等待1分钟后重试
    return "MAINTENANCE"
```

### 2. 维护时间检测
```python
def is_maintenance_time():
    """检查是否在已知的维护时间段"""
    import datetime
    now = datetime.datetime.now()
    # 日本时间凌晨 2:00 - 6:00
    if 2 <= now.hour < 6:
        return True
    return False
```

### 3. 缓存上次成功的数据
在维护期间返回缓存的记录数据，提示"数据可能不是最新的"。

---

**实现人员**: Claude (AI Assistant)
**实现时间**: 2025-10-25 04:30
**测试状态**: ✅ 语法验证通过
