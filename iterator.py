#!/usr/bin/env python3
"""
Network Testing Iterator
Performs TCP and UDP tests with fping monitoring in the background.
"""

import os
import sys
import signal
import subprocess
import time
import argparse
from datetime import datetime
from pathlib import Path
import yaml


class NetworkTester:
    def __init__(self, config_path="config.yaml"):
        """Initialize the network tester with configuration."""
        self.config = self.load_config(config_path)
        self.fping_process = None
        self.iter = self.config['iter_start']
        self.setup_logging()
        
    def load_config(self, config_path):
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"Error: Configuration file '{config_path}' not found.")
            sys.exit(1)
        except yaml.YAMLError as e:
            print(f"Error parsing YAML configuration: {e}")
            sys.exit(1)
    
    def setup_logging(self):
        """Create log directory and set up log file paths."""
        log_dir = Path(self.config['log_dir'])
        log_dir.mkdir(parents=True, exist_ok=True)
        
        self.log_files = {
            'metadata': log_dir / self.config['log_files']['metadata'],
            'tcp': log_dir / self.config['log_files']['tcp'],
            'udp': log_dir / self.config['log_files']['udp'],
            'fping': log_dir / self.config['log_files']['fping']
        }
    
    def cleanup_logs(self):
        """Remove existing log files."""
        for log_file in self.log_files.values():
            if log_file.exists():
                log_file.unlink()
        print("Logs cleaned.")
    
    def cleanup(self, signum=None, frame=None):
        """Cleanup handler for graceful shutdown."""
        timestamp = datetime.now().isoformat()
        msg = f"[{timestamp}] Caught shutdown signal, cleaning up\n"
        
        with open(self.log_files['metadata'], 'a') as f:
            f.write(msg)
        print(msg.strip())
        
        # Stop fping
        if self.fping_process and self.fping_process.poll() is None:
            self.fping_process.terminate()
            try:
                self.fping_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.fping_process.kill()
        
        # Log ethtool stats post-run
        self.log_ethtool("post-run")
        
        sys.exit(0)
    
    def log_ethtool(self, label):
        """Log ethtool statistics."""
        timestamp = datetime.now().isoformat()
        try:
            result = subprocess.run(
                ['ethtool', '-S', self.config['interface']],
                capture_output=True,
                text=True
            )
            with open(self.log_files['metadata'], 'a') as f:
                f.write(f"[{timestamp}] ethtool {label}\n")
                f.write(result.stdout)
                if result.stderr:
                    f.write(result.stderr)
        except Exception as e:
            with open(self.log_files['metadata'], 'a') as f:
                f.write(f"Error running ethtool: {e}\n")
    
    def write_metadata_header(self):
        """Write initial metadata to log."""
        timestamp = datetime.now().isoformat()
        with open(self.log_files['metadata'], 'a') as f:
            f.write("=" * 40 + "\n")
            f.write(f"Run start: {timestamp}\n")
            f.write(f"Server: {self.config['server']}:{self.config.get('port', 5201)}\n")
            f.write(f"Bind IP: {self.config['bind_ip']}\n")
            f.write(f"Interface: {self.config['interface']}\n")
            f.write("-" * 40 + "\n")
        
        self.log_ethtool("pre-run")
        
        with open(self.log_files['metadata'], 'a') as f:
            f.write("=" * 40 + "\n")
    
    def start_fping(self):
        """Start fping in the background."""
        fping_config = self.config['fping']
        cmd = [
            'fping',
            '-l',
            '-e',
            '-D',
            '-i', str(fping_config['interval_ms']),
            self.config['server']
        ]
        
        with open(self.log_files['fping'], 'a') as f:
            self.fping_process = subprocess.Popen(
                cmd,
                stdout=f,
                stderr=subprocess.STDOUT
            )
        print(f"Started fping (PID: {self.fping_process.pid})")
    
    def run_tcp_test(self, mode, timestamp):
        """Run a single TCP test with retries."""
        retries = self.config['retries']
        sleep_between = self.config['sleep_between']
        
        for attempt in range(1, retries + 1):
            header = f"========== ITER {self.iter} | {timestamp} | TCP {mode} ==========\n"
            
            # Build iperf3 command
            cmd = [
                'iperf3',
                '-c', self.config['server'],
                '-p', str(self.config.get('port', 5201)),
                '-t', str(self.config['duration']),
                '--omit', str(self.config['omit']),
                '-B', self.config['bind_ip']
            ]
            
            if mode == 'S2C':
                cmd.append('-R')
            elif mode == 'BIDIR':
                cmd.append('--bidir')
            
            # Write header and run test
            with open(self.log_files['tcp'], 'a') as f:
                f.write(header)
                f.flush()
                result = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)
            
            if result.returncode == 0:
                return True
            else:
                msg = f"Iteration {self.iter}, mode {mode} failed on attempt {attempt}, "
                if attempt < retries:
                    msg += f"retrying in {sleep_between} sec...\n"
                    with open(self.log_files['tcp'], 'a') as f:
                        f.write(msg)
                    time.sleep(sleep_between)
                else:
                    msg = f"Iteration {self.iter}, mode {mode} failed after {retries} attempts, skipping...\n"
                    with open(self.log_files['tcp'], 'a') as f:
                        f.write(msg)
        
        return False
    
    def run_udp_test(self, rate, timestamp):
        """Run a single UDP test with retries."""
        retries = self.config['retries']
        sleep_between = self.config['sleep_between']
        
        for attempt in range(1, retries + 1):
            header = f"========== ITER {self.iter} | {timestamp} | UDP {rate} ==========\n"
            
            cmd = [
                'iperf3',
                '-c', self.config['server'],
                '-p', str(self.config.get('port', 5201)),
                '-t', str(self.config['duration']),
                '-u',
                '-b', rate,
                '-B', self.config['bind_ip']
            ]
            
            with open(self.log_files['udp'], 'a') as f:
                f.write(header)
                f.flush()
                result = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)
            
            if result.returncode == 0:
                return True
            else:
                msg = f"Iteration {self.iter}, UDP {rate} failed on attempt {attempt}, "
                if attempt < retries:
                    msg += f"retrying in {sleep_between} sec...\n"
                    with open(self.log_files['udp'], 'a') as f:
                        f.write(msg)
                    time.sleep(sleep_between)
                else:
                    msg = f"Iteration {self.iter}, UDP {rate} failed after {retries} attempts, skipping...\n"
                    with open(self.log_files['udp'], 'a') as f:
                        f.write(msg)
        
        return False
    
    def run_iteration(self):
        """Run a complete test iteration."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sleep_between = self.config['sleep_between']
        
        print(f"\n=== Iteration {self.iter} | {timestamp} ===")
        
        # TCP Tests
        for mode in ['C2S', 'S2C', 'BIDIR']:
            print(f"Running TCP {mode}...")
            self.run_tcp_test(mode, timestamp)
            time.sleep(sleep_between)
        
        # UDP Tests
        for rate in self.config['udp_rates']:
            print(f"Running UDP {rate}...")
            self.run_udp_test(rate, timestamp)
            time.sleep(sleep_between)
        
        self.iter += 1
    
    def run(self, duration_minutes=None):
        """Main execution loop.
        
        Args:
            duration_minutes: If specified, run for this many minutes then exit gracefully.
        """
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.cleanup)
        signal.signal(signal.SIGTERM, self.cleanup)
        
        # Write metadata
        self.write_metadata_header()
        
        # Start background fping
        self.start_fping()
        
        # Calculate end time if duration specified
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60) if duration_minutes else None
        
        # Main loop
        try:
            while True:
                self.run_iteration()
                
                # Check if we've exceeded duration
                if end_time and time.time() >= end_time:
                    print(f"\nReached target duration of {duration_minutes} minutes. Stopping...")
                    break
        except KeyboardInterrupt:
            self.cleanup()
        
        # Clean shutdown after duration expires
        if end_time:
            self.cleanup()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Network Testing Iterator - TCP/UDP/ICMP benchmark suite"
    )
    parser.add_argument(
        '-c', '--config',
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    parser.add_argument(
        '-d', '--duration',
        type=int,
        metavar='MINUTES',
        help='Run for specified duration in minutes (e.g., -d 360 = 6 hours)'
    )
    parser.add_argument(
        '--clean',
        action='store_true',
        help='Clean log files and exit'
    )
    
    args = parser.parse_args()
    
    tester = NetworkTester(args.config)
    
    if args.clean:
        tester.cleanup_logs()
        sys.exit(0)
    
    # Normal execution
    tester.run(duration_minutes=args.duration)


if __name__ == "__main__":
    main()
