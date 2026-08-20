# EduNova 上线操作手册：香港 VPS + 阿里云域名 + Cloudflare + Vercel

本文档按两天内上线的目标写，默认域名示例为 `example.com`，请替换成你的真实域名。

## 0. 最终架构

```text
用户浏览器
  |
  | https://example.com
  v
Vercel 托管 Vue 前端
  |
  | https://api.example.com/api/*
  v
Cloudflare DNS / CDN / TLS
  |
  v
香港 VPS: Nginx 443 -> Gunicorn 127.0.0.1:5001 -> Flask
  |
  v
SQLite + uploads + ChromaDB 本地持久化
```

关键域名：

```text
example.com      -> Vercel 前端
www.example.com  -> Vercel 前端，可重定向到 example.com
api.example.com  -> 香港 VPS 后端
```

## 1. 本地代码改动清单

已完成的上线适配：

- `frontend/vite.config.ts`：移除构建时硬编码的 `VITE_API_BASE_URL=http://localhost:5001`。
- `frontend/src/config/api.ts`：允许 Vercel 构建时通过 `VITE_API_BASE_URL` 指向线上 API，同时保留本地 Vite 代理。
- `backend/main.py`：启动时加载 `backend/.env`，并通过 `CORS_ORIGINS` 控制允许访问的前端域名。
- `backend/templates/.env.example`：加入 `SECRET_KEY`、`JWT_SECRET_KEY`、`CORS_ORIGINS` 示例。
- `frontend/.env.production.example`：加入 Vercel 前端环境变量模板。
- `deploy/backend.production.env.example`：加入服务器后端 `.env` 模板。
- `deploy/systemd/edunova.service`：加入 Gunicorn systemd 服务模板。
- `deploy/nginx/edunova-api.conf`：加入 Nginx HTTPS 反向代理模板。

本地敏感信息处理：

- `backend/.env` 中原来的真实 `LLM_API_KEY` 已替换为占位符。
- `backend/.env` 没有被 Git 跟踪，但真实密钥已经出现在本地文件中，仍然建议到密钥供应商控制台立即轮换。

## 2. 购买域名：阿里云

1. 打开阿里云万网域名购买页。
2. 搜索你想要的域名，例如 `edunova-demo.com`。
3. 优先选 `.com`，不要选太冷门后缀，后续兼容性和信任感更好。
4. 下单购买。
5. 完成域名实名认证。
6. 等待实名审核通过。

注意事项：

- 新买域名如果未实名，可能处于不可解析状态，需要等审核通过。
- 如果你未来不想备案，网站前端和后端都不要放在中国大陆服务器；香港 VPS 不需要 ICP 备案。

## 3. 接入 Cloudflare

1. 登录 Cloudflare。
2. Add a site，输入你的根域名，例如 `example.com`。
3. 选择 Free 计划。
4. Cloudflare 会给出两个 nameserver，例如：

```text
alice.ns.cloudflare.com
bob.ns.cloudflare.com
```

5. 回到阿里云域名控制台。
6. 进入域名管理，找到 `修改 DNS` 或 `DNS 修改`。
7. 把阿里云默认 nameserver 改成 Cloudflare 给你的两个 nameserver。
8. 回到 Cloudflare 点击 Check nameservers。
9. 等 Cloudflare 状态变成 Active。

检查命令：

```powershell
nslookup -type=ns example.com 1.1.1.1
nslookup -type=ns example.com 8.8.8.8
```

看到 Cloudflare 的 nameserver 后，说明 DNS 托管已经接管。

## 4. 创建 GitHub 私有仓库

在 GitHub 创建私有仓库后，在本地执行：

```powershell
cd <你的项目目录>
git remote add origin https://github.com/<你的用户名>/edunova.git
git branch -M main
git push -u origin main
```

提交前检查：

```powershell
git status --short
git ls-files backend/.env
```

`git ls-files backend/.env` 应该没有输出。

## 5. 部署前端到 Vercel

Vercel 项目设置：

```text
Framework Preset: Vue.js
Root Directory: frontend
Build Command: npm run build-only
Output Directory: dist
Install Command: npm install
```

环境变量：

```text
VITE_API_BASE_URL=https://api.example.com
```

部署流程：

1. 用 GitHub 登录 Vercel。
2. Add New Project。
3. 选择 `edunova` 仓库。
4. Root Directory 选择 `frontend`。
5. 添加 `VITE_API_BASE_URL`。
6. Deploy。
7. 等 Vercel 给出 `*.vercel.app` 临时域名。

绑定自定义域名：

1. Vercel 项目 Settings -> Domains。
2. 添加 `example.com`。
3. 再添加 `www.example.com`。
4. Vercel 会提示需要在 Cloudflare 添加的 DNS 记录。

Cloudflare DNS 推荐记录：

```text
Type  Name  Content            Proxy
A     @     76.76.21.21        DNS only 或 Proxied，按 Vercel 当前提示为准
CNAME www   cname.vercel-dns.com DNS only 或 Proxied，按 Vercel 当前提示为准
```

说明：

- Vercel 的官方提示优先于固定教程，尤其是 CNAME 目标可能按项目变化。
- 如果 Vercel 验证失败，先把 Cloudflare 记录临时设为 DNS only，验证通过后再考虑开启代理。

## 6. 购买香港 VPS

最低建议：

```text
CPU: 2 核
内存: 2 GB 起步，4 GB 更稳
磁盘: 40 GB 起步
系统: Ubuntu 22.04 LTS 或 24.04 LTS
地区: 香港
```

为什么建议 4 GB：

- 本项目包含 LibreOffice、ChromaDB、文档解析、AI/RAG。
- 2 GB 可以跑 demo，但多个并发文档处理时更容易内存紧张。

安全组开放端口：

```text
22/tcp   SSH
80/tcp   HTTP，用于跳转和 Cloudflare 访问
443/tcp  HTTPS
```

不要开放：

```text
5001/tcp
```

Gunicorn 只绑定 `127.0.0.1:5001`，由 Nginx 转发。

## 7. 初始化 VPS

SSH 登录：

```bash
ssh root@<服务器公网IP>
```

安装基础环境：

```bash
apt update && apt upgrade -y
apt install -y python3 python3-venv python3-pip git nginx curl unzip
apt install -y libreoffice libreoffice-writer libreoffice-calc libreoffice-impress
apt install -y fonts-noto-cjk fonts-wqy-zenhei
```

创建项目目录：

```bash
mkdir -p /home/admin/project
cd /home/admin/project
git clone https://github.com/<你的用户名>/edunova.git
cd /home/admin/project/edunova
python3 -m venv venv
. venv/bin/activate
pip install --upgrade pip wheel setuptools
pip install -r requirements.txt
```

如果 `python-magic` 报错：

```bash
apt install -y libmagic1
pip install python-magic
```

创建运行目录并授权：

```bash
mkdir -p /home/admin/project/edunova/backend/uploads
mkdir -p /home/admin/project/edunova/uploads
mkdir -p /home/admin/project/edunova/backend/database
chown -R admin:admin /home/admin/project/edunova/backend/uploads /home/admin/project/edunova/uploads /home/admin/project/edunova/backend/database
```

## 8. 配置后端生产 `.env`

创建配置文件：

```bash
cp /home/admin/project/edunova/deploy/backend.production.env.example /home/admin/project/edunova/backend/.env
nano /home/admin/project/edunova/backend/.env
```

需要修改：

```text
SECRET_KEY=<随机长字符串>
JWT_SECRET_KEY=<另一个随机长字符串>
CORS_ORIGINS=https://example.com,https://www.example.com
LLM_API_KEY=<你的真实 API Key>
```

生成随机密钥：

```bash
python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
print(secrets.token_urlsafe(48))
PY
```

不要把服务器上的 `/home/admin/project/edunova/backend/.env` 提交到 Git。

## 9. 配置 Gunicorn systemd 服务

复制服务文件：

```bash
cp /home/admin/project/edunova/deploy/systemd/edunova.service /etc/systemd/system/edunova.service
systemctl daemon-reload
systemctl enable edunova
systemctl start edunova
systemctl status edunova
```

查看日志：

```bash
journalctl -u edunova -f
```

本机健康检查：

```bash
curl http://127.0.0.1:5001/api/health
```

## 10. 配置 Cloudflare Origin Certificate

在 Cloudflare：

1. SSL/TLS -> Origin Server。
2. Create Certificate。
3. Hostnames 填：

```text
api.example.com
*.example.com
example.com
```

4. 选择 RSA 或 ECC 都可以。
5. 保存证书和私钥。

在服务器创建文件：

```bash
mkdir -p /etc/ssl/cloudflare
nano /etc/ssl/cloudflare/edunova-origin.pem
nano /etc/ssl/cloudflare/edunova-origin.key
chmod 600 /etc/ssl/cloudflare/edunova-origin.key
```

Cloudflare SSL/TLS 模式：

```text
SSL/TLS -> Overview -> Full (strict)
```

## 11. 配置 Nginx 后端反向代理

复制配置：

```bash
cp /home/admin/project/edunova/deploy/nginx/edunova-api.conf /etc/nginx/sites-available/edunova-api
nano /etc/nginx/sites-available/edunova-api
```

替换：

```text
api.example.com -> api.你的真实域名
```

启用配置：

```bash
ln -s /etc/nginx/sites-available/edunova-api /etc/nginx/sites-enabled/edunova-api
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx
```

## 12. Cloudflare DNS 记录

在 Cloudflare -> DNS -> Records 添加：

```text
Type  Name  Content        Proxy
A     api   <服务器公网IP>  Proxied
```

前端记录按 Vercel 提示添加，常见形式：

```text
Type   Name  Content
A      @     76.76.21.21
CNAME  www   cname.vercel-dns.com
```

建议：

- `api` 开橙云代理。
- Vercel 域名记录如果验证卡住，先 DNS only，验证成功后再按实际情况决定是否开代理。
- API 不要做页面缓存。

## 13. Cloudflare 缓存和安全设置

推荐设置：

```text
SSL/TLS -> Overview: Full (strict)
SSL/TLS -> Edge Certificates: Always Use HTTPS 开启
Speed -> Optimization: Brotli 开启
Caching -> Configuration: Browser Cache TTL 4 hours
```

为 API 绕过缓存：

```text
Rules -> Cache Rules -> Create rule
Rule name: Bypass API cache
Hostname equals api.example.com
Cache eligibility: Bypass cache
```

## 14. 上线验证清单

DNS：

```bash
nslookup example.com 1.1.1.1
nslookup api.example.com 1.1.1.1
```

后端：

```bash
curl -I https://api.example.com/api/health
curl https://api.example.com/api/health
```

前端：

```text
打开 https://example.com
打开浏览器开发者工具 -> Network
确认 API 请求发往 https://api.example.com/api/*
确认没有 CORS error
```

服务器：

```bash
systemctl status edunova
systemctl status nginx
journalctl -u edunova -n 100 --no-pager
tail -n 100 /var/log/nginx/error.log
```

部署后推荐直接跑一遍 API 自检：

```bash
cd /home/admin/project/edunova
bash deploy/self_check_api.sh https://api.example.com https://example.com 17
```

如果课程是私有课，可额外提供 `TOKEN=<teacher-or-admin-bearer-token>`。

## 15. 常见故障

前端请求仍然是 `localhost:5001`：

- 检查 Vercel 环境变量是否配置了 `VITE_API_BASE_URL=https://api.example.com`。
- 修改环境变量后必须重新 Deploy。

CORS error：

- 检查 `/home/admin/project/edunova/backend/.env` 的 `CORS_ORIGINS` 是否包含前端完整 origin。
- 示例：`https://example.com,https://www.example.com`。
- 改完后执行 `systemctl restart edunova`。

Cloudflare 525：

- 通常是源站 443 没有正确证书。
- 检查 `/etc/ssl/cloudflare/edunova-origin.pem` 和 `.key`。
- 检查 Nginx 是否监听 443：`nginx -t && systemctl reload nginx`。

上传或知识库失败：

- 检查目录权限：

```bash
chown -R admin:admin /home/admin/project/edunova/backend/uploads /home/admin/project/edunova/uploads /home/admin/project/edunova/backend/database
```

LibreOffice 转换失败：

```bash
which soffice
which libreoffice
apt install -y libreoffice fonts-noto-cjk fonts-wqy-zenhei
systemctl restart edunova
```

服务启动失败：

```bash
journalctl -u edunova -n 200 --no-pager
```

## 16. 两天上线节奏

第一天上午：

- 买域名。
- 买香港 VPS。
- 接入 Cloudflare nameserver。

第一天下午：

- GitHub 私有仓库推送。
- Vercel 部署前端。
- VPS 初始化并启动后端。

第一天晚上：

- Cloudflare DNS、Origin Certificate、Nginx HTTPS。
- 前后端联调。

第二天：

- 真实上传文件测试。
- RAG/AI 流程测试。
- 默认账号密码修改。
- 备份 `/home/admin/project/edunova/backend/database` 和上传目录。

## 17. 上线前必须处理

- 轮换已经暴露过的 `LLM_API_KEY`。
- 修改默认账号密码：`admin/admin123`、`teacher/teacher123`、`student/student123`。
- 生产环境不要使用占位 `SECRET_KEY` 和 `JWT_SECRET_KEY`。
- 不要把 `backend/.env`、数据库、上传文件提交到 GitHub。
