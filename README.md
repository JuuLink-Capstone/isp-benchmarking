# juulink - Network Performance Testing

Network benchmarking tool for TCP, UDP, and ICMP tests using iperf3 and fping with automated analysis.

## Setup

Install dependencies and create Python virtual environment:

```bash
chmod +x setup.sh
./setup.sh
```

Installs: Python 3, fping, iperf3, traceroute, net-tools, ethtool, plus Python packages (numpy, matplotlib, pyyaml).

## Configuration

Edit `config.yaml` with your settings:

```yaml
server: "your.server.ip"     # iperf3 server
port: 5201                   # iperf3 server port
bind_ip: "your.local.ip"     # local interface IP
interface: "eth0"            # network interface
duration: 300                # test duration (seconds)
log_dir: "./benchmarks/test" # output directory
udp_rates: ["100M", "300M", "600M", "900M"]
```

## Running Tests

```bash
source .venv/bin/activate
./iterator.py                          # Use config.yaml, run until stopped
./iterator.py -c config-custom.yaml    # Use custom config
./iterator.py -d 360                   # Run for 360 minutes (6 hours)
./iterator.py -c config.yaml -d 120    # Custom config, 2 hours
./iterator.py --clean                  # Clean logs
```

Run multiple configs simultaneously (use different `log_dir` for each):
```bash
./iterator.py -c config1.yaml -d 360 &
./iterator.py -c config2.yaml -d 360 &
```

Tests run continuously until stopped (Ctrl+C) or duration expires. Performs TCP (C2S/S2C/BIDIR) and UDP tests with continuous ping monitoring.

## Analysis

Generate statistics and plots:

```bash
./analyze_ping.py benchmarks/test-dir/
./analyze_tcp.py benchmarks/test-dir/
./analyze_udp.py benchmarks/test-dir/
```

Output: `_stats_*.txt` files and PNG plots in `analysis/` subdirectory.

## Requirements

- Linux system with sudo access
- iperf3 server running on target host
- Network interface configured
