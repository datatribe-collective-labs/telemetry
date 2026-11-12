# Deploying the Digital Twin demo to UpCloud

A runbook for putting the whole app on one UpCloud Cloud Server, using the UpCloud
web console (no Terraform). The result is the public demo: the **Digital Twin
dashboard over HTTPS** at `https://<ip-with-dashes>.sslip.io`. The database, Kafka,
backend and Airflow UI are not reachable from the internet.

It runs the existing `docker-compose.yml` with the production override
`docker-compose.prod.yml` (see `RUN_SERVICES.md`, "Production"). Nothing is
installed on the server besides Docker.

```
Internet --80/443--> UpCloud firewall --> Caddy (HTTPS) --> dashboard --> backend --> TimescaleDB
                     (22: your IP only)    physics_models --> Redpanda --> consumer --^
                                           Airflow (daily ingest of NASA/JPL data) --^
```

Time: about 30 minutes, most of it the first image build. Part of #47 (#45).

## 0. Before you start

- **UpCloud organisation and workspace.** Create the server in the team's
  organisation (`datatribe-collective`), in the workspace its admin points you to,
  not in a personal trial organisation: moving a server between organisations means
  redeploying.
- **An SSH key** on your computer. If `~/.ssh/id_ed25519.pub` doesn't exist
  (`C:\Users\<you>\.ssh\` on Windows), create one with `ssh-keygen -t ed25519`.
  You paste the contents of the `.pub` file into the console.
- **Your public IP address** (for the SSH firewall rule), e.g. from
  `curl -4 https://ifconfig.me`.
- **A password manager** entry for the server: the `.env` secrets and the
  `deploy` user's password go there.

## 1. Create the server (console)

**Servers → Deploy server:**

| Setting | Value |
|---|---|
| Location | Close to the demo audience (e.g. `de-fra1`, `fi-hel1`, `us-nyc1`) |
| Plan | **4 vCPU / 8 GB**: *Starter* (cheapest, shared CPU, 40 GB disk) or *Premium* (dedicated, 100 GB). See "Costs" below. |
| Operating system | **Ubuntu Server 24.04 LTS** |
| Storage | The plan's default disk |
| Login method | **SSH key**: add the contents of your `.pub` file |
| Hostname | `telemetry-demo` |
| Initialization script | The script below (paste it as is) |

The script runs once, as root, on first boot: it installs Docker Engine with the
Compose plugin, creates the `deploy` user that runs the app, allows SSH with keys
only, turns on daily security updates and adds 2 GB of swap.

```bash
#!/bin/bash
# UpCloud initialization script: telemetry demo server (runs once, as root)
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

# 1. Docker Engine + Compose plugin, from Docker's own apt repository
apt-get update
apt-get -y upgrade
apt-get install -y ca-certificates curl git unattended-upgrades
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 2. `deploy` user: runs the app, gets the SSH key added in the console.
#    Passwordless sudo: the docker group is root-equivalent anyway.
id deploy >/dev/null 2>&1 || useradd --create-home --shell /bin/bash --groups docker,sudo deploy
echo 'deploy ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/90-deploy
chmod 440 /etc/sudoers.d/90-deploy
KEYS=""
for f in /root/.ssh/authorized_keys /home/*/.ssh/authorized_keys; do
  if [ -s "$f" ]; then KEYS="$f"; break; fi
done
if [ -z "$KEYS" ]; then echo "No SSH key found: add one in the console" >&2; exit 1; fi
install -d -m 700 -o deploy -g deploy /home/deploy/.ssh
install -m 600 -o deploy -g deploy "$KEYS" /home/deploy/.ssh/authorized_keys

# 3. SSH: keys only, no root login. Only after `deploy` has a key (no lock-out).
#    "10-" sorts before cloud-init's "50-cloud-init.conf"; sshd keeps the first value.
cat > /etc/ssh/sshd_config.d/10-hardening.conf <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
EOF
sshd -t
systemctl restart ssh

# 4. Daily security updates (no automatic reboots: see "Operations")
cat > /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
EOF

# 5. 2 GB swap: headroom for image builds next to the running app
if [ ! -f /swapfile ]; then
  fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

date -u > /var/log/telemetry-init.done
```

## 2. Firewall (console)

**Servers → telemetry-demo → Firewall**: turn the firewall on and add, in this order:

| Direction | Action | Protocol | Port | Source |
|---|---|---|---|---|
| In | Accept | TCP | 22 | **your IP** (`/32`) |
| In | Accept | TCP | 80 | any (IPv4 and IPv6) |
| In | Accept | TCP | 443 | any (IPv4 and IPv6) |
| In | Accept | UDP | 443 | any (IPv4 and IPv6), HTTP/3 |
| Default in | **Drop** | | | |
| Default out | Accept | | | |

The firewall runs outside the server. It is the second layer: the production
compose file already publishes only Caddy's 80/443, and that matters because
Docker bypasses the server's own firewall (ufw), so ufw is not used.

The server's own outbound requests (DNS, `git`, `apt`, image pulls, the NASA/JPL
APIs) must still get their replies. Step 3 checks this. If name lookups fail there,
add Accept rules for UpCloud's DNS resolvers (listed in the console and UpCloud's
firewall documentation) and check again.

If your IP changes later, update the port 22 rule. If you're locked out, log in
through the console's web terminal as `deploy` with the password set in step 3.

## 3. First login and checks

```bash
ssh deploy@<server-ip>

cat /var/log/telemetry-init.done           # the init script finished
docker compose version                     # v2.24 or newer (the prod file needs it)
getent hosts github.com                    # DNS works through the firewall
free -h                                    # Swap: 2.0Gi
sudo sshd -T | grep -E '^(passwordauthentication|permitrootlogin) '   # both "no"

sudo passwd deploy     # a password for the console's web terminal only (SSH stays key-only);
                       # store it in the password manager
```

If `telemetry-init.done` is missing, the script failed. Its output is in
`/var/log/cloud-init-output.log`.

## 4. Get the code and write `.env`

```bash
git clone https://github.com/datatribe-collective-labs/telemetry.git ~/telemetry
cd ~/telemetry

# The server's public IPv4 (compare it with the console)
IP=$(ip -4 route get 1.1.1.1 | awk '{for (i = 1; i < NF; i++) if ($i == "src") print $(i + 1)}')
echo "$IP"

cat > .env <<EOF
# Every docker compose command on this server uses the production setup
COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml
COMPOSE_PROFILES=airflow

POSTGRES_USER=telemetry
POSTGRES_DB=telemetry
POSTGRES_PASSWORD=$(openssl rand -hex 32)
AIRFLOW_ADMIN_PASSWORD=$(openssl rand -hex 32)
AIRFLOW_JWT_SECRET=$(openssl rand -hex 32)

PUBLIC_HOSTNAME=${IP//./-}.sslip.io
EOF
chmod 600 .env
```

- `COMPOSE_FILE` / `COMPOSE_PROFILES` make a plain `docker compose ...` on the server
  mean "production plus Airflow", so the laptop setup (which publishes the database
  and Kafka ports) can't start by accident. The commands below rely on it.
- Copy the three secrets into the password manager (open `.env` in your own SSH
  session). The server is the only other copy.
- `POSTGRES_PASSWORD` is applied only when the database volume is first created;
  changing it later in `.env` alone breaks the connections.
- [sslip.io](https://sslip.io) resolves `95-111-22-33.sslip.io` to `95.111.22.33`,
  so Let's Encrypt can issue a real certificate without a domain. With a domain
  later, set `PUBLIC_HOSTNAME` to it (and point an A record at the server).

## 5. Start the app

```bash
docker compose up -d --build --wait     # first build: several minutes, longer on Starter
docker compose ps                       # everything healthy; migrate and airflow-init "Exited (0)"
docker builder prune -f                 # free the build cache (disk)
```

On its first start Airflow runs today's `real_data_refresh` by itself (DONKI, GOES
protons, JPL CAD).

## 6. Load the real data

Until this is done, the Mission page and the trajectory charts show errors: the
ephemeris tables don't exist yet.

```bash
docker compose exec airflow-scheduler airflow dags trigger real_data_backfill
docker compose exec airflow-scheduler airflow dags list-runs real_data_backfill   # repeat until "success" (about a minute)
```

## 7. Check the deployment

From your computer:
```bash
curl -sI https://<PUBLIC_HOSTNAME> | head -1    # HTTP/2 200 (a real certificate, no -k)
curl -sI http://<PUBLIC_HOSTNAME> | head -1     # 308, redirect to HTTPS
```
Open `https://<PUBLIC_HOSTNAME>`: every page loads, and on the Mission page the
distance changes after a minute (the replay runs at 60x and loops).

On the server:
```bash
sudo ss -tlnp | grep -v 127.0.0    # public listeners: only 22, 80 and 443
docker stats --no-stream           # memory per container, within the limits
df -h / && free -h
```

Two more checks on the first deploy:
- **Reboot:** `sudo reboot`, wait two minutes, then `docker compose ps` (all healthy)
  and the site is back.
- **Load:** open the dashboard in about ten browser tabs and watch
  `docker stats dashboard` stay under its 1 GB limit.

## Operations

All commands from `~/telemetry` as `deploy`.

| Task | Command |
|---|---|
| Status | `docker compose ps` |
| Logs | `docker compose logs -f --tail 100 <service>` (rotated: 3 × 10 MB) |
| Restart a service | `docker compose restart <service>` |
| Stop / start everything | `docker compose stop` / `docker compose up -d` |
| Update to the latest `main` | `git pull && docker compose up -d --build --wait && docker image prune -f && docker builder prune -f` |
| Roll back | `git checkout <commit>`, then the same `up` command (later `git switch main`) |
| Airflow UI | On your computer: `ssh -L 8080:localhost:8080 deploy@<server-ip>`, then http://localhost:8080 (user `admin`, `AIRFLOW_ADMIN_PASSWORD`) |
| New Airflow admin password | Change it in `.env`, then `docker compose up -d --force-recreate airflow-init` |
| Reboot after updates | When `/var/run/reboot-required` exists: `sudo reboot` |

**Never run `docker compose down -v`**: `-v` deletes the database and the HTTPS
certificates (`caddy_data`; re-issuing them repeatedly hits Let's Encrypt's rate
limits). `docker compose down` without `-v` is safe.

**Weekly check:** in the Airflow UI, the daily `real_data_refresh` runs are green
(a failing source doesn't alert anyone, its data just goes stale), and `df -h /`
has room.

## Troubleshooting

| Symptom | Look at |
|---|---|
| No HTTPS / certificate error | `docker compose logs caddy`: ports 80/443 open in the firewall? `getent hosts <PUBLIC_HOSTNAME>` gives the server IP? |
| Mission page error | The backfill (step 6) hasn't run or failed: see the Airflow UI |
| `!reset` error on `up` | Docker Compose older than 2.24: `sudo apt-get install --only-upgrade docker-compose-plugin` |
| `required variable ... is missing a value` | A variable is missing in `.env` (step 4) |
| A container keeps restarting | `docker compose logs <service>`; an `OOMKilled` in `docker inspect <container>` means it hit its memory limit |
| Disk full | `docker system df`, then `docker image prune -f && docker builder prune -f` |

## Backups and recovery

No automated backups yet (#46: nightly `pg_dump` to UpCloud Object Storage). Until
then:
- **The data is reproducible:** the real data comes back with the backfill (step 6),
  as long as the NASA/JPL sources still serve it; the synthetic data is
  regenerated by the simulator.
- **Recovery** is this runbook on a new server, with the `.env` values from the
  password manager.
- **A manual copy** before risky changes:
  `docker compose exec -T timescaledb pg_dump -U telemetry -Fc telemetry > ~/telemetry-$(date +%F).dump`

## Costs

Approximate list prices for 4 vCPU / 8 GB; check them in the console:
**Starter** ~€20/month, **Premium** ~€52/month. The firewall and the public IPv4
address come with the server. Starter and Premium servers are billed even when
powered off: to stop paying, delete the server and its disk (keep `.env` first).

## Accepted risks (demo scope)

- One server: if it fails, the demo is down until it's redeployed.
- No rate limiting on the public dashboard.
- sslip.io is a third-party service; some company networks block sslip.io names.
  A real domain removes both.
- Updates build on the server and briefly restart the changed services; a rollback
  rebuilds an older commit (minutes).
- Base images are pinned by digest, so their OS patches arrive only when the pins
  are bumped. Kernel updates need a manual reboot.
- SSH only from the maintainer's IP: other team members need their own firewall rule.
