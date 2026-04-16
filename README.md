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
