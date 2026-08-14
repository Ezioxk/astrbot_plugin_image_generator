from __future__ import annotations

from astrbot.api import AstrBotConfig, llm_tool, logger, star
from astrbot.api.event import AstrMessageEvent, MessageEventResult, filter
from astrbot.api.message_components import Image
from astrbot.core.star.filter.command import GreedyStr

from .image_api import ImageAPIClient, ImageGenerationError, GeneratedImage


@star.register(
    "image_generator",
    "Siyo",
    "可配置图片生成 API，并提供绘图命令与 LLM 绘图工具",
    "1.3.0",
)
class ImageGeneratorPlugin(star.Star):
    def __init__(self, context: star.Context, config: AstrBotConfig) -> None:
        super().__init__(context)
        self.config = config

    def _client(self) -> ImageAPIClient:
        return ImageAPIClient.from_config(self.config)

    @staticmethod
    def _result(image: GeneratedImage) -> MessageEventResult:
        component = (
            Image.fromURL(image.value)
            if image.kind == "url"
            else Image.fromBase64(image.value)
        )
        return MessageEventResult(chain=[component])

    async def _generate(self, prompt: str) -> MessageEventResult:
        prompt = prompt.strip()
        if not prompt:
            return MessageEventResult().message("请提供绘图描述，例如：/画图 一只在月球上喝茶的猫")

        try:
            image = await self._client().generate(prompt)
            return self._result(image)
        except ImageGenerationError as exc:
            logger.warning("图片生成失败: %s", exc)
            return MessageEventResult().message(f"图片生成失败：{exc}")
        except Exception:
            logger.exception("图片生成发生未预期异常")
            return MessageEventResult().message("图片生成失败：发生未预期错误，请查看 AstrBot 日志。")

    @filter.command("画图", alias={"绘图", "draw"})
    async def draw_command(
        self, event: AstrMessageEvent, prompt: GreedyStr
    ) -> MessageEventResult:
        """根据文字描述生成图片。"""
        return await self._generate(str(prompt))

    @llm_tool("generate_image")
    async def generate_image_tool(
        self, event: AstrMessageEvent, prompt: str
    ) -> MessageEventResult:
        """当用户明确要求画画、绘图、生成图片或创作视觉画面时，调用此工具生成并发送图片。不要用于普通图片搜索。

        Args:
            prompt(string): 完整、具体的图片生成提示词，应包含主体、环境、构图、风格、光线等用户要求。
        """
        return await self._generate(prompt)

    async def terminate(self) -> None:
        return None
