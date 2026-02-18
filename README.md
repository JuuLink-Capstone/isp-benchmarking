# juulink - Network Performance Testing Suite

A comprehensive network benchmarking tool that performs TCP, UDP, and ICMP (ping) tests using iperf3 and fping, with automated analysis and visualization.

## Features

- **TCP Testing**: Client-to-server (C2S), server-to-client (S2C), and bidirectional (BIDIR) throughput tests
- **UDP Testing**: Bandwidth ladder tests at multiple rates (100M, 300M, 600M, 900M)
- **Ping Monitoring**: Continuous latency monitoring with fping during all tests
- **Automated Analysis**: Statistical analysis and visualization of all test results
- **Retry Logic**: Automatic retry on failed tests with configurable attempts
- **Structured Logging**: Organized log files for easy post-processing

## Prerequisites

- Linux operating system (Debian/Ubuntu, Fedora, CentOS/RHEL, or Arch)
- Root/sudo access for system package installation
- iperf3 server running on target host

## Installation

Run the setup script to install all dependencies:

```bash
chmod +x setup.sh
./setup.sh
```

This will:
- Install system packages: Python 3, fping, iperf3, traceroute, net-tools, ethtool
- Create and activate a Python virtual environment
- Install Python dependencies: numpy, matplotlib, pyyaml

## Configuration

Copy and edit the configuration file:

```bash
cp config.template.yaml config.yaml
nano config.yaml
```

Key configuration options:

- `server`: Target iperf3 server IP address
- `bind_ip`: Local IP address to bind to
- `interface`: Network interface to use
- `duration`: Test duration in seconds (default: 300)
- `omit`: TCP slow-start omit time (default: 30)
- `log_dir`: Directory for log files
- `udp_rates`: List of UDP bandwidth rates to test
- `retries`: Number of retry attempts on test failure

## Usage

### Running Tests

Activate the virtual environment and run the iterator:

```bash
source .venv/bin/activate
./iterator.py
```

The iterator will:
1. Clean up old log files
2. Start fping background monitoring
3. Run TCP tests (C2S, S2C, BIDIR)
4. Run UDP tests at each configured rate
5. Continue iterating until interrupted (Ctrl+C)

All results are logged to the directory specified in `config.yaml`.

### Analyzing Results

After collecting test data, analyze the results:

```bash
# Analyze ping data
./analyze_ping.py benchmarks/your-test-dir/

# Analyze TCP performance
./analyze_tcp.py benchmarks/your-test-dir/

# Analyze UDP performance
./analyze_udp.py benchmarks/your-test-dir/
```

Each analysis script generates:
- Statistical summary text file (`_stats_*.txt`)
- Time-series plots showing performance over iterations
- PNG images saved to `analysis/` subdirectory

### Analysis Outputs

**Ping Analysis:**
- Latency statistics (min, max, mean, median, P95, P99)
- Packet loss metrics
- Time-series plot of latency with percentiles

**TCP Analysis:**
- Per-test-type statistics (C2S, S2C, BIDIR)
- Throughput in Mbps/Gbps
- Retry count analysis
- Individual and combined performance plots

**UDP Analysis:**
- Per-rate statistics (100M, 300M, 600M, 900M)
- Achieved vs target bitrate
- Packet loss analysis
- Multi-panel comparison plots

## File Structure

```
juulink/
├── setup.sh              # Installation script
├── config.yaml           # Configuration file
├── iterator.py           # Main test runner
├── analyze_ping.py       # Ping analysis tool
├── analyze_tcp.py        # TCP analysis tool
├── analyze_udp.py        # UDP analysis tool
├── requirements.txt      # Python dependencies
└── benchmarks/           # Test results directory
    └── [test-name]/
        ├── metadata.log  # Test metadata
        ├── tcp.log       # TCP test results
        ├── udp.log       # UDP test results
        ├── fping.log     # Ping monitoring data
        └── analysis/     # Generated plots and stats
```

## Tips

- Run tests during different times of day to capture network variability
- Use descriptive names for `log_dir` to organize multiple test campaigns
- Adjust `duration` and `omit` based on your network's characteristics
- Monitor system resources during tests (CPU, memory, network)
- For long-running campaigns, use `screen` or `tmux` to prevent disconnection

## Troubleshooting

- **Permission denied**: Ensure scripts are executable (`chmod +x`)
- **fping not found**: Run `setup.sh` to install system dependencies
- **Connection refused**: Verify iperf3 server is running on target host
- **Network unreachable**: Check `bind_ip` and `interface` settings
- **Import errors**: Activate virtual environment with `source .venv/bin/activate`

## License

This project is provided as-is for network testing and research purposes.
