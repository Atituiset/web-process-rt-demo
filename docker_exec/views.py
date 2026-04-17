import json
import docker
from django.http import StreamingHttpResponse
from django.urls import path


def exec_container(client, container_id, command):
    """在容器中执行命令并实时返回输出"""
    container = client.containers.get(container_id)
    exec_result = container.exec_run(cmd=command, stream=True, demux=False)

    for line in exec_result.output:
        if line:
            yield f"data: {json.dumps({'type': 'stdout', 'data': line.decode('utf-8', errors='replace')})}\n\n"


def sse_view(request):
    """SSE端点：在Docker容器中执行命令并实时推送输出"""
    docker_host = request.GET.get('docker_host', 'unix:///var/run/docker.sock')
    container_id = request.GET.get('container', '')
    command = request.GET.get('command', 'echo "Hello from Docker"')

    client = docker.DockerClient(base_url=docker_host)

    def generate():
        try:
            for msg in exec_container(client, container_id, command):
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
    """前端页面"""
    return render(request, 'docker_exec/index.html')
