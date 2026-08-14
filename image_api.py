from __future__ import annotations

import asyncio
import base64
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import urlparse

import aiohttp


class ImageGenerationError(RuntimeError):
    """可安全展示给聊天用户的图片生成错误。"""


@dataclass(frozen=True)
class GeneratedImage:
    kind: str
    value: str


@dataclass(frozen=True)
class ProviderPreset:
    endpoint: str
    model: str
    protocol: str = "openai"


PROVIDERS: dict[str, ProviderPreset] = {
    "openai": ProviderPreset(
        "https://api.openai.com/v1/images/generations", "gpt-image-1"
    ),
    "aliyun_bailian": ProviderPreset(
        "",
        "wan2.6-t2i",
        "dashscope_multimodal",
    ),
    "aliyun_bailian_native": ProviderPreset(
        "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis",
        "wanx2.1-t2i-turbo",
        "dashscope_async",
    ),
    "volcengine_ark": ProviderPreset(
        "https://ark.cn-beijing.volces.com/api/v3/images/generations",
        "doubao-seedream-3-0-t2i-250415",
    ),
    "zhipu": ProviderPreset(
        "https://open.bigmodel.cn/api/paas/v4/images/generations", "cogview-4-250304"
    ),
    "siliconflow": ProviderPreset(
        "https://api.siliconflow.cn/v1/images/generations",
        "black-forest-labs/FLUX.1-schnell",
    ),
    "baidu_qianfan": ProviderPreset(
        "https://qianfan.baidubce.com/v2/images/generations", "irag-1.0"
    ),
}


@dataclass(frozen=True)
class ImageAPIClient:
    provider: str
    protocol: str
    endpoint: str
    api_key: str
    model: str
    size: str
    quality: str
    response_format: str
    timeout: float
    poll_interval: float
    auth_header: str
    auth_prefix: str
    extra_headers: Mapping[str, str]
    extra_payload: Mapping[str, Any]

    @classmethod
    def from_config(cls, config: Mapping[str, Any]) -> "ImageAPIClient":
        provider = str(config.get("provider", "custom")).strip() or "custom"
        preset = PROVIDERS.get(provider)
        configured_endpoint = str(config.get("api_endpoint", "")).strip()
        configured_model = str(config.get("model", "")).strip()

        if provider == "aliyun_bailian":
            workspace_id = str(config.get("aliyun_workspace_id", "")).strip()
            if not workspace_id:
                raise ImageGenerationError(
                    "使用 wan2.6/Qwen-Image 时必须配置阿里云百炼 Workspace ID（业务空间 ID）。"
                )
            if not re.fullmatch(r"[A-Za-z0-9-]+", workspace_id):
                raise ImageGenerationError("百炼 Workspace ID 格式不正确。")
            region = str(config.get("aliyun_region", "cn-beijing")).strip()
            region_domains = {
                "cn-beijing": "cn-beijing.maas.aliyuncs.com",
                "ap-southeast-1": "ap-southeast-1.maas.aliyuncs.com",
                "us-east-1": "us-east-1.maas.aliyuncs.com",
            }
            domain = region_domains.get(region)
            if not domain:
                raise ImageGenerationError(f"不支持的百炼地域：{region}")
            endpoint = (
                f"https://{workspace_id}.{domain}/api/v1/services/"
                "aigc/multimodal-generation/generation"
            )
            protocol = "dashscope_multimodal"
            old_defaults = {
                "gpt-image-1",
                "wanx-v1",
                "wanx2.1-t2i-turbo",
                "wanx2.1-t2i-plus",
            }
            model = (
                configured_model
                if configured_model and configured_model not in old_defaults
                else "wan2.6-t2i"
            )
        elif preset:
            endpoint = preset.endpoint
            protocol = preset.protocol
            # 配置文件从旧版本升级时会保留旧默认值，平台预设必须使用自己的模型。
            old_defaults = {"gpt-image-1", "wanx-v1"}
            model = (
                configured_model
                if configured_model and configured_model not in old_defaults
                else preset.model
            )
        else:
            endpoint = cls._normalize_custom_endpoint(configured_endpoint)
            protocol = str(config.get("protocol", "openai")).strip() or "openai"
            model = configured_model or "gpt-image-1"

        api_key = str(config.get("api_key", "")).strip()
        if not endpoint:
            raise ImageGenerationError("尚未配置 API 接口地址。")
        if not api_key and bool(config.get("require_api_key", True)):
            raise ImageGenerationError("尚未配置 API Key。")

        return cls(
            provider=provider,
            protocol=protocol,
            endpoint=endpoint,
            api_key=api_key,
            model=model,
            size=str(config.get("size", "1024x1024")).strip(),
            quality=str(config.get("quality", "auto")).strip(),
            response_format=str(config.get("response_format", "auto")).strip(),
            timeout=max(1.0, float(config.get("timeout", 180))),
            poll_interval=max(0.5, float(config.get("poll_interval", 2))),
            auth_header=str(config.get("auth_header", "Authorization")).strip(),
            auth_prefix=str(config.get("auth_prefix", "Bearer ")),
            extra_headers=cls._json_object(config.get("extra_headers", "{}"), "额外请求头"),
            extra_payload=cls._json_object(config.get("extra_payload", "{}"), "额外请求参数"),
        )

    @staticmethod
    def _normalize_custom_endpoint(endpoint: str) -> str:
        endpoint = endpoint.rstrip("/")
        path = urlparse(endpoint).path.rstrip("/")
        if path.endswith(("/v1", "/v2", "/v3", "/v4")):
            return endpoint + "/images/generations"
        return endpoint

    @staticmethod
    def _json_object(raw: Any, label: str) -> Mapping[str, Any]:
        if isinstance(raw, Mapping):
            return dict(raw)
        try:
            value = json.loads(str(raw or "{}"))
        except json.JSONDecodeError as exc:
            raise ImageGenerationError(f"{label}不是合法 JSON：{exc.msg}") from exc
        if not isinstance(value, dict):
            raise ImageGenerationError(f"{label}必须是 JSON 对象。")
        return value

    def _headers(self, *, dashscope_async: bool = False) -> dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        headers.update({str(k): str(v) for k, v in self.extra_headers.items()})
        if self.api_key and self.auth_header:
            headers[self.auth_header] = f"{self.auth_prefix}{self.api_key}"
        if dashscope_async:
            headers["X-DashScope-Async"] = "enable"
        return headers

    def _openai_payload(self, prompt: str) -> dict[str, Any]:
        payload: dict[str, Any] = dict(self.extra_payload)
        payload.update({"prompt": prompt, "model": self.model})
        if self.size:
            size = self.size
            if self.provider == "aliyun_bailian":
                # 百炼兼容端点沿用 DashScope 的“宽*高”尺寸格式。
                size = size.replace("x", "*")
            payload["size"] = size
        if self.quality and self.quality != "auto":
            payload["quality"] = self.quality
        if self.response_format in {"url", "b64_json"}:
            payload["response_format"] = self.response_format
        payload.setdefault("n", 1)
        return payload

    def _dashscope_payload(self, prompt: str) -> dict[str, Any]:
        # 百炼原生接口是嵌套结构，extra_payload 可覆盖 input/parameters。
        payload: dict[str, Any] = {
            "model": self.model,
            "input": {"prompt": prompt},
            "parameters": {"n": 1, "size": self.size or "1024*1024"},
        }
        extra = dict(self.extra_payload)
        extra_input = extra.pop("input", {})
        extra_parameters = extra.pop("parameters", {})
        payload.update(extra)
        if isinstance(extra_input, Mapping):
            payload["input"].update(extra_input)
        if isinstance(extra_parameters, Mapping):
            payload["parameters"].update(extra_parameters)
        # OpenAI 常用 1024x1024；百炼要求 1024*1024。
        payload["parameters"]["size"] = str(payload["parameters"]["size"]).replace("x", "*")
        return payload

    def _dashscope_multimodal_payload(self, prompt: str) -> dict[str, Any]:
        """构造百炼 wan2.6/Qwen-Image 官方多模态生成请求。"""
        parameters: dict[str, Any] = {
            "prompt_extend": True,
            "watermark": False,
            "negative_prompt": "",
            "size": (self.size or "1280*1280").replace("x", "*"),
        }
        if not self.model.startswith("qwen-image"):
            parameters["n"] = 1

        payload: dict[str, Any] = {
            "model": self.model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": prompt}],
                    }
                ]
            },
            "parameters": parameters,
        }
        extra = dict(self.extra_payload)
        extra_input = extra.pop("input", {})
        extra_parameters = extra.pop("parameters", {})
        payload.update(extra)
        if isinstance(extra_input, Mapping):
            payload["input"].update(extra_input)
        if isinstance(extra_parameters, Mapping):
            payload["parameters"].update(extra_parameters)
        return payload

    async def generate(self, prompt: str) -> GeneratedImage:
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                if self.protocol == "dashscope_async":
                    return await self._generate_dashscope(session, prompt)
                if self.protocol == "dashscope_multimodal":
                    data = await self._request_json(
                        session,
                        "POST",
                        self.endpoint,
                        self._headers(),
                        self._dashscope_multimodal_payload(prompt),
                    )
                    return self._extract_image(data)
                data = await self._request_json(
                    session, "POST", self.endpoint, self._headers(), self._openai_payload(prompt)
                )
                return self._extract_image(data)
        except ImageGenerationError:
            raise
        except (TimeoutError, asyncio.TimeoutError, aiohttp.ServerTimeoutError) as exc:
            raise ImageGenerationError(f"API 请求超过 {self.timeout:g} 秒。") from exc
        except aiohttp.ClientError as exc:
            raise ImageGenerationError(f"无法连接图片 API：{exc}") from exc

    async def _generate_dashscope(
        self, session: aiohttp.ClientSession, prompt: str
    ) -> GeneratedImage:
        submitted = await self._request_json(
            session,
            "POST",
            self.endpoint,
            self._headers(dashscope_async=True),
            self._dashscope_payload(prompt),
        )
        output = submitted.get("output", {}) if isinstance(submitted, dict) else {}
        task_id = output.get("task_id") if isinstance(output, dict) else None
        if not task_id:
            raise ImageGenerationError("百炼未返回 task_id，请检查模型名和接口权限。")

        task_url = self._dashscope_task_url(str(task_id))
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.timeout
        while loop.time() < deadline:
            await asyncio.sleep(self.poll_interval)
            task = await self._request_json(session, "GET", task_url, self._headers())
            output = task.get("output", {}) if isinstance(task, dict) else {}
            status = str(output.get("task_status", "")).upper()
            if status == "SUCCEEDED":
                return self._extract_image(output)
            if status in {"FAILED", "CANCELED", "UNKNOWN"}:
                detail = output.get("message") or task.get("message") or status
                raise ImageGenerationError(f"百炼任务失败：{detail}")
        raise ImageGenerationError(f"百炼任务轮询超过 {self.timeout:g} 秒。")

    def _dashscope_task_url(self, task_id: str) -> str:
        parsed = urlparse(self.endpoint)
        return f"{parsed.scheme}://{parsed.netloc}/api/v1/tasks/{task_id}"

    async def _request_json(
        self,
        session: aiohttp.ClientSession,
        method: str,
        url: str,
        headers: Mapping[str, str],
        payload: Mapping[str, Any] | None = None,
    ) -> Any:
        kwargs: dict[str, Any] = {"headers": headers}
        if payload is not None:
            kwargs["json"] = payload
        async with session.request(method, url, **kwargs) as response:
            body = await response.text()
            if not 200 <= response.status < 300:
                detail = self._error_detail(body)
                hint = ""
                if response.status == 404:
                    hint = f"；实际请求地址：{url}。请检查平台选择和接口路径"
                raise ImageGenerationError(
                    f"API 返回 HTTP {response.status}"
                    + (f"：{detail}" if detail else "")
                    + hint
                )
            try:
                return json.loads(body)
            except json.JSONDecodeError as exc:
                raise ImageGenerationError("API 返回的不是合法 JSON。") from exc

    @staticmethod
    def _extract_image(data: Any) -> GeneratedImage:
        queue: list[Any] = [data]
        visited = 0
        while queue and visited < 100:
            item = queue.pop(0)
            visited += 1
            if isinstance(item, str):
                if item.startswith(("http://", "https://")):
                    return GeneratedImage("url", item)
                continue
            if isinstance(item, list):
                queue.extend(item)
                continue
            if not isinstance(item, dict):
                continue
            for key in ("url", "image_url"):
                value = item.get(key)
                if isinstance(value, str) and value.startswith(("http://", "https://")):
                    return GeneratedImage("url", value)
            for key in ("b64_json", "base64", "image_base64"):
                value = item.get(key)
                if isinstance(value, str) and value:
                    return GeneratedImage("base64", ImageAPIClient._clean_base64(value))
            queue.extend(item.values())
        raise ImageGenerationError("API 响应中没有找到图片 URL 或 Base64 数据。")

    @staticmethod
    def _clean_base64(value: str) -> str:
        if value.startswith("data:") and "," in value:
            value = value.split(",", 1)[1]
        try:
            base64.b64decode(value, validate=True)
        except (ValueError, TypeError) as exc:
            raise ImageGenerationError("API 返回了无效的 Base64 图片数据。") from exc
        return value

    @staticmethod
    def _error_detail(body: str) -> str:
        try:
            data = json.loads(body)
            if isinstance(data, dict):
                error = data.get("error", data.get("message", data.get("detail")))
                if isinstance(error, dict):
                    error = error.get("message", error.get("code"))
                if error:
                    return str(error)[:500]
                if data.get("code"):
                    return f"{data['code']} {data.get('message', '')}".strip()[:500]
        except json.JSONDecodeError:
            pass
        return " ".join(body.split())[:500]
