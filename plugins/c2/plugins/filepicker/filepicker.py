from c2.plugins.internal.plugins import BasePlugin


class FilePickerPlugin(BasePlugin):
    name = "filepicker"
    js_file = "filepicker.js"

    async def pick(self, max_file_size_kb: int = 512) -> list:
        """Opens a native folder-picker dialog and recursively reads the selected tree.

        The browser will show a "Click to select folder" overlay (user gesture
        required by the File System Access API).  After the user picks a folder,
        every file in the directory tree is enumerated.

        Files whose size is ≤ max_file_size_kb are returned with their content
        as a base64 data URL (data:<mime>;base64,...).
        Files larger than the limit are returned with content: null.

        Each item in the returned list is a dict with keys:
            path, name, size (bytes), type (MIME), lastModified (Unix ms), content

        Note: the File System Access API is available in Chrome/Edge 86+ only.
        Firefox and Safari do not support showDirectoryPicker.

        :param max_file_size_kb: Per-file read limit in kilobytes. Default 512.
        :type max_file_size_kb: int
        :return: List of file descriptor dicts
        :rtype: list
        """
        return await self.methods.eval_js(
            f'return window.pickFolder({max_file_size_kb});',
            timeout=120,
        )
