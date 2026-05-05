# 快速开始：RouteFinder + GA-MDVRP 集成

## 一键运行（推荐）

### 方法 1: 使用 Python 脚本

```bash
# 在 system_test/ga_mdvrp_reproduction/ 目录下
python run_ga_with_routefinder.py p21
```

这会自动运行对比测试并显示结果。

### 方法 2: 使用批处理脚本

```bash
# 在 system_test/ga_mdvrp_reproduction/GA-MDVRP/ 目录下
compare_initialization.bat
```

## 详细步骤

### 步骤 1: 设置环境

```bash
cd system_test/ga_mdvrp_reproduction/GA-MDVRP
setup_gson.bat
```

### 步骤 2: 生成 RouteFinder 初始种群

```bash
cd RL4CO_Integration
python solve_p21_fixed.py
python convert_to_ga_format.py
```

### 步骤 3: 编译 Java 代码

```bash
cd system_test/ga_mdvrp_reproduction/GA-MDVRP
编译Java代码.bat
```

### 步骤 4: 运行测试

```bash
# 对比测试
compare_initialization.bat

# 或者单独运行 RouteFinder 初始化
run_p21_with_routefinder.bat
```

## 预期结果

### 纯随机初始化
- 初始 fitness: ~15000-20000
- 最终 fitness: ~7000-8000
- 收敛时间: 较慢

### RouteFinder 初始化
- 初始 fitness: ~8810 (RouteFinder 解)
- 最终 fitness: ~6000-7000 (预期更好)
- 收敛时间: 更快

### BKS (最优已知解)
- P21 BKS: 5474.84

## 观察要点

1. **初始种群质量**: RouteFinder 初始化应该从 ~8810 开始，而随机初始化从 ~15000 开始
2. **收敛速度**: 观察达到相同 fitness 所需的代数
3. **最终解质量**: 对比最终的 best fitness
4. **稳定性**: 多次运行，观察结果的方差

## 故障排除

### Gson 库未找到
```bash
cd system_test/ga_mdvrp_reproduction/GA-MDVRP
setup_gson.bat
```

### RouteFinder 种群未找到
```bash
cd RL4CO_Integration
python solve_p21_fixed.py
python convert_to_ga_format.py
```

### 编译失败
确保安装了 JDK 11 或更高版本：
```bash
java -version
javac -version
```

## 文件说明

### 输入文件
- `data/problems/p21` - P21 问题数据
- `RL4CO_Integration/p21_ga_initial_population.json` - RouteFinder 种子种群

### 输出文件
- `data/solutions/p21_random.res` - 纯随机初始化结果
- `data/solutions/p21_routefinder.res` - RouteFinder 初始化结果

## 下一步

1. 尝试其他问题实例 (p01-p23)
2. 调整种群大小和代数
3. 分析收敛曲线
4. 优化混合比例（RouteFinder vs 随机）

## 技术支持

详细文档请参考：
- `GA-MDVRP/ROUTEFINDER_INTEGRATION.md` - 集成技术文档
- `RL4CO_Integration/GA_INIT_README.md` - RouteFinder 导出文档
