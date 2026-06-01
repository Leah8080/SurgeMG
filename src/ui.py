import subprocess
import sys
import re
import os
from pathlib import Path
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.status import Status
from logic import generate_links, write_deploy_log

console = Console()
SCRIPT_DIR = Path(__file__).parent.parent.parent

def get_surge_version():
    try:
        # On Windows, npm global commands are often .cmd files, requiring shell=True
        result = subprocess.run("surge --version", shell=True, capture_output=True, text=True, check=True)
        # 提取版本号（匹配 v0.27.4 或 0.27.4 格式）
        match = re.search(r'v?(\d+\.\d+\.\d+)', result.stdout)
        return match.group(1) if match else "未安装"
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

def run_deploy(path, domain_url):
    with console.status(f"[bold green]🚀 正在部署到 {domain_url}...", spinner="bouncingBar"):
        try:
            process = subprocess.Popen(f"surge {path} --domain {domain_url}", 
                                     shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                     text=True, encoding="utf-8")
            
            stats = {}
            for line in process.stdout:
                clean_line = strip_ansi(line).strip()
                if not clean_line:
                    continue
                
                # 静默捕获关键统计信息
                if "project:" in clean_line.lower():
                    stats['project'] = clean_line.split("project:")[1].strip()
                if "domain:" in clean_line.lower():
                    stats['domain'] = clean_line.split("domain:")[1].strip()
                if "size:" in clean_line.lower():
                    stats['size'] = clean_line.split("size:")[1].strip()
                
                # 只在控制台输出极简进度或最终成功信息
                if "success!" in clean_line.lower():
                    console.print(f"\n[bold green]✓ {clean_line}[/bold green]")
                
            process.wait()
            
            if process.returncode == 0:
                # 部署成功后显示一个极其精美的总结面板
                summary_table = Table(show_header=False, box=None, padding=(0, 1))
                summary_table.add_row("📁 [bold]项目路径[/bold]", f"[dim]{stats.get('project', path)}[/dim]")
                summary_table.add_row("📦 [bold]文件大小[/bold]", f"[yellow]{stats.get('size', '未知')}[/yellow]")
                summary_table.add_row("🔗 [bold]项目地址[/bold]", f"[bold cyan]{domain_url}[/bold cyan]")
                
                console.print(Panel(
                    summary_table, 
                    title="[bold green]🎊 部署成功[/bold green]", 
                    border_style="green", 
                    expand=False,
                    padding=(1, 1)
                ))
                
                # 写入部署日志
                write_deploy_log(stats.get('project', path), domain_url)
                
                return True
            else:
                console.print(f"\n[bold red]✗ 部署失败 (退出码: {process.returncode})[/bold red]")
                return False
                
        except Exception as e:
            console.print(f"[bold red]错误: {e}[/bold red]")
            return False

def run_teardown(project):
    with console.status(f"[bold red]正在删除项目 {project}...", spinner="dots"):
        try:
            process = subprocess.Popen(f"surge teardown {project}", 
                                     shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                     text=True, encoding="utf-8")

            for line in process.stdout:
                clean_line = strip_ansi(line).strip()
                if not clean_line:
                    continue

                # 只显示成功移除的提示
                if "has been removed" in clean_line.lower() or "success" in clean_line.lower():
                    console.print(f"\n[bold green]✓ 成功删除：{project}[/bold green]")

            process.wait()
            if process.returncode != 0:
                console.print(f"\n[bold red]✗ 删除失败：{project} (退出码: {process.returncode})[/bold red]")

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
        menu_table.add_row("4.", "生成链接 (markdown)")
        menu_table.add_row("5.", "工具管理 (npm global)")
        menu_table.add_row("0.", "退出脚本")

        menu_panel = Panel(
            menu_table,
            title="[bold cyan]🚀 surge项目交互工具[/bold cyan]",
            border_style="bright_blue",
            padding=(1, 1),
            expand=False
        )
        console.print(menu_panel)
        
        choice = Prompt.ask("请选择操作", choices=["1", "2", "3", "4", "5", "0"], default="0")
        
        if choice == "1":
            run_surge_list()
            Prompt.ask("\n按回车键继续")
        elif choice == "2":
            path_str = Prompt.ask("请输入surge项目路径").strip().strip('"')
            if path_str:
                project_path = Path(path_str).expanduser().resolve()
                if project_path.exists() and project_path.is_dir():
                    cname_file = project_path / "CNAME"
                    domain = ""
                    
                    if cname_file.is_file():
                        # 如果存在 CNAME，读取并清理内容
                        raw_cname = cname_file.read_text(encoding="utf-8").strip().lstrip("\ufeff")
                        if raw_cname:
                            domain = raw_cname if "://" in raw_cname else f"https://{raw_cname}"
                            console.print(f"[bold green]检测到 CNAME 文件: [cyan]{raw_cname}[/cyan][/bold green]", highlight=False)
                    
                    if not domain:
                        prefix = Prompt.ask("请输入要使用的域名前缀 (例如: test)")
                        if prefix:
                            domain = f"https://{prefix}.surge.sh"
                    
                    if domain:
                        # 部署前进行二次确认
                        cname_existed = cname_file.is_file()
                        confirm_table = Table(show_header=False, box=None, padding=(0, 1))
                        confirm_table.add_row("项目路径:", f"[cyan]{project_path}[/cyan]")
                        confirm_table.add_row("部署域名:", f"[bold green]{domain}[/bold green]")
                        
                        console.print("\n")
                        console.print(Panel(
                            confirm_table,
                            title="[bold yellow]确认部署信息[/bold yellow]",
                            border_style="yellow",
                            expand=False,
                            padding=(1, 1)
                        ))
                        
                        if Confirm.ask("\n确定要开始部署吗？", default=True):
                            if run_deploy(str(project_path), domain):
                                # 如果之前没有 CNAME 文件，部署成功后自动创建
                                if not cname_existed:
                                    try:
                                        # 写入完整的域名地址（包括协议头）
                                        cname_file.write_text(domain, encoding="utf-8")
                                        console.print(f"[bold green]已自动创建 CNAME 文件: [cyan]{domain}[/cyan][/bold green]", highlight=False)
                                    except Exception as e:
                                        console.print(f"[bold red]创建 CNAME 失败: {e}[/bold red]")
                        else:
                            console.print("[yellow]已取消部署。[/yellow]")
                else:
                    console.print(f"[bold red]错误: 路径不存在或不是目录: {path_str}[/bold red]")
            Prompt.ask("\n按回车键继续")
        elif choice == "3":
            project = Prompt.ask("请输入要删除的项目域名")
            if project:
                if Confirm.ask(f"[bold red]确定要删除项目 [cyan]{project}[/cyan] 吗？[/bold red]", default=False):
                    run_teardown(project)
                else:
                    console.print("[yellow]已取消删除。[/yellow]")
            Prompt.ask("\n按回车键继续")
        elif choice == "4":
            path_str = Prompt.ask("请输入surge项目路径").strip().strip('"')
            if path_str:
                try:
                    with console.status("[bold green]正在生成链接...", spinner="dots"):
                        result = generate_links(path_str, SCRIPT_DIR)
                    
                    # 生成成功后显示精美的总结面板
                    summary_table = Table(show_header=False, box=None, padding=(0, 1))
                    summary_table.add_row("🌐 [bold]项目域名[/bold]", f"[bold cyan]{result['domain']}[/bold cyan]")
                    summary_table.add_row("📊 [bold]文件统计[/bold]", f"总数: [green]{result['total_count']}[/green] | 链接: [cyan]{result['files_count']}[/cyan] | 过滤: [yellow]{result['filtered_count']}[/yellow]")
                    summary_table.add_row("📝 [bold]输出文件[/bold]", f"[dim]{result['out_file']}[/dim]")
                    
                    console.print("\n")
                    console.print(Panel(
                        summary_table, 
                        title="[bold green]✨ 链接生成成功[/bold green]", 
                        border_style="green", 
                        expand=False,
                        padding=(1, 1)
                    ), highlight=False)
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
        tool_table.add_column("Index", style="green")
        tool_table.add_column("Option")
                
        tool_table.add_row("1.", "安装 surge (npm install -g surge)")
        tool_table.add_row("2.", "更新 surge (npm install -g surge)")
        tool_table.add_row("3.", "卸载 surge (npm uninstall -g surge)")
        tool_table.add_row("0.", "返回主菜单")

        tool_panel = Panel(
            tool_table,
            title=f"[bold cyan]🛠️ 工具管理[/bold cyan](surge:{version})",
            border_style="bright_blue",
            padding=(1, 1),
            expand=False
        )
        console.print(tool_panel)
        
        choice = Prompt.ask("请选择操作", choices=["1", "2", "3", "0"], default="0")
        
        if choice == "1":
            run_command("npm install -g surge", "正在安装 surge")
            Prompt.ask("\n按回车键继续")
        elif choice == "2":
            run_command("npm install -g surge", "正在更新 surge")
            Prompt.ask("\n按回车键继续")
        elif choice == "3":
            if Confirm.ask("[bold red]确定要卸载 surge 吗？[/bold red]", default=False):
                run_command("npm uninstall -g surge", "正在卸载 surge")
            else:
                console.print("[yellow]已取消卸载。[/yellow]")
            Prompt.ask("\n按回车键继续")
        elif choice == "0":
            break

if __name__ == "__main__":
    show_menu()
