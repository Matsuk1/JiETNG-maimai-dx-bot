# DXData 音符数量检查

在管理员面板的 DXData 页面中，进入独立的「NOTE 检查 · 音符数量」区域，点击「检查音符数量」。该区域有独立的状态和分页，统一显示全部检查问题，无需登录；官网定数/版本检查保留在另一个区域。原来的「检查当前数据」也会运行此检查；官网登录失败不会丢失已生成的音符报告。

部署时把整个 `simai_muconvert/` 放在服务器项目工作目录下，与 `main.py` 同级。也可给服务器进程设置环境变量 `SIMAI_CHART_DIR=/absolute/path/to/simai_muconvert`，重启进程后生效。目录只需读取权限；无需上传转换日志和 JSON 转换报告。代码和谱面库需分别部署。

检查比较 `data/dxdata/dxdata.json` 与已有 `data/dxdata/auto_override.csv` 合并后的音符数量，不应用定数/版本修正 CSV。报告保存于现有 `data/dxdata/music_level_audit.json` 的 `notes` 字段，与其他检查共享排他锁。运行在后台线程，不阻塞提交请求。`POST /admin/dxdata_audit` 的请求体 `{"mode":"notes"}` 可独立启动，沿用管理员认证及 CSRF；GET 同一接口读取结果。谱面文件增删、大小/修改时间变化、dxdata 或自动修正 CSV 内容变化会使结果标为过期。

匹配采用规范化歌名、谱面类型、难度三项。仅 `Link` 特殊处理：同难度下，部分音符类别数量相等即可作为对应依据，选择一致项最多且双方唯一的候选；STD 的不适用 TOUCH 项不参与判断。并列或没有一致项仍列为未匹配。匹配之后仍逐项检查差异，不把部分一致视为全部通过。其他同名歌曲不使用音符数量消歧。对于这批 MuConvert 导出目录，`music000xxx` 属于 STD、`music01xxxx` 属于 DX，数值 ID 大于等于 100000 的目录归为宴谱（支持 `_L` / `_R` 后缀识别）。`inote_2` 至 `inote_6` 分别对应 BASIC 至 Re:MASTER。不符合此命名约定的数据不应直接导入。宴谱目录（包括双人 L/R）、inote_7 和 dxdata 中的宴谱均跳过，不计入检查、未匹配或未覆盖。仍无法唯一对应的普通谱面单独报告，不强行比较。

按 TAP、HOLD、SLIDE、TOUCH、BREAK、TOTAL 对比。星星头单独计 TAP，`?` / `!` 无头滑条不计头；每条分支滑条计一次，连接滑条不按路径段重复计数；BREAK HOLD / SLIDE 归入 BREAK；TOUCH HOLD 归入 HOLD。STD 的 TOUCH 空值视为不适用（0），其余缺失值仍列为差异。语法依据 [Simai 官方格式说明](https://w.atwiki.jp/simai/pages/1003.html)，解析器针对当前 MuConvert 导出子集；未知语法报告解析失败，不使用部分统计。

结果分为一致、数量差异、未匹配和解析失败，并列出 dxdata 未覆盖的谱面数。数量差异优先显示，每页 20 项，提供文件名、难度槽位和各字段的 dxdata / Simai 值。匹配成功但解析失败不算一致。没有谱面库显示「未找到谱面库」，不会显示全部通过。

差异是待核对项，不等同于已证实 dxdata 错误：历史版本变更或源谱转换问题也会产生差异。核对后可在卡片点击「修改」，将该谱面的差异写入 `data/dxdata/auto_override.csv`，保留其他已有修正。保存值来自服务器的检查报告，不接受客户端提交任意音符数。过期报告和非唯一匹配不能保存。保存后仅更新当前报告中的对应项与计数，不重新解析谱面库；需要重新检查时，手动点击检查按钮。

读取 dxdata 时先应用 `auto_override.csv`，再应用地区修正 CSV，最后应用手动 `override.csv`（手动修正优先）。自动修正对 JP / INTL 均生效，文件变化会使读取缓存失效；`include_generated=False` 可读取未应用自动修正的数据。无需手动创建 CSV，首次保存时自动生成，不覆盖原始 dxdata JSON。服务器进程需有 `data/dxdata/` 写入权限。
