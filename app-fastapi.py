import collections, secrets, json, pathlib, os, base64, dataclasses, http
import setproctitle, re, logging
from typing import List

import fastapi, fastapi.staticfiles, starlette, webauthn
from fastapi import FastAPI, HTTPException, Request, Cookie, Header
import fastapi.responses as fr

#################
# General Setup #
#################

setproctitle.setproctitle('tir-na-nog')

__dir__ = pathlib.Path(__file__).parent

logger = logging.getLogger('uvicorn')

app = FastAPI()

challenge = None

tokens = []

@dataclasses.dataclass
class RegisteredKey:
    id: str
    public_key: str

registered_keys = [
    RegisteredKey( # localhost - Yubkey 5 NFC
        id='iEz0VA4zLJeDDQqmDsFxwyPsni1lCVAAevIEMKrruFfoVPIf1FYZJ8usYDTkjqH/tB1'
            'CpVQg71LrTChfpoAU9w==',
        public_key='pQECAyYgASFYIMX4QOP5gvEQH2nuQbjQ/1OoeiZ9mTWzN8LvLaSKVFjMIlg'
            'gLot+HtQvjuTuUJGOQ+3o34QzlFvP8uu7EV66bTzIFs0=',
    ),
    RegisteredKey( # localhost - Yubikey 5 NFC (Ars)
        id='am0MIQbgeDpimmSs5vTvfv30An1ELKiWtUEDDe9wXLdwiWElfTXd6cC3iiZVIsbQPwC'
            'pD7PzsOUyBx7TKfmBnQ==',
        public_key='pQECAyYgASFYIENWdY0TOVzPWHdbDzejUQ402qe4st8lCGPsLTSnECqfIlg'
            'g+cOG2IEQPQW51Zh4VgyFtTZGeW9yKEnzJKeZRAwX60Q=',
    ),
    RegisteredKey( # localhost - Yubikey 5 Nano
        id='WqHqs+1RUtuDpummLrFxnmQjRop/4x7JyTeaDwbF1HGDw96bbxDuoVZismqiKK2ylZS'
            'fEkiAn0ZNACQK3/zj3Q==',
        public_key='pQECAyYgASFYIOZIpVC7JbRnKeFSvqeiP8WtymmjyFsCwY8A3tmbkzgEIlg'
            'gNOhEmwyz7HwSpK84kyvf5BBoNKj42KZuT6BAugPPiug=',
    ),
    RegisteredKey( # den-antares.com
        id='pDvWeA8ZfgXsqoNZeo12WScVhQNPo9gioAScFyXlfdOKqlJCHwSiMXoTtcsTv8d2nS6'
            'AYp4yJUXkVRDaRPwa2A==',
        public_key='pQECAyYgASFYIAKteyStrylQok14QnfRPVNaBtrMX88dM1uSTFC5FOq4Ilg'
            'gkWZ/u3guarx7+5rSgXVzBp3tq7RoFe4FwpAOqWMSprM=',
    ),
    RegisteredKey( # den-antares.com - Yubikey 5 NFC (Ars)
        id='6Vbj8ydd2++owAKKJht0DVg/cTMoeitoIWb6jyJU2843y5fdfoQB0BrHbXhF2leaE1w'
            'p2TSZPRm0ouCsU0ZAQg==',
        public_key='pQECAyYgASFYIPQBXXqMi4KLyf9YSe6BXRzA5k6NPkw2xnzfzl/MdMelIlg'
            'gqHADqPonr9wPimc6vpb+maZBdift9nDYcLfHqaverL8=',
    ),
    RegisteredKey( # den-antares.com - Yubikey 5 Nano
        id='tjoXP+WRKwOR4EUG6t2txazV9z5oXshuLPArHc4z17bSjnRG8TtWCskqSBHTqKOpTOA'
            'ZTZJAJ3H9JO72zpzplA==',
        public_key='pQECAyYgASFYIOMM69cfD8rb7q0SCTp85hYWU3rJBw5FFTdjUteBM9T1Ilg'
            'gXeOV2n0MEIovV/clxEwpVH5xkqPmiDW+aJRkINeR06s=',
    ),
]

error_template = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="color-scheme" content="dark">
<meta name="viewport" content="width=device-width, initial-scale=1, minimum-scale=1, maximum-scale=1">

<title>Tir na Nog</title>
</head>

<body>
<h1>{status_code} {status}</h1>
{message}
</body>
</html>'''

# FastAPI docs advise intercepting the Starlette HTTP exception, not the FastAPI
# one
@app.exception_handler(starlette.exceptions.HTTPException)
async def http_exception_handler(request: Request,
err: starlette.exceptions.HTTPException):
    if request.headers.get('Sec-Fetch-Mode') == 'navigate':
        message = err.detail
        
        if err.status_code in [401, 403]:
            message += '<br /><a href="/static/login.html">Login here</a>'
        
        html = error_template.format(
            status_code=err.status_code,
            status=http.client.responses[err.status_code],
            message=message,
        )
        
        return fr.HTMLResponse(status_code=err.status_code, content=html)
    
    return await fastapi.exception_handlers.http_exception_handler(request, err)

#############
# Endpoints #
#############

@app.post('/api/challenge')
async def post_prelogin():
    global challenge
    # MDN states the challenge should be at least 16 bytes
    # https://developer.mozilla.org/en-US/docs/Web/API/Web_Authentication_API
    challenge = os.urandom(16)
    return fr.JSONResponse({
        'challenge': str(base64.b64encode(challenge), 'ascii'),
        'allowCredentials': [v.id for v in registered_keys],
    })

@app.post('/api/register-key')
async def post_api_register_key(request: Request):
    global challenge
    if challenge is None:
        raise HTTPException(422, 'Unprocessable Content - Challenge not set')
    challenge_local = challenge
    challenge = None
    
    try:
        body = json.loads(await request.body())
    except json.decoder.JSONDecodeError:
        raise HTTPException(400, 'Bad Request - Invalid JSON')
    
    if body['rpId'] not in ['localhost', 'den-antares.com']:
        raise HTTPException(403, 'Forbidden - This key is for '
            f'"{body['rpId']}", not this site')
    
    try:
        verified_registration = webauthn.verify_registration_response(
            credential=body,
            expected_challenge=challenge_local,
            expected_rp_id=body['rpId'],
            expected_origin=body['origin'],
            require_user_verification=False,
        )
    except webauthn.helpers.exceptions.InvalidRegistrationResponse as e:
        raise HTTPException(401, f'Unauthorized - {e}')
    
    return fr.JSONResponse({
        'id': str(
            base64.b64encode(verified_registration.credential_id),
            'ascii'),
        'public_key': str(
            base64.b64encode(verified_registration.credential_public_key),
            'ascii'),
    })

@app.post('/api/login')
async def post_api_login(request: Request):
    global challenge
    if challenge is None:
        raise HTTPException(422, 'Unprocessable Content - Challenge not set')
    challenge_local = challenge
    challenge = None
    
    try:
        body = json.loads(await request.body())
    except json.decoder.JSONDecodeError:
        raise HTTPException(400, 'Bad Request - Invalid JSON')
    
    if body['rpId'] not in ['localhost', 'den-antares.com']:
        raise HTTPException(403, 'Forbidden - This key is for '
            f'`{body['rpId']}`, not this site')
    
    for key in registered_keys:
        if key.id == body['rawId']:
            public_key = base64.b64decode(key.public_key)
            break
    else:
        raise HTTPException(403, 'Forbidden - Key ID not found in registered '
            'keys')
    
    try:
        verified_response = webauthn.verify_authentication_response(
            credential=body,
            expected_challenge=challenge_local,
            expected_rp_id=body['rpId'],
            expected_origin=body['origin'],
            credential_public_key=public_key,
            # Sign count is required, but doesn't seem to do anything
            credential_current_sign_count=0,
            require_user_verification=False,
        )
    except webauthn.helpers.exceptions.InvalidAuthenticationResponse as e:
        raise HTTPException(401, f'Unauthorized - {e}')
    
    token = str(base64.b64encode(os.urandom(32)), 'ascii')
    tokens.append(token)
    res = fr.PlainTextResponse(token)
    res.set_cookie(key='token', value=token)
    return res

def check_token(token: str | None):
    if not token:
        raise HTTPException(401, 'Unauthorized - login at https:/login.html')
    
    if token not in tokens:
        raise HTTPException(403, 'Forbidden')

@app.post('/api/logout')
async def post_api_logout(token: str | None = Cookie(default=None)):
    check_token(token)
    tokens.remove(token)

@app.post('/api/logout-all')
async def post_api_logout_all(token: str | None = Cookie(default=None)):
    check_token(token)
    tokens.clear()

@app.get('/verify')
async def get_auth_check(request: Request, x_forwarded_method: str = Header(),
x_forwarded_uri: str = Header(), token: str | None = Cookie(default=None)):
    logger.info(
        f'{request.client.host}:{request.client.port} - '
        f'{style([YELLOW])}Verifying '
        f'{style([BOLD, BLUE])}{x_forwarded_method} '
        f'{style([RESET, VIOLET])}{x_forwarded_uri} '
        f'{style([RESET])}...'
    )
    check_token(token)

################
# Style Helper #
################

# Copied from ffvrc. ffvrc's copy should be considered authoritative
def style(styles: List[str | int], string: object = '',
width: int | None = None) -> str:
    string = str(string)
    
    if width is not None:
        assert width > 0
        
        if len(string) <= width: string = f'{string:{width}}'
        else: string = string[:max(width - 3, 0)] + min(width, 3)*'.'
    
    ansi_codes = ''
    
    if not isinstance(styles, list):
        styles = [styles]
    
    for style in styles:
        match style:
            case int():
                ansi_codes += f'\033[{style}m'
            case str() if re.fullmatch('#[0-9a-fA-F]{3}', style):
                r, g, b = (int(style[i], 16)*0xff//0xf for i in [1, 2, 3])
                ansi_codes += f'\033[38;2;{r};{g};{b}m'
            case str() if re.fullmatch('#[0-9a-fA-F]{6}', style):
                r, g, b = (int(style[i:i+2], 16) for i in [1, 3, 5])
                ansi_codes += f'\033[38;2;{r};{g};{b}m'
            case _:
                raise ValueError(f'Unknown style: {style}')
    
    reset = '\033[0m' if styles and string else ''
    
    return ansi_codes + string + reset

RESET = 0
BOLD = 1
GRAY = '#ccc'
MAGENTA = '#f0f'
VIOLET = '#c6f'
BLUE = '#4ad'
AQUA = '#1aba97'
GREEN = '#4d4'
YELLOW = '#fe0'
ORANGE = '#ecb64a'
RED = '#f00'
