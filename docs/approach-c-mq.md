# 方案C - 消息队列执行

使用 Celery 作为任务队列，Redis 作为消息代理，通过 SSE 实时推送任务执行输出。

## 架构

```
浏览器 (EventSource)
    ↓ HTTP/SSE
Django
    ↓ 异步任务提交
Celery Broker (Redis)
    ↓
Celery Worker
    ↓ 执行命令
Redis Pub/Sub
    ↓
Django SSE 推送
    ↓
浏览器
```

## 核心组件

### 1. Celery 任务 (mq_exec/views.py)
```python
@shared_task
def execute_command_task(task_id, command):
    """Celery 异步任务：执行远程命令"""
    run_remote_command(task_id, command)
    return {'status': 'completed', 'task_id': task_id}
```

### 2. 命令执行 + Pub/Sub (mq_exec/views.py)
```python
def run_remote_command(task_id, command, redis_url='redis://localhost:6379/0'):
    """在远程服务器上执行命令并通过 Redis 发布输出"""
    r = redis.from_url(redis_url)

    proc = subprocess.Popen(command, shell=True, stdout=PIPE, stderr=PIPE, text=True)

    for line in proc.stdout:
        r.publish(f'task:{task_id}', json.dumps({'type': 'stdout', 'data': line}))

    for line in proc.stderr:
        r.publish(f'task:{task_id}', json.dumps({'type': 'stderr', 'data': line}))

    r.publish(f'task:{task_id}', json.dumps({'type': 'done', 'data': ''}))
    r.close()
```

### 3. SSE 端点 (mq_exec/views.py)
```python
def sse_view(request):
    task_id = request.GET.get('task_id', str(uuid.uuid4()))
    command = request.GET.get('command', '...')

    # 异步提交任务
    execute_command_task.delay(task_id, command)

    # 订阅 Redis channel 接收输出
    r = redis.from_url(redis_url)
    pubsub = r.pubsub()
    pubsub.subscribe(f'task:{task_id}')

    def generate():
        for message in pubsub.listen():
            if message['type'] == 'message':
                data = message['data']
                if isinstance(data, bytes):
                    data = data.decode('utf-8')
                yield f"data: {data}\n\n"
                # 检查是否结束...

    return StreamingHttpResponse(generate(), content_type='text/event-stream')
```

## 使用前提

### 启动 Redis
```bash
redis-server --daemonize yes
```

### 启动 Celery Worker
```bash
uv run celery -A rtstream worker -l info
```

### 启动 Django
```bash
uv run python manage.py runserver 0.0.0.0:8000
```

## 特点

- **任务队列**：命令作为异步任务执行，不阻塞 HTTP 请求
- **解耦**：生产者和消费者分离
- **高并发**：可启动多个 Worker 处理并发任务
- **持久化**：Redis 可以配置持久化，任务不会丢失

## 适用场景

- 需要任务调度和排队的场景
- 大量并发命令执行
- 需要任务重试、优先级等高级功能
- 长时间运行的任务（如编译、训练模型）
