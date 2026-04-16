# 文档 AI 脱敏工具

一个本地文档脱敏工具，让你安全地使用在线 AI 处理敏感文档。通过在本地完成文档脱敏，你可以放心地将处理后的文档提交给各类在线 AI 服务。

最新免安装版本网盘下载（推荐）： [0.5.0](https://pan.quark.cn/s/f630b3d7229e)

最新资讯、获取微信群最新二维码，请关注公众号：偷偷成精的咸鱼

[详细教程介绍与教程](介绍与教程.md)

## ✨ 主要功能

- 📄 支持多种文档格式：PDF（含扫描版）、Word（docx、doc）
- 🤖 智能文档转换：自动将文档转换为 LLM 友好的 markdown 格式
- 🔒 智能脱敏处理：
  - 默认识别：人名、地名、机构名、手机号、身份证号、银行卡号、电子邮箱、IPv4地址、时间
  - 脱敏格式：`__MASKED_{entity_type}_{uuid}__`
- ⚙️ 自定义功能：
  - 支持自定义敏感词识别
  - 支持自定义脱敏词及对应的脱敏值
- 💾 持久化存储：同一敏感信息在不同文档中保持一致的脱敏值
- 🔄 一键解敏：支持将 AI 处理后的文档快速还原

## 🚀 快速开始

### 系统要求

- Python 3.10 或更高版本
- 8GB 或以上内存
- 约 5.2GB 磁盘空间（用于存储 AI 模型）

### Windows 安装步骤

1. 下载本仓库：
   ```bash
   git clone https://github.com/NextDoorLaoHuang-HF/Local_Document_AI_Desensitization_Tool.git
   cd Local_Document_AI_Desensitization_Tool
   ```
2. 安装 Python 3.10+（如未安装）
3. 如需处理 Office 文档，请安装 [LibreOffice](https://www.libreoffice.org/download/download/)
4. 双击运行 `run.bat`
5. 等待安装依赖、下载模型

### macOS 安装步骤

1. 下载本仓库
2. 安装 Python 3.10+（如未安装）：
   ```bash
   brew install python@3.10
   ```
3. 安装 LibreOffice（如需处理office文档）：
   ```bash
   brew install --cask libreoffice
   ```
4. 为启动脚本添加执行权限：
   ```bash
   chmod +x /Users/huangweihao/Local_Document_AI_Desensitization_Tool/run.sh
   ```
5. 运行启动脚本：
   ```bash
   ./run.sh
   ```

## 📢 即将推出

可能会开发一个更轻量级、更易于使用的版本，敬请期待！
- 更小的模型体积
- 更快的处理速度
- 更简单的安装步骤
- 更友好的用户界面

## 📄 许可证

本项目采用 [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0) 许可证。

## 反馈、交流


![微信群二维码](pic/微信群.png)





## 🆕 Lite 聊天 TXT 脱敏子应用

为聊天记录蒸馏前清洗新增了独立 lite 子应用（不走原 PDF/Word/OCR 主流程）：

- 入口：`Data_Masking/ui/chat_gui_app.py`
- 支持聊天头格式：`YYYY-MM-DD HH:MM:SS '发送者'`
- 默认极速模式：仅规则+词典+上下文，低资源占用
- 严格模式：可选开启 NER（仅启用时检查模型）
- 白名单：`config/whitelist.txt`
- 大文件处理：流式解析，GUI 仅预览前 200 行、前 500 条命中
- 本地映射恢复：支持恢复原文与一键清空映射

### Lite 运行

```bash
# macOS / Linux
./run_lite.sh

# Windows
run_lite.bat
```

### Lite 打包

```bash
# macOS: 产出 .app（在 dist/chat_desensitizer_lite.app）
./build_lite.sh

# Windows: 产出 .exe（在 dist/chat_desensitizer_lite/ 或单文件配置）
build_lite.bat
```


### macOS 芯片兼容说明（Intel + Apple Silicon）

- `build_lite.sh` 会优先尝试 `--target-arch universal2`（同时支持 Intel + Apple Silicon）；若当前 Python/PyInstaller 工具链不支持，会自动回退到本机架构打包，避免构建冲突。
- 若应用双击闪退，可在终端执行以下命令查看报错：

```bash
./dist/chat_desensitizer_lite.app/Contents/MacOS/chat_desensitizer_lite
```

- Lite 应用的映射文件会写入用户目录：
  - `~/Library/Application Support/Local_Document_AI_Desensitization_Tool/chat_lite_masking_map.pkl`
  - 避免写入 `.app` 内部导致权限问题。
