"""Minimal i18n for the add-on (English / 简体中文).

Strings in the codebase are English source; ``t()`` returns the Simplified
Chinese translation when Blender's interface language is Chinese. The language
is read from ``bpy.context.preferences.view.language`` and cached in
``_LOCALE`` so ``t()`` can also run on worker threads without touching bpy.
"""

from __future__ import annotations

LANG_EN = "EN"
LANG_ZH = "ZH"

#: Cached add-on language, kept in sync with Blender's interface language.
_LOCALE = LANG_ZH


def refresh_language() -> None:
    """Sync the add-on language with Blender's interface language."""
    global _LOCALE
    import bpy

    try:
        language = bpy.context.preferences.view.language
    except (AttributeError, RuntimeError):
        return
    _LOCALE = LANG_ZH if str(language).lower().startswith("zh") else LANG_EN


def t(text: str) -> str:
    """Return ``text`` translated to the add-on's current language."""
    if _LOCALE == LANG_ZH:
        return _ZH.get(text, text)
    return text


#: English source -> Simplified Chinese.
_ZH: dict[str, str] = {
    # Panel
    "CnC Template Import": "CnC 模板导入",
    "Render Setup": "渲染设置",
    "SHP Settings": "SHP 设置",
    "Template: {name}": "模板：{name}",
    "Template file not found": "模板文件不存在",
    "Select an object first": "请先选择一个对象",
    "Direction count must be 1 or a multiple of 8": "方向数必须是 1 或 8 的倍数",
    "Download Template": "下载模板",
    "Batch Render": "批量渲染",
    "Holdout Materials": "阻隔材质",
    "Excluded Materials": "排除的材质",
    "Apply Holdout": "应用阻隔着色器",
    "Applied holdout to {count} materials": "已为 {count} 个材质应用阻隔着色器",
    "Apply Holdout can only be reverted via Undo (Ctrl+Z) - no separate undo.": (
        "应用阻隔着色器只能通过撤销（Ctrl+Z）恢复，没有单独的撤销功能。"
    ),
    "No active material to add": "没有可添加的活动材质",
    "Material already in the list": "材质已在列表中",
    "Added material: {name}": "已添加材质：{name}",
    "No material selected to remove": "未选择要移除的材质",
    # Properties
    "Faces (directions)": "面数（方向数）",
    "SHP direction count; must be 1 or a multiple of 8": "SHP 方向数，必须是 1 或 8 的倍数",
    "Reverse": "反向",
    "Render in reverse direction (for SHP vehicles)": "反向，用于制作 SHP 载具",
    "Target": "目标",
    "Target empty object of this scene": "本场景的目标空对象名称",
    "Imported from template": "模板导入",
    "Whether the scene was imported from a CnC template (shows render passes)": (
        "是否从 CnC 模板导入的场景（显示渲染通道）"
    ),
    "Render Engine": "渲染引擎",
    "Render engine used for the scene": "场景使用的渲染引擎",
    "Render Target": "渲染目标",
    "Render target (pass) applied to the scene": "应用到场景的渲染目标（通道）",
    "Plane Suffix": "平面后缀",
    "Plane object suffix recorded at import (e.g. RA2.INF)": (
        "导入时记录的平面对象后缀（如 RA2.INF）"
    ),
    "Enable the compositor's Alpha switch": "勾选后启用合成器中的 Alpha 开关",
    "Output Template": "输出模板",
    "Batch render output path template; supports <target>/<face>, frame added by Blender": (
        "批量渲染输出路径模板，支持 <target>/<face>，帧号由 Blender 追加"
    ),
    "Game": "游戏",
    "CnC game template to import": "选择要导入的 CnC 游戏模板",
    "Variant": "变体",
    "Template scene variant (Standard / Effects / Infantry)": (
        "选择模板场景变体（标准 / Effects / 步兵）"
    ),
    # Operators
    "Import Scene": "导入场景",
    "Append the selected game + variant scene from the CnC template": (
        "从 CnC 模板按所选游戏 + 变体导入场景"
    ),
    "Render SHP animation frames per direction, rotating the target after each": (
        "按方向数批量渲染 SHP 动画帧：每方向渲染动画并旋转目标"
    ),
    "Download the missing CnC template file asynchronously (pinned version)": (
        "异步下载缺少的 CnC 模板文件（固定版本）"
    ),
    # Reports / messages
    "Could not get template file: {exc}": "无法获取模板文件：{exc}",
    "Current scene is not a valid template scene": "当前场景不是有效的模板场景",
    "Applied {label} to the current scene": "已应用 {label} 到当前场景",
    "Import a template scene before batch rendering": "请先导入模板场景再批量渲染",
    "Target empty not found": "未找到目标空对象",
    "Invalid render pass: {name}": "无效的渲染通道：{name}",
    "Batch render {name}: face {face}/{faces}, frame {frame}/{end} ({pct}%)": (
        "批量渲染 {name}：方向 {face}/{faces}，帧 {frame}/{end}（{pct}%）"
    ),
    "Batch render cancelled": "批量渲染已取消",
    "Batch render done: {name} × {faces} directions": "批量渲染完成：{name} × {faces} 方向",
    "Template ready: {name}": "模板已就绪：{name}",
    "Template ready": "模板已就绪",
    "Template is already downloading": "模板已在下载中",
    "Template download failed: {exc}": "下载模板失败：{exc}",
    "Download template {phase}{pct}": "下载模板 {phase}{pct}",
    # Download phases
    "Connecting…": "正在连接…",
    "Downloading…": "正在下载…",
    "Extracting…": "正在解压…",
    "Download complete": "下载完成",
    "No .zip asset in release {version}": "release {version} 中没有 .zip 资源",
    "No .blend file in the template archive": "模板压缩包中没有 .blend 文件",
}
