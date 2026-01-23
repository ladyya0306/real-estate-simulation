@echo off
REM 房产交易仿真启动脚本

echo ========================================
echo 🏠 启动房产交易仿真 MVP...
echo ========================================

REM 1. 激活 Conda 环境
call conda activate oasis
if %errorlevel% neq 0 (
    echo ❌ 激活环境失败，尝试直接运行...
)

REM 2. 设置 API Key (如果没设置的话)
if "%DEEPSEEK_API_KEY%"=="" (
    echo.
    echo ⚠️ 未检测到 API Key，请临时输入：
    set /p DEEPSEEK_API_KEY="DeepSeek API Key: "
)

echo.
echo 🎬 仿真开始！(DeepSeek 驱动)
echo.

REM 3. 运行脚本
python real_estate_demo.py

echo.
echo ========================================
echo 🎉 运行结束
echo ========================================
pause
