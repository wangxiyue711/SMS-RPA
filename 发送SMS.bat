@echo off
chcp 65001 >nul
title 简单SMS发送工具
echo.
echo ================================================
echo           简单SMS发送工具
echo ================================================
echo.
echo 使用说明：
echo 1. 准备好您的SMS API配置信息
echo 2. 准备好要发送的手机号和消息内容
echo 3. 按照提示输入信息即可发送
echo.
echo 按任意键开始...
pause >nul
echo.

python simple_sms_tool.py

echo.
echo 程序已结束
pause
