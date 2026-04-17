import json
import paramiko
from django.http import StreamingHttpResponse
from django.shortcuts import render
from django.urls import path


def execSSH(client, command):
    """执行远程命令并实时返回输出"""
    _, stdout, stderr = client.exec_command(command)
    for line in stdout:
        yield f"data: {json.dumps({'type': 'stdout', 'data': line})}\n\n"
    for line in stderr:
        yield f"data: {json.dumps({'type': 'stderr', 'data': line})}\n\n"


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
            for msg in execSSH(client, command):
                yield msg
            yield f"data: {json.dumps({'type': 'done', 'data': ''})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"
        finally:
            client.close()

    response = StreamingHttpResponse(generate(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


def index(request):
    """简单的前端页面"""
    return render(request, 'ssh_exec/index.html')
