@echo off
chcp 65001 >nul
title RPA网站服务器启动工具

echo ================================================
echo           RPA网站服务器启动工具
echo ================================================
echo.

echo 请设置SMS API配置:
echo.

set /p SMS_API_URL="SMS API URL (默认: https://www.sms-console.jp/api/): "
if "%SMS_API_URL%"=="" set SMS_API_URL=https://www.sms-console.jp/api/

set /p SMS_API_ID="SMS API ID: "
set /p SMS_API_PASSWORD="SMS API Password: "

if "%SMS_API_ID%"=="" (
    echo.
    echo ❌ 警告: 未设置SMS API配置，将使用Firebase配置模式
    echo    请确保已在网页界面中设置SMS配置
    echo.
    pause
) else (
    echo.
    echo ✅ SMS配置已设置:
    echo    URL: %SMS_API_URL%
    echo    ID: %SMS_API_ID%
    echo    Password: [已设置]
    echo.
)

echo 正在启动Node.js服务器...
echo 服务器将运行在: http://localhost:3001
echo.
echo 网页访问地址:
echo   - 登录页面: file:///c:/Users/xwang/OneDrive/lesson/SMS%%20PUBLISHER/src/frontend/login.html
echo   - 主应用页面: file:///c:/Users/xwang/OneDrive/lesson/SMS%%20PUBLISHER/src/frontend/main_app.html
echo.
echo 按 Ctrl+C 停止服务器
echo ================================================
echo.

cd /d "c:\Users\xwang\OneDrive\lesson\SMS PUBLISHER\src\backend"
node rpa_server.js

echo.
echo 服务器已停止
pause
