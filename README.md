# AstrBot 可配置图片生成插件

支持复用 AstrBot“模型提供商”页面中已经配置好的 API Base、API Key、自定义请求头和模型名称，也保留旧版插件独立配置。提供 `/画图` 命令和 `generate_image` LLM 工具。

仓库地址：<https://github.com/Ezioxk/astrbot_plugin_image_generator>

## 安装

将整个 `astrbot_plugin_image_generator` 目录放入 AstrBot 的 `data/plugins/`，然后在 WebUI 的插件管理中重载/启用插件。AstrBot 会根据 `requirements.txt` 安装依赖。

## 推荐配置：复用 AstrBot 模型提供商

1. 在 AstrBot WebUI 的“模型提供商 → 对话”中新增一个专门用于图片生成的模型，例如命名为“生图”。
2. 在该模型中配置平台的 API Base、API Key 和图片模型名称。
3. 打开本插件配置，在“AstrBot 图片模型提供商”下拉框中选择这个模型。
4. 设置默认图片尺寸和请求超时，保存即可。

以后更换 API 地址、Key 或模型时，只需修改“模型提供商”中的对应模型，不需要再修改插件配置。插件不会把提供商的 API Key 复制保存到插件配置中。

### 阿里云百炼

模型提供商的 API Base 可以填写百炼兼容模式地址，例如：

```text
https://dashscope.aliyuncs.com/compatible-mode/v1
```

或业务空间提供的兼容模式地址：

```text
https://<workspace-host>.cn-beijing.maas.aliyuncs.com/compatible-mode/v1
```

插件在协议为 `auto` 时会自动选择正确接口：

- `wan2.6-t2i`、`qwen-image-*`：将兼容模式 Base 转为同一域名下的百炼多模态生成接口。
- `wanx*`：使用旧版万相异步任务接口。
- 其他平台：默认按 OpenAI Images API，在 Base 后补充 `/images/generations`。

因此不要把百炼控制台页面地址填入 API Base，也不需要在插件中重复填写 Workspace ID。

## 高级与旧版手动配置

开启“显示高级/手动配置”后可以：

- 覆盖所选 AstrBot 提供商的图片协议、模型或完整图片接口地址。
- 设置质量、响应格式、自定义鉴权头、额外请求头和额外请求参数。
- 在未选择 AstrBot 图片模型提供商时，继续使用旧版的平台预设、API Key、Workspace ID 等独立配置。

自动判断不适合某个平台时，先把“AstrBot 提供商图片协议”改为对应协议；仍有特殊路径时再填写“覆盖 AstrBot 提供商图片接口”。

## 使用

主动命令（别名为 `/绘图`、`/draw`）：

```text
/画图 一只戴宇航员头盔的橘猫，电影感灯光
```

正常对话时，LLM 可调用 `generate_image` 工具。请同时在 AstrBot 的工具管理中确认该工具没有被停用。

## 支持的响应

插件可自动从常见 JSON 响应结构中提取图片 URL 或 Base64 数据，包括 `data[0].url`、`data[0].b64_json`、`image_url`、`base64` 和 `image_base64`。图片 URL 通常有有效期，插件收到结果后会立即发送。

## 安全提示

不要在截图、聊天或 GitHub 提交中公开 API Key。如果密钥已经出现在截图或聊天中，请立即到平台控制台撤销并重新生成。
