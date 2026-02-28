import asyncio
import urllib.request
import urllib.error

from c2.plugins.internal.plugins import BasePlugin


class NetworkPlugin(BasePlugin):
    name = "network"

    async def fetch(self, url: str, method: str = "GET", body: str = "", timeout: float = 30) -> dict:
        """Issues an HTTP request from the C2 server and returns the response.

        Running server-side avoids the browser's mixed-content restriction, so
        plain http:// intranet targets are reachable even when the client page
        is served over HTTPS.

        :param url: URL to request
        :type url: str
        :param method: HTTP method (GET, POST, PUT, DELETE, …). Default "GET".
        :type method: str
        :param body: Request body (for POST/PUT). Default empty string.
        :type body: str
        :param timeout: Seconds to wait for the response. Default 30.
        :type timeout: float
        :return: Dict with keys: status (int), ok (bool), headers (dict), body (str)
        :rtype: dict
        """
        def _do_fetch():
            req = urllib.request.Request(
                url,
                method=method,
                data=body.encode() if body else None,
            )
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return {
                        "status":  resp.status,
                        "ok":      200 <= resp.status < 300,
                        "headers": dict(resp.headers),
                        "body":    resp.read().decode("utf-8", errors="replace"),
                    }
            except urllib.error.HTTPError as e:
                return {
                    "status":  e.code,
                    "ok":      False,
                    "headers": dict(e.headers) if e.headers else {},
                    "body":    e.read().decode("utf-8", errors="replace"),
                }

        return await asyncio.get_event_loop().run_in_executor(None, _do_fetch)
