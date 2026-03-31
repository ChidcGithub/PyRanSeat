<#
.SYNOPSIS
    PyRanSeat 一键启动脚本
    
.DESCRIPTION
    自动检查环境、安装依赖并启动教室座位编排应用
    
.NOTES
    适用于 Windows PowerShell 5.1+
#>

# 设置控制台编码
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 颜色输出函数
function Write-ColorHost {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

# 打印横幅
function Show-Banner {
    Write-Host ""
    Write-ColorHost "================================================" "Cyan"
    Write-ColorHost "       PyRanSeat - 教室座位编排工具" "Green"
    Write-ColorHost "================================================" "Cyan"
    Write-Host ""
}

# 检查 Python 环境
function Test-Python {
    Write-ColorHost "[*] 检查 Python 环境..." "Yellow"
    
    $pythonCmd = $null
    
    # 尝试 python 命令
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $pythonCmd = "python"
    }
    # 尝试 python3 命令
    elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
        $pythonCmd = "python3"
    }
    
    if (-not $pythonCmd) {
        Write-ColorHost "[X] 未找到 Python，请先安装 Python 3.8+" "Red"
        Write-ColorHost "    下载地址: https://www.python.org/downloads/" "White"
        exit 1
    }
    
    # 获取版本
    $version = & $pythonCmd --version 2>&1
    Write-ColorHost "[OK] 找到 $version" "Green"
    
    return $pythonCmd
}

# 安装依赖
function Install-Dependencies {
    param([string]$PythonCmd)
    
    Write-ColorHost "[*] 检查依赖..." "Yellow"
    
    # 检查是否已安装 Flask
    $flaskInstalled = & $PythonCmd -c "import flask; print(flask.__version__)" 2>$null
    
    if ($flaskInstalled) {
        Write-ColorHost "[OK] Flask 已安装 (版本: $flaskInstalled)" "Green"
        return
    }
    
    Write-ColorHost "[*] 正在安装 Flask..." "Yellow"
    
    # 升级 pip
    & $PythonCmd -m pip install --upgrade pip --quiet 2>$null
    
    # 安装依赖
    $installResult = & $PythonCmd -m pip install -r requirements.txt 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-ColorHost "[OK] 依赖安装完成" "Green"
    } else {
        Write-ColorHost "[X] 依赖安装失败" "Red"
        Write-Host $installResult
        exit 1
    }
}

# 启动应用
function Start-Application {
    param([string]$PythonCmd)
    
    Write-ColorHost "[*] 启动应用..." "Yellow"
    Write-Host ""
    
    # 获取脚本所在目录
    $scriptDir = Split-Path -Parent $MyInvocation.ScriptName
    if (-not $scriptDir) {
        $scriptDir = $PWD.Path
    }
    
    # 切换到应用目录
    Set-Location $scriptDir
    
    # 启动 Flask 服务器（后台运行）
    $job = Start-Job -ScriptBlock {
        param($dir, $cmd)
        Set-Location $dir
        & $cmd app.py 2>&1
    } -ArgumentList $scriptDir, $PythonCmd
    
    # 等待服务器启动
    Write-ColorHost "[*] 等待服务器启动..." "Yellow"
    Start-Sleep -Seconds 3
    
    # 检查服务器是否成功启动
    $maxRetries = 5
    $retryCount = 0
    $serverReady = $false
    
    while ($retryCount -lt $maxRetries) {
        try {
            $response = Invoke-WebRequest -Uri "http://127.0.0.1:5000" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                $serverReady = $true
                break
            }
        } catch {
            # 忽略错误，继续重试
        }
        Start-Sleep -Seconds 1
        $retryCount++
    }
    
    if ($serverReady) {
        Write-ColorHost "[OK] 服务器已启动" "Green"
        Write-Host ""
        Write-ColorHost "================================================" "Cyan"
        Write-ColorHost "  应用地址: http://127.0.0.1:5000" "White"
        Write-ColorHost "  按 Ctrl+C 可停止服务器" "White"
        Write-ColorHost "================================================" "Cyan"
        Write-Host ""
        
        # 打开浏览器
        Write-ColorHost "[*] 正在打开浏览器..." "Yellow"
        Start-Process "http://127.0.0.1:5000"
        
        # 保持脚本运行，显示服务器输出
        Write-ColorHost "[*] 服务器运行中，按任意键停止..." "Yellow"
        
        # 接收作业输出
        while ($true) {
            $output = Receive-Job -Job $job -ErrorAction SilentlyContinue
            if ($output) {
                $output | ForEach-Object { Write-Host $_ }
            }
            
            if ([Console]::KeyAvailable) {
                $key = [Console]::ReadKey($true)
                if ($key.Key -eq 'Q' -or $key.Key -eq 'Escape') {
                    break
                }
            }
            
            Start-Sleep -Milliseconds 100
        }
        
        # 清理
        Stop-Job -Job $job
        Remove-Job -Job $job
        Write-ColorHost "[*] 服务器已停止" "Yellow"
    } else {
        Write-ColorHost "[X] 服务器启动失败" "Red"
        
        # 显示错误日志
        $output = Receive-Job -Job $job -ErrorAction SilentlyContinue
        if ($output) {
            Write-Host $output
        }
        
        Stop-Job -Job $job
        Remove-Job -Job $job
        exit 1
    }
}

# 主程序
function Main {
    Show-Banner
    
    $pythonCmd = Test-Python
    Install-Dependencies -PythonCmd $pythonCmd
    Start-Application -PythonCmd $pythonCmd
}

# 运行主程序
Main
