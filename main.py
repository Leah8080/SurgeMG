from pathlib import Path
import fnmatch
from collections import defaultdict


def read_cname(base_path: Path) -> str:
    cname_file = base_path / "CNAME"
    if not cname_file.is_file():
        raise FileNotFoundError(f"未找到 CNAME 文件: {cname_file}")

    raw = cname_file.read_text(encoding="utf-8").strip().lstrip("\ufeff")
    if not raw:
        raise ValueError("CNAME 文件为空")

    if raw.startswith("<") and raw.endswith(">"):
        raw = raw[1:-1].strip()

    if raw.startswith("https://") or raw.startswith("http://"):
        return raw

    return f"http://{raw}"


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


def should_ignore(rel_posix: str, name: str, patterns: list[str]) -> bool:
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


def collect_files(base_path: Path, patterns: list[str]) -> list[Path]:
    files: list[Path] = []

    for path in base_path.rglob("*"):
        rel = path.relative_to(base_path)
        rel_posix = rel.as_posix()

        # Always ignore surge config files and CNAME in output list.
        if rel_posix in (".surgeignore", "CNAME"):
            continue

        if should_ignore(rel_posix, path.name, patterns):
            continue

        if path.is_file():
            files.append(rel)

    return sorted(files, key=lambda p: p.as_posix().lower())


def build_markdown(base_path: Path, domain: str, files: list[Path]) -> str:
    lines = [f"# 🚀 {base_path.name}", ""]
    grouped: dict[str, list[Path]] = defaultdict(list)

    for rel in files:
        parent = rel.parent.as_posix()
        group = "Root" if parent == "." else parent
        grouped[group].append(rel)

    group_names = ["Root"] if "Root" in grouped else []
    group_names.extend(sorted((g for g in grouped.keys() if g != "Root"), key=str.lower))

    for group in group_names:
        lines.append(f"- 📁 {group}")
        lines.append("")

        group_files = sorted(grouped[group], key=lambda p: p.name.lower())
        for rel in group_files:
            rel_posix = rel.as_posix()
            url = f"{domain.rstrip('/')}/{rel_posix}"
            lines.append(f"  - 📄 {rel.name}")
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
    user_input = input("请输入要扫描的路径: ").strip().strip('"')
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

    ignore_patterns = read_ignore_patterns(base_path)
    files = collect_files(base_path, ignore_patterns)

    markdown = build_markdown(base_path, domain, files)
    out_file = write_links_file(base_path, markdown)

    print(f"已生成: {out_file}")
    print(f"共写入 {len(files)} 个链接")


if __name__ == "__main__":
    main()

