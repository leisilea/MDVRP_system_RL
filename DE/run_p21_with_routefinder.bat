@echo off
chcp 65001 >nul
echo ============================================================
echo 运行 GA-MDVRP P21 测试 (使用 RouteFinder 初始化)
echo ============================================================
echo.

cd /d "%~dp0"

echo 检查编译输出...
if not exist "out\MainCLI.class" (
    echo ❌ 未找到编译输出，请先运行 编译Java代码.bat
    pause
    exit /b 1
)
echo ✓ 编译输出存在
echo.

echo 检查 Gson 库...
if not exist "lib\gson-2.10.1.jar" (
    echo ❌ Gson 库未找到
    echo 请运行 setup_gson.bat 下载 Gson 库
    pause
    exit /b 1
)
echo ✓ Gson 库存在
echo.

echo 检查 RouteFinder 初始种群...
set SEED_PATH=..\..\..\RL4CO_Integration\p21_ga_initial_population.json
if not exist "%SEED_PATH%" (
    echo ❌ RouteFinder 初始种群未找到: %SEED_PATH%
    echo 请先运行 RL4CO_Integration 中的脚本生成初始种群
    pause
    exit /b 1
)
echo ✓ RouteFinder 初始种群存在
echo.

echo 运行 GA-MDVRP...
echo 问题: P21
echo 初始种群: RouteFinder (10 individuals)
echo.
echo ============================================================
echo.

java -cp "out;lib\gson-2.10.1.jar" MainCLI data/problems/p21 data/solutions/p21_routefinder.res "%SEED_PATH%"

echo.
echo ============================================================
if errorlevel 1 (
    echo ❌ 运行失败
) else (
    echo ✓ 运行完成
    echo 解决方案已保存到: data/solutions/p21_routefinder.res
)
echo ============================================================
echo.
pause
