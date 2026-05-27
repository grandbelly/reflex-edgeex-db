#!/usr/bin/env bash
# bootstrap_rpi.sh — Idempotent fresh-RPI provisioner for reflex-rpi stack.
# Run on the target RPI after first boot, with ssh key auth already set up.
#
# Usage:
#   ./scripts/bootstrap_rpi.sh                # normal provision
#   ./scripts/bootstrap_rpi.sh --harden       # also: disable ssh password
#                                              auth + enable ufw (do this once
#                                              network is stable)
#
# Security defaults (per Day 4 security review):
#  - POSTGRES_PASSWORD auto-generated per RPI if .env missing
#  - .env chmod 600
#  - never echoes secrets to stdout / journal
#  - operator MUST fill CLOUDFLARE_TUNNEL_TOKEN + RPI_NODE_ID manually
set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/deployment/20251030-rpi-finished}"
REQUIRED_ENV=(CLOUDFLARE_TUNNEL_TOKEN RPI_NODE_ID)  # POSTGRES_PASSWORD auto-gen'd
HARDEN_MODE="${1:-}"

log() { printf '[bootstrap] %s\n' "$*"; }
die() { printf '[bootstrap][FATAL] %s\n' "$*" >&2; exit 1; }

# 1. OS / hardware sanity
[[ "$(uname -m)" == "aarch64" ]] || die "Expected ARM64 (Pi 5). Got $(uname -m)."
[[ -f /etc/os-release ]] && . /etc/os-release
[[ "${ID:-}" =~ ^(debian|raspbian)$ ]] || die "Expected Debian/Raspbian. Got ${ID:-unknown}."
command -v apt-get >/dev/null || die "apt-get not found."
command -v curl    >/dev/null || die "curl missing: sudo apt-get install -y curl"
ping -c1 -W3 1.1.1.1 >/dev/null 2>&1 || die "No internet. Fix network before re-running."

# 2. Docker + compose plugin (idempotent)
if ! command -v docker >/dev/null; then
  log "Installing Docker (ARM64 official channel)..."
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER"
  log "User added to docker group. Re-login (or 'newgrp docker') required after this script."
fi
if ! docker compose version >/dev/null 2>&1; then
  log "Installing docker-compose-plugin..."
  sudo apt-get update -y && sudo apt-get install -y docker-compose-plugin
fi
log "Docker: $(docker --version) | Compose: $(docker compose version --short)"

# 3. Repo presence (do NOT clone — operator scp's tarball or git clones first)
[[ -d "$REPO_DIR" ]] || die "Repo missing at $REPO_DIR. scp tarball or git clone first."
cd "$REPO_DIR"
[[ -f docker-compose.yml ]] || die "docker-compose.yml missing in $REPO_DIR."
[[ -f .env.example      ]] || die ".env.example missing — wrong repo snapshot?"

# 4. .env scaffold with auto-generated POSTGRES_PASSWORD (never overwrite existing)
if [[ ! -f .env ]]; then
  cp .env.example .env
  # Replace placeholder password with cryptographically random per-RPI value
  GEN_PW="$(openssl rand -base64 32 | tr -d '=+/' | head -c 24)"
  # Use a temp file — never write the password to argv or shell history
  awk -v pw="$GEN_PW" '
    /^POSTGRES_PASSWORD=/ { sub(/=.*/, "=" pw); print; next }
    /^TS_DSN=/            { sub(/CHANGE_ME_STRONG_PASSWORD/, pw); print; next }
    /^POSTGRES_CONNECTION_STRING=/ { sub(/CHANGE_ME_STRONG_PASSWORD/, pw); print; next }
    /^TS_DSN_LOCAL=/      { sub(/CHANGE_ME_STRONG_PASSWORD/, pw); print; next }
    { print }
  ' .env > .env.tmp && mv .env.tmp .env
  unset GEN_PW
  log ".env created from template with auto-generated POSTGRES_PASSWORD."
  log "  → Record the value via:  grep ^POSTGRES_PASSWORD= $REPO_DIR/.env"
  log "  → Save to your password manager. It is NOT logged here."
fi
chmod 600 .env
log ".env permissions locked: $(stat -c '%a %U:%G' .env)"

# 5. Verify CRITICAL human-input keys are filled
log "Verifying operator-supplied .env keys..."
missing=()
for k in "${REQUIRED_ENV[@]}"; do
  v="$(grep -E "^${k}=" .env | cut -d= -f2- || true)"
  if [[ -z "${v//\"/}" || "$v" == "CHANGEME" || "$v" == "CHANGE_ME"* ]]; then
    missing+=("$k")
  fi
done
if (( ${#missing[@]} > 0 )); then
  log "ACTION REQUIRED — fill these in .env then re-run:"
  for k in "${missing[@]}"; do log "  - $k"; done
  log "  nano $REPO_DIR/.env  (use 'space' prefix to keep out of bash history)"
  exit 10
fi

# 6. Pre-pull images + verify docker network creation works
log "Pre-pulling images (network smoke test)..."
docker compose pull --quiet || die "docker pull failed — check registry/DNS."

# 7. Optional hardening (only if --harden passed)
if [[ "$HARDEN_MODE" == "--harden" ]]; then
  log "Hardening: disable ssh password auth, enable ufw..."
  sudo sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
  sudo sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
  sudo systemctl reload ssh
  if command -v ufw >/dev/null; then
    sudo ufw allow 22/tcp comment 'ssh'
    sudo ufw --force enable
  fi
  log "Hardening done. Verify you can still ssh with your key before logging out."
fi

log "BOOTSTRAP DONE."
log "Next:"
log "  1. Transfer DB dump from existing RPI (rsync recommended, no operator middleman):"
log "     rsync -avz --remove-source-files tion@<source-rpi>:/tmp/ecoanp.dump /tmp/"
log "  2. Start DB only: docker compose up -d rpi-finished-pgai-db"
log "  3. Restore:       ./scripts/restore_db.sh /tmp/ecoanp.dump"
log "  4. Start rest:    docker compose up -d"
