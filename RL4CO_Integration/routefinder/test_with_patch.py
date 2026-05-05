"""
RouteFinder测试脚本 - 带兼容性补丁

在加载checkpoint之前应用TorchRL兼容性补丁
"""

# ============================================================
# 步骤1: 应用兼容性补丁 (必须在所有import之前)
# ============================================================
print("=" * 60)
print("应用TorchRL兼容性补丁...")
print("=" * 60)

try:
    from torchrl.data.tensor_specs import Composite
    import torchrl.data.tensor_specs as specs
    
    # 添加CompositeSpec别名以兼容旧checkpoint
    if not hasattr(specs, 'CompositeSpec'):
        specs.CompositeSpec = Composite
        print("✓ CompositeSpec别名已添加 (Composite -> CompositeSpec)")
    else:
        print("✓ CompositeSpec已存在")
        
    # 验证
    from torchrl.data.tensor_specs import CompositeSpec
    print("✓ 补丁验证成功")
    
except Exception as e:
    print(f"✗ 补丁应用失败: {e}")
    print("尝试继续...")

print()

# ============================================================
# 步骤2: 导入并运行原始test.py
# ============================================================

# 现在可以安全地导入test.py的内容
import sys
import os

# 确保在routefinder目录
if not os.path.exists('test.py'):
    print("✗ 错误: 请在routefinder目录下运行此脚本")
    print("  cd E:\\GraduationDesign\\RL4CO_Integration\\routefinder")
    print("  python test_with_patch.py --checkpoint checkpoints/100/rf-transformer.ckpt --problem cvrp --size 100")
    sys.exit(1)

# 执行原始test.py
print("=" * 60)
print("运行RouteFinder测试...")
print("=" * 60)
print()

# 导入test.py的main逻辑
exec(open('test.py').read())
