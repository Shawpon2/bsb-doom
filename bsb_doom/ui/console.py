import time
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.live import Live
from rich.table import Table
from rich.text import Text
from rich.align import Align
from ..config import ERROR_THRESHOLD

console = Console()

class LiveDisplay:
    def __init__(self, target):
        self.target = target
        self.layout = self._create_layout()
        self.live = Live(self.layout, refresh_per_second=10, screen=True)
        self.start_time = time.time()

    def _create_layout(self):
        layout = Layout()
        layout.split(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        layout["main"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        layout["left"].split(
            Layout(name="stats"),
            Layout(name="progress"),
            Layout(name="attacks")
        )
        layout["right"].split(
            Layout(name="info"),
        )
        return layout

    def _progress_bar(self, percentage):
        filled = int(percentage // 2)  # width 50
        bar = "█" * filled + "░" * (50 - filled)
        return f"[{bar}] {percentage:.1f}%"

    def update(self, metrics, failure_detected):
        elapsed = time.time() - self.start_time
        error_rate = metrics.error_rate()
        # Progress = how close error rate is to threshold (capped at 100%)
        progress = min(100, (error_rate / ERROR_THRESHOLD) * 100) if ERROR_THRESHOLD > 0 else 0

        # Header
        header_text = Text(f"BSB-DOOM v9.0 - Testing {self.target} [{elapsed:.0f}s]", style="bold cyan")
        self.layout["header"].update(Panel(header_text, style="blue"))

        # Progress bar
        bar = self._progress_bar(progress)
        bar_color = "red" if failure_detected else "green"
        self.layout["progress"].update(Panel(f"{bar}", title="⏳ Load Level", border_style=bar_color))

        # Stats panel
        stats_text = (
            f"Total Requests: {metrics.total_requests:,}\n"
            f"Current RPS: {metrics.current_rps:.1f}\n"
            f"Peak RPS: {metrics.peak_rps:.1f}\n"
            f"Errors: {metrics.error_count:,} ({error_rate*100:.1f}%)\n"
            f"Avg Latency: {metrics.avg_latency()*1000:.1f}ms\n"
            f"p95 Latency: {metrics.percentile(95)*1000:.1f}ms"
        )
        self.layout["stats"].update(Panel(stats_text, title="📊 Statistics", border_style="cyan"))

        # Attack breakdown
        attack_table = Table(show_header=True, header_style="bold magenta")
        attack_table.add_column("Attack")
        attack_table.add_column("Requests")
        attack_table.add_column("Errors")
        for name, stats in metrics.attack_stats.items():
            attack_table.add_row(name, str(stats['total']), str(stats['errors']))
        self.layout["attacks"].update(Panel(attack_table, title="⚔️ Attacks", border_style="magenta"))

        # Info panel (threshold)
        info_text = f"Error Threshold: {ERROR_THRESHOLD*100}%\nWhen the bar fills to 100%, the site is considered DOWN."
        self.layout["right"].update(Panel(info_text, title="ℹ️ Info", border_style="green"))

        # Footer
        footer_text = Text("Press Ctrl+C to stop | Admin: bsb-admin chandrima2020", style="dim")
        self.layout["footer"].update(Panel(Align.center(footer_text)))

    def start(self):
        self.live.__enter__()

    def stop(self):
        self.live.__exit__(None, None, None)

def print_banner():
    banner = """                                                       
                                                       
█████▄ ▄█████ █████▄     ████▄  ▄████▄ ▄████▄ ██▄  ▄██ 
██▄▄██ ▀▀▀▄▄▄ ██▄▄██ ▄▄▄ ██  ██ ██  ██ ██  ██ ██ ▀▀ ██ 
██▄▄█▀ █████▀ ██▄▄█▀     ████▀  ▀████▀ ▀████▀ ██    ██ 
                                                       """
    console.print(banner, style="bold magenta")
    console.print("[bold cyan]Ultimate Load Testing Suite[/bold cyan] - Professional Edition v9.0\n", justify="center")

def print_contact():
    from ..config import CONTACT_INFO
    table = Table(title="Contact Information", show_header=False, border_style="blue")
    table.add_column("Platform", style="cyan")
    table.add_column("Link", style="green")
    for platform, url in CONTACT_INFO.items():
        table.add_row(platform, url)
    console.print(table)
