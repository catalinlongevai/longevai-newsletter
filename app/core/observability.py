from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "longevai_api_requests_total",
    "Total API requests",
    ["method", "path", "status"],
)

REQUEST_LATENCY = Histogram(
    "longevai_api_request_latency_seconds",
    "API request latency",
    ["method", "path"],
)

TASK_COUNT = Counter(
    "longevai_task_total",
    "Total task executions",
    ["task", "status"],
)

LLM_LATENCY = Histogram(
    "longevai_llm_latency_seconds",
    "LLM call latency",
    ["stage", "provider", "model"],
)
