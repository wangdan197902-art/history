"""图片处理模块 — WebP 转换 / 缩略图 / 响应式图片

依赖: Pillow >= 10.0
"""
import asyncio
from pathlib import Path
from typing import Optional

from PIL import Image


def convert_to_webp(
    input_path: str,
    output_path: str,
    quality: int = 85,
    max_width: int | None = None,
) -> str:
    """将图片转换为 WebP 格式

    Args:
        input_path: 输入图片路径
        output_path: 输出 WebP 路径
        quality: 质量(1-100)
        max_width: 最大宽度(等比缩放)

    Returns:
        str: 输出文件路径

    Raises:
        FileNotFoundError: 输入文件不存在
        PIL.UnidentifiedImageError: 无法识别的图片格式
    """
    input_file = Path(input_path)
    if not input_file.exists():
        raise FileNotFoundError(f"Input image not found: {input_path}")

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(input_path) as img:
        # 转换为 RGB(如果是 RGBA/P 模式)
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")

        # 等比缩放
        if max_width and img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

        img.save(output_file, format="WEBP", quality=quality, method=4)

    return str(output_file)


def generate_responsive_images(
    input_path: str,
    output_dir: str,
    sizes: list[int] | None = None,
    quality: int = 85,
) -> dict[int, str]:
    """生成响应式图片(多尺寸 WebP)

    Args:
        input_path: 输入图片路径
        output_dir: 输出目录
        sizes: 宽度列表(默认 [400, 800])
        quality: 质量

    Returns:
        dict[width, file_path]
    """
    if sizes is None:
        sizes = [400, 800]

    input_file = Path(input_path)
    stem = input_file.stem
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    results: dict[int, str] = {}
    for size in sizes:
        output_path = output_dir_path / f"{stem}_{size}w.webp"
        convert_to_webp(input_path, str(output_path), quality=quality, max_width=size)
        results[size] = str(output_path)

    return results


def get_image_info(image_path: str) -> dict:
    """获取图片信息

    Returns:
        dict: 宽度/高度/格式/大小
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    with Image.open(image_path) as img:
        return {
            "path": str(path),
            "width": img.width,
            "height": img.height,
            "format": img.format,
            "size_bytes": path.stat().st_size,
            "size_kb": round(path.stat().st_size / 1024, 2),
        }


def generate_picture_tag(
    image_paths: dict[int, str],
    alt: str,
    css_class: str = "responsive-image",
) -> str:
    """生成 HTML <picture> 标签

    Args:
        image_paths: {width: file_path} 字典
        alt: alt 文本
        css_class: CSS 类名

    Returns:
        str: HTML <picture> 标签
    """
    if not image_paths:
        return f'<img src="" alt="{alt}" class="{css_class}">'

    # 按宽度排序
    sorted_paths = sorted(image_paths.items())
    sources = []
    for width, path in sorted_paths[:-1]:
        rel_path = path.replace("site/static/", "/")
        sources.append(f'<source media="(max-width: {width}px)" srcset="{rel_path}">')

    # 最大尺寸作为 fallback
    max_width, max_path = sorted_paths[-1]
    rel_max_path = max_path.replace("site/static/", "/")

    sources_str = "\n  ".join(sources)
    return f'''<picture class="{css_class}">
  {sources_str}
  <img src="{rel_max_path}" alt="{alt}" loading="lazy">
</picture>'''


async def process_image_async(
    input_path: str,
    output_dir: str,
    sizes: list[int] | None = None,
    quality: int = 85,
) -> dict[int, str]:
    """异步处理图片(在线程池中执行)

    Args:
        input_path: 输入图片路径
        output_dir: 输出目录
        sizes: 宽度列表
        quality: 质量

    Returns:
        dict[width, file_path]
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        generate_responsive_images,
        input_path,
        output_dir,
        sizes,
        quality,
    )
