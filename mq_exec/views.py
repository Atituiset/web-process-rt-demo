import json
import subprocess
import redis
from django.http import StreamingHttpResponse
from django.shortcuts import render
from django.urls import path
from celery import shared_task


def run_remote_command(task_id, command, redis_url='redis://localhost:6379/0'):
    """在远程服务器上执行命令并通过Redis发布输出"""
    r = redis.from_url(redis_url)

    try:
        # 模拟远程执行 - 实际场景中这里会通过SSH或Docker执行
        proc = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        for line in proc.stdout:
            r.publish(f'task:{task_id}', json.dumps({'type': 'stdout', 'data': line}))

        for line in proc.stderr:
            r.publish(f'task:{task_id}', json.dumps({'type': 'stderr', 'data': line}))

        r.publish(f'task:{task_id}', json.dumps({'type': 'done', 'data': ''}))

    except Exception as e:
        r.publish(f'task:{task_id}', json.dumps({'type': 'error', 'data': str(e)}))
    finally:
        r.close()


@shared_task
def execute_command_task(task_id, command):
    """Celery异步任务：执行远程命令"""
    run_remote_command(task_id, command)
    return {'status': 'completed', 'task_id': task_id}


def sse_view(request):
    """SSE端点：通过Celery任务执行命令并实时推送输出"""
    import uuid
    task_id = request.GET.get('task_id', str(uuid.uuid4()))
    command = request.GET.get('command', 'for i in 1 2 3 4 5; do echo "MQ Line $i"; sleep 1; done')
    redis_url = request.GET.get('redis_url', 'redis://localhost:6379/0')

    # 异步提交任务
    execute_command_task.delay(task_id, command)

    r = redis.from_url(redis_url)
    pubsub = r.pubsub()
    pubsub.subscribe(f'task:{task_id}')

    def generate():
        try:
            for message in pubsub.listen():
                if message['type'] == 'message':
                    data = message['data']
                    if isinstance(data, bytes):
                        data = data.decode('utf-8')
                    yield f"data: {data}\n\n"
                    parsed = json.loads(data)
                    if parsed.get('type') in ('done', 'error'):
                        break
        finally:
            pubsub.unsubscribe()
            r.close()

    response = StreamingHttpResponse(generate(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


def index(request):
    """前端页面"""
    return render(request, 'mq_exec/index.html')
