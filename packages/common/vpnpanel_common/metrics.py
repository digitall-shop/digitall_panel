from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry, generate_latest
from prometheus_client import CONTENT_TYPE_LATEST
from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Route
import time

registry = CollectorRegistry()
http_requests_total = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "path", "status"], registry=registry
)
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds", "HTTP request latency", ["method", "path"], registry=registry
)
service_info = Gauge("service_info", "Static service info", ["service", "version"], registry=registry)

async def metrics(request):  # type: ignore
    return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)

metrics_app = Starlette(routes=[Route("/", metrics, methods=["GET"])])

class HTTPMetricsMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        method = scope.get("method", "?")
        path = scope.get("path", "?")
        start = time.perf_counter()
        status_holder = {}

        async def send_wrapper(message):
            if message.get("type") == "http.response.start":
                status_holder["status"] = str(message.get("status"))
            await send(message)

        await self.app(scope, receive, send_wrapper)
        duration = time.perf_counter() - start
        http_request_duration_seconds.labels(method=method, path=path).observe(duration)
        if "status" in status_holder:
            http_requests_total.labels(method=method, path=path, status=status_holder["status"]).inc()

