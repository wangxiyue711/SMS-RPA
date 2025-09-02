@echo off
title SMS API Configuration Setup
echo ================================
echo     SMS API 配置设置
echo ================================
echo.
echo 请输入您的SMS API配置信息：
echo.

set /p SMS_API_ID="SMS API ID: "
set /p SMS_API_PASSWORD="SMS API Password: "

echo.
echo 设置环境变量...

setx SMS_API_URL "https://www.sms-console.jp/api/"
setx SMS_API_ID "%SMS_API_ID%"
setx SMS_API_PASSWORD "%SMS_API_PASSWORD%"

echo.
echo ✅ 配置已保存到系统环境变量！
echo.
echo 注意：环境变量设置后需要重启命令行或重新启动程序才能生效。
echo.
pause
