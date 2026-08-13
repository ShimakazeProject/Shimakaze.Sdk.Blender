"""Minimal i18n for the add-on (English / 简体中文).

Strings in the codebase are English source; ``t()`` returns the Simplified
Chinese translation when the add-on language is set to Chinese. Static
tooltips/labels that Blender reads at registration time stay English; the
panel and report messages are localized at draw/runtime via ``t()``.
"""

from __future__ import annotations

LANG_EN = "EN"
LANG_ZH = "ZH"

#: Add-on language, defaulting to Chinese (preserving the current behavior).
_LOCALE = LANG_ZH

#: English source -> Simplified Chinese.
_ZH: dict[str, str] = {
    # Panel
    "CnC Template Import": "CnC 模板导入",
    "Render Passes": "渲染通道",
    "SHP Settings": "SHP 设置",
    "Template: {name}": "模板：{name}",
    "Template file not found": "模板文件不存在",
    "Select an object first": "请先选择一个对象",
    "Direction count must be 1 or a multiple of 8": "方向数必须是 1 或 8 的倍数",
    "Active pass: {name}": "当前通道：{name}",
    "Download Template": "下载模板",
    "Batch Render": "批量渲染",
    "Language": "语言",
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
    "Active Pass": "当前通道",
    "Last applied render pass (used by batch render)": "最近应用的渲染通道（批量渲染使用）",
    "Enable the compositor's Alpha switch": "勾选后启用合成器中的 Alpha 开关",
    "Output Template": "输出模板",
    "Batch render output path template; supports <template>/<face>, frame added by Blender": (
        "批量渲染输出路径模板，支持 <template>/<face>，帧号由 Blender 追加"
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
    "Object pass: render the model, hide all planes": "物体通道：渲染物体本体，隐藏全部平面",
    "Buildup pass: blue plane visible for the construction animation": (
        "建造动画通道：蓝面可见，用于渲染建造动画"
    ),
    "Shadow pass: shadow planes visible": "阴影通道：阴影面可见，用于渲染阴影",
    "Preview pass: grey plane visible": "预览通道：灰面可见",
    "Reset to default: grey plane visible, all pass switches off": (
        "重置为默认状态：灰面可见，所有通道开关关闭"
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


def set_language(locale: str) -> None:
    """Set the add-on UI language (LANG_EN or LANG_ZH)."""
    global _LOCALE
    if locale in (LANG_EN, LANG_ZH):
        _LOCALE = locale


def t(text: str) -> str:
    """Return ``text`` translated to the add-on's current language."""
    if _LOCALE == LANG_ZH:
        return _ZH.get(text, text)
    return text
