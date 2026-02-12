function load_website_plugin(url) {
    document.body.innerHTML = `
        <style>
            body,
            html {
                margin: 0;
                padding: 0;
                width: 100%;
                height: 100%;
                overflow: hidden;
            }
            iframe {
                width: 100vw;
                height: 100vh;
                border: none;
                display: block;
            }
        </style>
        <iframe src="${url}"></iframe>
    `
    return "website_content"
}