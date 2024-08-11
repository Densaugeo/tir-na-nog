# Installed fastapi, fastapi[standard]

import collections, secrets, json, pathlib, os, base64, hashlib, re

#import requests
from fastapi import FastAPI, Header, Form, Response, HTTPException, Depends, Request, Cookie
from fastapi.responses import PlainTextResponse, HTMLResponse, FileResponse, JSONResponse
import fastapi.responses
from fastapi.staticfiles import StaticFiles
from starlette.types import Receive, Scope, Send
from setproctitle import setproctitle

import helpers


setproctitle('tir-na-nog')


class StaticFilesCustom(helpers.StaticFilesWithDir):
    async def __call__(self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        for key, value in scope['headers']:
            if key == b'user-agent':
                user_agent = str(value, 'utf8')
        
        likely_vrc_client = bool(user_agent) and (
            'NSPlayer'         in user_agent or
            'GStreamer'        in user_agent or
            'AVProMobileVideo' in user_agent or
            'stagefright'      in user_agent
        )
        
        if scope['path'].startswith('/files/restricted/') \
        and not likely_vrc_client:
            token = None
            print(scope['headers'])
            for key, value in scope['headers']:
                if key == b'cookie':
                    match = re.match('token="(.*)"', str(value, 'ascii'))
                    if match:
                        token = match.group(1)
            
            print(token)
            if token not in tokens:
                raise HTTPException(401, 'Unauthorized - login at '
                    'https:/login.html')
        
        await super().__call__(scope, receive, send)

app = FastAPI()

#@app.get('/', response_class=HTMLResponse)
#def get_():
#    with open('index.html') as f:
#        return f.read()

@app.get('/foo')
async def get_foo(response: Response):
    #response.status_code = 409
    #return 'A 409 error occurred'
    return { 'foo': 'bar' }
    #return send_file('index.html')

from typing import Annotated
from fastapi import Query

@app.get('/echo')
async def get_echo(number: int, string: Annotated[str, Query(max_length=4)]):
    return number


from fastapi.security import OAuth2PasswordBearer
import json
from webauthn import verify_authentication_response, verify_registration_response
import base64
import dataclasses


@dataclasses.dataclass
class RegisteredKey:
    id: str
    public_key: str

registered_keys = [
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
]

challenge = None

tokens = []

@app.post('/api/challenge')
async def post_prelogin():
    global challenge
    # MDN states the challenge should be at least 16 bytes
    # https://developer.mozilla.org/en-US/docs/Web/API/Web_Authentication_API
    challenge = os.urandom(16)
    return JSONResponse({
        'challenge': str(base64.b64encode(challenge), 'ascii'),
        'allowCredentials': [v.id for v in registered_keys],
    })

@app.post('/api/register-key')
async def post_api_register_key(request: Request):
    global challenge
    if challenge is None:
        raise HTTPException(403, 'Forbidden - Challenge not set')
    challenge_local = challenge
    challenge = None
    
    body = json.loads(await request.body())
    print(body)
    print()
    
    assert body['rpId'] in ['localhost', 'den-antares.com']
    
    print('Attempting verify_registration_response()')
    verified_registration = verify_registration_response(
        credential=body,
        expected_challenge=challenge_local,
        expected_rp_id=body['rpId'],
        expected_origin=body['origin'],
        require_user_verification=False,
    )
    print(verified_registration)
    print()
    
    print('Trying to find strings that need persisting:')
    print('id:', base64.b64encode(verified_registration.credential_id))
    print('public key:',
        base64.b64encode(verified_registration.credential_public_key))
    print()
    
    return JSONResponse({
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
        raise HTTPException(403, 'Forbidden - Challenge not set')
    challenge_local = challenge
    challenge = None
    
    body = json.loads(await request.body())
    print(body)
    print()
    
    for key in registered_keys:
        if key.id == body['rawId']:
            public_key = base64.b64decode(key.public_key)
            break
    else:
        raise HTTPException(403, 'Key ID not found in registered keys')
    
    verified_response = verify_authentication_response(
        credential=body,
        expected_challenge=challenge_local,
        expected_rp_id='localhost',
        expected_origin='https://localhost:8443',
        credential_public_key=public_key,
        credential_current_sign_count=0,
        require_user_verification=False,
    )
    
    print('Finally got a verified response:')
    print(verified_response)
    print()
    
    token = str(base64.b64encode(os.urandom(32)), 'ascii')
    tokens.append(token)
    res = PlainTextResponse(token)
    res.set_cookie(key='token', value=token)
    return res

@app.post('/api/logout')
async def post_api_logout(token: str | None = Cookie(default=None)):
    if token not in tokens:
        raise HTTPException(401, 'Unauthorized - login at https:/login.html')
    
    tokens.remove(token)
    
    return PlainTextResponse('Success!')

@app.post('/api/logout-all')
async def post_api_logout(token: str | None = Cookie(default=None)):
    if token not in tokens:
        raise HTTPException(401, 'Unauthorized - login at https:/login.html')
    
    tokens.clear()
    
    return PlainTextResponse('Success!')

@app.get('/files/test')
async def get_files_test():
    return PlainTextResponse('hello from files path')

# Keep .mount() calls at end, so that endpoints inside /files are still served
app.mount(
    name='static',
    path='/static',
    app=StaticFilesCustom(directory=pathlib.Path(__file__).parent / 'static'),
)
app.mount(
    name='files',
    path='/files',
    app=StaticFilesCustom(directory='/www', html=True),
)
