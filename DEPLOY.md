# 刷题应用部署说明

## 1. 项目结构

当前应用是一个纯静态网页应用，没有独立后端服务，也没有服务端数据库。

核心文件：

```text
index.html                 # 应用主文件，包含页面、前端逻辑、题库数据
README.md                  # 项目简介
DEPLOY.md                  # 部署说明
import_questions_to_app.py # 题库导入脚本，服务器运行应用时不需要
其他题_未导入应用.txt       # 其他/案例类题目，未进入刷题应用
题库导入报告.json           # 题库导入统计
```

服务器部署时，最少只需要：

```text
index.html
```

如果想保留说明和题库导入记录，建议同时上传：

```text
README.md
DEPLOY.md
其他题_未导入应用.txt
题库导入报告.json
```

## 2. 前端在哪里

前端全部在：

```text
index.html
```

里面包含：

- HTML 页面结构
- CSS 样式
- JavaScript 交互逻辑
- 题库数据数组 `const questions = [...]`

## 3. 后端在哪里

当前没有后端。

应用不依赖 Node.js、Java、Python Web 框架、数据库接口或 API 服务。

只要服务器能托管静态文件，就可以运行。

## 4. 数据库在哪里

当前没有服务端数据库。

题库数据直接内置在 `index.html` 的 JavaScript 数组中：

```js
const questions = [...]
```

用户个人数据存储在浏览器本地 `localStorage` 中，包括：

- 当前刷题分类
- 每个分类的刷题位置
- 每个分类的随机题序
- 收藏题目
- 已选择答案和是否显示解析

本地存储 Key：

```text
examPracticeState.v3
```

注意：

- 换手机、换浏览器、清理浏览器缓存后，刷题记录会丢失。
- 如果以后希望多设备同步进度，需要新增后端和数据库。

## 5. 本地启动方式

在项目目录下执行：

```bash
python -m http.server 8080 --bind 0.0.0.0
```

电脑浏览器访问：

```text
http://127.0.0.1:8080/index.html
```

手机和电脑在同一 Wi-Fi 下，访问：

```text
http://电脑局域网IP:8080/index.html
```

例如：

```text
http://192.168.1.6:8080/index.html
```

## 6. 服务器部署方式

### 方式一：Nginx 静态部署

把文件上传到服务器目录，例如：

```text
/var/www/qingbei/
```

目录内至少包含：

```text
/var/www/qingbei/index.html
```

Nginx 配置示例：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    root /var/www/qingbei;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

重载 Nginx：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

访问：

```text
http://your-domain.com/
```

### 方式二：临时 Python 静态服务

适合测试，不建议长期生产使用。

```bash
cd /var/www/qingbei
python3 -m http.server 8080 --bind 0.0.0.0
```

访问：

```text
http://服务器IP:8080/index.html
```

### 方式三：GitHub Pages

当前代码已推送到：

```text
https://github.com/ginger-1212/qingbei
```

在 GitHub 仓库中开启 Pages：

1. 进入仓库 `Settings`
2. 找到 `Pages`
3. Source 选择 `Deploy from a branch`
4. Branch 选择 `main`
5. 目录选择 `/root`
6. 保存

稍等后会生成一个 GitHub Pages 地址。

## 7. 更新题库

题库导入脚本是：

```text
import_questions_to_app.py
```

它会读取整理好的 TXT 题库，并把单选、多选题写入 `index.html`。

当前脚本里的题库来源目录是：

```text
C:\Users\Administrator\Desktop\知识点\02试题整理\整理好的
```

如果在服务器上重新导入题库，需要修改脚本里的 `SOURCE_DIR` 路径。

一般部署服务器只负责运行网页，不需要执行题库导入脚本。

## 8. 重要配置点

应用状态存储版本：

```js
const STORE_KEY = "examPracticeState.v3";
```

业务分类配置：

```js
const BUSINESS_LABELS = {
  BA: "BA",
  IA: "IA",
  AA: "AA",
  "data-governance": "数据治理",
  "product-design": "产品设计",
  "digital-transformation": "数字化转型",
  PMP: "PMP",
  NPDP: "NPDP",
  "cloud-native": "云原生",
  "product-thinking": "产品思维"
};
```

题型配置：

```js
const TYPE_LABELS = {
  single: "单选题",
  multiple: "多选题",
  other: "其他题"
};
```

## 9. 当前功能说明

- 首页三个入口：知识点、刷题、收藏
- 知识点入口目前是占位
- 刷题支持按题型分类和按业务分类
- 单选题选择后立即显示答案和解析
- 多选题选择后需要点击确认答案
- 收藏页可复习收藏题，并支持移除收藏
- 每个分类自动记录上次刷题位置
- 每个分类刷完一轮后，再刷会重新随机题目顺序

## 10. 后续如果要做成正式系统

如果后续要多人使用、跨设备同步、后台维护题库，建议增加：

- 后端接口：例如 Node.js、Python FastAPI、Java Spring Boot
- 数据库：例如 MySQL、PostgreSQL、SQLite
- 用户系统：账号登录、同步收藏和进度
- 管理后台：上传题库、编辑题目、分类管理
- 服务端统计：正确率、错题本、刷题次数

当前版本适合个人刷题、静态部署、手机访问。
