"""
运行 GA-MDVRP 并使用 RouteFinder 初始化
"""
import subprocess
import os
import sys
from pathlib import Path

def run_ga_mdvrp(problem_file, output_file=None, seed_population_path=None, verbose=True):
    """
    运行 GA-MDVRP
    
    Args:
        problem_file: 问题文件路径 (例如: "data/problems/p21")
        output_file: 输出文件路径 (可选)
        seed_population_path: RouteFinder 种子种群 JSON 路径 (可选)
        verbose: 是否打印详细输出
    
    Returns:
        (success, best_fitness, output)
    """
    ga_dir = Path(__file__).parent / "GA-MDVRP"
    
    # 检查编译输出
    if not (ga_dir / "out" / "MainCLI.class").exists():
        print("❌ GA-MDVRP 未编译，请先运行 编译Java代码.bat")
        return False, None, None
    
    # 检查 Gson 库
    if not (ga_dir / "lib" / "gson-2.10.1.jar").exists():
        print("❌ Gson 库未找到，请运行 setup_gson.bat")
        return False, None, None
    
    # 构建命令
    cmd = [
        "java",
        "-cp", f"out;lib{os.sep}gson-2.10.1.jar",
        "MainCLI",
        problem_file
    ]
    
    if output_file:
        cmd.append(output_file)
    
    if seed_population_path:
        cmd.append(seed_population_path)
    
    if verbose:
        print(f"运行命令: {' '.join(cmd)}")
        print(f"工作目录: {ga_dir}")
        print()
    
    # 运行
    try:
        result = subprocess.run(
            cmd,
            cwd=ga_dir,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        output = result.stdout
        if verbose:
            print(output)
        
        if result.returncode != 0:
            print("❌ 运行失败")
            print(result.stderr)
            return False, None, output
        
        # 提取最佳 fitness
        best_fitness = None
        for line in output.split('\n'):
            if 'Total distance best solution:' in line:
                try:
                    best_fitness = float(line.split(':')[1].strip())
                except:
                    pass
        
        return True, best_fitness, output
        
    except Exception as e:
        print(f"❌ 运行出错: {e}")
        return False, None, None


def compare_initialization(problem="p21", verbose=True):
    """
    对比纯随机初始化 vs RouteFinder 初始化
    
    Args:
        problem: 问题名称 (例如: "p21")
        verbose: 是否打印详细输出
    
    Returns:
        (random_fitness, routefinder_fitness)
    """
    ga_dir = Path(__file__).parent / "GA-MDVRP"
    problem_file = f"data/problems/{problem}"
    
    # RouteFinder 种子种群路径
    seed_path = Path(__file__).parent.parent / "RL4CO_Integration" / f"{problem}_ga_initial_population.json"
    
    if not seed_path.exists():
        print(f"❌ RouteFinder 种子种群未找到: {seed_path}")
        print(f"请先运行 RL4CO_Integration 中的脚本生成初始种群")
        return None, None
    
    print("="*70)
    print("GA-MDVRP 初始化方法对比测试")
    print("="*70)
    print()
    
    # 测试 1: 纯随机初始化
    print("测试 1/2: 纯随机初始化")
    print("-"*70)
    success1, fitness1, _ = run_ga_mdvrp(
        problem_file,
        f"data/solutions/{problem}_random.res",
        seed_population_path=None,
        verbose=verbose
    )
    
    if not success1:
        print("❌ 纯随机初始化测试失败")
        return None, None
    
    print()
    print("="*70)
    print()
    
    # 测试 2: RouteFinder 初始化
    print("测试 2/2: RouteFinder 初始化")
    print("-"*70)
    success2, fitness2, _ = run_ga_mdvrp(
        problem_file,
        f"data/solutions/{problem}_routefinder.res",
        seed_population_path=str(seed_path),
        verbose=verbose
    )
    
    if not success2:
        print("❌ RouteFinder 初始化测试失败")
        return fitness1, None
    
    print()
    print("="*70)
    print("对比结果")
    print("="*70)
    print(f"纯随机初始化:      {fitness1:.2f}")
    print(f"RouteFinder 初始化: {fitness2:.2f}")
    
    if fitness1 and fitness2:
        improvement = ((fitness1 - fitness2) / fitness1) * 100
        print(f"改进:              {improvement:.2f}%")
    
    print("="*70)
    
    return fitness1, fitness2


if __name__ == "__main__":
    if len(sys.argv) > 1:
        problem = sys.argv[1]
    else:
        problem = "p21"
    
    compare_initialization(problem, verbose=True)
