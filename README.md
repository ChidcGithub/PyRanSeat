<div align="center">

# PyRanSeat

**教室座位编排工具** - 让排座变得简单高效

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Build Status](https://github.com/ChidcGithub/PyRanSeat/actions/workflows/build-windows.yml/badge.svg)](https://github.com/ChidcGithub/PyRanSeat/actions/workflows/build-windows.yml)
[![Release](https://img.shields.io/github/v/release/ChidcGithub/PyRanSeat?include_prereleases)](https://github.com/ChidcGithub/PyRanSeat/releases)

[English](README_EN.md) | 简体中文

<img src="https://img.shields.io/badge/平台-Windows-0078D6?logo=windows&logoColor=white" alt="Platform"/>
<img src="https://img.shields.io/badge/框架-Flask-000000?logo=flask&logoColor=white" alt="Flask"/>

</div>

---

## 简介

PyRanSeat 是一款专为教师设计的教室座位编排工具，旨在简化座位安排流程，提高教学管理效率。支持随机排座、约束条件设置、多种轮换模式等功能，让座位编排更加科学合理。

## 功能特性

### 核心功能

| 功能 | 描述 |
|:-----|:-----|
| **随机排座** | 一键随机分配学生座位，公平高效 |
| **约束排座** | 设置学生之间的座位关系约束 |
| **前后排轮换** | 前排与后排互换，保证公平性 |
| **大组轮换** | 按列或行分组进行轮换 |
| **座位交换** | 手动调整个别学生座位 |
| **数据持久化** | 自动保存座位配置，下次打开继续使用 |

### 约束条件

- **规避 (Avoid)**: 设置两个学生不能相邻就座
- **坐一起 (Together)**: 设置两个学生必须相邻就座

## 快速开始

### 方式一：直接运行可执行文件（推荐）

前往 [Releases](https://github.com/ChidcGithub/PyRanSeat/releases) 页面下载最新的 `PyRanSeat.exe`，双击运行即可。

启动后访问: http://127.0.0.1:5000

### 方式二：从源码运行

```bash
# 克隆仓库
git clone https://github.com/ChidcGithub/PyRanSeat.git
cd PyRanSeat

# 安装依赖
pip install -r requirements.txt

# 运行
python app.py
```

### 环境要求

- Python 3.8+ （从源码运行时需要）
- 现代浏览器（Chrome、Firefox、Edge 等）

## 使用指南

### 1. 配置教室

设置教室的行数和列数，适配不同大小的教室。

### 2. 导入学生名单

输入学生姓名，每行一个姓名，或使用逗号/空格分隔。

### 3. 设置约束（可选）

为学生设置座位约束条件，系统会自动优化排座结果。

### 4. 开始排座

点击「随机排座」按钮，系统自动分配座位并优化约束条件。

### 5. 轮换与调整

- 使用「前后排轮换」定期调整学生位置
- 使用「大组轮换」按组进行位置调整
- 点击两个座位可手动交换学生

## API 参考

| 端点 | 方法 | 描述 |
|:-----|:-----|:-----|
| `/api/seats` | GET | 获取当前座位信息 |
| `/api/config` | POST | 更新教室配置 |
| `/api/students` | POST | 更新学生名单 |
| `/api/randomize` | POST | 随机排座 |
| `/api/swap` | POST | 交换座位 |
| `/api/reset` | POST | 重置座位 |
| `/api/constraints` | GET/POST/DELETE | 约束管理 |
| `/api/row_swap` | POST | 前后排轮换 |
| `/api/group_rotate` | POST | 大组轮换 |

## 技术架构

```
PyRanSeat/
├── app.py              # Flask 后端服务
├── templates/
│   └── index.html      # 前端界面
├── data/
│   └── seat_data.json  # 数据存储
├── pyranseat.spec      # PyInstaller 配置
└── requirements.txt    # Python 依赖
```

**技术栈**: Python + Flask + HTML/CSS/JavaScript

## 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 许可证

本项目基于 [MIT License](LICENSE) 开源。

---

<div align="center">

**Made with ❤️ by [Chidc](https://github.com/ChidcGithub)**

如果这个项目对你有帮助，请给一个 ⭐ Star 支持一下！

</div>