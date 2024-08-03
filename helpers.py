import os, html, urllib.parse

from starlette.types import Receive, Scope, Send
from starlette.staticfiles import StaticFiles, PathLike
from starlette.responses import HTMLResponse

# HTTPException must be imported from starlette, NOT from fastapi. If it is
# import from fastapi then matching HTTPException from internal method calls
# with StaticFiles does not work
from starlette.exceptions import HTTPException


class StaticFilesWithDir(StaticFiles):
    '''
    Extension of starlette.staticfiles.StaticFiles that adds directory listings
    '''
    
    async def __call__(self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        try:
            await super().__call__(scope, receive, send)
        except HTTPException as e:
            # Most HTTP errors should just be passed through. This function
            # only needs to do special handling if a 404 was caused by
            # requesting a folder
            if e.status_code != 404 or scope['path'][-1] != '/':
                raise e
            
            path = os.path.join(self.directory, self.get_path(scope))
            res = self.get_dir_list(path, scope)
            await res(scope, receive, send)
    
    def get_dir_list(self, path: PathLike, scope: Scope) -> HTMLResponse:
        # Generation of this HTML is heavily informed by http.server's
        # SimpleHTTPRequestHandler.list_directory() method
        try:
            entries = os.listdir(path)
        except OSError:
            raise HTTPException(status_code=404)
        entries.sort(key=lambda a: a.lower())
        
        try:
            displaypath = urllib.parse.unquote(scope['path'],
                errors='surrogatepass')
        except UnicodeDecodeError:
            displaypath = urllib.parse.unquote(scope['path'])
        title = f'Directory listing for {html.escape(displaypath, quote=False)}'
        
        lines = [
            '<!DOCTYPE HTML>',
            '<head>',
            f'<title>{title}</title>',
            '<meta name="color-scheme" content="dark">',
            '<meta name="viewport" content="width=device-width, user-scalable=no">',
            '</head>',
            '',
            '<body>',
            f'<h1>{title}</h1>',
            '<hr />',
            '<ul>',
        ]
        
        for name in entries:
            fullname = os.path.join(path, name)
            displayname = linkname = name
            # Append / for directories or @ for symbolic links
            if os.path.isdir(fullname):
                displayname = name + '/'
                linkname = name + '/'
            if os.path.islink(fullname):
                displayname = name + '@'
            # Note: a link to a directory displays with @ and links with /
            lines.append('  <li><a href="{}">{}</a></li>'.format(
                urllib.parse.quote(linkname, errors='surrogatepass'),
                html.escape(displayname, quote=False)
            ))
        
        lines += [
            '</ul>',
            '<hr />',
            '</body>',
            '</html>',
        ]
        
        return HTMLResponse('\n'.join(lines))
