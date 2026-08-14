# AstrBot 可配置图片生成插件

支持阿里云百炼等国内主流图片平台，支持用户命令主动调用，也会向 AstrBot 的 LLM 注册绘图工具，让 Bot 在用户要求画画时自行调用。

仓库地址：<https://github.com/Ezioxk/astrbot_plugin_image_generator>

## 安装

将整个 `astrbot_plugin_image_generator` 目录放入 AstrBot 的 `data/plugins/`，然后在 WebUI 的插件管理中重载/启用插件。AstrBot 会根据 `requirements.txt` 安装依赖。

## 配置

在 AstrBot WebUI 的插件配置页先选择 `provider`，再填写 API Key。平台预设包括：

- `aliyun_bailian`：阿里云百炼 OpenAI 兼容图片接口，支持 `wan2.6-t2i`、Qwen-Image 等新模型
- `aliyun_bailian_native`：旧版通义万相原生异步接口，仅在使用 `wanx2.1-t2i-turbo` 等旧模型时选择
- `volcengine_ark`：火山引擎方舟/豆包 Seedream
- `zhipu`：智谱 CogView
- `siliconflow`：硅基流动 FLUX 等模型
- `baidu_qianfan`：百度智能云千帆
- `openai`：OpenAI
- `custom`：其他 OpenAI Images API 兼容服务

主要配置：

- `api_endpoint`：仅 `custom` 模式使用；推荐填写完整图片接口
- `api_key`：平台密钥
- `model`：留空使用平台预设模型。百炼兼容模式默认 `wan2.6-t2i`，也可填写 `qwen-image-3.0-pro`；火山方舟通常需要填推理接入点 ID
- `size`、`quality`、`response_format`：生成参数
- `extra_headers`、`extra_payload`：平台需要的额外 JSON 参数

除 `aliyun_bailian_native` 外，平台默认按 OpenAI Images API 兼容格式发送：

```json
{
  "model": "gpt-image-1",
  "prompt": "图片描述",
  "size": "1024x1024",
  "n": 1
}
```

插件可自动识别常见响应字段：`data[0].url`、`data[0].b64_json`、`image_url`、`base64`、`image_base64`。

## 使用

主动命令（别名为 `/绘图`、`/draw`）：

```text
/画图 一只戴宇航员头盔的橘猫，电影感灯光
```

正常对话时，LLM 可调用 `generate_image` 工具。请同时在 AstrBot 的工具管理中确认该工具没有被停用；只有当用户明确要求生成图片时，工具描述才会引导模型调用。

## 兼容性说明

插件支持同步返回 URL/Base64 的 OpenAI Images API 兼容接口。百炼默认使用 `/compatible-mode/v1/images/generations`，避免把新模型错误地发送到旧万相协议；同时保留“提交任务 + 轮询结果”的旧版原生协议。图片 URL 通常有有效期，插件收到结果后会立即发送。

### 百炼升级说明

从 1.2.0 起，`aliyun_bailian` 代表兼容接口。旧配置中的 `wanx2.1-t2i-turbo` 会自动迁移为兼容接口默认模型 `wan2.6-t2i`。如果仍需使用旧模型，请把平台改为 `aliyun_bailian_native` 并明确填写模型名。

## 404 排查

出现 `HTTP 404` 一般代表域名可以访问，但接口路径不对。建议直接选择正确的 `provider`，不要把控制台地址、API 根地址或聊天补全地址填入图片接口。新版错误会显示实际请求 URL，便于定位。
