# NovaCloud平台部署指南

## 1. 概述

本指南详细介绍如何在生产环境中部署NovaCloud物联网平台。NovaCloud采用现代Web架构，推荐使用以下技术栈进行部署：

- **Web服务器**：Nginx（反向代理）
- **应用服务器**：Gunicorn（WSGI）/ Daphne（ASGI）
- **数据库**：PostgreSQL
- **缓存/消息队列**：Redis
- **MQTT broker**：EMQX或Mosquitto

本指南假设您具备Linux系统管理经验和基本的网络配置知识。

## 2. 环境准备

### 2.1 操作系统

推荐使用Ubuntu LTS版本（20.04或22.04）作为服务器操作系统，以获得最佳的稳定性和安全支持。

#### 系统更新

首先确保系统处于最新状态：

```bash
sudo apt update
sudo apt upgrade -y
```

#### 安装基础工具

```bash
sudo apt install -y build-essential python3-dev python3-pip python3-venv git
```

### 2.2 Python环境

NovaCloud需要Python 3.12.3或更高版本：

```bash
# 检查Python版本
python3 --version

# 如果版本低于3.12.3，可以使用以下命令安装最新版本
# 使用deadsnakes PPA安装Python 3.12
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.12 python3.12-dev python3.12-venv python3.12-distutils
```

### 2.3 PostgreSQL数据库

NovaCloud在生产环境中推荐使用PostgreSQL数据库：

```bash
# 安装PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# 启动并设置为开机自启
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 创建数据库和用户
sudo -u postgres psql -c "CREATE USER novacloud WITH PASSWORD 'strong_password_here';"
sudo -u postgres psql -c "CREATE DATABASE novacloud_db OWNER novacloud;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE novacloud_db TO novacloud;"
```

### 2.4 Redis

安装Redis用于会话存储、缓存和消息队列：

```bash
# 安装Redis
sudo apt install -y redis-server

# 启动并设置开机自启
sudo systemctl start redis-server
sudo systemctl enable redis-server

# 简单测试Redis连接
redis-cli ping
# 应返回PONG
```

### 2.5 MQTT Broker (Mosquitto)

安装和配置Mosquitto MQTT Broker：

```bash
# 安装Mosquitto
sudo apt install -y mosquitto mosquitto-clients

# 启动并设置为开机自启
sudo systemctl start mosquitto
sudo systemctl enable mosquitto
```

配置Mosquitto以使用用户名和密码认证：

```bash
# 创建配置目录（如果不存在）
sudo mkdir -p /etc/mosquitto/conf.d/

# 创建密码文件
sudo mosquitto_passwd -c /etc/mosquitto/passwd novacloud_platform
# 输入平台连接MQTT Broker的密码

# 创建配置文件
sudo nano /etc/mosquitto/conf.d/default.conf
```

在配置文件中添加以下内容：

```
# 默认监听未加密连接
listener 1883
protocol mqtt

# 启用密码认证
allow_anonymous false
password_file /etc/mosquitto/passwd

# 启用日志记录
log_dest file /var/log/mosquitto/mosquitto.log
```

重启Mosquitto以应用更改：

```bash
sudo systemctl restart mosquitto
```

#### 配置TLS/SSL (生产环境)

在生产环境中，建议为MQTT启用TLS/SSL加密：

```bash
# 创建证书目录
sudo mkdir -p /etc/mosquitto/certs/

# 如果使用Let's Encrypt证书，可以将证书复制到此目录
sudo cp /etc/letsencrypt/live/your.domain.com/fullchain.pem /etc/mosquitto/certs/
sudo cp /etc/letsencrypt/live/your.domain.com/privkey.pem /etc/mosquitto/certs/
sudo chmod 640 /etc/mosquitto/certs/*.pem
sudo chown mosquitto:mosquitto /etc/mosquitto/certs/*.pem

# 编辑TLS配置
sudo nano /etc/mosquitto/conf.d/tls.conf
```

TLS配置内容：

```
# TLS/SSL配置
listener 8883
protocol mqtt
cafile /etc/mosquitto/certs/fullchain.pem
certfile /etc/mosquitto/certs/fullchain.pem
keyfile /etc/mosquitto/certs/privkey.pem
tls_version tlsv1.2
```

重启Mosquitto：

```bash
sudo systemctl restart mosquitto
```

## 3. NovaCloud应用部署

### 3.1 获取代码

克隆NovaCloud代码库：

```bash
cd /opt
sudo mkdir novacloud
sudo chown $USER:$USER novacloud
cd novacloud
git clone https://github.com/your-organization/novacloud.git .
```

### 3.2 创建虚拟环境

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3.3 配置环境变量

创建`.env`文件保存环境变量：

```bash
nano .env
```

添加以下配置（根据实际情况修改）：

```
# Django设置
DEBUG=False
SECRET_KEY=your_very_long_and_random_secret_key_here
ALLOWED_HOSTS=your.domain.com,www.your.domain.com,127.0.0.1

# 数据库设置
DB_ENGINE=django.db.backends.postgresql
DB_NAME=novacloud_db
DB_USER=novacloud
DB_PASSWORD=strong_password_here
DB_HOST=localhost
DB_PORT=5432

# Redis设置
REDIS_URL=redis://localhost:6379/0

# MQTT设置
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
MQTT_BROKER_PORT_TLS=8883
MQTT_USERNAME=novacloud_platform
MQTT_PASSWORD=mqtt_password_here
MQTT_USE_TLS=False

# 邮件设置 (可选)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@example.com
EMAIL_HOST_PASSWORD=your_email_password
```

### 3.4 数据库迁移

创建数据库表结构：

```bash
python manage.py migrate
```

### 3.5 收集静态文件

```bash
python manage.py collectstatic --noinput
```

### 3.6 创建超级用户

```bash
python manage.py createsuperuser
```

按照提示创建管理员账户。

## 4. WSGI/ASGI服务器配置

### 4.1 Gunicorn (WSGI)

安装Gunicorn：

```bash
pip install gunicorn
```

创建Gunicorn配置文件：

```bash
nano gunicorn_config.py
```

添加以下配置：

```python
import multiprocessing

bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1
max_requests = 1000
max_requests_jitter = 50
timeout = 30
keepalive = 5
```

创建systemd服务文件：

```bash
sudo nano /etc/systemd/system/novacloud.service
```

添加以下内容：

```
[Unit]
Description=NovaCloud Gunicorn Service
After=network.target postgresql.service redis-server.service

[Service]
User=your_user
Group=your_group
WorkingDirectory=/opt/novacloud
Environment="PATH=/opt/novacloud/venv/bin"
EnvironmentFile=/opt/novacloud/.env
ExecStart=/opt/novacloud/venv/bin/gunicorn -c gunicorn_config.py DjangoNovaCloud.wsgi:application
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

### 4.2 Daphne (ASGI，用于Channels支持)

如果需要使用Django Channels（例如websockets或异步任务），需要配置Daphne：

```bash
pip install daphne
```

创建systemd服务文件：

```bash
sudo nano /etc/systemd/system/novacloud-asgi.service
```

添加以下内容：

```
[Unit]
Description=NovaCloud Daphne Service
After=network.target postgresql.service redis-server.service

[Service]
User=your_user
Group=your_group
WorkingDirectory=/opt/novacloud
Environment="PATH=/opt/novacloud/venv/bin"
EnvironmentFile=/opt/novacloud/.env
ExecStart=/opt/novacloud/venv/bin/daphne -b 127.0.0.1 -p 8001 DjangoNovaCloud.asgi:application
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

### 4.3 启动服务

刷新systemd配置并启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl start novacloud
sudo systemctl enable novacloud

# 如果使用Daphne
sudo systemctl start novacloud-asgi
sudo systemctl enable novacloud-asgi
```

## 5. Nginx反向代理配置

### 5.1 安装Nginx

```bash
sudo apt install -y nginx
```

### 5.2 创建Nginx配置文件

```bash
sudo nano /etc/nginx/sites-available/novacloud
```

添加以下配置：

```nginx
upstream django {
    server 127.0.0.1:8000;
}

upstream channels {
    server 127.0.0.1:8001;
}

server {
    listen 80;
    server_name your.domain.com www.your.domain.com;
    
    # 将HTTP请求重定向到HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name your.domain.com www.your.domain.com;
    
    # SSL配置
    ssl_certificate /etc/letsencrypt/live/your.domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your.domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    
    # HSTS (可选，但推荐)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # 其他安全头
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    
    # 客户端最大上传大小
    client_max_body_size 10M;
    
    # 日志
    access_log /var/log/nginx/novacloud-access.log;
    error_log /var/log/nginx/novacloud-error.log;
    
    # 静态文件
    location /static/ {
        alias /opt/novacloud/static/;
        expires 30d;
        access_log off;
        add_header Cache-Control "public";
    }
    
    # WebSocket连接（如果使用Channels）
    location /ws/ {
        proxy_pass http://channels;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_redirect off;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Host $server_name;
        proxy_set_header X-Forwarded-Proto https;
    }
    
    # 其他请求代理到Django
    location / {
        proxy_pass http://django;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Host $server_name;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

启用配置并重启Nginx：

```bash
sudo ln -s /etc/nginx/sites-available/novacloud /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

### 5.3 SSL/TLS证书（使用Let's Encrypt）

使用Certbot获取免费的SSL/TLS证书：

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your.domain.com -d www.your.domain.com
```

按照提示完成操作，Certbot会自动更新Nginx配置以使用SSL/TLS证书。

## 6. 后台任务（使用Celery）

如果需要处理后台任务（如数据处理、报告生成、策略执行等），可以配置Celery：

### 6.1 安装Celery

```bash
pip install celery
```

### 6.2 配置Celery服务

创建Celery Worker服务文件：

```bash
sudo nano /etc/systemd/system/novacloud-celery.service
```

添加以下内容：

```
[Unit]
Description=NovaCloud Celery Worker
After=network.target redis-server.service

[Service]
User=your_user
Group=your_group
WorkingDirectory=/opt/novacloud
Environment="PATH=/opt/novacloud/venv/bin"
EnvironmentFile=/opt/novacloud/.env
ExecStart=/opt/novacloud/venv/bin/celery -A DjangoNovaCloud worker --loglevel=info
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

如果需要周期性任务，创建Celery Beat服务文件：

```bash
sudo nano /etc/systemd/system/novacloud-celerybeat.service
```

添加以下内容：

```
[Unit]
Description=NovaCloud Celery Beat
After=network.target redis-server.service

[Service]
User=your_user
Group=your_group
WorkingDirectory=/opt/novacloud
Environment="PATH=/opt/novacloud/venv/bin"
EnvironmentFile=/opt/novacloud/.env
ExecStart=/opt/novacloud/venv/bin/celery -A DjangoNovaCloud beat --loglevel=info
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

启动Celery服务：

```bash
sudo systemctl daemon-reload
sudo systemctl start novacloud-celery
sudo systemctl enable novacloud-celery
sudo systemctl start novacloud-celerybeat
sudo systemctl enable novacloud-celerybeat
```

## 7. 安全与维护

### 7.1 防火墙配置

使用UFW配置防火墙：

```bash
sudo apt install -y ufw

# 允许SSH连接（防止锁定）
sudo ufw allow ssh

# 允许HTTP和HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 如果需要外部访问MQTT，允许MQTT端口
sudo ufw allow 1883/tcp  # 非加密MQTT
sudo ufw allow 8883/tcp  # TLS加密MQTT

# 启用防火墙
sudo ufw enable
```

### 7.2 定期备份

设置数据库定期备份：

创建备份脚本`/opt/novacloud/backup.sh`：

```bash
#!/bin/bash
DATE=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_DIR=/opt/backups
mkdir -p $BACKUP_DIR

# 备份PostgreSQL数据库
PGPASSWORD=your_db_password pg_dump -h localhost -U novacloud novacloud_db > $BACKUP_DIR/novacloud_db_$DATE.sql

# 备份.env文件
cp /opt/novacloud/.env $BACKUP_DIR/novacloud_env_$DATE.txt

# 压缩备份
tar -czf $BACKUP_DIR/novacloud_backup_$DATE.tar.gz $BACKUP_DIR/novacloud_db_$DATE.sql $BACKUP_DIR/novacloud_env_$DATE.txt

# 删除单独的文件
rm $BACKUP_DIR/novacloud_db_$DATE.sql $BACKUP_DIR/novacloud_env_$DATE.txt

# 保留最近30天的备份，删除旧备份
find $BACKUP_DIR -name "novacloud_backup_*.tar.gz" -type f -mtime +30 -delete
```

设置脚本权限：

```bash
chmod +x /opt/novacloud/backup.sh
```

添加到crontab定期执行：

```bash
crontab -e
```

添加以下行（每天凌晨3点执行）：

```
0 3 * * * /opt/novacloud/backup.sh >> /var/log/novacloud-backup.log 2>&1
```

### 7.3 日志轮转

配置NovaCloud日志的轮转：

```bash
sudo nano /etc/logrotate.d/novacloud
```

添加以下内容：

```
/var/log/nginx/novacloud-*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        if [ -f /var/run/nginx.pid ]; then
            kill -USR1 `cat /var/run/nginx.pid`
        fi
    endscript
}

/opt/novacloud/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 your_user your_group
    sharedscripts
    postrotate
        systemctl restart novacloud
    endscript
}
```

### 7.4 系统和应用更新

#### 系统更新

设置自动安全更新：

```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

#### 应用更新

创建更新脚本`/opt/novacloud/update.sh`：

```bash
#!/bin/bash
set -e

cd /opt/novacloud

# 激活虚拟环境
source venv/bin/activate

# 备份数据库
./backup.sh

# 获取最新代码
git pull

# 安装依赖
pip install --upgrade -r requirements.txt

# 应用数据库迁移
python manage.py migrate

# 收集静态文件
python manage.py collectstatic --noinput

# 重启服务
sudo systemctl restart novacloud
sudo systemctl restart novacloud-asgi
sudo systemctl restart novacloud-celery
sudo systemctl restart novacloud-celerybeat
```

设置脚本权限：

```bash
chmod +x /opt/novacloud/update.sh
```

## 8. 多节点部署（高可用性配置）

对于需要高可用性的生产环境，可以考虑以下多节点部署架构：

### 8.1 架构概览

- **负载均衡**: HAProxy或Nginx Plus
- **应用服务器**: 多个运行Gunicorn/Daphne的节点
- **数据库**: PostgreSQL主从复制
- **缓存/消息队列**: Redis Sentinel或Redis Cluster
- **MQTT Broker**: EMQX集群

### 8.2 负载均衡配置

使用HAProxy作为负载均衡器的配置示例：

```
global
    log /dev/log local0
    log /dev/log local1 notice
    chroot /var/lib/haproxy
    stats socket /run/haproxy/admin.sock mode 660 level admin expose-fd listeners
    stats timeout 30s
    user haproxy
    group haproxy
    daemon

defaults
    log global
    mode http
    option httplog
    option dontlognull
    timeout connect 5000
    timeout client 50000
    timeout server 50000

frontend http_front
    bind *:80
    stats uri /haproxy?stats
    default_backend http_back
    redirect scheme https code 301 if !{ ssl_fc }

frontend https_front
    bind *:443 ssl crt /etc/haproxy/certs/combined.pem
    default_backend http_back

backend http_back
    balance roundrobin
    option httpchk GET /health-check/
    server app1 app1.internal:8000 check
    server app2 app2.internal:8000 check
    server app3 app3.internal:8000 check
```

### 8.3 高可用数据库

使用PostgreSQL的主从复制配置：

1. 主服务器配置（postgresql.conf）：

```
listen_addresses = '*'
wal_level = replica
max_wal_senders = 10
wal_keep_segments = 64
```

2. 设置从服务器访问权限（pg_hba.conf）：

```
host    replication     replicator      <standby_server_ip>/32          md5
```

3. 从服务器设置：

```bash
pg_basebackup -h <主服务器IP> -D /var/lib/postgresql/12/main -U replicator -P -v
```

4. 创建`recovery.conf`（PostgreSQL 12+使用`standby.signal`文件）：

```
standby_mode = 'on'
primary_conninfo = 'host=<主服务器IP> port=5432 user=replicator password=<password>'
trigger_file = '/tmp/postgresql.trigger'
```

### 8.4 使用Docker和Docker Compose

对于更灵活的部署，可以使用Docker和Docker Compose：

`docker-compose.yml`示例：

```yaml
version: '3.7'

services:
  db:
    image: postgres:14
    volumes:
      - postgres_data:/var/lib/postgresql/data/
    env_file:
      - ./.env.db
    networks:
      - novacloud_network

  redis:
    image: redis:6
    volumes:
      - redis_data:/data
    networks:
      - novacloud_network

  mqtt:
    image: eclipse-mosquitto:2
    ports:
      - "1883:1883"
      - "8883:8883"
    volumes:
      - ./mosquitto/config:/mosquitto/config
      - ./mosquitto/data:/mosquitto/data
      - ./mosquitto/log:/mosquitto/log
    networks:
      - novacloud_network

  web:
    build: .
    command: gunicorn DjangoNovaCloud.wsgi:application --bind 0.0.0.0:8000
    volumes:
      - .:/app
      - static_volume:/app/static
    expose:
      - 8000
    depends_on:
      - db
      - redis
      - mqtt
    env_file:
      - ./.env
    networks:
      - novacloud_network

  asgi:
    build: .
    command: daphne -b 0.0.0.0 -p 8001 DjangoNovaCloud.asgi:application
    volumes:
      - .:/app
    expose:
      - 8001
    depends_on:
      - db
      - redis
    env_file:
      - ./.env
    networks:
      - novacloud_network

  celery:
    build: .
    command: celery -A DjangoNovaCloud worker --loglevel=info
    volumes:
      - .:/app
    depends_on:
      - db
      - redis
    env_file:
      - ./.env
    networks:
      - novacloud_network

  celery-beat:
    build: .
    command: celery -A DjangoNovaCloud beat --loglevel=info
    volumes:
      - .:/app
    depends_on:
      - db
      - redis
    env_file:
      - ./.env
    networks:
      - novacloud_network

  nginx:
    image: nginx:1.21
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d
      - ./nginx/ssl:/etc/nginx/ssl
      - static_volume:/app/static
    depends_on:
      - web
      - asgi
    networks:
      - novacloud_network

networks:
  novacloud_network:

volumes:
  postgres_data:
  redis_data:
  static_volume:
```

## 9. 故障排查

### 9.1 常见问题

1. **应用无法启动**：
   - 检查日志：`journalctl -u novacloud`
   - 验证.env文件中的配置是否正确
   - 检查数据库连接是否正常

2. **数据库连接错误**：
   - 确认PostgreSQL服务是否运行：`systemctl status postgresql`
   - 验证数据库凭证和权限设置
   - 检查防火墙规则

3. **网站无法访问**：
   - 检查Nginx配置：`nginx -t`
   - 确认Nginx服务是否运行：`systemctl status nginx`
   - 查看Nginx错误日志：`tail -f /var/log/nginx/error.log`
   - 验证Gunicorn/Daphne服务是否运行

4. **MQTT连接问题**：
   - 检查Mosquitto是否运行：`systemctl status mosquitto`
   - 验证Mosquitto配置：`mosquitto -c /etc/mosquitto/mosquitto.conf -t`
   - 测试MQTT连接：`mosquitto_pub -h localhost -p 1883 -t test -m "hello" -u novacloud_platform -P password`

### 9.2 日志分析

#### NovaCloud应用日志

```bash
# 查看应用日志
tail -f /opt/novacloud/logs/novacloud.log

# 查看Gunicorn日志
journalctl -u novacloud
```

#### Nginx访问和错误日志

```bash
# 访问日志
tail -f /var/log/nginx/novacloud-access.log

# 错误日志
tail -f /var/log/nginx/novacloud-error.log
```

#### 数据库日志

```bash
# PostgreSQL日志
tail -f /var/log/postgresql/postgresql-*.log
```

#### MQTT Broker日志

```bash
# Mosquitto日志
tail -f /var/log/mosquitto/mosquitto.log
```

### 9.3 性能监控

使用基本工具监控系统性能：

```bash
# 查看CPU、内存使用情况
htop

# 查看磁盘使用情况
df -h

# 监控网络活动
nethogs

# 监控系统负载
sar -u 1 10
```

## 10. 生产环境注意事项

### 10.1 安全设置

1. **禁用DEBUG模式**: 
   确保在.env文件中设置`DEBUG=False`

2. **设置安全密钥**:
   在.env文件中使用一个强随机字符串作为`SECRET_KEY`

3. **HTTPS配置**:
   确保启用TLS/SSL和HSTS

4. **限制管理界面访问**:
   考虑通过IP限制或VPN保护Django管理界面

### 10.2 性能优化

1. **数据库索引**:
   基于常用查询优化数据库索引

2. **缓存策略**:
   使用Redis缓存视图和查询结果

3. **静态文件服务**:
   使用Nginx直接服务静态文件，考虑使用CDN

4. **合理配置Gunicorn**:
   调整工作进程数量和超时设置

### 10.3 监控与告警

1. **设置监控系统**:
   使用Prometheus、Grafana或类似工具监控系统

2. **配置告警**:
   对关键指标设置告警阈值，比如CPU使用率、内存使用、磁盘空间等

3. **应用性能监控**:
   考虑使用APM工具，如New Relic或Datadog

### 10.4 扩展建议

1. **水平扩展**:
   添加更多应用服务器节点，通过负载均衡分发流量

2. **数据库优化**:
   设置主从复制、读写分离或分片

3. **分布式缓存**:
   配置Redis集群用于高可用性和负载

4. **队列优化**:
   使用专用的Celery服务器处理后台任务 

## 1. 概述

本指南详细介绍如何在生产环境中部署NovaCloud物联网平台。NovaCloud采用现代Web架构，推荐使用以下技术栈进行部署：

- **Web服务器**：Nginx（反向代理）
- **应用服务器**：Gunicorn（WSGI）/ Daphne（ASGI）
- **数据库**：PostgreSQL
- **缓存/消息队列**：Redis
- **MQTT broker**：EMQX或Mosquitto

本指南假设您具备Linux系统管理经验和基本的网络配置知识。

## 2. 环境准备

### 2.1 操作系统

推荐使用Ubuntu LTS版本（20.04或22.04）作为服务器操作系统，以获得最佳的稳定性和安全支持。

#### 系统更新

首先确保系统处于最新状态：

```bash
sudo apt update
sudo apt upgrade -y
```

#### 安装基础工具

```bash
sudo apt install -y build-essential python3-dev python3-pip python3-venv git
```

### 2.2 Python环境

NovaCloud需要Python 3.12.3或更高版本：

```bash
# 检查Python版本
python3 --version

# 如果版本低于3.12.3，可以使用以下命令安装最新版本
# 使用deadsnakes PPA安装Python 3.12
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.12 python3.12-dev python3.12-venv python3.12-distutils
```

### 2.3 PostgreSQL数据库

NovaCloud在生产环境中推荐使用PostgreSQL数据库：

```bash
# 安装PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# 启动并设置为开机自启
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 创建数据库和用户
sudo -u postgres psql -c "CREATE USER novacloud WITH PASSWORD 'strong_password_here';"
sudo -u postgres psql -c "CREATE DATABASE novacloud_db OWNER novacloud;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE novacloud_db TO novacloud;"
```

### 2.4 Redis

安装Redis用于会话存储、缓存和消息队列：

```bash
# 安装Redis
sudo apt install -y redis-server

# 启动并设置开机自启
sudo systemctl start redis-server
sudo systemctl enable redis-server

# 简单测试Redis连接
redis-cli ping
# 应返回PONG
```

### 2.5 MQTT Broker (Mosquitto)

安装和配置Mosquitto MQTT Broker：

```bash
# 安装Mosquitto
sudo apt install -y mosquitto mosquitto-clients

# 启动并设置为开机自启
sudo systemctl start mosquitto
sudo systemctl enable mosquitto
```

配置Mosquitto以使用用户名和密码认证：

```bash
# 创建配置目录（如果不存在）
sudo mkdir -p /etc/mosquitto/conf.d/

# 创建密码文件
sudo mosquitto_passwd -c /etc/mosquitto/passwd novacloud_platform
# 输入平台连接MQTT Broker的密码

# 创建配置文件
sudo nano /etc/mosquitto/conf.d/default.conf
```

在配置文件中添加以下内容：

```
# 默认监听未加密连接
listener 1883
protocol mqtt

# 启用密码认证
allow_anonymous false
password_file /etc/mosquitto/passwd

# 启用日志记录
log_dest file /var/log/mosquitto/mosquitto.log
```

重启Mosquitto以应用更改：

```bash
sudo systemctl restart mosquitto
```

#### 配置TLS/SSL (生产环境)

在生产环境中，建议为MQTT启用TLS/SSL加密：

```bash
# 创建证书目录
sudo mkdir -p /etc/mosquitto/certs/

# 如果使用Let's Encrypt证书，可以将证书复制到此目录
sudo cp /etc/letsencrypt/live/your.domain.com/fullchain.pem /etc/mosquitto/certs/
sudo cp /etc/letsencrypt/live/your.domain.com/privkey.pem /etc/mosquitto/certs/
sudo chmod 640 /etc/mosquitto/certs/*.pem
sudo chown mosquitto:mosquitto /etc/mosquitto/certs/*.pem

# 编辑TLS配置
sudo nano /etc/mosquitto/conf.d/tls.conf
```

TLS配置内容：

```
# TLS/SSL配置
listener 8883
protocol mqtt
cafile /etc/mosquitto/certs/fullchain.pem
certfile /etc/mosquitto/certs/fullchain.pem
keyfile /etc/mosquitto/certs/privkey.pem
tls_version tlsv1.2
```

重启Mosquitto：

```bash
sudo systemctl restart mosquitto
```

## 3. NovaCloud应用部署

### 3.1 获取代码

克隆NovaCloud代码库：

```bash
cd /opt
sudo mkdir novacloud
sudo chown $USER:$USER novacloud
cd novacloud
git clone https://github.com/your-organization/novacloud.git .
```

### 3.2 创建虚拟环境

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3.3 配置环境变量

创建`.env`文件保存环境变量：

```bash
nano .env
```

添加以下配置（根据实际情况修改）：

```
# Django设置
DEBUG=False
SECRET_KEY=your_very_long_and_random_secret_key_here
ALLOWED_HOSTS=your.domain.com,www.your.domain.com,127.0.0.1

# 数据库设置
DB_ENGINE=django.db.backends.postgresql
DB_NAME=novacloud_db
DB_USER=novacloud
DB_PASSWORD=strong_password_here
DB_HOST=localhost
DB_PORT=5432

# Redis设置
REDIS_URL=redis://localhost:6379/0

# MQTT设置
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
MQTT_BROKER_PORT_TLS=8883
MQTT_USERNAME=novacloud_platform
MQTT_PASSWORD=mqtt_password_here
MQTT_USE_TLS=False

# 邮件设置 (可选)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@example.com
EMAIL_HOST_PASSWORD=your_email_password
```

### 3.4 数据库迁移

创建数据库表结构：

```bash
python manage.py migrate
```

### 3.5 收集静态文件

```bash
python manage.py collectstatic --noinput
```

### 3.6 创建超级用户

```bash
python manage.py createsuperuser
```

按照提示创建管理员账户。

## 4. WSGI/ASGI服务器配置

### 4.1 Gunicorn (WSGI)

安装Gunicorn：

```bash
pip install gunicorn
```

创建Gunicorn配置文件：

```bash
nano gunicorn_config.py
```

添加以下配置：

```python
import multiprocessing

bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1
max_requests = 1000
max_requests_jitter = 50
timeout = 30
keepalive = 5
```

创建systemd服务文件：

```bash
sudo nano /etc/systemd/system/novacloud.service
```

添加以下内容：

```
[Unit]
Description=NovaCloud Gunicorn Service
After=network.target postgresql.service redis-server.service

[Service]
User=your_user
Group=your_group
WorkingDirectory=/opt/novacloud
Environment="PATH=/opt/novacloud/venv/bin"
EnvironmentFile=/opt/novacloud/.env
ExecStart=/opt/novacloud/venv/bin/gunicorn -c gunicorn_config.py DjangoNovaCloud.wsgi:application
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

### 4.2 Daphne (ASGI，用于Channels支持)

如果需要使用Django Channels（例如websockets或异步任务），需要配置Daphne：

```bash
pip install daphne
```

创建systemd服务文件：

```bash
sudo nano /etc/systemd/system/novacloud-asgi.service
```

添加以下内容：

```
[Unit]
Description=NovaCloud Daphne Service
After=network.target postgresql.service redis-server.service

[Service]
User=your_user
Group=your_group
WorkingDirectory=/opt/novacloud
Environment="PATH=/opt/novacloud/venv/bin"
EnvironmentFile=/opt/novacloud/.env
ExecStart=/opt/novacloud/venv/bin/daphne -b 127.0.0.1 -p 8001 DjangoNovaCloud.asgi:application
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

### 4.3 启动服务

刷新systemd配置并启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl start novacloud
sudo systemctl enable novacloud

# 如果使用Daphne
sudo systemctl start novacloud-asgi
sudo systemctl enable novacloud-asgi
```

## 5. Nginx反向代理配置

### 5.1 安装Nginx

```bash
sudo apt install -y nginx
```

### 5.2 创建Nginx配置文件

```bash
sudo nano /etc/nginx/sites-available/novacloud
```

添加以下配置：

```nginx
upstream django {
    server 127.0.0.1:8000;
}

upstream channels {
    server 127.0.0.1:8001;
}

server {
    listen 80;
    server_name your.domain.com www.your.domain.com;
    
    # 将HTTP请求重定向到HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name your.domain.com www.your.domain.com;
    
    # SSL配置
    ssl_certificate /etc/letsencrypt/live/your.domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your.domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    
    # HSTS (可选，但推荐)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # 其他安全头
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    
    # 客户端最大上传大小
    client_max_body_size 10M;
    
    # 日志
    access_log /var/log/nginx/novacloud-access.log;
    error_log /var/log/nginx/novacloud-error.log;
    
    # 静态文件
    location /static/ {
        alias /opt/novacloud/static/;
        expires 30d;
        access_log off;
        add_header Cache-Control "public";
    }
    
    # WebSocket连接（如果使用Channels）
    location /ws/ {
        proxy_pass http://channels;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_redirect off;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Host $server_name;
        proxy_set_header X-Forwarded-Proto https;
    }
    
    # 其他请求代理到Django
    location / {
        proxy_pass http://django;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Host $server_name;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

启用配置并重启Nginx：

```bash
sudo ln -s /etc/nginx/sites-available/novacloud /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

### 5.3 SSL/TLS证书（使用Let's Encrypt）

使用Certbot获取免费的SSL/TLS证书：

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your.domain.com -d www.your.domain.com
```

按照提示完成操作，Certbot会自动更新Nginx配置以使用SSL/TLS证书。

## 6. 后台任务（使用Celery）

如果需要处理后台任务（如数据处理、报告生成、策略执行等），可以配置Celery：

### 6.1 安装Celery

```bash
pip install celery
```

### 6.2 配置Celery服务

创建Celery Worker服务文件：

```bash
sudo nano /etc/systemd/system/novacloud-celery.service
```

添加以下内容：

```
[Unit]
Description=NovaCloud Celery Worker
After=network.target redis-server.service

[Service]
User=your_user
Group=your_group
WorkingDirectory=/opt/novacloud
Environment="PATH=/opt/novacloud/venv/bin"
EnvironmentFile=/opt/novacloud/.env
ExecStart=/opt/novacloud/venv/bin/celery -A DjangoNovaCloud worker --loglevel=info
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

如果需要周期性任务，创建Celery Beat服务文件：

```bash
sudo nano /etc/systemd/system/novacloud-celerybeat.service
```

添加以下内容：

```
[Unit]
Description=NovaCloud Celery Beat
After=network.target redis-server.service

[Service]
User=your_user
Group=your_group
WorkingDirectory=/opt/novacloud
Environment="PATH=/opt/novacloud/venv/bin"
EnvironmentFile=/opt/novacloud/.env
ExecStart=/opt/novacloud/venv/bin/celery -A DjangoNovaCloud beat --loglevel=info
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

启动Celery服务：

```bash
sudo systemctl daemon-reload
sudo systemctl start novacloud-celery
sudo systemctl enable novacloud-celery
sudo systemctl start novacloud-celerybeat
sudo systemctl enable novacloud-celerybeat
```

## 7. 安全与维护

### 7.1 防火墙配置

使用UFW配置防火墙：

```bash
sudo apt install -y ufw

# 允许SSH连接（防止锁定）
sudo ufw allow ssh

# 允许HTTP和HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 如果需要外部访问MQTT，允许MQTT端口
sudo ufw allow 1883/tcp  # 非加密MQTT
sudo ufw allow 8883/tcp  # TLS加密MQTT

# 启用防火墙
sudo ufw enable
```

### 7.2 定期备份

设置数据库定期备份：

创建备份脚本`/opt/novacloud/backup.sh`：

```bash
#!/bin/bash
DATE=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_DIR=/opt/backups
mkdir -p $BACKUP_DIR

# 备份PostgreSQL数据库
PGPASSWORD=your_db_password pg_dump -h localhost -U novacloud novacloud_db > $BACKUP_DIR/novacloud_db_$DATE.sql

# 备份.env文件
cp /opt/novacloud/.env $BACKUP_DIR/novacloud_env_$DATE.txt

# 压缩备份
tar -czf $BACKUP_DIR/novacloud_backup_$DATE.tar.gz $BACKUP_DIR/novacloud_db_$DATE.sql $BACKUP_DIR/novacloud_env_$DATE.txt

# 删除单独的文件
rm $BACKUP_DIR/novacloud_db_$DATE.sql $BACKUP_DIR/novacloud_env_$DATE.txt

# 保留最近30天的备份，删除旧备份
find $BACKUP_DIR -name "novacloud_backup_*.tar.gz" -type f -mtime +30 -delete
```

设置脚本权限：

```bash
chmod +x /opt/novacloud/backup.sh
```

添加到crontab定期执行：

```bash
crontab -e
```

添加以下行（每天凌晨3点执行）：

```
0 3 * * * /opt/novacloud/backup.sh >> /var/log/novacloud-backup.log 2>&1
```

### 7.3 日志轮转

配置NovaCloud日志的轮转：

```bash
sudo nano /etc/logrotate.d/novacloud
```

添加以下内容：

```
/var/log/nginx/novacloud-*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        if [ -f /var/run/nginx.pid ]; then
            kill -USR1 `cat /var/run/nginx.pid`
        fi
    endscript
}

/opt/novacloud/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 your_user your_group
    sharedscripts
    postrotate
        systemctl restart novacloud
    endscript
}
```

### 7.4 系统和应用更新

#### 系统更新

设置自动安全更新：

```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

#### 应用更新

创建更新脚本`/opt/novacloud/update.sh`：

```bash
#!/bin/bash
set -e

cd /opt/novacloud

# 激活虚拟环境
source venv/bin/activate

# 备份数据库
./backup.sh

# 获取最新代码
git pull

# 安装依赖
pip install --upgrade -r requirements.txt

# 应用数据库迁移
python manage.py migrate

# 收集静态文件
python manage.py collectstatic --noinput

# 重启服务
sudo systemctl restart novacloud
sudo systemctl restart novacloud-asgi
sudo systemctl restart novacloud-celery
sudo systemctl restart novacloud-celerybeat
```

设置脚本权限：

```bash
chmod +x /opt/novacloud/update.sh
```

## 8. 多节点部署（高可用性配置）

对于需要高可用性的生产环境，可以考虑以下多节点部署架构：

### 8.1 架构概览

- **负载均衡**: HAProxy或Nginx Plus
- **应用服务器**: 多个运行Gunicorn/Daphne的节点
- **数据库**: PostgreSQL主从复制
- **缓存/消息队列**: Redis Sentinel或Redis Cluster
- **MQTT Broker**: EMQX集群

### 8.2 负载均衡配置

使用HAProxy作为负载均衡器的配置示例：

```
global
    log /dev/log local0
    log /dev/log local1 notice
    chroot /var/lib/haproxy
    stats socket /run/haproxy/admin.sock mode 660 level admin expose-fd listeners
    stats timeout 30s
    user haproxy
    group haproxy
    daemon

defaults
    log global
    mode http
    option httplog
    option dontlognull
    timeout connect 5000
    timeout client 50000
    timeout server 50000

frontend http_front
    bind *:80
    stats uri /haproxy?stats
    default_backend http_back
    redirect scheme https code 301 if !{ ssl_fc }

frontend https_front
    bind *:443 ssl crt /etc/haproxy/certs/combined.pem
    default_backend http_back

backend http_back
    balance roundrobin
    option httpchk GET /health-check/
    server app1 app1.internal:8000 check
    server app2 app2.internal:8000 check
    server app3 app3.internal:8000 check
```

### 8.3 高可用数据库

使用PostgreSQL的主从复制配置：

1. 主服务器配置（postgresql.conf）：

```
listen_addresses = '*'
wal_level = replica
max_wal_senders = 10
wal_keep_segments = 64
```

2. 设置从服务器访问权限（pg_hba.conf）：

```
host    replication     replicator      <standby_server_ip>/32          md5
```

3. 从服务器设置：

```bash
pg_basebackup -h <主服务器IP> -D /var/lib/postgresql/12/main -U replicator -P -v
```

4. 创建`recovery.conf`（PostgreSQL 12+使用`standby.signal`文件）：

```
standby_mode = 'on'
primary_conninfo = 'host=<主服务器IP> port=5432 user=replicator password=<password>'
trigger_file = '/tmp/postgresql.trigger'
```

### 8.4 使用Docker和Docker Compose

对于更灵活的部署，可以使用Docker和Docker Compose：

`docker-compose.yml`示例：

```yaml
version: '3.7'

services:
  db:
    image: postgres:14
    volumes:
      - postgres_data:/var/lib/postgresql/data/
    env_file:
      - ./.env.db
    networks:
      - novacloud_network

  redis:
    image: redis:6
    volumes:
      - redis_data:/data
    networks:
      - novacloud_network

  mqtt:
    image: eclipse-mosquitto:2
    ports:
      - "1883:1883"
      - "8883:8883"
    volumes:
      - ./mosquitto/config:/mosquitto/config
      - ./mosquitto/data:/mosquitto/data
      - ./mosquitto/log:/mosquitto/log
    networks:
      - novacloud_network

  web:
    build: .
    command: gunicorn DjangoNovaCloud.wsgi:application --bind 0.0.0.0:8000
    volumes:
      - .:/app
      - static_volume:/app/static
    expose:
      - 8000
    depends_on:
      - db
      - redis
      - mqtt
    env_file:
      - ./.env
    networks:
      - novacloud_network

  asgi:
    build: .
    command: daphne -b 0.0.0.0 -p 8001 DjangoNovaCloud.asgi:application
    volumes:
      - .:/app
    expose:
      - 8001
    depends_on:
      - db
      - redis
    env_file:
      - ./.env
    networks:
      - novacloud_network

  celery:
    build: .
    command: celery -A DjangoNovaCloud worker --loglevel=info
    volumes:
      - .:/app
    depends_on:
      - db
      - redis
    env_file:
      - ./.env
    networks:
      - novacloud_network

  celery-beat:
    build: .
    command: celery -A DjangoNovaCloud beat --loglevel=info
    volumes:
      - .:/app
    depends_on:
      - db
      - redis
    env_file:
      - ./.env
    networks:
      - novacloud_network

  nginx:
    image: nginx:1.21
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d
      - ./nginx/ssl:/etc/nginx/ssl
      - static_volume:/app/static
    depends_on:
      - web
      - asgi
    networks:
      - novacloud_network

networks:
  novacloud_network:

volumes:
  postgres_data:
  redis_data:
  static_volume:
```

## 9. 故障排查

### 9.1 常见问题

1. **应用无法启动**：
   - 检查日志：`journalctl -u novacloud`
   - 验证.env文件中的配置是否正确
   - 检查数据库连接是否正常

2. **数据库连接错误**：
   - 确认PostgreSQL服务是否运行：`systemctl status postgresql`
   - 验证数据库凭证和权限设置
   - 检查防火墙规则

3. **网站无法访问**：
   - 检查Nginx配置：`nginx -t`
   - 确认Nginx服务是否运行：`systemctl status nginx`
   - 查看Nginx错误日志：`tail -f /var/log/nginx/error.log`
   - 验证Gunicorn/Daphne服务是否运行

4. **MQTT连接问题**：
   - 检查Mosquitto是否运行：`systemctl status mosquitto`
   - 验证Mosquitto配置：`mosquitto -c /etc/mosquitto/mosquitto.conf -t`
   - 测试MQTT连接：`mosquitto_pub -h localhost -p 1883 -t test -m "hello" -u novacloud_platform -P password`

### 9.2 日志分析

#### NovaCloud应用日志

```bash
# 查看应用日志
tail -f /opt/novacloud/logs/novacloud.log

# 查看Gunicorn日志
journalctl -u novacloud
```

#### Nginx访问和错误日志

```bash
# 访问日志
tail -f /var/log/nginx/novacloud-access.log

# 错误日志
tail -f /var/log/nginx/novacloud-error.log
```

#### 数据库日志

```bash
# PostgreSQL日志
tail -f /var/log/postgresql/postgresql-*.log
```

#### MQTT Broker日志

```bash
# Mosquitto日志
tail -f /var/log/mosquitto/mosquitto.log
```

### 9.3 性能监控

使用基本工具监控系统性能：

```bash
# 查看CPU、内存使用情况
htop

# 查看磁盘使用情况
df -h

# 监控网络活动
nethogs

# 监控系统负载
sar -u 1 10
```

## 10. 生产环境注意事项

### 10.1 安全设置

1. **禁用DEBUG模式**: 
   确保在.env文件中设置`DEBUG=False`

2. **设置安全密钥**:
   在.env文件中使用一个强随机字符串作为`SECRET_KEY`

3. **HTTPS配置**:
   确保启用TLS/SSL和HSTS

4. **限制管理界面访问**:
   考虑通过IP限制或VPN保护Django管理界面

### 10.2 性能优化

1. **数据库索引**:
   基于常用查询优化数据库索引

2. **缓存策略**:
   使用Redis缓存视图和查询结果

3. **静态文件服务**:
   使用Nginx直接服务静态文件，考虑使用CDN

4. **合理配置Gunicorn**:
   调整工作进程数量和超时设置

### 10.3 监控与告警

1. **设置监控系统**:
   使用Prometheus、Grafana或类似工具监控系统

2. **配置告警**:
   对关键指标设置告警阈值，比如CPU使用率、内存使用、磁盘空间等

3. **应用性能监控**:
   考虑使用APM工具，如New Relic或Datadog

### 10.4 扩展建议

1. **水平扩展**:
   添加更多应用服务器节点，通过负载均衡分发流量

2. **数据库优化**:
   设置主从复制、读写分离或分片

3. **分布式缓存**:
   配置Redis集群用于高可用性和负载

4. **队列优化**:
   使用专用的Celery服务器处理后台任务 