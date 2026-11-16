# Deploying the Digital Twin demo to UpCloud

A runbook for putting the whole app on one UpCloud Cloud Server plus an UpCloud
Managed PostgreSQL database, using the UpCloud web console (no Terraform). The result
is the public demo: the **Digital Twin dashboard over HTTPS** at
`https://<ip-with-dashes>.sslip.io`. The database, Kafka, backend and Airflow UI are not
reachable from the internet.

It runs the existing `docker-compose.yml` with the production override
`docker-compose.prod.yml` and `docker-compose.managed-db.yml` (see `RUN_SERVICES.md`,
"Production"). Nothing is installed on the server besides Docker.

```
Internet --80/443--> UpCloud firewall --> Caddy (HTTPS) --> dashboard --> backend --+
                     (22: your IP only)    physics_models --> Redpanda --> consumer -+--> Managed PostgreSQL
                                           Airflow (daily ingest of NASA/JPL data) -+    (TimescaleDB; utility
                                                                                          network, no public access)
```

Time: about 45 minutes, most of it the first image build. Part of #47 (#45, #46).

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
| Operating system | **Ubuntu Server 26.04 LTS** (used on the first deploy) or 24.04 LTS |
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

**Servers → telemetry-demo → Firewall**: turn the firewall on and, under
**Incoming traffic rules → Edit rules**, add in this order:

| # | Action | Protocol | Source address | Source port | Target port |
|---|---|---|---|---|---|
| 1 | Accept | TCP | **your IP** (IPv4, e.g. `203.0.113.7`) | all | 22 |
| 2 | Accept | TCP | All IPv4 addresses | all | 80 |
| 3 | Accept | TCP | All IPv4 addresses | all | 443 |
| 4 | Accept | UDP | All IPv4 addresses | all | 443 (HTTP/3) |
| 5 | Accept | UDP | `94.237.127.9` (UpCloud DNS) | **53** | all |
| 6 | Accept | UDP | `94.237.40.9` (UpCloud DNS) | **53** | all |
| 7 | Accept | UDP | All IPv4 addresses | **123** | all |

Rules 5-7 let the **replies** to the server's own DNS and time (NTP) queries back in:
the console firewall tracks TCP connections but not UDP, so with "Drop all" every DNS
answer is dropped (the image builds fail with `dns error`, and the clock stops
syncing). Note the *source* port is set and the target port is "all", the opposite of
rules 1-4. The DNS addresses are the resolvers the server is given (`resolvectl dns`
on the server); check them in UpCloud's documentation if they differ.

Leave the target address at "All IPv4 addresses". Then set the **incoming default
rule** to **Drop all** and keep the **outgoing default rule** at **Accept all**
(UpCloud's own outgoing "SMTP blocked" rule can stay).

A console rule is either IPv4 or IPv6, and IPv4 is enough: the
`<ip-with-dashes>.sslip.io` name resolves only to the server's IPv4 address, so
neither visitors nor Let's Encrypt reach it over IPv6. With a real domain that has an
AAAA record, add rules 2-4 again for IPv6.

The firewall runs outside the server. It is the second layer: the production
compose file already publishes only Caddy's 80/443, and that matters because
Docker bypasses the server's own firewall (ufw), so ufw is not used.

Firewall changes take up to a minute to apply.

If your IP changes later, update the port 22 rule. If you're locked out, log in
through the console's web terminal as `deploy` with the password set in step 3.

## 2b. Database (console)

**Databases → Create**, in the **same location as the server**:

| Setting | Value |
|---|---|
| Type / version | **PostgreSQL 16** (TimescaleDB is one of its supported extensions) |
| Compute | **Developer**: 1 core / **2 GiB** (the data is tens of MB) |
| Storage | 10 GiB |
| Nodes | **Single node** (a second one is a standby that doubles the price) |
| Public connection | **off** |
| Private connection | **Utility network** (leave "Attach private network" alone: that's for SDN networks) |
| Automatic access from Utility network servers | **on** (lets the server in) |
| Allow access from all IPs | off; no CIDRs needed |
| Maintenance schedule | a quiet slot, e.g. Sunday 05:00 UTC (a single node is briefly unavailable then) |
| Termination protection | **on** (turn it off before deleting, see "Shutting down") |
| Service name / hostname prefix | `telemetry-db` / a unique prefix, e.g. `dtc-telemetry-db` (can't be changed later) |

Check that the summary says about €14/month, not the larger default. It takes a few
minutes to start; when it's **Running**, note the **host, port, user** (`upadmin`) and
**password** from its overview page; the password goes to the password manager.

## 3. First login and checks

`<server-ip>` is the **public IPv4** address on the server's overview page. The
console also lists an SDN address: that's UpCloud's private network between your own
servers, not reachable from your computer.

```bash
ssh deploy@<server-ip>

cat /var/log/telemetry-init.done           # the init script finished
docker compose version                     # v2.24 or newer (the prod file needs it)
docker run --rm busybox:1.37 nslookup pypi.org   # DNS works through the firewall (rules 5-6);
                                           # not `getent` on the host: it can answer from cache
timedatectl show -p NTPSynchronized        # yes (rule 7; can take a minute)
free -h                                    # Swap: 2.0Gi
sudo sshd -T | grep -E '^(passwordauthentication|permitrootlogin) '   # both "no"
getent hosts <db-host>                     # a 10.x address (the utility network)
timeout 5 bash -c 'exec 3<>/dev/tcp/<db-host>/<db-port>' && echo db port open

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

# The database's password from the console: pasted, not shown, not in the shell history
read -rs -p "Managed DB password: " DBPW; echo

umask 077
cat > .env <<EOF
# Every docker compose command on this server uses the production setup
COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml:docker-compose.managed-db.yml
COMPOSE_PROFILES=airflow

# UpCloud Managed PostgreSQL (step 2b)
POSTGRES_HOST=<db-host>
POSTGRES_PORT=<db-port>
POSTGRES_SSLMODE=require
POSTGRES_USER=upadmin
POSTGRES_DB=telemetry
POSTGRES_PASSWORD=$DBPW

AIRFLOW_ADMIN_PASSWORD=$(openssl rand -hex 32)
AIRFLOW_JWT_SECRET=$(openssl rand -hex 32)

PUBLIC_HOSTNAME=${IP//./-}.sslip.io
EOF
unset DBPW

# One-time: the `telemetry` database (the managed service starts with `defaultdb` only).
# The migrations create the TimescaleDB extension; airflow-init creates `airflow`.
set -a; . ./.env; set +a
docker run --rm -e PGPASSWORD="$POSTGRES_PASSWORD" postgres:16-alpine psql \
  "host=$POSTGRES_HOST port=$POSTGRES_PORT user=upadmin dbname=defaultdb sslmode=require" \
  -c 'CREATE DATABASE telemetry'
```

- `COMPOSE_FILE` / `COMPOSE_PROFILES` make a plain `docker compose ...` on the server
  mean "production plus Airflow, on the managed database", so the laptop setup (which
  publishes the database and Kafka ports) can't start by accident. The commands below
  rely on it.
- `password authentication failed` means the pasted password doesn't match the
  console's: copy it again from the database's overview page. It goes into connection
  URLs as is, so it must be URL-safe (UpCloud's generated ones are).
- Copy the two Airflow secrets into the password manager (open `.env` in your own SSH
  session). The server is the only other copy.
- Without a managed database (the container instead): leave out the third
  `COMPOSE_FILE` entry and the `POSTGRES_HOST`/`PORT`/`SSLMODE` lines, and use
  `POSTGRES_USER=telemetry`, `POSTGRES_PASSWORD=$(openssl rand -hex 32)`. That password
  is applied only when the database volume is first created.
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
| Database shell | `set -a; . ./.env; set +a; docker run --rm -it -e PGPASSWORD="$POSTGRES_PASSWORD" postgres:16-alpine psql "host=$POSTGRES_HOST port=$POSTGRES_PORT user=$POSTGRES_USER dbname=telemetry sslmode=require"` |
| Reboot after updates | When `/var/run/reboot-required` exists: `sudo reboot` |

**Never run `docker compose down -v`**: `-v` deletes the HTTPS certificates
(`caddy_data`; re-issuing them repeatedly hits Let's Encrypt's rate limits) and, without
the managed database, the database itself. `docker compose down` without `-v` is safe.

**Weekly check:** in the Airflow UI, the daily `real_data_refresh` runs are green
(a failing source doesn't alert anyone, its data just goes stale), and `df -h /`
has room.

## Troubleshooting

| Symptom | Look at |
|---|---|
| No HTTPS / certificate error | `docker compose logs caddy`: ports 80/443 open in the firewall? `getent hosts <PUBLIC_HOSTNAME>` gives the server IP? |
| Build fails with `dns error` / `failed to lookup address` | Firewall rules 5-6 (step 2) missing; the running app is untouched, rerun the `up` after adding them |
| Mission page error | The backfill (step 6) hasn't run or failed: see the Airflow UI |
| `!reset` error on `up` | Docker Compose older than 2.24: `sudo apt-get install --only-upgrade docker-compose-plugin` |
| `required variable ... is missing a value` | A variable is missing in `.env` (step 4) |
| `migrate` / `airflow-init` exit 1: `password authentication failed` | `POSTGRES_PASSWORD` in `.env` doesn't match the console's |
| `could not translate host name` / connection timeout to the database | `POSTGRES_HOST`/`PORT` in `.env`; the database is Running, in the server's location, with "Automatic access from Utility network servers" on |
| `database "telemetry" does not exist` | The one-time `CREATE DATABASE telemetry` (step 4) |
| A container keeps restarting | `docker compose logs <service>`; an `OOMKilled` in `docker inspect <container>` means it hit its memory limit |
| Disk full | `docker system df`, then `docker image prune -f && docker builder prune -f` |

## Backups and recovery

- **The managed database is backed up by UpCloud** (included in the price; the
  database's page in the console shows the backups and how to restore them).
  The server itself holds no data: only `.env` (in the password manager too) and the
  HTTPS certificates, which Caddy re-issues.
- **The data is also reproducible:** the real data comes back with the backfill
  (step 6), as long as the NASA/JPL sources still serve it; the synthetic data is
  regenerated by the simulator.
- **Recovery** of the server is this runbook on a new server (steps 1-6, skipping 2b),
  with the `.env` values from the password manager.
- **A manual copy** before risky changes (after `set -a; . ./.env; set +a`):
  `docker run --rm -e PGPASSWORD="$POSTGRES_PASSWORD" postgres:16-alpine pg_dump "host=$POSTGRES_HOST port=$POSTGRES_PORT user=$POSTGRES_USER dbname=telemetry sslmode=require" -Fc > ~/telemetry-$(date +%F).dump`

## Moving an existing server to the managed database

What was done on the demo server on 2026-11-16 (outage about 70 s). Data isn't copied:
the migrations and the backfill rebuild it, the simulator regenerates the synthetic
data, and Airflow starts with an empty run history.

1. Step 2b (create the database), the two network checks from step 3, and the one-time
   `CREATE DATABASE telemetry` from step 4.
2. `git pull` (the server needs `docker-compose.managed-db.yml`), then
   `cp -p .env .env.container-db` (the rollback).
3. In `.env`: add `docker-compose.managed-db.yml` to `COMPOSE_FILE`, add
   `POSTGRES_HOST`/`PORT`/`SSLMODE=require`, and set `POSTGRES_USER=upadmin` and the
   database's `POSTGRES_PASSWORD`. Check with `docker compose config --services`: no
   `timescaledb`.
4. `docker compose stop`, then `docker compose up -d --wait` (the old database container
   stays stopped, its volume untouched), then step 6 and step 7.
5. **Roll back** (if needed): `cp .env.container-db .env && docker compose up -d --wait`.
6. **After a week or so of stable running:** remove the old container and volume:
   `docker rm telemetry-timescaledb-1 && docker volume rm telemetry_timescaledb_data`,
   and delete `.env.container-db` (it holds the old password).

## Shutting down (end of the project)

Both are billed until deleted (a stopped Starter server too).

1. Optional: a last database copy ("A manual copy" above), downloaded to your computer.
2. **Database:** in its settings turn **termination protection off**, then delete it.
3. **Server:** delete it **with its storage**.
4. Remove the server's and the database's entries from the password manager.

## Costs

Approximate list prices; check them in the console:

| Resource | €/month |
|---|---|
| Server, 4 vCPU / 8 GB: **Starter** (shared CPU, 40 GB) / Premium (dedicated, 100 GB) | ~20 / ~52 |
| Managed PostgreSQL, Developer 1 core / 2 GiB, 10 GiB, single node (backups included) | ~14.40 |

The firewall, the public IPv4 address and the utility network come with the server.

## Accepted risks (demo scope)

- One server: if it fails, the demo is down until it's redeployed.
- A single-node database: briefly unavailable in its weekly maintenance window, and
  down until UpCloud restores it if the node fails.
- `sslmode=require` encrypts the database connections but doesn't verify the server's
  certificate; the traffic stays on UpCloud's utility network.
- No rate limiting on the public dashboard.
- sslip.io is a third-party service; some company networks block sslip.io names.
  A real domain removes both.
- Updates build on the server and briefly restart the changed services; a rollback
  rebuilds an older commit (minutes).
- Base images are pinned by digest, so their OS patches arrive only when the pins
  are bumped. Kernel updates need a manual reboot.
- SSH only from the maintainer's IP: other team members need their own firewall rule.
