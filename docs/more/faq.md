# 常见问题

关于使用 JiETNG 的常见问题和解答。

## 入门

### 什么是 JiETNG？

JiETNG 是一个面向 『maimai でらっくす』 玩家的 LINE 机器人，提供以下功能：
- 成绩追踪和分析
- Best 50 图表生成
- 曲目搜索和发现
- 牌子进度追踪
- 好友排名对比
- 还有更多！

### JiETNG 需要付费吗？

不！JiETNG 完全**免费**使用。但是，您可以通过[捐赠](/more/support)支持开发。


### 我需要 SEGA ID 吗？

是的，要使用大多数功能，您需要：
- SEGA ID 账户
- 访问 maimai NET（在线成绩追踪）
- 将账户绑定到机器人

请参阅[账号绑定](/guide/binding)了解设置说明。

## 账号绑定

### 如何绑定我的 SEGA ID？

1. 向机器人发送 `bind`
2. 点击绑定 URL 按钮
3. 在 Web 表单上输入您的 SEGA ID 和密码
4. 选择您的服务器版本
5. 确认绑定

**重要**: 不要在聊天中输入您的凭据。绑定仅通过 Web 完成。

详情请参阅[账号绑定指南](/guide/binding)。

### 我可以在聊天中输入 SEGA 凭据吗？

**不可以。** 出于安全原因，JiETNG 仅使用基于 Web 的绑定。切勿在聊天中输入您的密码。

### 绑定链接过期了，怎么办？

绑定令牌会在 **2 分钟后**过期。只需再次发送 `bind` 获取新链接。

## 使用功能

### 如何生成我的 Best 50？

发送以下任一命令：
- `b50`
- `best50`
- `ベスト50`

首先确保您已绑定 SEGA ID！

详情请参阅 [成绩命令](/commands/record)。

### 我应该多久更新一次成绩？

每次游玩后更新：
```
maimai update
```

这会从 maimai NET 获取您的最新成绩。

### 成绩更新需要多长时间？

通常 20 秒到 30 秒，取决于：
- 您游玩的曲目数量
- SEGA 服务器响应时间
- 队列等待时间（如果有很多用户正在更新）

### 为什么我的最新成绩没有显示？

1. **您更新了吗？** 先运行 `maimai update`
2. **检查 maimai NET**: 您的成绩在官方网站上吗？
3. **等待时间**: 成绩可能需要几分钟才能出现在 maimai NET 上
4. **网络问题**: SEGA 服务器可能很慢

## 功能和命令

### 什么是好友系统？

添加其他 JiETNG 用户为好友以：
- 对比 Best 50 图表
- 查看彼此的成绩
- 建立您的 maimai 社区

详情请参阅[好友系统](/features/friends)。

## 故障排除

### "您还没有绑定 SEGA ID"

**解决方案**: 使用 `bind` 命令绑定您的账户。

请参阅[账号绑定](/guide/binding)。

### "更新成绩失败"

**可能原因**:
- SEGA 服务器宕机
- SEGA 凭据错误
- 网络超时
- maimai NET 维护

**解决方案**:
- 等待几分钟后重试
- 通过直接登录 maimai NET 验证凭据
- 检查 SEGA 维护公告
- 如果凭据已更改，重新绑定

### "曲目未找到"

**原因**:
- 曲名拼写错误
- 『maimai でらっくす』 中不存在该曲目
- 版本错误（jp vs intl）

**解决方案**:
- 尝试不同的关键词
- 检查拼写
- 在 [maimai wiki](https://maimai.fandom.com/) 搜索
- 尝试日语名称而不是英语名称（反之亦然）

### 命令不起作用

**排查步骤**:
1. 检查拼写和语法
2. 验证您已绑定（`get me`）
3. 更新成绩（`maimai update`）
4. 查看[命令参考](/commands/basic)
5. 先尝试简单命令（例如，在 `b50 -lv 14` 之前尝试 `b50`）


## 社区与支持

### 如何报告 bug？

1. 查看 [FAQ](/more/faq)（本页）
2. 搜索 [GitHub Issues](https://github.com/Matsuk1/JiETNG/issues)
3. 如果未找到，创建新 issue：
   - bug 描述
   - 复现步骤
   - 截图（如适用）
   - 您的版本（日本版/国际版）

### 如何支持项目？

- 💰 **财务支持**: [捐赠](/more/support)
- ⭐ **GitHub**: 为[仓库](https://github.com/Matsuk1/JiETNG)加星
- 📢 **分享**: 告诉朋友关于 JiETNG
- 📝 **贡献**: 改进文档、修复 bug、添加功能
- 🐛 **报告**: 帮助识别和报告 bug

详情请参阅[支持页面](/more/support)。

## 隐私与安全

### 我的数据安全吗？

是的！JiETNG：
- ✅ 加密您的 SEGA 凭据
- ✅ 仅访问公开的 maimai NET 数据
- ✅ 不存储聊天记录
- ✅ 遵循数据保护最佳实践

详情请参阅[隐私政策](/more/privacy)。

### 如何删除我的数据？

发送 `unbind` 从 JiETNG 永久删除您的所有数据。

## 还有问题？

### 文档

- 📖 [入门指南](/guide/getting-started)
- 📚 [命令参考](/commands/basic)
- 🔍 [成绩命令](/commands/record)

### 社区

- 💬 [Discord 服务器](https://discord.gg/NXxFn9T8Xz)
- 🐛 [GitHub Issues](https://github.com/Matsuk1/JiETNG/issues)
- 📧 [支持页面](/more/support)

---

**找不到答案？**

1. 搜索此 FAQ（Ctrl+F / Cmd+F）
2. 查看其他[文档页面](/)
3. 搜索 [GitHub Issues](https://github.com/Matsuk1/JiETNG/issues)
4. 在 [Discord](https://discord.gg/NXxFn9T8Xz) 提问
5. 创建新 [GitHub Issue](https://github.com/Matsuk1/JiETNG/issues/new)

我们随时为您提供帮助！💙
