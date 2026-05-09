@echo off
chcp 65001 >nul
echo ============================================================
echo 编译 GA-MDVRP Java 代码
echo ============================================================
echo.

cd /d "%~dp0"

echo 检查 Java 环境...
java -version
if errorlevel 1 (
    echo ❌ Java 未安装或未配置到 PATH
    pause
    exit /b 1
)
echo.

echo 检查 javac 编译器...
javac -version
if errorlevel 1 (
    echo ❌ javac 未找到，请确保安装了 JDK（不是 JRE）
    pause
    exit /b 1
)
echo.

echo 检查 Gson 库...
if not exist "lib\gson-2.10.1.jar" (
    echo ❌ Gson 库未找到
    echo 请运行 setup_gson.bat 下载 Gson 库
    pause
    exit /b 1
)
echo ✓ Gson 库: lib\gson-2.10.1.jar
echo.

echo 创建输出目录...
if not exist "out" mkdir out
echo ✓ 输出目录: out\
echo.

echo 开始编译...
echo 源代码目录: src\
echo 编译 CLI 版本（无需 JavaFX）...
echo.

javac -cp "lib\gson-2.10.1.jar" -d out -sourcepath src -encoding UTF-8 src\MainCLI.java

if errorlevel 1 (
    echo.
    echo ❌ 编译失败！
    echo 请检查错误信息
    pause
    exit /b 1
)

echo.
echo ============================================================
echo ✓ 编译成功！
echo ============================================================
echo.
echo 编译输出位置: out\
echo 主类: MainCLI （命令行版本，无需 JavaFX）
echo.
echo 现在可以运行测试脚本了
echo.
pause
