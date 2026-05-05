@echo off
REM 批量处理所有PSO结果文件

cd /d "%~dp0"

for /L %%i in (2,1,23) do (
    if %%i LSS 10 (
        set "problem=p0%%i"
    ) else (
        set "problem=p%%i"
    )
    
    echo ========================================
    echo 处理 !problem!
    echo ========================================
    
    REM 合并数据
    python merge_pso_convergence.py pso_p01_p23_results\!problem!_pso_results.json
    
    REM 绘图
    python plot_pso_convergence.py pso_p01_p23_results\!problem!_pso_results_merged.json pso_p01_p23_results\
    
    echo.
)

echo ========================================
echo 所有文件处理完成！
echo ========================================
pause
