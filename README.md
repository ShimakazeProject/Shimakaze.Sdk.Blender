# Shimakaze SDK for Blender

一个遵循 **Blender 4.5 扩展（Extension）最佳实践** 的 SDK 脚手架项目。
清单声明、目录布局、注册流程、构建与安装方式均基于 Blender 4.2+ 官方 `extension` 体系，
并已在本机 Blender 4.5 上实测通过（构建、安装、注册、运行、卸载重载）。

## 功能特性

- `blender_manifest.toml` 标准清单：唯一标识、平台、权限、许可证（SPDX）等。
- 模块化结构：偏好设置、属性、操作符、面板、快捷键、纯逻辑工具分层清晰。
- 示例操作符：`shimakaze.hello`、`shimakaze.bump_asset_version`。
- 快捷键以 `type="NONE"` 注册，不占用任何默认热键，用户可按需绑定。
- 版本号单一来源：`__init__.py` 直接读取清单中的 `version`。
- 构建脚本（`build.ps1` / `Makefile`）与 GitHub Actions CI。

## 环境要求

| 依赖 | 版本 |
| --- | --- |
| Blender | >= 4.5.0 |
| Python（仅开发用） | 3.11+ |

## 安装

### 方式一：作为扩展安装（推荐）

1. 构建扩展（见下），得到 `dist/shimakaze_sdk_blender-0.1.0.zip`。
2. Blender 菜单 **Edit > Preferences > Get Extensions > Install from Disk**，选择该 `.zip`。
3. 在 **Add-ons** 列表中启用 **Shimakaze SDK**。

### 方式二：开发模式

在 **Preferences > Get Extensions > Repositories** 中新增本地仓库，目录指向本仓库根目录。
Blender 会扫描仓库下的扩展子目录（含清单的 `extension/`），并在磁盘内容变化时热重载。

## 开发

### 环境准备

```bash
# 项目内已创建 .venv（基于 Blender 4.5 自带的 Python 3.11）
.venv/Scripts/activate        # Windows
pip install -r requirements-dev.txt   # ruff / pyright / fake-bpy-module-4.5
```

### 常用命令

| 命令 | 作用 |
| --- | --- |
| `ruff check .` / `ruff format .` | 静态检查 / 自动格式化 |
| `pyright` | 类型检查（基于 fake-bpy-module 的 bpy 存根） |
| `.\build.ps1` | Windows 下构建扩展到 `dist/` |
| `make build` | macOS / Linux 下构建扩展到 `dist/` |

### 构建

使用 Blender 官方命令，从 `extension/`（清单所在目录）构建：

```bash
blender --command extension build --source-dir extension --output-dir dist
```

### 添加 Python 运行时依赖（Blender 4.3+）

若扩展需要第三方 Python 包，在 `pyproject.toml` 中补充 `[project]` 表：

```toml
[project]
name = "shimakaze-sdk"
version = "0.1.0"
dependencies = ["requests>=2.31"]
```

构建/安装时 Blender 会从 PyPI 解析并打包进扩展的 `site-packages`。

## 清单（blender_manifest.toml）要点

以下规则经 Blender 4.5 实测校验：

- `id` 必须是合法 Python 标识符（**不能含点号**），如 `shimakaze_sdk_blender`。
- `tagline` 长度不超过 64 字符，且不能以标点结尾。
- `permissions` 是**字符串表**（非数组），无权限时写 `permissions = {}`；
  需要时如 `permissions = { files = "Write" }`。
- `platforms` 需要带架构后缀，如 `windows-x64`、`linux-aarch64`、`macos-arm64` 等。
- `license`、`copyright`、`maintainer`、`python_version` 均必填。
- 扩展包的 `__init__.py` 必须位于**清单同目录**（即 `extension/` 根）。

## 项目结构

```
.
├── extension/                  # 扩展源码目录（清单与包同层）
│   ├── blender_manifest.toml   # 扩展清单（扩展的“身份证”）
│   ├── __init__.py             # 入口：版本单一来源 + register/unregister
│   ├── preferences.py          # AddonPreferences（bl_idname = __package__）
│   ├── properties.py           # PropertyGroup，挂载到 bpy.types.Scene
│   ├── operators.py            # Operator 定义
│   ├── ui.py                   # 3D 视图侧边栏面板
│   ├── keymap.py               # 快捷键注册与清理
│   └── utils.py                # 纯逻辑工具
├── build.ps1                   # Windows 构建脚本
├── Makefile                    # macOS/Linux 构建与开发命令
├── pyproject.toml              # 开发工具链配置
└── .github/workflows/ci.yml    # lint + typecheck + build CI
```

## 版本号

版本号只在 `extension/blender_manifest.toml` 的 `version` 中维护，
`extension/__init__.py` 读取它作为 `__version__` / `__version_info__`，避免多源不同步。

## 许可证

MIT，详见 [LICENSE](LICENSE)。
