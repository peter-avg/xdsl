import textwrap
import xml.etree.ElementTree as etree
from collections.abc import Callable
from typing import Any

from pymdownx.blocks import BlocksExtension  # pyright: ignore[reportMissingTypeStubs]
from pymdownx.blocks.block import (  # pyright: ignore[reportMissingTypeStubs]
    Block,
    type_string,
    type_string_in,
)


class BaseMarimoBlock(Block):
    """Base class for marimo embed blocks"""

    OPTIONS: dict[str, tuple[Any, Callable[[Any], Any]]] = {
        "size": (
            "medium",
            type_string_in(["small", "medium", "large", "xlarge", "xxlarge"]),
        ),
        "mode": ("read", type_string_in(["read", "edit"])),
    }

    options: dict[str, Any]

    def on_create(self, parent: etree.Element) -> etree.Element:
        container = etree.SubElement(parent, "div")
        container.set("class", "marimo-embed-container")
        return container

    def on_add(self, block: etree.Element) -> etree.Element:
        return block

    def _create_iframe(self, block: etree.Element, url: str) -> None:
        # Clear existing content
        block.text = None
        for child in block:
            block.remove(child)

        # Add iframe
        size: str = self.options["size"]
        iframe = etree.SubElement(block, "iframe")
        iframe.set("class", f"demo {size}")
        iframe.set("src", url)
        iframe.set(
            "allow",
            "camera; geolocation; microphone; fullscreen; autoplay; encrypted-media; "
            "picture-in-picture; clipboard-read; clipboard-write",
        )
        iframe.set("width", "100%")
        iframe.set("frameborder", "0")
        iframe.set("scrolling", "no")
        iframe.set("style", "height: 75vh")

    def on_markdown(self) -> str:
        return "raw"


class MarimoEmbedBlock(BaseMarimoBlock):
    NAME: str = "marimo-embed"
    OPTIONS: dict[str, tuple[Any, Callable[[Any], Any]]] = {
        **BaseMarimoBlock.OPTIONS,
        "app_width": ("wide", type_string_in(["wide", "full", "compact"])),
    }

    def on_end(self, block: etree.Element) -> None:
        code = block.text.strip() if block.text else ""
        if code.startswith("```python"):
            code = code[9:]
            code = code[:-3]
        code = textwrap.dedent(code)

        app_width: str = self.options["app_width"]
        mode: str = self.options["mode"]
        url = create_marimo_app_url(
            code=create_marimo_app_code(code=code, app_width=app_width),
            mode=mode,
        )
        self._create_iframe(block, url)


class MarimoEmbedFileBlock(BaseMarimoBlock):
    NAME: str = "marimo-embed-file"
    OPTIONS: dict[str, tuple[Any, Callable[[Any], Any]]] = {
        **BaseMarimoBlock.OPTIONS,
        "filepath": ("", type_string),
        "show_source": ("true", type_string_in(["true", "false"])),
    }

    def on_end(self, block: etree.Element) -> None:
        filepath = self.options["filepath"]
        if not filepath:
            raise ValueError("File path must be provided")

        # Read from project root
        try:
            with open(filepath) as f:
                code = f.read()
        except FileNotFoundError:
            raise ValueError(f"File not found: {filepath}")

        mode: str = self.options["mode"]
        url = create_marimo_app_url(code=code, mode=mode)
        self._create_iframe(block, url)

        # Add source code section if enabled
        show_source: str = self.options.get("show_source", "true")
        if show_source == "true":
            details = etree.SubElement(block, "details")
            summary = etree.SubElement(details, "summary")
            summary.text = f"Source code for `{filepath}`"

            # TODO: figure out syntax highlighting
            # md_text = f"\n\n```python\n{code}\n```\n\n"
            # result = self.md.htmlStash.store(self.md.convert(md_text))
            # container.text = result

            copy_paste_container = etree.SubElement(details, "p")
            copy_paste_container.text = (
                "Tip: paste this code into an empty cell, and the marimo editor will "
                "create cells for you"
            )

            code_container = etree.SubElement(details, "pre")
            code_container.set("class", "marimo-source-code")
            code_block = etree.SubElement(code_container, "code")
            code_block.set("class", "language-python")
            code_block.text = code


def create_marimo_app_code(
    *,
    code: str,
    app_width: str = "wide",
) -> str:
    header = "\n".join(
        [
            "import marimo",
            f'app = marimo.App(width="{app_width}")',
            "",
        ]
    ) + "\n".join(
        [
            "",
            "@app.cell",
            "def __():",
            "    import marimo as mo",
            "    return",
        ]
    )
    return header + code


def create_marimo_app_url(code: str, mode: str = "read") -> str:
    from lzstring2 import LZString

    encoded_code = LZString.compress_to_encoded_URI_component(code)
    return f"https://marimo.app/#code/{encoded_code}&embed=true"


class MarimoBlocksExtension(BlocksExtension):
    def extendMarkdownBlocks(self, md: Any, block_mgr: Any) -> None:
        block_mgr.register(MarimoEmbedBlock, self.getConfigs())
        block_mgr.register(MarimoEmbedFileBlock, self.getConfigs())


def makeExtension(*args: Any, **kwargs: Any) -> MarimoBlocksExtension:
    return MarimoBlocksExtension(*args, **kwargs)
