import subprocess
import sys
import re
from pathlib import Path
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, IntPrompt
from rich.status import Status
from logic import generate_links

console = Console()
SCRIPT_DIR = Path(__file__).parent.parent.parent

def get_surge_version():
    try:
        # On Windows, npm global commands are often .cmd files, requiring shell=True
        result = subprocess.run("surge --version", shell=True, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except Exception:
        return "未安装"

def run_command(command, description):
    with console.status(f"[bold green]{description}...", spinner="dots"):
        try:
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8")
            # Clear status before printing command output to avoid mixing
            console.print(f"\n[bold blue]>>> {description}[/bold blue]")
            for line in process.stdout:
                # Use highlight=False to prevent rich from adding its own coloring to already colored/messy strings
                # and strip trailing whitespace
                clean_line = line.rstrip()
                if clean_line:
                    console.print(clean_line, highlight=False)
            process.wait()
            if process.returncode == 0:
                console.print(f"\n[bold green]✓ {description} 成功[/bold green]")
            else:
                console.print(f"\n[bold red]✗ {description} 失败 (退出码: {process.returncode})[/bold red]")
        except Exception as e:
            console.print(f"[bold red]错误: {e}[/bold red]")

def strip_ansi(text):
    """移除字符串中的 ANSI 转义序列"""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def run_surge_list():
    with console.status("[bold green]正在获取项目列表...", spinner="dots"):
        try:
            result = subprocess.run("surge list", shell=True, capture_output=True, text=True, encoding="utf-8")
            if result.returncode != 0:
                console.print(f"[bold red]✗ 获取列表失败: {result.stderr}[/bold red]")
                return

            # 预处理：移除 ANSI 代码并按行拆分
            raw_lines = result.stdout.strip().splitlines()
            if not raw_lines:
                console.print("[yellow]未找到任何项目。[/yellow]")
                return

            table = Table(title="[bold cyan]Surge 项目列表[/bold cyan]", border_style="bright_blue", header_style="bold magenta")
            table.add_column("#", style="dim", width=3)
            table.add_column("域名 (Domain)", style="cyan")
            table.add_column("发布时间 (Published)", style="green")
            table.add_column("服务商 (Provider)", style="dim")
            table.add_column("计划 (Plan)", style="yellow")

            for i, line in enumerate(raw_lines, 1):
                clean_line = strip_ansi(line).strip()
                if not clean_line:
                    continue
                
                # 按照 2 个或更多空格拆分
                parts = re.split(r'\s{2,}', clean_line)
                
                if len(parts) >= 2:
                    domain = parts[0]
                    time = parts[1]
                    provider = parts[2] if len(parts) > 2 else "-"
                    plan = parts[-1] if len(parts) > 3 else "-"
                    
                    table.add_row(str(i), domain, time, provider, plan)

            console.print(table)
        except Exception as e:
            console.print(f"[bold red]错误: {e}[/bold red]")

def show_menu():
    while True:
        console.clear()
        
        menu_table = Table(show_header=False, box=None, padding=(0, 1))
        menu_table.add_column("Index", style="green")
        menu_table.add_column("Option")
        
        menu_table.add_row("1.", "查看项目 (surge list)")
        menu_table.add_row("2.", "部署项目 (surge deploy)")
        menu_table.add_row("3.", "删除项目 (surge teardown)")
        menu_table.add_row("4.", "生成链接 (Markdown)")
        menu_table.add_row("5.", "工具管理 (Install/Update/Uninstall)")
        menu_table.add_row("0.", "退出脚本")

        menu_panel = Panel(
            menu_table,
            title="[bold cyan]🚀 surge部署交互工具[/bold cyan]",
            border_style="bright_blue",
            padding=(1, 2),
            expand=False
        )
        console.print(menu_panel)
        
        choice = Prompt.ask("请选择操作", choices=["1", "2", "3", "4", "5", "0"], default="1")
        
        if choice == "1":
            run_surge_list()
            Prompt.ask("\n按回车键继续")
        elif choice == "2":
            path = Prompt.ask("请输入surge项目路径").strip().strip('"')
            prefix = Prompt.ask("请输入要使用的域名前缀 (例如: test)")
            if path and prefix:
                domain = f"https://{prefix}.surge.sh"
                run_command(f"surge {path} --domain {domain}", f"正在部署项目到 {domain}")
            Prompt.ask("\n按回车键继续")
        elif choice == "3":
            project = Prompt.ask("请输入要删除的项目域名 (例如 example.surge.sh)")
            if project:
                run_command(f"surge teardown {project}", f"正在删除项目 {project}")
            Prompt.ask("\n按回车键继续")
        elif choice == "4":
            path = Prompt.ask("请输入surge项目路径").strip().strip('"')
            if path:
                try:
                    with console.status("[bold green]正在生成链接...", spinner="dots"):
                        result = generate_links(path, SCRIPT_DIR)
                    
                    console.print(f"\n[bold green]✓ 生成成功![/bold green]")
                    console.print(f"项目域名: [cyan]{result['domain']}[/cyan]")
                    console.print(f"总文件数: {result['total_count']} | 生成链接: {result['files_count']} | 过滤数量: {result['filtered_count']}")
                    console.print(f"输出文件: [link=file://{result['out_file']}]{result['out_file']}[/link]")
                except Exception as e:
                    console.print(f"[bold red]错误: {e}[/bold red]")
            Prompt.ask("\n按回车键继续")
        elif choice == "5":
            show_tool_management()
        elif choice == "0":
            console.print("[yellow]感谢使用，再见！[/yellow]")
            break

def show_tool_management():
    while True:
        version = get_surge_version()
        console.clear()
        
        tool_table = Table(show_header=False, box=None, padding=(0, 1))
        tool_table.add_column("Index", style="green", width=3)
        tool_table.add_column("Option")
        
        # Add version info as a row in the main table
        tool_table.add_row("", f"[dim]当前版本: {version}[/dim]")
        tool_table.add_row("", "") # Spacer
        
        tool_table.add_row("1.", "安装 surge (npm install -g surge)")
        tool_table.add_row("2.", "更新 surge (npm install -g surge)")
        tool_table.add_row("3.", "卸载 surge (npm uninstall -g surge)")
        tool_table.add_row("0.", "返回主菜单")

        tool_panel = Panel(
            tool_table,
            title="[bold cyan]🛠️ 工具管理[/bold cyan]",
            border_style="bright_blue",
            padding=(1, 1),
            expand=False
        )
        console.print(tool_panel)
        
        choice = Prompt.ask("请选择操作", choices=["1", "2", "3", "0"], default="1")
        
        if choice == "1":
            run_command("npm install -g surge", "正在安装 surge")
            Prompt.ask("\n按回车键继续")
        elif choice == "2":
            run_command("npm install -g surge", "正在更新 surge")
            Prompt.ask("\n按回车键继续")
        elif choice == "3":
            run_command("npm uninstall -g surge", "正在卸载 surge")
            Prompt.ask("\n按回车键继续")
        elif choice == "0":
            break

if __name__ == "__main__":
    show_menu()
