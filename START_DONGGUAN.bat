@echo off
chcp 65001 >nul
title [窗口A] 东莞房产市场仿真生成器

echo ========================================================
echo 🏘️  Oasis 东莞房产仿真启动器 (Direct Mode)
echo ========================================================
echo.

rem 设置 Python 解释器的绝对路径
set PYTHON_EXE=C:\Users\wyl\anaconda3\envs\oasis\python.exe

rem 检查解释器是否存在
if not exist "%PYTHON_EXE%" (
    echo ❌ 错误：找不到 Python 解释器！
    echo 路径不存在: %PYTHON_EXE%
    echo 请检查 Anaconda 安装路径。
    pause
    exit /b
)

echo [1/2] 检查 API Key...
if "%DEEPSEEK_API_KEY%"=="" (
    set DEEPSEEK_API_KEY=sk-45765318152f49cbafae11286f222697
    echo ✅ 已自动注入默认 API Key
) else (
    echo ✅ 检测到已有 API Key
)

echo.
echo [2/2] 启动仿真引擎 (dongguan_market.py)...
echo --------------------------------------------------------
echo ⚠️  提示：请确保在另一个窗口已经运行了 Streamlit 看板：
echo    streamlit run real_estate_app.py
echo --------------------------------------------------------
echo.
echo 正在使用解释器: %PYTHON_EXE%
echo 正在模拟松山湖、南城等地交易... (请耐心等待)
echo.

"%PYTHON_EXE%" dongguan_market.py

echo.
echo ========================================================
echo 🎉 仿真结束！请去浏览器刷新看板查看结果。
echo ========================================================
pause
