@echo off
cd /d "%~dp0"
echo 🚀 SMS Publisher - Vercel部署脚本
echo 当前目录: %CD%
echo.

echo 📋 检查Node.js...
node --version
if %errorlevel% neq 0 (
    echo ❌ Node.js未安装，请先安装Node.js
    pause
    exit /b 1
)

echo � 检查npm...
npm --version
if %errorlevel% neq 0 (
    echo ❌ npm未找到
    pause
    exit /b 1
)

echo 📦 安装项目依赖...
call npm install
if %errorlevel% neq 0 (
    echo ❌ 依赖安装失败
    pause
    exit /b 1
)

echo.
echo 🔄 使用npx部署到Vercel...
echo 如果这是第一次部署，系统会要求您登录Vercel账户
echo.
call npx vercel --prod
if %errorlevel% neq 0 (
    echo ❌ 部署失败
    pause
    exit /b 1
)

echo.
echo ✅ 部署完成！
echo 🌐 请查看终端输出的URL访问您的项目
echo.
pause
