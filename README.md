# PyRanSeat

> 教室座位编排工具，减轻教师工作压力

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Build Windows EXE](https://github.com/ChidcGithub/PyRanSeat/actions/workflows/build-windows.yml/badge.svg)](https://github.com/ChidcGithub/PyRanSeat/actions/workflows/build-windows.yml)

## 功能特性

- **随机排座** - 一键随机分配学生座位
- **约束排座** - 支持设置学生之间的座位约束
  - 规避（avoid）：两个学生不能相邻
  - 坐一起（together）：两个学生必须相邻
- **前后排轮换** - 前排与后排互换位置
- **大组轮换** - 按列或行分组进行轮换
- **座位交换** - 手动交换两个座位的学生
- **数据持久化** - 座位数据自动保存到本地

## 快速开始

### 环境要求

- Python 3.8 或更高版本

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行程序

```bash
python app.py
```

启动后访问 http://127.0.0.1:5000

### Windows 可执行文件

在 [Releases](https://github.com/ChidcGithub/PyRanSeat/releases) 页面下载最新的 Windows 可执行文件，无需安装 Python 环境即可运行。

## API 文档

### 获取座位信息

```
GET /api/seats
```

返回当前座位矩阵、行列数、学生列表和约束列表。

### 更新教室配置

```
POST /api/config
```

参数：
- `rows`: 行数 (1-20)
- `cols`: 列数 (1-20)

### 更新学生名单

```
POST /api/students
```

参数：
- `students`: 学生姓名列表

### 随机排座

```
POST /api/randomize
```

随机分配学生座位，自动优化约束条件。

### 交换座位

```
POST /api/swap
```

参数：
- `pos1`: 座位1坐标 `[row, col]`
- `pos2`: 座位2坐标 `[row, col]`

### 重置座位

```
POST /api/reset
```

清空所有座位的学生。

### 约束管理

```
GET /api/constraints          # 获取约束列表
POST /api/constraints         # 添加约束
DELETE /api/constraints       # 删除约束
```

约束参数：
- `studentA`: 学生A姓名
- `studentB`: 学生B姓名
- `type`: 约束类型 (`avoid` 或 `together`)

### 轮换功能

```
POST /api/row_swap            # 前后排轮换
POST /api/group_rotate        # 大组轮换
```

大组轮换参数：
- `groupBy`: 分组方式 (`col` 按列, `row` 按行)
- `groupSize`: 每组大小
- `direction`: 轮换方向 (`right`, `left`)

## 数据存储

座位数据存储在 `data/seat_data.json` 文件中，包含：

- `rows`: 行数
- `cols`: 列数
- `seats`: 座位矩阵
- `students`: 学生名单
- `constraints`: 约束列表

## 技术栈

- **后端**: Python Flask
- **前端**: HTML/CSS/JavaScript
- **数据存储**: JSON 文件

## 开发

### 本地开发

```bash
# 克隆仓库
git clone https://github.com/ChidcGithub/PyRanSeat.git
cd PyRanSeat

# 安装依赖
pip install -r requirements.txt

# 运行开发服务器
python app.py
```

### 打包可执行文件

```bash
# 安装 PyInstaller
pip install pyinstaller

# 打包
pyinstaller pyranseat.spec
```

## 许可证

[MIT License](LICENSE)

## 作者

Chidc

## 贡献

欢迎提交 Issue 和 Pull Request！
