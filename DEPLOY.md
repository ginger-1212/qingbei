# 刷题应用部署说明

## 1. 项目结构

核心文件：

```text
index.html   # 应用主文件，包含页面、前端逻辑、题库数据
server.py    # 静态网页服务 + SQLite 云同步 API
README.md    # 项目简介
DEPLOY.md    # 部署说明
```

运行后会生成：

```text
data/sync.sqlite3  # 多端同步数据库，不提交到 Git
```

## 2. 前端在哪里

前端全部在：

```text
index.html
```

里面包含：HTML、CSS、JavaScript 交互逻辑和题库数据数组 `const questions = [...]`。

## 3. 后端在哪里

后端在：

```text
server.py
```

它只使用 Python 标准库，不需要安装 Flask、FastAPI 或 Node.js。

提供接口：

```text
GET  /api/health
GET  /api/state?user=同步码
POST /api/state
```

`POST /api/state` 请求体：

```json
{"user":"qingbei001","state":{}}
```

## 4. 数据库在哪里

云同步数据库默认在：

```text
data/sync.sqlite3
```

可用环境变量指定其他位置：

```bash
QINGBEI_DB=/opt/qingbei-data/sync.sqlite3 python server.py
```

用户个人数据包括：

- 当前刷题分类
- 每个分类的刷题位置
- 每个分类的随机题序
- 收藏题目
- 错题本和答对次数
- 已选择答案和是否显示解析

浏览器本地仍会保存一份 `localStorage`，云同步启用后会自动上传/拉取并合并。

## 5. 本地启动方式

在项目目录下执行：

```bash
python server.py
```

默认监听：

```text
0.0.0.0:8080
```

电脑浏览器访问：

```text
http://127.0.0.1:8080/index.html
```

手机和电脑在同一 Wi-Fi 下访问：

```text
http://电脑局域网IP:8080/index.html
```

## 6. 服务器部署方式

### 方式一：直接运行 server.py

```bash
cd /opt/qingbei
python3 server.py
```

访问：

```text
http://服务器IP:8080/index.html
```

### 方式二：systemd 常驻服务

创建 `/etc/systemd/system/qingbei.service`：

```ini
[Unit]
Description=Qingbei exam practice app
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/qingbei
Environment=HOST=127.0.0.1
Environment=PORT=8080
Environment=QINGBEI_DB=/opt/qingbei/data/sync.sqlite3
ExecStart=/usr/bin/python3 /opt/qingbei/server.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

启用：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now qingbei
sudo systemctl status qingbei
```

### 方式三：Nginx 反向代理

如果使用 Nginx 对外提供 80 端口，建议让 Nginx 代理到 `server.py`：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

重载 Nginx：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## 7. 更新代码

当前代码仓库：

```text
https://github.com/ginger-1212/qingbei
```

服务器目录：

```text
/opt/qingbei
```

更新：

```bash
cd /opt/qingbei
git pull --ff-only origin main
sudo systemctl restart qingbei
```

如果服务器访问 GitHub 不稳定，可以用 Git bundle 更新。

## 8. 注意事项

- `data/sync.sqlite3` 是真实用户同步数据，备份服务器时要保留。
- 同步码不是密码，只是数据隔离标识。建议使用不容易被猜到的同步码。
- 如果只用 `python -m http.server` 或纯 Nginx 静态部署，云同步不可用，只能使用保存码导入导出。
