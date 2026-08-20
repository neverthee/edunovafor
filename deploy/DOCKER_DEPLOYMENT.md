# EduNova Docker 部署方案

这套方案按你当前项目约定分成两条线：

1. 推荐线上方案：前端继续部署在 Vercel，后端改为 Docker 部署到香港 VPS。
2. 可选本地 / 演示方案：前后端都放进 Docker，本机直接通过 `http://localhost:8080` 访问。

---

## 1. 已提供的文件

仓库里已经补好这些 Docker 相关文件：

- `Dockerfile.backend`
- `Dockerfile.frontend`
- `docker-compose.yml`
- `.dockerignore`
- `deploy/docker/backend-entrypoint.sh`
- `deploy/docker/frontend.nginx.conf`
- `deploy/docker/backend.docker.env.example`

---

## 2. 方案选择

### 方案 A：推荐，保持现有线上拓扑

- 前端：继续走 Vercel
- DNS / CDN：继续走 Cloudflare
- 后端：VPS 上运行 `edunova-backend` 容器
- 反向代理：VPS 宿主机 Nginx 继续代理到 `127.0.0.1:5001`

优点：

- 改动最小
- 和你现在 `edunova.xin + Vercel + VPS + Cloudflare` 的结构一致
- 出问题时好排查，前后端边界清晰

### 方案 B：本地或内网演示全容器

- `backend` 容器跑 Flask/Gunicorn
- `frontend` 容器跑 Nginx，静态托管前端并反代 `/api`、`/uploads`
- 浏览器入口：`http://localhost:8080`

优点：

- 本地一键起完整环境
- 适合演示和回归测试

---

## 3. 第一次准备

### 3.1 创建后端环境变量

从模板复制：

```powershell
Copy-Item .\deploy\docker\backend.docker.env.example .\backend\.env
```

至少改这些值：

```env
SECRET_KEY=你自己的随机串
JWT_SECRET_KEY=另一条随机串
LLM_API_KEY=你自己的真实密钥
LLM_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
```

### 3.2 按部署方式设置 `CORS_ORIGINS`

如果你要本地全容器跑前端：

```env
CORS_ORIGINS=http://localhost:8080,http://127.0.0.1:8080
```

如果你要线上保持 Vercel 前端：

```env
CORS_ORIGINS=https://edunova.xin,https://www.edunova.xin,https://<你的-vercel-域名>
```

如果 Vercel 还有预览域名，也建议一并加上。

---

## 4. 本地 Docker Desktop 启动

### 4.1 只启动后端容器

适合你继续用 Vite / Vercel 前端，只把后端放进 Docker：

```powershell
docker compose up -d backend
```

检查：

```powershell
docker compose ps
docker compose logs -f backend
```

健康检查地址：

```text
http://127.0.0.1:5001/api/health
```

### 4.2 启动完整前后端

```powershell
docker compose --profile fullstack up -d --build
```

访问：

- 前端：`http://localhost:8080`
- 后端健康检查：`http://127.0.0.1:5001/api/health`

查看日志：

```powershell
docker compose logs -f backend
docker compose logs -f frontend
```

停止：

```powershell
docker compose down
```

---

## 5. 数据持久化说明

`docker-compose.yml` 已经把这几个目录映射到宿主机：

- `./backend/database -> /app/backend/database`
- `./backend/uploads -> /app/backend/uploads`
- `./uploads -> /app/uploads`

这意味着：

- SQLite 数据不会因为重建容器丢失
- 上传文件、知识库、Chroma 持久化产物会保留
- 你可以直接备份宿主机这几个目录

建议备份重点：

- `backend/database`
- `backend/uploads`
- `uploads`
- `backend/.env`

---

## 6. 推荐线上部署步骤

下面是最贴合你当前线上拓扑的方案：只把后端 Docker 化。

### 6.1 服务器目录

服务器进入项目目录：

```bash
cd /home/admin/project/edunova
```

### 6.2 同步代码

可以走你现有的 Git 拉取流程，把仓库更新到 VPS。

### 6.3 准备后端环境变量

```bash
cp deploy/docker/backend.docker.env.example backend/.env
nano backend/.env
```

把这些改成线上值：

- `SECRET_KEY`
- `JWT_SECRET_KEY`
- `LLM_API_KEY`
- `CORS_ORIGINS=https://edunova.xin,https://www.edunova.xin,https://<你的-vercel-域名>`

### 6.4 构建并启动后端容器

```bash
cd /home/admin/project/edunova
docker compose build backend
docker compose up -d backend
docker compose ps
docker compose logs -f backend
```

### 6.5 宿主机 Nginx 保持反代

你现有的思路不变，继续由宿主机 Nginx 代理：

- `443/80` 对外
- 反代到 `127.0.0.1:5001`

现有配置文件可继续参考：

- `deploy/nginx/edunova-api.conf`

因为 Compose 已经把后端容器绑定到宿主机 `127.0.0.1:5001:5001`，所以 Nginx 不需要改成容器名。

### 6.6 线上自检

服务器本机：

```bash
curl http://127.0.0.1:5001/api/health
```

外网：

```bash
curl https://<你的-api-域名>/api/health
```

如果前端仍在 Vercel，还要检查浏览器里接口请求是否已经命中线上 API，而不是 `localhost:5001`。

---

## 7. 服务器止血 / 热修路径

如果线上后端容器异常，不要只想着重发版，建议两条线并行。

### 7.1 本地代码线

1. 在本地修改代码。
2. 本地先用 `docker compose up -d backend --build` 验证。
3. 提交代码并同步到 VPS。
4. 服务器执行：

```bash
cd /home/admin/project/edunova
docker compose build backend
docker compose up -d backend
```

### 7.2 服务器热修线

先最小化止血：

```bash
cd /home/admin/project/edunova
docker compose logs --tail=200 backend
docker compose restart backend
docker compose ps
curl http://127.0.0.1:5001/api/health
```

如果是环境变量问题：

```bash
cd /home/admin/project/edunova
nano backend/.env
docker compose up -d backend
```

如果是容器镜像未更新：

```bash
cd /home/admin/project/edunova
docker compose build backend
docker compose up -d backend
```

如果要快速回滚到上一版代码：

```bash
cd /home/admin/project/edunova
git log --oneline -n 5
git checkout <上一版提交号>
docker compose build backend
docker compose up -d backend
```

---

## 8. 常用排障命令

查看容器状态：

```bash
docker compose ps
```

查看后端日志：

```bash
docker compose logs -f backend
```

进入后端容器：

```bash
docker compose exec backend bash
```

检查 LibreOffice：

```bash
docker compose exec backend which soffice
```

检查 FFmpeg：

```bash
docker compose exec backend which ffmpeg
```

检查环境变量：

```bash
docker compose exec backend env | grep -E "LLM_API|CORS_ORIGINS|SOFFICE_PATH|FFMPEG_PATH"
```

重建后端：

```bash
docker compose up -d --build backend
```

清理未使用镜像：

```bash
docker image prune -f
```

---

## 9. 已知注意点

### 9.1 镜像会比较大

因为后端需要：

- LibreOffice
- ffmpeg
- 中文字体
- 文档处理依赖

所以后端镜像不会轻。这个是正常现象。

### 9.2 首次启动会慢

首次 `build` 和首次健康检查会比较慢，尤其是：

- pip 安装
- LibreOffice 安装
- Chroma / 文档依赖初始化

### 9.3 前端继续走 Vercel 时，不建议再把前端容器暴露到公网

你当前最稳的线上方式还是：

- Vercel 出前端
- VPS Docker 只承接后端
- Cloudflare 做 DNS / CDN / TLS

---

## 10. 最推荐的实际命令

### 本地先验证后端容器

```powershell
Copy-Item .\deploy\docker\backend.docker.env.example .\backend\.env
docker compose up -d --build backend
docker compose logs -f backend
```

### 服务器上线后端容器

```bash
cd /home/admin/project/edunova
docker compose up -d --build backend
docker compose ps
curl http://127.0.0.1:5001/api/health
```

### 本地完整演示

```powershell
docker compose --profile fullstack up -d --build
```
