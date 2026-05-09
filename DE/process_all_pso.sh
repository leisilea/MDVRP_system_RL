#!/bin/bash
# 批量处理所有PSO结果文件

cd "$(dirname "$0")"

for i in {2..23}; do
    problem=$(printf "p%02d" $i)
    echo "========================================"
    echo "处理 ${problem}"
    echo "========================================"
    
    # 合并数据
    python merge_pso_convergence.py pso_p01_p23_results/${problem}_pso_results.json
    
    # 绘图
    python plot_pso_convergence.py pso_p01_p23_results/${problem}_pso_results_merged.json pso_p01_p23_results/
    
    echo ""
done

echo "========================================"
echo "所有文件处理完成！"
echo "========================================"
