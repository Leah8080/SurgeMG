import re
import json
from pathlib import Path
import fnmatch
from collections import defaultdict

# 脚本所在目录
SCRIPT_DIR = Path(__file__).parent


def natural_sort_key(s):
    """自然排序算法的 Key 函数 (例如使 file2 排在 file10 前面)"""
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', str(s))]


def load_config() -> dict:
    """从脚本目录加载默认配置"""
    config = {
        "global_ignore": [],
        "icons": {
            "folder": "📁",
            "file": "📄",
            "ext": {}
        }
    }

    config_path = SCRIPT_DIR / ".surge-url.json"
    if config_path.is_file():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8-sig"))
            if "global_ignore" in data:
                config["global_ignore"] = data["global_ignore"]
            if "icons" in data:
                config["icons"].update(data["icons"])
        except Exception as e:
            print(f"警告: 加载配置文件失败: {e}")

    return config


def get_icon(path: Path, icons_config: dict, is_folder=False) -> str:
    """根据路径获取对应的图标"""
    if is_folder:
        return icons_config.get("folder", "📁")
    ext = path.suffix.lower()
    return icons_config.get("ext", {}).get(ext, icons_config.get("file", "📄"))


def read_cname(base_path: Path) -> str:
    cname_file = base_path / "CNAME"
    if not cname_file.is_file():
        raise FileNotFoundError(f"\n未找到 CNAME 文件：{cname_file}\n退出脚本...")

    raw = cname_file.read_text(encoding="utf-8").strip().lstrip("\ufeff")
    if not raw:
        raise ValueError("CNAME 文件为空")

    if raw.startswith("<") and raw.endswith(">"):
        raw = raw[1:-1].strip()

    if raw.startswith("https://") or raw.startswith("http://"):
        return raw

    return f"https://{raw}"


def read_ignore_patterns(base_path: Path) -> list[str]:
    ignore_file = base_path / ".surgeignore"
    if not ignore_file.is_file():
        return []

    patterns: list[str] = []
    for line in ignore_file.read_text(encoding="utf-8").splitlines():
        rule = line.strip()
        if not rule or rule.startswith("#"):
            continue
        patterns.append(rule)

    return patterns


def should_ignore(rel_posix: str, name: str, patterns: list[str], global_ignore: list) -> bool:
    # 检查全局忽略名单
    if name in global_ignore:
        return True

    for p in patterns:
        p_norm = p.replace("\\", "/").rstrip("/")
        if not p_norm:
            continue

        if "/" not in p_norm:
            if name == p_norm or fnmatch.fnmatch(name, p_norm):
                return True

        if rel_posix == p_norm:
            return True

        if rel_posix.startswith(p_norm + "/"):
            return True

        if fnmatch.fnmatch(rel_posix, p_norm):
            return True

    return False


def collect_files(base_path: Path, patterns: list[str], global_ignore: list) -> tuple[list[Path], int, int]:
    files: list[Path] = []
    total_count = 0
    filtered_count = 0

    for path in base_path.rglob("*"):
        if not path.is_file():
            continue

        total_count += 1
        rel = path.relative_to(base_path)
        rel_posix = rel.as_posix()

        if should_ignore(rel_posix, path.name, patterns, global_ignore):
            filtered_count += 1
            continue

        files.append(rel)

    return sorted(files, key=lambda p: natural_sort_key(p.as_posix())), total_count, filtered_count


def build_markdown(base_path: Path, domain: str, files: list[Path], icons_config: dict) -> str:
    lines = [f"# 🚀 {base_path.name}", ""]
    grouped: dict[str, list[Path]] = defaultdict(list)

    for rel in files:
        parent = rel.parent.as_posix()
        group = "Root" if parent == "." else parent
        grouped[group].append(rel)

    group_names = ["Root"] if "Root" in grouped else []
    others = sorted((g for g in grouped.keys() if g != "Root"), key=natural_sort_key)
    group_names.extend(others)

    for group in group_names:
        folder_icon = get_icon(Path(group), icons_config, is_folder=True)
        lines.append(f"- {folder_icon} {group}")
        lines.append("")

        group_files = sorted(grouped[group], key=lambda p: natural_sort_key(p.name))
        for rel in group_files:
            rel_posix = rel.as_posix()
            url = f"{domain.rstrip('/')}/{rel_posix}"
            file_icon = get_icon(rel, icons_config)
            lines.append(f"  - {file_icon} {rel.name}")
            lines.append("")
            lines.append("    ```text")
            lines.append(f"    {url}")
            lines.append("    ```")
            lines.append("")

    lines.append("")
    return "\n".join(lines)


def write_links_file(base_path: Path, content: str) -> Path:
    out_dir = Path.cwd() / "links"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_file = out_dir / f"{base_path.name}.md"
    out_file.write_text(content, encoding="utf-8")
    return out_file


def main() -> None:
    user_input = input("请输入surge项目路径: ").strip().strip('"')
    if not user_input:
        print("路径不能为空")
        return

    base_path = Path(user_input).expanduser().resolve()
    if not base_path.exists() or not base_path.is_dir():
        print(f"路径不存在或不是目录: {base_path}")
        return

    try:
        domain = read_cname(base_path)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc))
        return

    config = load_config()
    ignore_patterns = read_ignore_patterns(base_path)
    files, total_count, filtered_count = collect_files(base_path, ignore_patterns, config["global_ignore"])

    markdown = build_markdown(base_path, domain, files, config["icons"])
    out_file = write_links_file(base_path, markdown)

    print(f"\n项目域名: {domain}")
    print(f"总文件数: {total_count} | 生成链接: {len(files)} | 过滤数量: {filtered_count}")
    print(f"输出文件: {out_file}")


if __name__ == "__main__":
    main()

