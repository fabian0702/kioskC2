from fastapi import FastAPI, Response
from pydantic import BaseModel

from c2.bundler.fetch import fetch_page
from c2.bundler.preview import preview_page


class FetchRequest(BaseModel):
    url: str


app = FastAPI()


@app.post("/bundle")
async def bundle(request: FetchRequest):
    print(f"Received fetch request for URL: {request.url}")
    page_data = await fetch_page(request.url)
    return Response(content=page_data, media_type="text/html")


@app.post("/preview")
async def preview(request: FetchRequest):
    print(f"Received preview request for URL: {request.url}")
    screenshot = await preview_page(request.url)
    return Response(content=screenshot, media_type="image/png")
