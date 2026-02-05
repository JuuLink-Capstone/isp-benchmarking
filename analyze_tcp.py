#!/usr/bin/env python3
"""
TCP Performance Analysis Script
Analyzes iperf3 TCP log files and generates plots and statistical summaries.
Handles C2S (upload), S2C (download), and BIDIR (bidirectional) tests.
"""

import re
import argparse
from pathlib import Path
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from collections import defaultdict


def parse_tcp_log(log_file):
    """
    Parse iperf3 TCP log file and extract performance data.
    
    Returns data organized by test type and iteration:
    {
        'c2s': {'iterations': [...], 'timestamps': [...], 'bitrates': [...], 'retries': [...]},
        's2c': {'iterations': [...], 'timestamps': [...], 'bitrates': [...]},
        'bidir': {'iterations': [...], 'timestamps': [...], 'tx_bitrates': [...], 'rx_bitrates': [...]}
    }
    """
    data = {
        'c2s': defaultdict(list),
        's2c': defaultdict(list),
        'bidir': defaultdict(list)
    }
    
    current_test = None
    current_iter = None
    current_timestamp = None
    
    # Patterns
    header_pattern = r'========== ITER (\d+) \| (\d+_\d+) \| TCP (C2S|S2C|BIDIR) =========='
    # C2S pattern: has Retr and Cwnd columns
    c2s_pattern = r'\[\s*\d+\]\s+([\d.]+)-([\d.]+)\s+sec\s+[\d.]+\s+[MG]Bytes\s+([\d.]+)\s+([MG])bits/sec\s+(\d+)\s+[\d.]+\s+[MG]Bytes(?:\s+\(omitted\))?$'
    # S2C pattern: no Retr/Cwnd columns
    s2c_pattern = r'\[\s*\d+\]\s+([\d.]+)-([\d.]+)\s+sec\s+[\d.]+\s+[MG]Bytes\s+([\d.]+)\s+([MG])bits/sec(?:\s+\(omitted\))?$'
    # BIDIR patterns: has role indicator [TX-C] or [RX-C]
    bidir_tx_pattern = r'\[\s*\d+\]\[TX-C\]\s+([\d.]+)-([\d.]+)\s+sec\s+[\d.]+\s+[MG]Bytes\s+([\d.]+)\s+([MG])bits/sec\s+\d+\s+[\d.]+\s+[MG]Bytes(?:\s+\(omitted\))?$'
    bidir_rx_pattern = r'\[\s*\d+\]\[RX-C\]\s+([\d.]+)-([\d.]+)\s+sec\s+[\d.]+\s+[MG]Bytes\s+([\d.]+)\s+([MG])bits/sec(?:\s+\(omitted\))?$'
    
    with open(log_file, 'r') as f:
        for line in f:
            line = line.strip()
            
            # Check for test header
            header_match = re.match(header_pattern, line)
            if header_match:
                current_iter = int(header_match.group(1))
                timestamp_str = header_match.group(2)
                test_type = header_match.group(3).lower()
                current_test = test_type
                # Parse timestamp: format is YYYYMMDD_HHMMSS
                current_timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                continue
            
            if current_test is None:
                continue
            
            # Skip omitted lines
            if '(omitted)' in line:
                continue
            
            # Parse data based on test type
            if current_test == 'c2s':
                match = re.match(c2s_pattern, line)
                if match:
                    end_time = float(match.group(2))
                    bitrate = float(match.group(3))
                    unit = match.group(4)
                    retries = int(match.group(5))
                    
                    # Convert to Mbps
                    if unit == 'G':
                        bitrate *= 1000
                    
                    # Calculate timestamp for this data point
                    point_time = current_timestamp.timestamp() + end_time
                    
                    data['c2s']['iterations'].append(current_iter)
                    data['c2s']['timestamps'].append(datetime.fromtimestamp(point_time))
                    data['c2s']['bitrates'].append(bitrate)
                    data['c2s']['retries'].append(retries)
            
            elif current_test == 's2c':
                match = re.match(s2c_pattern, line)
                if match:
                    end_time = float(match.group(2))
                    bitrate = float(match.group(3))
                    unit = match.group(4)
                    
                    # Convert to Mbps
                    if unit == 'G':
                        bitrate *= 1000
                    
                    point_time = current_timestamp.timestamp() + end_time
                    
                    data['s2c']['iterations'].append(current_iter)
                    data['s2c']['timestamps'].append(datetime.fromtimestamp(point_time))
                    data['s2c']['bitrates'].append(bitrate)
            
            elif current_test == 'bidir':
                tx_match = re.match(bidir_tx_pattern, line)
                rx_match = re.match(bidir_rx_pattern, line)
                
                if tx_match:
                    end_time = float(tx_match.group(2))
                    bitrate = float(tx_match.group(3))
                    unit = tx_match.group(4)
                    
                    if unit == 'G':
                        bitrate *= 1000
                    
                    point_time = current_timestamp.timestamp() + end_time
                    
                    data['bidir']['iterations'].append(current_iter)
                    data['bidir']['timestamps'].append(datetime.fromtimestamp(point_time))
                    data['bidir']['tx_bitrates'].append(bitrate)
                
                elif rx_match:
                    end_time = float(rx_match.group(2))
                    bitrate = float(rx_match.group(3))
                    unit = rx_match.group(4)
                    
                    if unit == 'G':
                        bitrate *= 1000
                    
                    # Only append RX data if we have a corresponding TX entry
                    # In BIDIR tests, RX and TX lines should be paired
                    if len(data['bidir']['rx_bitrates']) < len(data['bidir']['tx_bitrates']):
                        data['bidir']['rx_bitrates'].append(bitrate)
    
    # Convert to regular dicts
    return {k: dict(v) for k, v in data.items()}


def calculate_statistics(bitrates, test_name):
    """Calculate comprehensive statistics for throughput data."""
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
    
    return stats


def create_plots(data, output_dir):
    """Create visualization plots for TCP performance data."""
    
    # C2S (Upload) plots
    if data['c2s']['bitrates']:
        fig, axes = plt.subplots(3, 1, figsize=(14, 12))
        
        timestamps = data['c2s']['timestamps']
        bitrates = data['c2s']['bitrates']
        
        # Time series
        axes[0].plot(timestamps, bitrates, linewidth=0.5, alpha=0.7, color='blue')
        axes[0].set_xlabel('Time')
        axes[0].set_ylabel('Bitrate (Mbps)')
        axes[0].set_title('TCP C2S (Upload) - Bitrate Over Time')
        axes[0].grid(True, alpha=0.3)
        axes[0].xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
        
        # Distribution histogram
        axes[1].hist(bitrates, bins=100, color='blue', alpha=0.7, edgecolor='black')
        axes[1].set_xlabel('Bitrate (Mbps)')
        axes[1].set_ylabel('Frequency (log scale)')
        axes[1].set_title('TCP C2S - Bitrate Distribution')
        axes[1].set_yscale('log')
        axes[1].grid(True, alpha=0.3, axis='y')
        
        # Box plot
        axes[2].boxplot([bitrates], vert=False, widths=0.5, 
                          whis=[5, 95], showfliers=True,
                          flierprops=dict(marker='o', markersize=2, alpha=0.3, markerfacecolor='red'))
        axes[2].set_xlabel('Bitrate (Mbps)')
        axes[2].set_title('TCP C2S - Bitrate Box Plot (1st-99th %ile)')
        p1 = np.percentile(bitrates, 1)
        p99 = np.percentile(bitrates, 99)
        axes[2].set_xlim(left=p1, right=p99)
        axes[2].grid(True, alpha=0.3, axis='x')
        axes[2].set_yticklabels(['Upload'])
        axes[2].text(0.02, 0.98, 'Orange line = Median', 
                       transform=axes[2].transAxes, fontsize=9,
                       verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        plot_file = output_dir / 'tcp_c2s_analysis.png'
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"C2S plot saved to: {plot_file}")
    
    # S2C (Download) plots
    if data['s2c']['bitrates']:
        fig, axes = plt.subplots(3, 1, figsize=(14, 12))
        
        timestamps = data['s2c']['timestamps']
        bitrates = data['s2c']['bitrates']
        
        # Time series
        axes[0].plot(timestamps, bitrates, linewidth=0.5, alpha=0.7, color='green')
        axes[0].set_xlabel('Time')
        axes[0].set_ylabel('Bitrate (Mbps)')
        axes[0].set_title('TCP S2C (Download) - Bitrate Over Time')
        axes[0].grid(True, alpha=0.3)
        axes[0].xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
        
        # Distribution histogram
        axes[1].hist(bitrates, bins=100, color='green', alpha=0.7, edgecolor='black')
        axes[1].set_xlabel('Bitrate (Mbps)')
        axes[1].set_ylabel('Frequency (log scale)')
        axes[1].set_title('TCP S2C - Bitrate Distribution')
        axes[1].set_yscale('log')
        axes[1].grid(True, alpha=0.3, axis='y')
        
        # Box plot
        axes[2].boxplot([bitrates], vert=False, widths=0.5, 
                          whis=[5, 95], showfliers=True,
                          flierprops=dict(marker='o', markersize=2, alpha=0.3, markerfacecolor='red'))
        axes[2].set_xlabel('Bitrate (Mbps)')
        axes[2].set_title('TCP S2C - Bitrate Box Plot (1st-99th %ile)')
        p1 = np.percentile(bitrates, 1)
        p99 = np.percentile(bitrates, 99)
        axes[2].set_xlim(left=p1, right=p99)
        axes[2].grid(True, alpha=0.3, axis='x')
        axes[2].set_yticklabels(['Download'])
        axes[2].text(0.02, 0.98, 'Orange line = Median', 
                       transform=axes[2].transAxes, fontsize=9,
                       verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        plot_file = output_dir / 'tcp_s2c_analysis.png'
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"S2C plot saved to: {plot_file}")
    
    # BIDIR plots
    if data['bidir']['tx_bitrates']:
        fig, axes = plt.subplots(3, 1, figsize=(14, 12))
        
        timestamps = data['bidir']['timestamps']
        tx_bitrates = data['bidir']['tx_bitrates']
        rx_bitrates = data['bidir']['rx_bitrates']
        
        # Time series
        axes[0].plot(timestamps, tx_bitrates, linewidth=0.5, alpha=0.7, color='blue', label='TX (Upload)')
        axes[0].plot(timestamps, rx_bitrates, linewidth=0.5, alpha=0.7, color='green', label='RX (Download)')
        axes[0].set_xlabel('Time')
        axes[0].set_ylabel('Bitrate (Mbps)')
        axes[0].set_title('TCP BIDIR - Bitrate Over Time')
        axes[0].grid(True, alpha=0.3)
        axes[0].legend(loc='upper right')
        axes[0].xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
        
        # Combined distribution
        axes[1].hist([tx_bitrates, rx_bitrates], bins=100, 
                       color=['blue', 'green'], alpha=0.6, edgecolor='black',
                       label=['TX (Upload)', 'RX (Download)'])
        axes[1].set_xlabel('Bitrate (Mbps)')
        axes[1].set_ylabel('Frequency (log scale)')
        axes[1].set_title('TCP BIDIR - Bitrate Distribution')
        axes[1].set_yscale('log')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3, axis='y')
        
        # Box plot - both directions
        axes[2].boxplot([tx_bitrates, rx_bitrates], vert=False, widths=0.5, 
                          whis=[5, 95], showfliers=True,
                          flierprops=dict(marker='o', markersize=2, alpha=0.3, markerfacecolor='red'))
        axes[2].set_xlabel('Bitrate (Mbps)')
        axes[2].set_title('TCP BIDIR - Bitrate Box Plot (1st-99th %ile)')
        all_rates = tx_bitrates + rx_bitrates
        p1 = np.percentile(all_rates, 1)
        p99 = np.percentile(all_rates, 99)
        axes[2].set_xlim(left=p1, right=p99)
        axes[2].grid(True, alpha=0.3, axis='x')
        axes[2].set_yticklabels(['TX', 'RX'])
        axes[2].text(0.02, 0.98, 'Orange line = Median', 
                       transform=axes[2].transAxes, fontsize=9,
                       verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        plot_file = output_dir / 'tcp_bidir_analysis.png'
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"BIDIR plot saved to: {plot_file}")


def save_statistics(data, output_dir):
    """Save statistical results to a text file."""
    output_file = output_dir / 'tcp_stats.txt'
    
    with open(output_file, 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("TCP PERFORMANCE ANALYSIS RESULTS\n")
        f.write("=" * 70 + "\n\n")
        
        # C2S Statistics
        if data['c2s']['bitrates']:
            stats = calculate_statistics(data['c2s']['bitrates'], 'TCP C2S (Upload)')
            
            f.write("TCP C2S (Upload) Statistics:\n")
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
            
            if data['c2s']['retries']:
                total_retries = sum(data['c2s']['retries'])
                f.write(f"  Total Retries:     {total_retries:,}\n")
            f.write("\n")
        
        # S2C Statistics
        if data['s2c']['bitrates']:
            stats = calculate_statistics(data['s2c']['bitrates'], 'TCP S2C (Download)')
            
            f.write("TCP S2C (Download) Statistics:\n")
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
            f.write(f"  99th Percentile:   {stats['percentile_99']:.2f} Mbps\n\n")
        
        # BIDIR Statistics
        if data['bidir']['tx_bitrates']:
            tx_stats = calculate_statistics(data['bidir']['tx_bitrates'], 'TCP BIDIR TX (Upload)')
            rx_stats = calculate_statistics(data['bidir']['rx_bitrates'], 'TCP BIDIR RX (Download)')
            
            f.write("TCP BIDIR TX (Upload) Statistics:\n")
            f.write("-" * 50 + "\n")
            f.write(f"  Total Samples:     {tx_stats['total_samples']:,}\n")
            f.write(f"  Mean Bitrate:      {tx_stats['mean_bitrate']:.2f} Mbps\n")
            f.write(f"  Median Bitrate:    {tx_stats['median_bitrate']:.2f} Mbps\n")
            f.write(f"  Std Deviation:     {tx_stats['std_dev']:.2f} Mbps\n")
            f.write(f"  Min Bitrate:       {tx_stats['min_bitrate']:.2f} Mbps\n")
            f.write(f"  Max Bitrate:       {tx_stats['max_bitrate']:.2f} Mbps\n")
            f.write(f"  5th Percentile:    {tx_stats['percentile_5']:.2f} Mbps\n")
            f.write(f"  25th Percentile:   {tx_stats['percentile_25']:.2f} Mbps\n")
            f.write(f"  75th Percentile:   {tx_stats['percentile_75']:.2f} Mbps\n")
            f.write(f"  95th Percentile:   {tx_stats['percentile_95']:.2f} Mbps\n")
            f.write(f"  99th Percentile:   {tx_stats['percentile_99']:.2f} Mbps\n\n")
            
            f.write("TCP BIDIR RX (Download) Statistics:\n")
            f.write("-" * 50 + "\n")
            f.write(f"  Total Samples:     {rx_stats['total_samples']:,}\n")
            f.write(f"  Mean Bitrate:      {rx_stats['mean_bitrate']:.2f} Mbps\n")
            f.write(f"  Median Bitrate:    {rx_stats['median_bitrate']:.2f} Mbps\n")
            f.write(f"  Std Deviation:     {rx_stats['std_dev']:.2f} Mbps\n")
            f.write(f"  Min Bitrate:       {rx_stats['min_bitrate']:.2f} Mbps\n")
            f.write(f"  Max Bitrate:       {rx_stats['max_bitrate']:.2f} Mbps\n")
            f.write(f"  5th Percentile:    {rx_stats['percentile_5']:.2f} Mbps\n")
            f.write(f"  25th Percentile:   {rx_stats['percentile_25']:.2f} Mbps\n")
            f.write(f"  75th Percentile:   {rx_stats['percentile_75']:.2f} Mbps\n")
            f.write(f"  95th Percentile:   {rx_stats['percentile_95']:.2f} Mbps\n")
            f.write(f"  99th Percentile:   {rx_stats['percentile_99']:.2f} Mbps\n\n")
        
        f.write("=" * 70 + "\n")
    
    print(f"Statistics saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Analyze TCP performance data from iperf3 log files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  python analyze_tcp.py                        # Uses default 'starlink_raw' folder
  python analyze_tcp.py --folder my_dataset    # Uses 'my_dataset' folder
        """
    )
    
    parser.add_argument(
        '--folder',
        type=str,
        default='starlink_raw',
        help='Name of the folder inside benchmarks/ containing tests/log/tcp.log (default: starlink_raw)'
    )
    
    args = parser.parse_args()
    
    # Set up paths
    script_dir = Path(__file__).parent
    data_folder = script_dir / 'benchmarks' / args.folder / 'tests' / 'log'
    log_file = data_folder / 'tcp.log'
    output_dir = script_dir / 'analysis' / args.folder
    
    # Validate input file
    if not log_file.exists():
        print(f"Error: Log file not found at {log_file}")
        print(f"Expected structure: benchmarks/{args.folder}/tests/log/tcp.log")
        return 1
    
    # Create output directory if needed
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Reading TCP performance data from: {log_file}")
    print(f"Output directory: {output_dir}")
    print()
    
    # Parse the log file
    print("Parsing log file...")
    data = parse_tcp_log(log_file)
    
    # Check if we got data
    total_samples = sum([
        len(data['c2s'].get('bitrates', [])),
        len(data['s2c'].get('bitrates', [])),
        len(data['bidir'].get('tx_bitrates', []))
    ])
    
    if total_samples == 0:
        print("Error: No valid TCP performance data found in log file")
        return 1
    
    print(f"Parsed TCP performance data:")
    print(f"  C2S (Upload):      {len(data['c2s'].get('bitrates', [])):,} samples")
    print(f"  S2C (Download):    {len(data['s2c'].get('bitrates', [])):,} samples")
    print(f"  BIDIR:             {len(data['bidir'].get('tx_bitrates', [])):,} samples")
    print()
    
    # Create plots
    print("Generating plots...")
    create_plots(data, output_dir)
    
    # Save statistics
    print("Saving statistics...")
    save_statistics(data, output_dir)
    
    print()
    print("Analysis complete!")
    
    return 0


if __name__ == '__main__':
    exit(main())
