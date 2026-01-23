@echo off
chcp 65001 >nul
title [窗口B] 房产交易可视化看板

echo ========================================================
echo 📊 正在启动 Oasis 交易看板 (Streamlit)
echo ========================================================
echo.

rem 设置 Python 解释器的绝对路径
set PYTHON_EXE=C:\Users\wyl\anaconda3\envs\oasis\python.exe

if not exist "%PYTHON_EXE%" (
    echo ❌ 错误：找不到 Python 解释器！
    pause
    exit /b
)

echo 正在使用解释器: %PYTHON_EXE%
echo 请稍候，浏览器将自动打开...
echo.

"%PYTHON_EXE%" -m streamlit run real_estate_app.py

pause
