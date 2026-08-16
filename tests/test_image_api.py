from __future__ import annotations

import unittest

from image_api import ImageAPIClient, ImageGenerationError


class AstrBotProviderConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.plugin_config = {
            "astrbot_protocol": "auto",
            "astrbot_model_override": "",
            "astrbot_endpoint_override": "",
            "size": "1280x1280",
            "quality": "auto",
            "response_format": "auto",
            "timeout": 180,
            "poll_interval": 2,
            "auth_header": "Authorization",
            "auth_prefix": "Bearer ",
            "require_api_key": True,
            "extra_headers": "{}",
            "extra_payload": "{}",
        }

    def test_wan_26_uses_dashscope_multimodal_endpoint(self) -> None:
        client = ImageAPIClient.from_astrbot_provider(
            {
                "id": "image",
                "type": "openai_chat_completion",
                "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "model": "wan2.6-t2i",
                "key": ["provider-key"],
            },
            self.plugin_config,
        )

        self.assertEqual(client.protocol, "dashscope_multimodal")
        self.assertEqual(
            client.endpoint,
            "https://dashscope.aliyuncs.com/api/v1/services/"
            "aigc/multimodal-generation/generation",
        )
        self.assertEqual(client.model, "wan2.6-t2i")
        self.assertEqual(client.api_key, "provider-key")
        self.assertEqual(
            client._dashscope_multimodal_payload("a cat"),
            {
                "model": "wan2.6-t2i",
                "input": {
                    "messages": [
                        {"role": "user", "content": [{"text": "a cat"}]}
                    ]
                },
                "parameters": {
                    "prompt_extend": True,
                    "watermark": False,
                    "negative_prompt": "",
                    "size": "1280*1280",
                    "n": 1,
                },
            },
        )
        self.assertEqual(client._headers()["Authorization"], "Bearer provider-key")

    def test_workspace_qwen_image_keeps_workspace_host(self) -> None:
        client = ImageAPIClient.from_astrbot_provider(
            {
                "id": "image",
                "type": "openai_chat_completion",
                "api_base": (
                    "https://workspace.cn-beijing.maas.aliyuncs.com/"
                    "compatible-mode/v1"
                ),
                "model": "qwen-image-3.0-pro",
                "key": ["provider-key"],
            },
            self.plugin_config,
        )

        self.assertEqual(client.protocol, "dashscope_multimodal")
        self.assertEqual(
            client.endpoint,
            "https://workspace.cn-beijing.maas.aliyuncs.com/api/v1/services/"
            "aigc/multimodal-generation/generation",
        )

    def test_wanx_uses_legacy_async_endpoint(self) -> None:
        client = ImageAPIClient.from_astrbot_provider(
            {
                "id": "image",
                "type": "openai_chat_completion",
                "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "model": "wanx2.1-t2i-turbo",
                "key": ["provider-key"],
            },
            self.plugin_config,
        )

        self.assertEqual(client.protocol, "dashscope_async")
        self.assertEqual(
            client.endpoint,
            "https://dashscope.aliyuncs.com/api/v1/services/"
            "aigc/text2image/image-synthesis",
        )

    def test_openai_compatible_base_gets_images_path(self) -> None:
        client = ImageAPIClient.from_astrbot_provider(
            {
                "id": "ark-image",
                "type": "openai_chat_completion",
                "api_base": "https://ark.example.com/api/v3",
                "model": "seedream-image",
                "key": ["provider-key"],
            },
            self.plugin_config,
        )

        self.assertEqual(client.protocol, "openai")
        self.assertEqual(
            client.endpoint, "https://ark.example.com/api/v3/images/generations"
        )

    def test_provider_headers_are_reused_and_plugin_headers_override(self) -> None:
        plugin_config = dict(self.plugin_config)
        plugin_config["extra_headers"] = '{"X-Source": "plugin"}'
        client = ImageAPIClient.from_astrbot_provider(
            {
                "id": "image",
                "type": "openai_chat_completion",
                "api_base": "https://images.example.com/v1",
                "model": "image-model",
                "key": ["provider-key"],
                "custom_headers": {"X-Source": "provider", "X-Tenant": "one"},
            },
            plugin_config,
            api_key="current-key",
        )

        self.assertEqual(client.api_key, "current-key")
        self.assertEqual(client.extra_headers["X-Source"], "plugin")
        self.assertEqual(client.extra_headers["X-Tenant"], "one")

    def test_missing_provider_model_is_reported(self) -> None:
        with self.assertRaisesRegex(ImageGenerationError, "没有配置模型名称"):
            ImageAPIClient.from_astrbot_provider(
                {
                    "id": "image",
                    "type": "openai_chat_completion",
                    "api_base": "https://images.example.com/v1",
                    "key": ["provider-key"],
                },
                self.plugin_config,
            )


if __name__ == "__main__":
    unittest.main()
