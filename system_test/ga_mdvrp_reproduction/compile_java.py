"""
编译 GA-MDVRP Java 代码
"""

import subprocess
import os
from pathlib import Path


def check_java():
    """检查 Java 环境"""
    print("检查 Java 环境...")
    try:
        result = subprocess.run(
            ['java', '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        version_info = result.stderr.split('\n')[0]
        print(f"✓ Java: {version_info}")
        return True
    except FileNotFoundError:
        print("❌ Java 未安装或未配置到 PATH")
        return False
    except Exception as e:
        print(f"❌ Java 检查失败: {e}")
        return False


def check_javac():
    """检查 javac 编译器"""
    print("检查 javac 编译器...")
    try:
        result = subprocess.run(
            ['javac', '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        version_info = result.stderr.strip() if result.stderr else result.stdout.strip()
        print(f"✓ javac: {version_info}")
        return True
    except FileNotFoundError:
        print("❌ javac 未找到，请确保安装了 JDK（不是 JRE）")
        print("   下载地址: https://www.oracle.com/java/technologies/downloads/")
        return False
    except Exception as e:
        print(f"❌ javac 检查失败: {e}")
        return False


def compile_java():
    """编译 Java 代码"""
    current_dir = Path(__file__).parent
    ga_mdvrp_dir = current_dir / 'GA-MDVRP'
    src_dir = ga_mdvrp_dir / 'src'
    out_dir = ga_mdvrp_dir / 'out'
    
    print(f"\n项目目录: {ga_mdvrp_dir}")
    print(f"源代码目录: {src_dir}")
    print(f"输出目录: {out_dir}")
    
    # 检查源代码目录
    if not src_dir.exists():
        print(f"\n❌ 源代码目录不存在: {src_dir}")
        return False
    
    # 创建输出目录
    out_dir.mkdir(exist_ok=True)
    print(f"✓ 输出目录已创建")
    
    # 编译 CLI 版本（无需 JavaFX）
    print(f"\n开始编译 CLI 版本（无需 JavaFX）...")
    main_file = src_dir / 'MainCLI.java'
    
    if not main_file.exists():
        print(f"❌ MainCLI.java 不存在: {main_file}")
        return False
    
    try:
        result = subprocess.run(
            [
                'javac',
                '-d', str(out_dir),
                '-sourcepath', str(src_dir),
                '-encoding', 'UTF-8',
                str(main_file)
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(ga_mdvrp_dir)
        )
        
        if result.returncode != 0:
            print(f"\n❌ 编译失败！")
            print(f"错误输出:")
            print(result.stderr)
            return False
        
        # 检查编译结果
        main_class = out_dir / 'MainCLI.class'
        if main_class.exists():
            print(f"\n✓ 编译成功！")
            print(f"  主类文件: {main_class}")
            
            # 列出编译的类文件
            class_files = list(out_dir.rglob('*.class'))
            print(f"  共编译 {len(class_files)} 个类文件")
            
            return True
        else:
            print(f"\n⚠ 编译完成但未找到 MainCLI.class")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"\n❌ 编译超时（60秒）")
        return False
    except Exception as e:
        print(f"\n❌ 编译过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("="*60)
    print("GA-MDVRP Java 代码编译工具")
    print("="*60)
    print()
    
    # 检查环境
    if not check_java():
        return False
    
    if not check_javac():
        return False
    
    print()
    
    # 编译
    success = compile_java()
    
    print()
    print("="*60)
    if success:
        print("✓ 编译完成！")
        print()
        print("现在可以运行测试脚本:")
        print("  python quick_test.py")
        print("  或")
        print("  python batch_run_datasets.py")
    else:
        print("❌ 编译失败")
        print()
        print("请检查:")
        print("  1. 是否安装了 JDK（不是 JRE）")
        print("  2. javac 是否在 PATH 中")
        print("  3. 源代码是否完整")
    print("="*60)
    
    return success


if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)
