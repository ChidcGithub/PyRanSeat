<div align="center">

# PyRanSeat

**Classroom Seating Arrangement Tool** - Make seating simple and efficient

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Build Status](https://github.com/ChidcGithub/PyRanSeat/actions/workflows/build-windows.yml/badge.svg)](https://github.com/ChidcGithub/PyRanSeat/actions/workflows/build-windows.yml)
[![Release](https://img.shields.io/github/v/release/ChidcGithub/PyRanSeat?include_prereleases)](https://github.com/ChidcGithub/PyRanSeat/releases)

English | [简体中文](README.md)

<img src="https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white" alt="Platform"/>
<img src="https://img.shields.io/badge/Framework-Flask-000000?logo=flask&logoColor=white" alt="Flask"/>

</div>

---

## Overview

PyRanSeat is a classroom seating arrangement tool designed for teachers to simplify the seating process and improve teaching management efficiency. It supports random seating, constraint settings, multiple rotation modes, and more.

## Features

### Core Features

| Feature | Description |
|:--------|:------------|
| **Random Seating** | One-click random seat assignment, fair and efficient |
| **Constraint Seating** | Set seating relationship constraints between students |
| **Front-Back Rotation** | Swap front and back rows for fairness |
| **Group Rotation** | Rotate by columns or rows in groups |
| **Seat Swap** | Manually adjust individual student seats |
| **Data Persistence** | Auto-save seat configuration for next session |

### Constraint Types

- **Avoid**: Set two students to not sit adjacent to each other
- **Together**: Set two students to sit adjacent to each other

## Quick Start

### Option 1: Run Executable (Recommended)

Download the latest `PyRanSeat.exe` from the [Releases](https://github.com/ChidcGithub/PyRanSeat/releases) page and double-click to run.

Access at: http://127.0.0.1:5000

### Option 2: Run from Source

```bash
# Clone repository
git clone https://github.com/ChidcGithub/PyRanSeat.git
cd PyRanSeat

# Install dependencies
pip install -r requirements.txt

# Run
python app.py
```

### Requirements

- Python 3.8+ (required for source code execution)
- Modern browser (Chrome, Firefox, Edge, etc.)

## Usage Guide

### 1. Configure Classroom

Set the number of rows and columns to match your classroom size.

### 2. Import Student List

Enter student names, one per line, or separate with commas/spaces.

### 3. Set Constraints (Optional)

Set seating constraints for students; the system will automatically optimize seating results.

### 4. Start Seating

Click the "Random Seating" button to automatically assign seats and optimize constraints.

### 5. Rotation & Adjustment

- Use "Front-Back Rotation" to periodically adjust student positions
- Use "Group Rotation" to rotate positions by groups
- Click two seats to manually swap students

## API Reference

| Endpoint | Method | Description |
|:---------|:-------|:------------|
| `/api/seats` | GET | Get current seating information |
| `/api/config` | POST | Update classroom configuration |
| `/api/students` | POST | Update student list |
| `/api/randomize` | POST | Random seating assignment |
| `/api/swap` | POST | Swap seats |
| `/api/reset` | POST | Reset seating |
| `/api/constraints` | GET/POST/DELETE | Constraint management |
| `/api/row_swap` | POST | Front-back row rotation |
| `/api/group_rotate` | POST | Group rotation |

## Architecture

```
PyRanSeat/
├── app.py              # Flask backend service
├── templates/
│   └── index.html      # Frontend interface
├── data/
│   └── seat_data.json  # Data storage
├── pyranseat.spec      # PyInstaller configuration
└── requirements.txt    # Python dependencies
```

**Tech Stack**: Python + Flask + HTML/CSS/JavaScript

## Contributing

Issues and Pull Requests are welcome!

1. Fork this repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Create a Pull Request

## License

This project is open-sourced under the [MIT License](LICENSE).

---

<div align="center">

**Made with ❤️ by [Chidc](https://github.com/ChidcGithub)**

If this project helps you, please give it a ⭐ Star!

</div>
