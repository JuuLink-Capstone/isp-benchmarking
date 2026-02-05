#!/usr/bin/env python3
"""
Ping Data Analysis Script
Analyzes fping log files and generates plots and statistical summaries.
"""

import re
import argparse
import os
from pathlib import Path
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def parse_fping_log(log_file):
    """
    Parse fping log file and extract ping data.
    
    Format: [timestamp] IP : [seq], size bytes, latency ms (avg ms, loss%)
    """
    timestamps = []
    latencies = []
    packet_loss = []
    
    pattern = r'\[([0-9.]+)\]\s+[\d.]+\s+:\s+\[(\d+)\],\s+\d+\s+bytes,\s+([\d.]+)\s+ms\s+\(([\d.]+)\s+avg,\s+([\d.]+)%\s+loss\)'
    
    with open(log_file, 'r') as f:
        for line in f:
            match = re.match(pattern, line.strip())
            if match:
                timestamp = float(match.group(1))
                latency = float(match.group(3))
                avg_latency = float(match.group(4))
                loss = float(match.group(5))
                
                timestamps.append(datetime.fromtimestamp(timestamp))
                latencies.append(latency)
                packet_loss.append(loss)
    
    return timestamps, latencies, packet_loss


def calculate_statistics(latencies, packet_loss):
    """Calculate comprehensive statistics for ping data."""
    latencies_array = np.array(latencies)
    
    stats = {
        'total_pings': len(latencies),
        'min_latency': np.min(latencies_array),
        'max_latency': np.max(latencies_array),
        'mean_latency': np.mean(latencies_array),
        'median_latency': np.median(latencies_array),
        'std_dev': np.std(latencies_array),
        'percentile_95': np.percentile(latencies_array, 95),
        'percentile_99': np.percentile(latencies_array, 99),
        'final_packet_loss': packet_loss[-1] if packet_loss else 0
    }
    
    # Calculate jitter (variance in latency)
    if len(latencies_array) > 1:
        jitter = np.mean(np.abs(np.diff(latencies_array)))
        stats['avg_jitter'] = jitter
    else:
        stats['avg_jitter'] = 0
    
    return stats


def create_plots(timestamps, latencies, output_dir):
    """Create visualization plots for ping data."""
    fig, axes = plt.subplots(3, 1, figsize=(14, 12))
    
    # Plot 1: Latency over time
    axes[0].plot(timestamps, latencies, linewidth=0.5, alpha=0.7, color='blue')
    axes[0].set_xlabel('Time')
    axes[0].set_ylabel('Latency (ms)')
    axes[0].set_title('Ping Latency Over Time')
    axes[0].grid(True, alpha=0.3)
    axes[0].xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
    
    # Plot 2: Latency distribution (histogram)
    axes[1].hist(latencies, bins=100, color='green', alpha=0.7, edgecolor='black')
    axes[1].set_xlabel('Latency (ms)')
    axes[1].set_ylabel('Frequency (log scale)')
    axes[1].set_title('Latency Distribution')
    axes[1].set_yscale('log')
    axes[1].grid(True, alpha=0.3, axis='y')
    
    # Plot 3: Box plot (with extended whiskers to reduce outliers)
    axes[2].boxplot([latencies], vert=False, widths=0.5, 
                    whis=[5, 95], showfliers=True,
                    flierprops=dict(marker='o', markersize=2, alpha=0.3, markerfacecolor='red'))
    axes[2].set_xlabel('Latency (ms)')
    axes[2].set_title('Latency Box Plot (1st-99th percentile range)')
    # Set x-axis to 1st-99th percentile range to focus on the box and whiskers
    p1 = np.percentile(latencies, 1)
    p99 = np.percentile(latencies, 99)
    axes[2].set_xlim(left=p1, right=p99)
    axes[2].grid(True, alpha=0.3, axis='x')
    axes[2].set_yticklabels(['Latency'])
    # Add label for the median line in top left corner
    axes[2].text(0.02, 0.98, 'Orange line = Median', 
                transform=axes[2].transAxes, fontsize=10,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    plot_file = output_dir / 'ping_analysis.png'
    plt.savefig(plot_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Plot saved to: {plot_file}")


def save_statistics(stats, timestamps, output_dir):
    """Save statistical results to a text file."""
    output_file = output_dir / 'fping_stats.txt'
    
    with open(output_file, 'w') as f:
        f.write("=" * 60 + "\n")
        f.write("PING DATA ANALYSIS RESULTS\n")
        f.write("=" * 60 + "\n\n")
        
        if timestamps:
            f.write(f"Analysis Period:\n")
            f.write(f"  Start: {timestamps[0].strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"  End:   {timestamps[-1].strftime('%Y-%m-%d %H:%M:%S')}\n")
            duration = timestamps[-1] - timestamps[0]
            f.write(f"  Duration: {duration}\n\n")
        
        f.write(f"Total Pings: {stats['total_pings']:,}\n\n")
        
        f.write("Latency Statistics (ms):\n")
        f.write("-" * 40 + "\n")
        f.write(f"  Minimum:       {stats['min_latency']:.2f}\n")
        f.write(f"  Maximum:       {stats['max_latency']:.2f}\n")
        f.write(f"  Mean:          {stats['mean_latency']:.2f}\n")
        f.write(f"  Median:        {stats['median_latency']:.2f}\n")
        f.write(f"  Std Deviation: {stats['std_dev']:.2f}\n")
        f.write(f"  95th %ile:     {stats['percentile_95']:.2f}\n")
        f.write(f"  99th %ile:     {stats['percentile_99']:.2f}\n")
        f.write(f"  Avg Jitter:    {stats['avg_jitter']:.2f}\n\n")
        
        f.write(f"Packet Loss:\n")
        f.write("-" * 40 + "\n")
        f.write(f"  Final Loss %:  {stats['final_packet_loss']:.2f}%\n\n")
        
        f.write("=" * 60 + "\n")
    
    print(f"Statistics saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Analyze ping data from fping log files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  python analyze_ping.py                        # Uses default 'starlink_raw' folder
  python analyze_ping.py --folder my_dataset    # Uses 'my_dataset' folder
        """
    )
    
    parser.add_argument(
        '--folder',
        type=str,
        default='starlink_raw',
        help='Name of the folder inside benchmarks/ containing tests/log/fping.log (default: starlink_raw)'
    )
    
    args = parser.parse_args()
    
    # Set up paths
    script_dir = Path(__file__).parent
    data_folder = script_dir / 'benchmarks' / args.folder / 'tests' / 'log'
    log_file = data_folder / 'fping.log'
    output_dir = script_dir / 'analysis' / args.folder
    
    # Validate input file
    if not log_file.exists():
        print(f"Error: Log file not found at {log_file}")
        print(f"Expected structure: benchmarks/{args.folder}/tests/log/fping.log")
        return 1
    
    # Create output directory if needed
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Reading ping data from: {log_file}")
    print(f"Output directory: {output_dir}")
    print()
    
    # Parse the log file
    print("Parsing log file...")
    timestamps, latencies, packet_loss = parse_fping_log(log_file)
    
    if not latencies:
        print("Error: No valid ping data found in log file")
        return 1
    
    print(f"Parsed {len(latencies):,} ping records")
    print()
    
    # Calculate statistics
    print("Calculating statistics...")
    stats = calculate_statistics(latencies, packet_loss)
    
    # Create plots
    print("Generating plots...")
    create_plots(timestamps, latencies, output_dir)
    
    # Save statistics
    print("Saving statistics...")
    save_statistics(stats, timestamps, output_dir)
    
    print()
    print("Analysis complete!")
    print(f"\nQuick Summary:")
    print(f"  Mean Latency: {stats['mean_latency']:.2f} ms")
    print(f"  Std Dev: {stats['std_dev']:.2f} ms")
    print(f"  Packet Loss: {stats['final_packet_loss']:.2f}%")
    
    return 0


if __name__ == '__main__':
    exit(main())
