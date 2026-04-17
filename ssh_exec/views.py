import json
import paramiko
from django.http import StreamingHttpResponse
from django.shortcuts import render
from django.urls import path


def decode_output(data):
    """尝试多种编码解码输出"""
    if isinstance(data, bytes):
        for encoding in ('utf-8', 'gbk', 'cp936', 'latin-1'):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        return data.decode('utf-8', errors='replace')
    return data


def execSSH(client, command):
    """执行远程命令并实时返回输出 - 使用 channel.recv 避免 paramiko text mode 解码问题"""
    transport = client.get_transport()
    channel = transport.open_session()
    channel.exec_command(command)

    while True:
        # 使用 recv 读原始数据，避免 paramiko 内部 text mode 解码
        while channel.recv_ready():
            data = channel.recv(4096)
            if not data:
                break
            decoded = decode_output(data)
            yield f"data: {json.dumps({'type': 'stdout', 'data': decoded}, ensure_ascii=False)}\n\n"
        while channel.recv_stderr_ready():
            data = channel.recv_stderr(4096)
            if not data:
                break
            decoded = decode_output(data)
            yield f"data: {json.dumps({'type': 'stderr', 'data': decoded}, ensure_ascii=False)}\n\n"
        if channel.exit_status_ready():
            break

    channel.close()
    transport.close()


def sse_view(request):
    """SSE端点：执行远程命令并实时推送输出"""
    host = request.GET.get('host', 'localhost')
    port = int(request.GET.get('port', 22))
    username = request.GET.get('username', 'root')
    password = request.GET.get('password', '')
    command = request.GET.get('command', 'echo "Hello from SSH"')

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def generate():
        try:
            client.connect(host, port=port, username=username, password=password, timeout=10)
            yield f"data: {json.dumps({'type': 'status', 'data': 'connected'})}\n\n"
            for msg in execSSH(client, command):
                yield msg
            yield f"data: {json.dumps({'type': 'done', 'data': ''})}\n\n"
        except Exception as e:
            import traceback
            yield f"data: {json.dumps({'type': 'error', 'data': f'{type(e).__name__}: {e}'})}\n\n"
            yield f"data: {json.dumps({'type': 'error', 'data': f'TB: {traceback.format_exc()}'})}\n\n"
        finally:
            client.close()

    response = StreamingHttpResponse(generate(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


def index(request):
    """简单的前端页面"""
    return render(request, 'ssh_exec/index.html')
