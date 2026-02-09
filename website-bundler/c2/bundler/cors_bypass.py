from playwright.async_api import Request, Route

HEADERS_TO_REMOVE = [
    "access-control-allow-origin",
    "access-control-allow-credentials",
    "access-control-allow-methods",
    "access-control-allow-headers",
    "access-control-expose-headers",
    "x-frame-options",
    "content-security-policy",
    "content-security-policy-report-only",
    "x-xss-protection",
    "x-content-type-options",
    "strict-transport-security",
    "referrer-policy",
    "permissions-policy"
]

def clean_headers(headers:dict[str, str]) -> dict[str, str]:
    return {
        k: v
        for k, v in headers.items()
        if k.lower() not in HEADERS_TO_REMOVE
    }

async def handle_route(route:Route, request:Request):
        response = await route.fetch()
        new_headers = clean_headers(response.headers)
        await route.fulfill(
            status=response.status,
            headers=new_headers,
            body=await response.body(),
            content_type=response.headers.get("content-type")
        )