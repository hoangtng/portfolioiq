#!/usr/bin/env bash
#
# EC2 bootstrap script — run once on a fresh Ubuntu 22.04 instance.
# Installs Docker, configures security basics, prepares /opt/portfolioiq.
#
# Usage (after SCP'ing or fetching from GitHub):
#   sudo bash ec2-setup.sh

set -euo pipefail

echo "─── Updating system packages ───"
apt-get update
apt-get upgrade -y

echo "─── Installing prerequisites ───"
apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git \
    ufw \
    fail2ban \
    unattended-upgrades \
    awscli \
    mailutils

echo "─── Installing Docker ───"
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
    > /etc/apt/sources.list.d/docker.list

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "─── Configuring Docker log rotation (caps logs at 30 MB per container) ───"
tee /etc/docker/daemon.json >/dev/null <<'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF
systemctl restart docker

echo "─── Adding ubuntu user to docker group ───"
usermod -aG docker ubuntu || true

echo "─── Setting up UFW firewall ───"
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp   comment 'SSH'
ufw allow 80/tcp   comment 'HTTP'
ufw allow 443/tcp  comment 'HTTPS'
ufw --force enable

echo "─── Enabling automatic security updates ───"
dpkg-reconfigure -plow unattended-upgrades || true

echo "─── Enabling fail2ban (SSH brute-force protection) ───"
systemctl enable --now fail2ban

echo "─── Creating app directory ───"
mkdir -p /opt/portfolioiq
chown ubuntu:ubuntu /opt/portfolioiq

echo "─── Setting up 2 GB swap (helps t3.medium handle ES + Postgres peaks) ───"
if ! swapon --show | grep -q '/swapfile'; then
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    sysctl vm.swappiness=10 >/dev/null
    echo 'vm.swappiness=10' >> /etc/sysctl.conf
fi

echo "─── Setting up backup log file ───"
touch /var/log/portfolioiq-backup.log
chown ubuntu:ubuntu /var/log/portfolioiq-backup.log

echo ""
echo "════════════════════════════════════════════════════════════"
echo "✓ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. exit and re-SSH (so docker group takes effect)"
echo "  2. cd /opt/portfolioiq"
echo "  3. git clone https://github.com/hoangtng/PortfolioIQ.git ."
echo "  4. cp .env.production.example .env.production"
echo "  5. nano .env.production    # fill in secrets"
echo "  6. chmod 600 .env.production"
echo "  7. docker compose -f docker-compose.prod.yml up -d --build"
echo "  8. aws configure                                   # for S3 backups"
echo "  9. crontab -e   # add: 0 3 * * * /opt/portfolioiq/scripts/backup.sh >> /var/log/portfolioiq-backup.log 2>&1"
echo "════════════════════════════════════════════════════════════"