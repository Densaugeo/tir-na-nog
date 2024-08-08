# Installed fastapi, fastapi[standard]

import collections, secrets, json, pathlib, os, base64, hashlib

#import requests
from fastapi import FastAPI, Header, Form, Response, HTTPException, Depends
from fastapi.responses import PlainTextResponse, HTMLResponse
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
            raise HTTPException(status_code=403)
        
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

def validate_token(token: str):
    if token != 'some-token':
        raise HTTPException(401, 'Invalid token')
    
    return token

@app.get('/restricted')
async def get_restricted(token: Annotated[str, Depends(validate_token)]):
    print(f'Got token: {token}')
    return 'hi'

@app.post('/login')
async def post_login():
    return PlainTextResponse('some-token')
