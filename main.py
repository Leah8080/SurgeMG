import sys
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 将 src 目录添加到 sys.path
src_path = Path(__file__).parent / "src"
if src_path.exists() and str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

try:
    from ui import show_menu
except ImportError as e:
    print(f"错误: 无法导入 surge_tool 模块. {e}")
    sys.exit(1)

if __name__ == "__main__":
    try:
        show_menu()
    except KeyboardInterrupt:
        print("\n已退出")
        sys.exit(0)
