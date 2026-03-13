# tir-na-nog

Scratch server for tir-na-nog

## TODO

Auth system
- Test stringifying `navigator.credentials.create/get()` - seems to work in Chromium now
- Update request bodies in /api/register-key and /api/login endpoints to use pydantic templates
- Break out into library
- Set up auto tests with new CLI passkey tool
- Update /verify to return username (in header maybe)
- Move accepted keys into config file
