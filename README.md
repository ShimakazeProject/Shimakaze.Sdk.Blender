# Shimakaze SDK for Blender

一个基于 Blender 官方 **Extension（扩展）体系**（`blender_manifest.toml`）的 CnC/SHP 模板工具扩展，
支持 Blender **4.2 – 5.3**，并按运行版本自动选用对应渲染器的模板（4.x → Eevee Next，5.x → Hi Five）。

## 功能特性

- **模板自动下载**：当前 Blender 版本对应的模板缺失时，从
  `Zawaro/blender-cnc-templates` 的**固定版本 release**（当前 `v1.1.0`）下载对应
  渲染器的 `.zip` 并解出 `.blend`，不会使用 `latest`。
- **模板场景导入**：SHP 侧边栏面板中按「游戏 + 变体」向导导入模板场景
  （C&C Remastered / Dune 2000 / Red Alert / Tiberian Dawn / Red Alert 2 /
  ReWire / Tiberian Sun × 标准 / Effects / 步兵）。当前选中的物体（不复制）会
  递归链接进新场景，并归入 `Z=225°` 的 target 空对象。
- **渲染通道按钮**：Object / Buildup / Shadow / Preview / Reset，切换合成器
  通道开关与平面可见性。
- **批量渲染**：按方向数逐帧渲染 SHP 动画，每方向旋转 target，输出路径可配
  置模板，状态栏与进度条显示进度，支持 ESC 取消。
- **按版本适配**：合成器适配按渲染器分目录（`adaptations/eevee_next/`、
  `adaptations/hi_five/`），运行时根据版本动态导入。
- **界面语言**：面板顶部可选择 **English / 中文**，面板与提示信息随语言切换
  （静态工具提示保持英文源）。
- 版本号单一来源：`__init__.py` 直接读取清单中的 `version`。
- 构建脚本（`build.ps1` / `Makefile`）与 GitHub Actions CI。

## 环境要求

| 依赖 | 版本 |
| --- | --- |
| Blender | 4.2 – 5.3（4.x 用 Eevee Next，5.x 用 Hi Five 模板） |
| Python（仅开发用） | 3.10+ |

## 安装

### 方式一：作为扩展安装（推荐）

1. 构建扩展（见下），得到 `dist/shimakaze_sdk_blender-0.1.0.zip`。
2. Blender 菜单 **Edit > Preferences > Get Extensions > Install from Disk**，选择该 `.zip`。
3. 在 **Add-ons** 列表中启用 **Shimakaze SDK**。

### 方式二：开发模式

在 **Preferences > Get Extensions > Repositories** 中新增本地仓库，目录指向本仓库根目录。
Blender 会扫描仓库下的扩展子目录（含清单的 `extension/`），并在磁盘内容变化时热重载。

## 使用

1. 面板顶部会显示当前模板文件名；缺失时出现「下载模板」按钮；可在此选择界面语言
   （English / 中文）。
2. 选中要放入的物体后，选择游戏与变体，点击「导入场景」。
3. 导入后出现渲染通道按钮：先点一个通道（Object/Buildup/Shadow/Preview/Reset），
   需要时勾选 Alpha，再点「批量渲染」。
4. 面数（方向数）必须为 1 或 8 的倍数；勾选「反向」时每方向逆时针旋转。

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

### 适配新模板版本

不同模板版本需要不同的代码适配。新增渲染器时：

1. 在 `extension/adaptations/` 下新建与渲染器同名的子包，
   提供 `get_template_file_name()` 与 `repair_compositor(node_tree)`。
2. 在 `adaptations/__init__.py` 的 `current_template_renderer()` 中按 Blender
   版本映射到该渲染器。
3. 更新 `CNC_TEMPLATE_VERSION`（不要用 `latest`）。

## 项目结构

```
.
├── extension/                  # 扩展源码目录（清单与包同层）
│   ├── blender_manifest.toml   # 扩展清单（扩展的“身份证”）
│   ├── __init__.py             # 入口：版本单一来源 + register/unregister
│   ├── adaptations/            # 按渲染器分目录的模板适配
│   │   ├── __init__.py         # 运行时按版本分发（get_template_file_name / repair_compositor）
│   │   ├── _common.py          # 节点插座操作公共工具
│   │   ├── eevee_next/         # Blender 4.x：模板文件名 + 合成器修复
│   │   │   ├── __init__.py
│   │   │   └── compositor.py
│   │   └── hi_five/            # Blender 5.x：模板文件名 + 合成器修复
│   │       ├── __init__.py
│   │       └── compositor.py
│   ├── properties.py           # PropertyGroup，挂载到 Scene / WindowManager
│   ├── operators.py            # 导入、渲染通道、批量渲染、下载模板
│   ├── ui.py                   # 3D 视图侧边栏 SHP 面板
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
