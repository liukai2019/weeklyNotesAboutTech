WSL Proxy Configuration Notes

Purpose

This document records the changes made to persist HTTP/HTTPS/SOCKS proxy settings inside WSL2, and the temporary apt proxy config used to verify access to external package repositories via the local Clash proxy running on Windows.

Files created

1. /etc/profile.d/95proxy.sh
   - Purpose: system-wide environment variables for shells started on WSL.
   - Contents (example):
     # Persist proxy settings for system shells
     export http_proxy="http://127.0.0.1:7897"
     export https_proxy="http://127.0.0.1:7897"
     export all_proxy="socks5://127.0.0.1:7897"
     export HTTP_PROXY="$http_proxy"
     export HTTPS_PROXY="$https_proxy"
     export ALL_PROXY="$all_proxy"
     export no_proxy="localhost,127.0.0.1,::1,192.168.0.0/16,10.0.0.0/8"
     export NO_PROXY="$no_proxy"

2. /etc/apt/apt.conf.d/95proxies
   - Purpose: allow apt to fetch packages through the local HTTP proxy
   - Contents (example):
     Acquire::http::Proxy "http://127.0.0.1:7897";
     Acquire::https::Proxy "http://127.0.0.1:7897";

Verification steps

1. Verify the profile script exists and contains the proxy exports:
   sudo sed -n '1,200p' /etc/profile.d/95proxy.sh

2. Start a new shell or source the script to apply variables immediately:
   . /etc/profile.d/95proxy.sh
   env | egrep -i 'http_proxy|https_proxy|all_proxy|no_proxy'

3. Verify HTTP access via proxy (curl will use http_proxy env):
   curl -I -v --max-time 10 http://example.com

4. Verify apt works through proxy:
   sudo apt-get update

Rollback / Removal

- To remove system-wide proxy settings:
  sudo rm /etc/profile.d/95proxy.sh
  # then restart shells (logout/login) or run: exec $SHELL

- To remove apt proxy config:
  sudo rm /etc/apt/apt.conf.d/95proxies
  sudo apt-get update

Notes and caveats

- ICMP (ping) does not go through HTTP/SOCKS proxy. A failure to ping a host does not mean HTTP/SOCKS traffic is broken. Use tcp-based tests (curl, nc) to test service reachability.
- WSL's /etc/resolv.conf is managed by Windows/WSL by default. If you change DNS settings, consider setting generateResolvConf=false in /etc/wsl.conf and writing resolv.conf manually.
- If you want *all* traffic (not just proxied TCP/HTTP) to use the VPN/Clash, enable TUN/system proxy in the Windows-side Clash or use a system-level VPN. Clash's TUN mode can make WSL traffic go through the VPN-like interface.
- Adjust NO_PROXY as needed to exclude internal network ranges or specific hosts.

Next steps (optional)

- Persist user-level proxy variables in ~/.bashrc if you prefer not to use system-wide settings.
- Configure Windows Clash to expose a TUN or set system proxy to global to capture non-proxied traffic from WSL.
- Add a small script to toggle proxy on/off quickly.

Generated on: 2025-12-14
