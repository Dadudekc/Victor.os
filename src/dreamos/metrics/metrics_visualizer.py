"""
Metrics visualization and reporting functionality.
"""

import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import json

class MetricsVisualizer:
    """Visualizes and generates reports for agent metrics."""
    
    def __init__(self, output_dir: str = "runtime/metrics/reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        plt.style.use('seaborn')
    
    def plot_response_times(self, response_times: List[Dict[str, Any]], title: str = "Response Times"):
        """Plot response times over time."""
        if not response_times:
            return None
        
        timestamps = [datetime.fromisoformat(rt['timestamp']) for rt in response_times]
        durations = [rt['duration_ms'] for rt in response_times]
        
        plt.figure(figsize=(12, 6))
        plt.plot(timestamps, durations, marker='o', linestyle='-', alpha=0.7)
        plt.title(title)
        plt.xlabel('Time')
        plt.ylabel('Response Time (ms)')
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        return plt.gcf()
    
    def plot_success_rates(self, success_rates: List[Dict[str, Any]], title: str = "Success Rates"):
        """Plot success rates over time."""
        if not success_rates:
            return None
        
        timestamps = [datetime.fromisoformat(sr['timestamp']) for sr in success_rates]
        successes = [1 if sr['success'] else 0 for sr in success_rates]
        
        plt.figure(figsize=(12, 6))
        plt.plot(timestamps, successes, marker='o', linestyle='-', alpha=0.7)
        plt.title(title)
        plt.xlabel('Time')
        plt.ylabel('Success (1) / Failure (0)')
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        return plt.gcf()
    
    def plot_resource_utilization(self, resource_utilization: List[Dict[str, Any]], title: str = "Resource Utilization"):
        """Plot resource utilization over time."""
        if not resource_utilization:
            return None
        
        # Group by resource type
        resource_types = set(ru['resource_type'] for ru in resource_utilization)
        
        plt.figure(figsize=(12, 6))
        for resource_type in resource_types:
            resource_data = [ru for ru in resource_utilization if ru['resource_type'] == resource_type]
            timestamps = [datetime.fromisoformat(ru['timestamp']) for ru in resource_data]
            utilization = [ru['utilization'] for ru in resource_data]
            plt.plot(timestamps, utilization, marker='o', linestyle='-', alpha=0.7, label=resource_type)
        
        plt.title(title)
        plt.xlabel('Time')
        plt.ylabel('Utilization')
        plt.xticks(rotation=45)
        plt.legend()
        plt.tight_layout()
        
        return plt.gcf()
    
    def generate_html_report(self, metrics_data: Dict[str, Any], output_file: Optional[str] = None):
        """Generate an HTML report with all metrics visualizations."""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.output_dir / f"metrics_report_{timestamp}.html"
        
        # Create visualizations
        response_times_fig = self.plot_response_times(metrics_data.get('response_times', []))
        success_rates_fig = self.plot_success_rates(metrics_data.get('success_rates', []))
        resource_utilization_fig = self.plot_resource_utilization(metrics_data.get('resource_utilization', []))
        
        # Save figures
        figures = []
        if response_times_fig:
            fig_path = self.output_dir / "response_times.png"
            response_times_fig.savefig(fig_path)
            figures.append(('Response Times', fig_path))
        
        if success_rates_fig:
            fig_path = self.output_dir / "success_rates.png"
            success_rates_fig.savefig(fig_path)
            figures.append(('Success Rates', fig_path))
        
        if resource_utilization_fig:
            fig_path = self.output_dir / "resource_utilization.png"
            resource_utilization_fig.savefig(fig_path)
            figures.append(('Resource Utilization', fig_path))
        
        # Generate HTML
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Agent Metrics Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .figure {{ margin: 20px 0; }}
                .figure img {{ max-width: 100%; }}
                .timestamp {{ color: #666; }}
            </style>
        </head>
        <body>
            <h1>Agent Metrics Report</h1>
            <p class="timestamp">Generated: {datetime.now().isoformat()}</p>
        """
        
        for title, fig_path in figures:
            html_content += f"""
            <div class="figure">
                <h2>{title}</h2>
                <img src="{fig_path.name}" alt="{title}">
            </div>
            """
        
        html_content += """
        </body>
        </html>
        """
        
        # Save HTML report
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        return output_file 