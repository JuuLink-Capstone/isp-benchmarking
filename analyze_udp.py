#!/usr/bin/env python3
"""
UDP Performance Analysis Script
Analyzes iperf3 UDP log files and generates plots and statistical summaries.
Handles multiple target bitrate tests (100M, 300M, 600M, 900M).
"""

import re
import argparse
from pathlib import Path
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from collections import defaultdict


def parse_udp_log(log_file):
    """
    Parse iperf3 UDP log file and extract performance data.
    
    Returns data organized by target bitrate:
    {
        '100M': {'iterations': [...], 'timestamps': [...], 'bitrates': [...], 'lost': [...], 'total': [...]},
        '300M': {...},
        '600M': {...},
        '900M': {...}
    }
    """
    data = {
        '100M': defaultdict(list),
        '300M': defaultdict(list),
        '600M': defaultdict(list),
        '900M': defaultdict(list)
    }
    
    current_test = None
    current_iter = None
    current_timestamp = None
    
    # Patterns
    header_pattern = r'========== ITER (\d+) \| (\d+_\d+) \| UDP (\d+M) =========='
    # Data line pattern: has interval, transfer, bitrate, datagrams
    data_pattern = r'\[\s*\d+\]\s+([\d.]+)-([\d.]+)\s+sec\s+[\d.]+\s+[MG]Bytes\s+([\d.]+)\s+([MG])bits/sec\s+\d+'
    # Summary line pattern with jitter and loss
    summary_pattern = r'\[\s*\d+\]\s+[\d.]+-([\d.]+)\s+sec\s+[\d.]+\s+[MG]Bytes\s+([\d.]+)\s+([MG])bits/sec\s+([\d.]+)\s+ms\s+(\d+)/(\d+)\s+\(([\d.]+)%\)\s+(sender|receiver)'
    
    with open(log_file, 'r') as f:
        for line in f:
            line = line.strip()
            
            # Check for test header
            header_match = re.match(header_pattern, line)
            if header_match:
                current_iter = int(header_match.group(1))
                timestamp_str = header_match.group(2)
                test_type = header_match.group(3)
                current_test = test_type
                # Parse timestamp: format is YYYYMMDD_HHMMSS
                current_timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                continue
            
            if current_test is None:
                continue
            
            # Parse data lines
            data_match = re.match(data_pattern, line)
            if data_match:
                end_time = float(data_match.group(2))
                bitrate = float(data_match.group(3))
                unit = data_match.group(4)
                
                # Convert to Mbps
                if unit == 'G':
                    bitrate *= 1000
                
                # Calculate timestamp for this data point
                point_time = current_timestamp.timestamp() + end_time
                
                data[current_test]['iterations'].append(current_iter)
                data[current_test]['timestamps'].append(datetime.fromtimestamp(point_time))
                data[current_test]['bitrates'].append(bitrate)
            
            # Parse summary line for loss data
            summary_match = re.match(summary_pattern, line)
            if summary_match and summary_match.group(8) == 'receiver':
                lost = int(summary_match.group(5))
                total = int(summary_match.group(6))
                loss_pct = float(summary_match.group(7))
                
                # Store summary stats
                if 'total_lost' not in data[current_test]:
                    data[current_test]['total_lost'] = []
                    data[current_test]['total_datagrams'] = []
                    data[current_test]['loss_pct'] = []
                
                data[current_test]['total_lost'].append(lost)
                data[current_test]['total_datagrams'].append(total)
                data[current_test]['loss_pct'].append(loss_pct)
    
    # Convert to regular dicts
    return {k: dict(v) for k, v in data.items()}


def calculate_statistics(bitrates, loss_pcts, test_name):
    """Calculate comprehensive statistics for UDP performance data."""
    bitrates_array = np.array(bitrates)
    
    stats = {
        'test_name': test_name,
        'total_samples': len(bitrates),
        'min_bitrate': np.min(bitrates_array),
        'max_bitrate': np.max(bitrates_array),
        'mean_bitrate': np.mean(bitrates_array),
        'median_bitrate': np.median(bitrates_array),
        'std_dev': np.std(bitrates_array),
        'percentile_5': np.percentile(bitrates_array, 5),
        'percentile_25': np.percentile(bitrates_array, 25),
        'percentile_75': np.percentile(bitrates_array, 75),
        'percentile_95': np.percentile(bitrates_array, 95),
        'percentile_99': np.percentile(bitrates_array, 99),
    }
    
    # Add loss statistics if available
    if loss_pcts:
        loss_array = np.array(loss_pcts)
        stats['mean_loss_pct'] = np.mean(loss_array)
        stats['median_loss_pct'] = np.median(loss_array)
        stats['max_loss_pct'] = np.max(loss_array)
        stats['min_loss_pct'] = np.min(loss_array)
    
    return stats


def create_plots(data, target_rate, output_dir):
    """Create visualization plots for UDP performance data for a specific target rate."""
    
    if not data['bitrates']:
        return
    
    fig, axes = plt.subplots(3, 1, figsize=(14, 12))
    
    timestamps = data['timestamps']
    bitrates = data['bitrates']
    
    # Time series
    axes[0].plot(timestamps, bitrates, linewidth=0.5, alpha=0.7, color='blue')
    axes[0].set_xlabel('Time')
    axes[0].set_ylabel('Bitrate (Mbps)')
    axes[0].set_title(f'UDP {target_rate} - Bitrate Over Time')
    axes[0].grid(True, alpha=0.3)
    axes[0].xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
    
    # Distribution histogram
    axes[1].hist(bitrates, bins=100, color='purple', alpha=0.7, edgecolor='black')
    axes[1].set_xlabel('Bitrate (Mbps)')
    axes[1].set_ylabel('Frequency (log scale)')
    axes[1].set_title(f'UDP {target_rate} - Bitrate Distribution')
    axes[1].set_yscale('log')
    axes[1].grid(True, alpha=0.3, axis='y')
    
    # Box plot
    axes[2].boxplot([bitrates], vert=False, widths=0.5, 
                      whis=[5, 95], showfliers=True,
                      flierprops=dict(marker='o', markersize=2, alpha=0.3, markerfacecolor='red'))
    axes[2].set_xlabel('Bitrate (Mbps)')
    axes[2].set_title(f'UDP {target_rate} - Bitrate Box Plot (1st-99th %ile)')
    p1 = np.percentile(bitrates, 1)
    p99 = np.percentile(bitrates, 99)
    axes[2].set_xlim(left=p1, right=p99)
    axes[2].grid(True, alpha=0.3, axis='x')
    axes[2].set_yticklabels([target_rate])
    axes[2].text(0.02, 0.98, 'Orange line = Median', 
                   transform=axes[2].transAxes, fontsize=9,
                   verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    plot_file = output_dir / f'udp_{target_rate.lower()}_analysis.png'
    plt.savefig(plot_file, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"UDP {target_rate} plot saved to: {plot_file}")


def save_statistics(data, output_dir):
    """Save statistical results to a text file."""
    output_file = output_dir / '_stats_udp.txt'
    
    with open(output_file, 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("UDP PERFORMANCE ANALYSIS RESULTS\n")
        f.write("=" * 70 + "\n\n")
        
        # Iterate through each target rate
        for target_rate in ['100M', '300M', '600M', '900M']:
            if data[target_rate]['bitrates']:
                loss_pcts = data[target_rate].get('loss_pct', [])
                stats = calculate_statistics(data[target_rate]['bitrates'], loss_pcts, f'UDP {target_rate}')
                
                f.write(f"UDP {target_rate} Statistics:\n")
                f.write("-" * 50 + "\n")
                f.write(f"  Total Samples:     {stats['total_samples']:,}\n")
                f.write(f"  Mean Bitrate:      {stats['mean_bitrate']:.2f} Mbps\n")
                f.write(f"  Median Bitrate:    {stats['median_bitrate']:.2f} Mbps\n")
                f.write(f"  Std Deviation:     {stats['std_dev']:.2f} Mbps\n")
                f.write(f"  Min Bitrate:       {stats['min_bitrate']:.2f} Mbps\n")
                f.write(f"  Max Bitrate:       {stats['max_bitrate']:.2f} Mbps\n")
                f.write(f"  5th Percentile:    {stats['percentile_5']:.2f} Mbps\n")
                f.write(f"  25th Percentile:   {stats['percentile_25']:.2f} Mbps\n")
                f.write(f"  75th Percentile:   {stats['percentile_75']:.2f} Mbps\n")
                f.write(f"  95th Percentile:   {stats['percentile_95']:.2f} Mbps\n")
                f.write(f"  99th Percentile:   {stats['percentile_99']:.2f} Mbps\n")
                
                if loss_pcts:
                    f.write(f"\n  Packet Loss Statistics:\n")
                    f.write(f"  Mean Loss:         {stats['mean_loss_pct']:.4f}%\n")
                    f.write(f"  Median Loss:       {stats['median_loss_pct']:.4f}%\n")
                    f.write(f"  Min Loss:          {stats['min_loss_pct']:.4f}%\n")
                    f.write(f"  Max Loss:          {stats['max_loss_pct']:.4f}%\n")
                
                f.write("\n")
        
        f.write("=" * 70 + "\n")
    
    print(f"Statistics saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Analyze UDP performance data from iperf3 log files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  python analyze_udp.py                        # Uses default 'starlink_raw' folder
  python analyze_udp.py --folder my_dataset    # Uses 'my_dataset' folder
        """
    )
    
    parser.add_argument(
        '--folder',
        type=str,
        default='starlink_raw',
        help='Name of the folder inside benchmarks/ containing tests/log/udp.log (default: starlink_raw)'
    )
    
    args = parser.parse_args()
    
    # Set up paths
    script_dir = Path(__file__).parent
    data_folder = script_dir / 'benchmarks' / args.folder / 'tests' / 'log'
    log_file = data_folder / 'udp.log'
    output_dir = script_dir / 'analysis' / args.folder
    
    # Validate input file
    if not log_file.exists():
        print(f"Error: Log file not found at {log_file}")
        print(f"Expected structure: benchmarks/{args.folder}/tests/log/udp.log")
        return 1
    
    # Create output directory if needed
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Reading UDP performance data from: {log_file}")
    print(f"Output directory: {output_dir}")
    print()
    
    # Parse the log file
    print("Parsing log file...")
    data = parse_udp_log(log_file)
    
    # Check if we got data
    total_samples = sum([
        len(data['100M'].get('bitrates', [])),
        len(data['300M'].get('bitrates', [])),
        len(data['600M'].get('bitrates', [])),
        len(data['900M'].get('bitrates', []))
    ])
    
    if total_samples == 0:
        print("Error: No valid UDP performance data found in log file")
        return 1
    
    print(f"Parsed UDP performance data:")
    print(f"  UDP 100M:  {len(data['100M'].get('bitrates', [])):,} samples")
    print(f"  UDP 300M:  {len(data['300M'].get('bitrates', [])):,} samples")
    print(f"  UDP 600M:  {len(data['600M'].get('bitrates', [])):,} samples")
    print(f"  UDP 900M:  {len(data['900M'].get('bitrates', [])):,} samples")
    print()
    
    # Create plots for each target rate
    print("Generating plots...")
    for target_rate in ['100M', '300M', '600M', '900M']:
        create_plots(data[target_rate], target_rate, output_dir)
    
    # Save statistics
    print("Saving statistics...")
    save_statistics(data, output_dir)
    
    print()
    print("Analysis complete!")
    
    return 0


if __name__ == '__main__':
    exit(main())
