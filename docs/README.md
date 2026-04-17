# 实时输出推送系统

通过 Web 页面实时查看远程服务器/容器中执行的命令输出。

## 方案概览

| 方案 | 技术栈 | 适用场景 | 复杂度 |
|------|--------|----------|--------|
| A - SSH | paramiko + SSE | 通用远程服务器执行 | 低 |
| B - Docker | Docker SDK + SSE | 容器化环境 | 中 |
| C - 消息队列 | Celery + Redis + SSE | 解耦/高并发/任务队列 | 高 |

## 快速启动

```bash
# 安装依赖
uv sync

# 启动 Django
uv run python manage.py runserver 0.0.0.0:8000

# 方案C需要启动 Redis 和 Celery
redis-server --daemonize yes
uv run celery -A rtstream worker -l info
```

## 访问地址

- 方案A: http://localhost:8000/ssh/
- 方案B: http://localhost:8000/docker/
- 方案C: http://localhost:8000/mq/

---

## 详细文档

- [方案A - SSH 远程执行](./approach-a-ssh.md)
- [方案B - Docker 容器执行](./approach-b-docker.md)
- [方案C - 消息队列执行](./approach-c-mq.md)
