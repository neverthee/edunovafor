# EduNova

EduNova 是一个面向教学场景的前后端分离项目，提供课程管理、智能备课、知识库问答、课堂活动、评估与学情分析等能力。后端使用 Flask，前端使用 Vue 3 + Vite，RAG、资料解析和课件生成逻辑集中在 `backend/rag/`。

## 快速启动前必须修改的配置

收到项目后，优先检查下面 4 类配置。

### 1. 启动路径

正常情况下不需要手动改路径：三个启动脚本都会用脚本所在目录作为项目根目录。

- 一键启动：`run.bat`
- 后端启动：`start_backend.bat`
- 前端启动：`start_frontend.bat`

请把整个项目解压到一个路径中，并在项目根目录运行：

```powershell
.\run.bat
```

如果前后端分开启动：

```powershell
.\start_backend.bat
.\start_frontend.bat
```

### 2. Python 解释器路径

后端默认使用系统 PATH 里的 `python`。如果你的 Python 不在 PATH，不要修改启动脚本，在启动前临时指定：

也可以在启动前临时指定：

```powershell
$env:PYTHON_EXE_OVERRIDE="<你的 Conda 或 Python 环境>\python.exe"
.\start_backend.bat
```

### 3. Node / npm 路径

前端默认使用系统 PATH 里的 `node` 和 `npm.cmd`。如果你的 Node 不在 PATH，修改 `start_frontend.bat`：

```bat
set "NODE_EXE=node"
set "NPM_CMD=npm.cmd"
```

例如：

```bat
set "NODE_EXE=<你的 Node.js 安装目录>\node.exe"
set "NPM_CMD=<你的 Node.js 安装目录>\npm.cmd"
```

也可以临时覆盖：

```powershell
$env:NODE_EXE_OVERRIDE="<你的 Node.js 安装目录>\node.exe"
$env:NPM_CMD_OVERRIDE="<你的 Node.js 安装目录>\npm.cmd"
.\start_frontend.bat
```

### 4. LibreOffice 路径

Word / PPT 导出和部分文档转码依赖 LibreOffice。通常安装后 `soffice` / `libreoffice` 在 PATH 中即可；如果安装位置不同，请启动前临时指定：

```powershell
$env:SOFFICE_PATH="<你的 LibreOffice 安装目录>\program\soffice.exe"
.\start_backend.bat
```

### 5. API 配置

后端 API 配置在：

```text
backend\.env
```

至少需要把 `LLM_API_KEY` 改成自己的密钥：

```env
LLM_API_KEY=your-api-key-here
LLM_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL_TEXT_PRIMARY=qwen-flash
MODEL_EMBEDDING_PRIMARY=text-embedding-v4
MODEL_RERANK_PRIMARY=qwen3-rerank
MODEL_OCR_PRIMARY=qwen-vl-ocr-latest
MODEL_ASR_PRIMARY=qwen3-asr-flash-realtime
```

如果接入其他 OpenAI Compatible 服务，通常需要同时修改 `LLM_API_BASE` 和模型名。参考模板文件：

```text
backend\templates\.env.example
```

## 安装依赖

后端依赖：

```powershell
cd <项目根目录>
python -m pip install -r requirements.txt
```

前端依赖：

```powershell
cd <项目根目录>\frontend
npm install
```

`start_frontend.bat` 会在 `frontend\node_modules` 不存在时自动执行 `npm install`。

## 运行后检查

- 前端首页：`http://127.0.0.1:3000`
- 后端健康检查：`http://127.0.0.1:5001/api/health`

## 默认测试账号

后端首次启动会自动建表，并自动创建默认账号：

- 管理员：`admin / admin123`
- 教师：`teacher / teacher123`
- 学生：`student / student123`

## 技术栈

- 前端：Vue 3、Vite、Pinia、Vue Router、Element Plus、Tailwind CSS
- 后端：Flask、SQLAlchemy、Flask-JWT-Extended、Flask-Migrate
- AI / RAG：LangChain、ChromaDB、OpenAI Compatible API
- 文档处理：PyMuPDF、python-docx、python-pptx、LibreOffice
- 数据库：SQLite

## 项目结构

```text
<项目根目录>
├── backend/                    后端 Flask 服务
│   ├── api/                    API 路由
│   ├── config/                 模型与模块配置
│   ├── database/               SQLite 数据与迁移脚本
│   ├── graph_rag/              图谱检索相关逻辑
│   ├── models/                 数据模型
│   ├── rag/                    检索、解析、课件/文档生成
│   ├── tasks/                  后台任务
│   ├── templates/              模板与 .env.example
│   ├── utils/                  工具函数
│   ├── main.py                 后端入口
│   └── run.py                  调试启动入口
├── frontend/                   Vue 3 前端
│   ├── public/                 静态资源
│   ├── src/                    前端源码
│   └── package.json
├── source/                     本地示例素材，不提交到 Git
├── example/                    示例资料
├── uploads/                    运行时知识库产物目录
├── run.bat                     同时启动前后端
├── start_backend.bat           后端启动脚本
├── start_frontend.bat          前端启动脚本
├── requirements.txt            Python 依赖
└── README.md
```

## 打包发送前建议

压缩前不要带以下运行生成物：

- `frontend\node_modules`
- `frontend\dist`
- `backend\uploads` 中的真实上传文件和缓存
- `uploads` 中的知识库产物
- `__pycache__`
- 任何写有真实密钥的 `.env`

当前仓库不跟踪 `backend\.env`，接收方需要从模板复制并填写自己的 API Key。
