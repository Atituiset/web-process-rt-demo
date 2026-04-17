# 方案A - SSH 远程执行

通过 paramiko SSH 连接到远程服务器，执行命令并通过 SSE 实时推送输出。

## 架构

```
浏览器 (EventSource)
    ↓ HTTP/SSE
Django (StreamingHttpResponse)
    ↓ paramiko SSH
远程服务器 (Windows/Linux)
```

## 核心代码

**ssh_exec/views.py**
```python
def execSSH(client, command):
    """使用 channel.recv 避免 paramiko 内部 GBK 解码问题"""
    transport = client.get_transport()
    channel = transport.open_session()
    channel.exec_command(command)

    while True:
        while channel.recv_ready():
            data = channel.recv(4096)
            decoded = decode_output(data)  # 尝试 utf-8/gbk/cp936/latin-1
            yield f"data: {json.dumps({'type': 'stdout', 'data': decoded}, ensure_ascii=False)}\n\n"
        while channel.recv_stderr_ready():
            data = channel.recv_stderr(4096)
            decoded = decode_output(data)
            yield f"data: {json.dumps({'type': 'stderr', 'data': decoded}, ensure_ascii=False)}\n\n"
        if channel.exit_status_ready():
            break

    channel.close()
    transport.close()
```

## 已知问题

### Windows SSH GBK 编码

Windows SSH 服务器的 stderr 输出是 GBK 编码，paramiko 内部的 `ChannelFile.readline()` 默认用 UTF-8 解码会失败。

**解决方案**：使用 `channel.recv()` 代替 `ChannelFile`，手动处理多编码解码。

### Windows 命令语法

- Windows CMD 不支持 bash 语法 (`for i in ...`)
- 使用 Windows 语法：`for /L %i in (1,1,5) do echo Line %i`
- `timeout` 命令在无终端时会报错，改用 `ping -n X 127.0.0.1 >nul`

## 测试命令

**Windows:**
```
ping -t 127.0.0.1
for /L %i in (1,1,10) do @echo Line %i && ping -n 2 127.0.0.1 >nul
```

**Linux:**
```bash
ping -t 127.0.0.1
for i in 1 2 3 4 5; do echo "Line $i"; sleep 1; done
```

## 使用前提

- SSH 服务已启动并监听 22 端口
- 用户名密码或 SSH key 可用于认证
- 网络可达（注意 WSL2 与 Windows 的网络差异）

### WSL2 连接 Windows SSH

WSL2 使用 NAT 模式，Windows IP 通常在 `172.26.x.x` 网段：

```bash
# 查看 Windows IP
ip route show | grep default
```

连接时使用网关 IP（如 `172.26.80.1`）而非 `localhost`。
