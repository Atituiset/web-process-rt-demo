# 方案B - Docker 容器执行

通过 Docker SDK 连接远程 Docker daemon，在指定容器中执行命令并通过 SSE 实时推送输出。

## 架构

```
浏览器 (EventSource)
    ↓ HTTP/SSE
Django (StreamingHttpResponse)
    ↓ Docker SDK
Docker Daemon (tcp:// 或 unix://)
    ↓
容器 (exec_run)
```

## 核心代码

**docker_exec/views.py**
```python
def exec_container(client, container_id, command):
    """在容器中执行命令并实时返回输出"""
    container = client.containers.get(container_id)
    exec_result = container.exec_run(
        cmd=command,
        stream=True,    # 启用流式输出
        demux=False     # 不分离 stdout/stderr
    )

    for line in exec_result.output:
        if line:
            yield f"data: {json.dumps({'type': 'stdout', 'data': line.decode('utf-8', errors='replace')})}\n\n"
```

## 使用前提

- Docker daemon 已启动
- Docker API 可通过 TCP 或 Unix Socket 访问
- 容器已运行

### 启用 Docker TCP (WSL/Linux)

```bash
# 编辑 Docker 配置 /etc/docker/daemon.json
# 添加或修改 hosts 配置
{
  "hosts": ["unix:///var/run/docker.sock", "tcp://0.0.0.0:2375"]
}

# 重启 Docker
sudo systemctl restart docker
```

或直接启动：
```bash
dockerd -H unix:///var/run/docker.sock -H tcp://0.0.0.0:2375 --iptables=false
```

## 测试命令

```bash
# Alpine/轻量镜像（无 bash）
sh -c 'for i in 1 2 3 4 5; do echo "Docker Line $i"; sleep 1; done'

# Ubuntu/Debian（有 bash）
for i in 1 2 3 4 5; do echo "Docker Line $i"; sleep 1; done
```

## 注意事项

- 容器内可能没有 bash，使用 `sh`
- 长时间运行的命令会占用 Docker exec 会话
- 不同镜像的基础命令可能不同
