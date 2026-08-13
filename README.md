# Shimakaze SDK for Blender

面向 CnC/SHP 精灵渲染的 Blender 扩展（Blender 4.2–5.3，按运行版本自动选用 Eevee Next / Hi Five 模板）。

## 功能

- **模板自动下载**：缺失时从固定版本 release 获取对应渲染器的模板
- **模板场景导入**：按「游戏 + 变体」导入模板场景，选中物体递归链接并归入 target 空对象
- **渲染通道**：Object / Buildup / Shadow / Preview / Reset 一键切换
- **批量渲染**：按方向数逐帧渲染动画，逐方向旋转 target，带进度条与状态栏，可取消
- **阻隔着色器**：批量为列表外材质应用 Holdout，服务所属色工作流
- **界面语言**：English / 中文

## 所属色

阻隔着色器是为 [Shimakaze.Sdk](https://github.com/ShimakazeProject/Shimakaze.Sdk) 的所属色工作流设计的。

模型上作为所属色（玩家色）的区域，传统做法需渲染前改色或转 SHP 后替换颜色，繁琐且模型本身含该颜色时结果不可预期。Shimakaze.Sdk 的 SHP 工具采用分步转换：

1. 用非所属色（色板 32–240）范围的颜色转换对象图片
2. 用所属色（色板 16–32）范围的颜色转换所属色图片
3. 合并为 SHP 帧

阻隔着色器把场景中非目标材质设为 Holdout，只保留需要渲染的对象，从而分别产出对象图与所属色图。
