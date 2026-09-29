# jietng — Python SDK

[`pip install jietng`](https://pypi.org/project/jietng/) — Python 客户端，封装 [JiETNG](https://jietng.matsuk1.com) 舞萌DX 查分器的 HTTP API。

支持同步 / 异步两套客户端、覆盖 v2 开发者端点和 Import Token 上传端点（用户 / 权限 / 同步 / 搜歌 / 成绩图 / 导出 / 导入 …）、类型注解齐全。

## 安装

```bash
pip install jietng
```

需要 Python ≥ 3.8、httpx ≥ 0.25。

## 获取 Token

JiETNG API 通过 Bearer Token 鉴权。申请方式见 <https://jietng.matsuk1.com/developer-api> —— 发邮件到 `matsuk1@proton.me` 索取。

## 快速开始

### 同步

```python
from jietng import jietngClient

with jietngClient(token="your_token") as client:
    users = client.users.list()
    print(users["count"], "registered users")

    # 取 B50 成绩图（返回 PNG bytes）
    png = client.images.records("U1234567890", command="b50")
    with open("b50.png", "wb") as f:
        f.write(png)

    # 流式同步：先收到 accepted，结束时收到 completed / failed
    for event in client.users.sync_stream("U1234567890"):
        print(event["event"], event.get("message"))

    # 导出成绩为 JSON / XML，文件名由服务端推荐（含玩家名 + 时间戳）
    path = client.exports.save("U1234567890", fmt="json")
    print("exported to", path)

    # OCR 成绩图；只有完整成绩成功匹配、校验时才返回
    with open("result.jpg", "rb") as f:
        image = f.read()
    result = client.score_recognition.recognize(image, ver="jp")
    print(result["song"]["id"], result["score"]["achievement"])

    # 获取完整 DXData；ver 支持 "jp"（默认）或 "intl"
    dxdata = client.dxdata.get(ver="intl")
    print(len(dxdata["songs"]), "songs")

    # 也可以直接取得排版完成的 OCR 结果图片
    png = client.score_recognition.recognize_image(image, ver="jp")
    with open("ocr-result.png", "wb") as f:
        f.write(png)
```

### 异步

```python
import asyncio
from jietng import AsyncjietngClient

async def main():
    async with AsyncjietngClient(token="your_token") as client:
        print(await client.songs.search("PANDORA", user_id="U1234567890", max_results=3))
        async for event in client.users.sync_stream("U1234567890"):
            print("sync event:", event["event"])

        png = await client.images.plate("U1234567890", title="真神")
        with open("plate.png", "wb") as f:
            f.write(png)

        with open("result.jpg", "rb") as f:
            image = f.read()
        result = await client.score_recognition.recognize(image, ver="jp")
        print(result["song"]["title"])

        dxdata = await client.dxdata.get(ver="intl")
        print(len(dxdata["songs"]), "songs")

        png = await client.score_recognition.recognize_image(image, ver="jp")
        with open("ocr-result.png", "wb") as f:
            f.write(png)

asyncio.run(main())
```

## 资源总览

| 命名空间 | 主要方法 |
|---|---|
| `client.users` | `list / get / create / delete / sync_stream / bind / update_bind / get_bind_url / get_rebind_url / get_settings_url` |
| `client.permissions` | `request / list_requests / accept / reject / revoke / revoke_self` |
| `client.songs` | `search / info` |
| `client.versions` | `list` |
| `client.dxdata` | `get` |
| `client.images` | `user_song / records / plate / achievement` |
| `client.exports` | `download / save` |
| `client.imports` | `records` |
| `client.score_recognition` | `recognize / recognize_image` |

所有方法的形参 / 返回结构与 [JiETNG API 文档](https://jietng.matsuk1.com/developer-api) 一一对应。

## 错误处理

所有 HTTP 非 2xx 状态都会抛 `APIError` 子类。可以按需 catch 具体类型：

```python
from jietng import jietngClient, NotFoundError, PermissionDeniedError, RateLimitedError, QueueFullError

try:
    png = client.images.records("U_unknown", command="b50")
except NotFoundError:
    print("user has no records yet")
except PermissionDeniedError:
    print("your token doesn't have access to this user")
except RateLimitedError:
    print("slow down")
except QueueFullError:
    print("server task queue is full, retry later")
```

完整异常层级：

```
jietngError                  # 基类
└─ APIError                  # 任意 HTTP 非 2xx
   ├─ ValidationError        # 400 / 413 / 415 / 422
   ├─ AuthenticationError    # 401
   ├─ PermissionDeniedError  # 403
   ├─ NotFoundError          # 404
   ├─ RateLimitedError       # 429
   ├─ ServerError            # 500
   └─ QueueFullError         # 503
```

每个异常实例都带 `status_code` / `error` / `message` / `payload` 字段，方便排查。

## 自定义

```python
client = jietngClient(
    token="your_token",
    base_url="https://your-self-hosted.example.com/api/v2",   # 自托管时
    timeout=60.0,
    extra_headers={"X-App-Name": "MyBot"},
)
```

## 许可

MIT。代码：<https://github.com/Matsuk1/JiETNG/tree/main/client>
