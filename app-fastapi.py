# Installed fastapi, fastapi[standard]

import collections, secrets, json, pathlib, os, base64, hashlib

#import requests
from fastapi import FastAPI, Header, Form, Response, HTTPException, Depends, Request
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
        
        if scope['path'].startswith('/static/restricted/') \
        and not likely_vrc_client:
            raise HTTPException(401, 'Unauthorized - login at https:/login.html')
        
        await super().__call__(scope, receive, send)

app = FastAPI()
app.mount(
    name='static',
    path='/static',
    app=StaticFilesCustom(directory='/www', html=True),
)
app.mount(
    name='acme',
    path='/.well-known/acme-challenge',
    app=StaticFiles(directory='/www/.well-known/acme-challenge', html=True),
)

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
from webauthn import verify_authentication_response, base64url_to_bytes, verify_registration_response

challenge = None
allow_credentials = [
    'iJdDqCOfx8Fkh+6PJHsw2sI98RevmuQ2UXiMe2gUgEQHTIVYpIUxvWoX6izv6M2IHXFp5IVXj6PSXAB+ephfog==',
]
public_keys = [
    #bytes([48, 89, 48, 19, 6, 7, 42, 134, 72, 206, 61, 2, 1, 6, 8, 42, 134, 72, 206, 61, 3, 1, 7, 3, 66, 0, 4, 213, 234, 207, 60, 174, 205, 100, 74, 105, 96, 227, 16, 254, 247, 215, 131, 195, 28, 29, 245, 38, 9, 61, 170, 223, 102, 211, 100, 71, 50, 33, 95, 206, 89, 85, 124, 248, 12, 138, 196, 77, 188, 60, 177, 222, 51, 232, 71, 203, 41, 203, 225, 231, 5, 185, 35, 175, 179, 142, 206, 200, 11, 86, 189]),
    'MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE1erPPK7NZEppYOMQ/vfXg8McHfUmCT2q32bTZEcyIV/OWVV8+AyKxE28PLHeM+hHyynL4ecFuSOvs47OyAtWvQ',
]

@app.get('/login.html')
async def get_login_html():
    return FileResponse('login.html')

@app.post('/prelogin')
async def post_prelogin():
    global challenge
    challenge = [1, 2, 3, 4, 5, 6, 7, 8]
    return JSONResponse({
        'challenge': challenge,
        'allowCredentials': allow_credentials,
    })

@app.post('/login')
async def post_login(request: Request):
    global challenge
    if challenge is None:
        raise HTTPException(403, 'Forbidden - Challenge not set')
    challenge_local = challenge
    challenge = None
    
    body = json.loads(await request.body())
    print(body)
    
    credential = """{{
        "id": "{}",
        "rawId": "{}",
        "response": {{
            "authenticatorData": "{}",
            "clientDataJSON": "{}",
            "signature": "{}",
            "userHandle": "{}"
        }},
        "type": "public-key",
        "authenticatorAttachment": "cross-platform",
        "clientExtensionResults": {{}}
    }}""".format(allow_credentials[0], allow_credentials[0], body['authenticatorData'], body['clientDataJSON'], body['signature'], 'den_antares')
    
    print()
    print(credential)
    #print(base64url_to_bytes(public_keys[0]))
    print()
    print(json.loads(body['create_string']))
    print()
    
    print('Attempting verify_registration_response()')
    verified_registration = verify_registration_response(
        credential=json.loads(body['create_string']),
        expected_challenge=bytes([117, 61, 252, 231, 191, 241, 7, 8, 117, 61, 252, 231, 191, 241, 7, 8]),
        expected_rp_id='localhost',
        expected_origin='https://localhost:8443',
        require_user_verification=False,
    )
    print(verified_registration)
    print()
    
    verified_response = verify_authentication_response(
        credential=body['json_dump'],
        expected_challenge=bytes(challenge_local),
        expected_rp_id='localhost',
        expected_origin='https://localhost:8443',
        credential_public_key=verified_registration.credential_public_key,
        credential_current_sign_count=0,
        require_user_verification=False,
    )
    print('Finally got a verified response:')
    print(verified_response)
    print()
    
    return PlainTextResponse('some-token')

def validate_token(token: str):
    if token != 'some-token':
        raise HTTPException(401, 'Unauthorized - Invalid token')
    
    return token

@app.get('/restricted')
async def get_restricted(token: Annotated[str, Depends(validate_token)]):
    print(f'Got token: {token}')
    return 'hi'
