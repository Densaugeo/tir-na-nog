Create a non-resident key:

```
// In Firefox, this cannot be run while the browser console is open
credential = await navigator.credentials.create({
  publicKey: {
    // MDN states the challenge should be at least 16 bytes
    // https://developer.mozilla.org/en-US/docs/Web/API/Web_Authentication_API
    challenge: new Uint8Array([117, 61, 252, 231, 191, 241, 7, 8, 117, 61, 252, 231, 191, 241, 7, 8]),
    rp: { id: "localhost", name: "Localhost" },
    user: {
      id: new TextEncoder().encode('den_antares'),
      name: "den_antares",
      displayName: "Den Antares"
    },
    pubKeyCredParams: [
      // Chrome logs a warning unless both of these algorithms are specified
      { type: "public-key", alg: -7 },
      { type: "public-key", alg: -257 },
    ],
  }
});
```



credential.id // 'iJdDqCOfx8Fkh-6PJHsw2sI98RevmuQ2UXiMe2gUgEQHTIVYpIUxvWoX6izv6M2IHXFp5IVXj6PSXAB-ephfog'
buffer_to_b64(credential.rawId) // 'iJdDqCOfx8Fkh+6PJHsw2sI98RevmuQ2UXiMe2gUgEQHTIVYpIUxvWoX6izv6M2IHXFp5IVXj6PSXAB+ephfog=='
new Uint8Array(credential.response.getPublicKey()) // [48, 89, 48, 19, 6, 7, 42, 134, 72, 206, 61, 2, 1, 6, 8, 42, 134, 72, 206, 61, 3, 1, 7, 3, 66, 0, 4, 175, 66, 227, 211, 220, 207, 44, 137, 22, 146, 96, 237, 70, 69, 38, 176, 161, 126, 213, 144, 161, 203, 213, 34, 133, 154, 66, 213, 250, 59, 14, 173, 39, 236, 42, 109, 100, 176, 15, 41, 246, 194, 225, 108, 232, 212, 248, 155, 222, 246, 225, 202, 228, 209, 31, 149, 89, 94, 69, 128, 141, 118, 19, 216]
buffer_to_b64(credential.response.getPublicKey()) // 'MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEr0Lj09zPLIkWkmDtRkUmsKF+1ZChy9UihZpC1fo7Dq0n7CptZLAPKfbC4Wzo1Pib3vbhyuTRH5VZXkWAjXYT2A=='

JSON.stringify({
  id: credential.id,
  rawId: buffer_to_b64(credential.rawId),
  response: {
    attestationObject: buffer_to_b64(credential.response.attestationObject),
    clientDataJSON: buffer_to_b64(credential.response.clientDataJSON),
  },
  type: credential.type,
}) // '{"id":"iJdDqCOfx8Fkh-6PJHsw2sI98RevmuQ2UXiMe2gUgEQHTIVYpIUxvWoX6izv6M2IHXFp5IVXj6PSXAB-ephfog","rawId":"iJdDqCOfx8Fkh+6PJHsw2sI98RevmuQ2UXiMe2gUgEQHTIVYpIUxvWoX6izv6M2IHXFp5IVXj6PSXAB+ephfog==","response":{"attestationObject":"o2NmbXRkbm9uZWdhdHRTdG10oGhhdXRoRGF0YVjESZYN5YgOjGh0NBcPZHZgW4/krrmihjLHmVzzuoMdl2NBAAAAAQAAAAAAAAAAAAAAAAAAAAAAQIiXQ6gjn8fBZIfujyR7MNrCPfEXr5rkNlF4jHtoFIBEB0yFWKSFMb1qF+os7+jNiB1xaeSFV4+j0lwAfnqYX6KlAQIDJiABIVggr0Lj09zPLIkWkmDtRkUmsKF+1ZChy9UihZpC1fo7Dq0iWCAn7CptZLAPKfbC4Wzo1Pib3vbhyuTRH5VZXkWAjXYT2A==","clientDataJSON":"eyJ0eXBlIjoid2ViYXV0aG4uY3JlYXRlIiwiY2hhbGxlbmdlIjoiZFQzODU3X3hCd2gxUGZ6bnZfRUhDQSIsIm9yaWdpbiI6Imh0dHBzOi8vbG9jYWxob3N0Ojg0NDMiLCJjcm9zc09yaWdpbiI6ZmFsc2V9"},"type":"public-key"}'

Authenticate with non-resident key:

```
login_response = await navigator.credentials.get({
  publicKey: {
    challenge: new Uint8Array([139, 66, 181, 87, 7, 203, 45]),
    rp: { id: "localhost", name: "Localhost" },
    allowCredentials: [{
      type: "public-key",
      // id field here is equal to credential.rawId. Do not use credential.id -
      // it is supposed to be a base64 representation of .rawId, but atob()
      // and btoa() cannot convert it correctly (they error or gives results
      // of the wrong length)
      id: new Uint8Array([99, 128, 141, 100, 203, 241, 206, 10, 161, 13, 124, 96, 38, 184, 221, 61, 30, 67, 149, 19, 217, 246, 120, 165, 8, 210, 88, 54, 204, 169, 53, 203, 220, 60, 185, 32, 252, 88, 12, 158, 86, 231, 94, 162, 164, 36, 74, 212, 156, 170, 71, 159, 33, 117, 124, 126, 154, 237, 99, 69, 163, 183, 47, 225]),
      //id: new TextEncoder().encode(credential.id),
    }],
  }
});
```
