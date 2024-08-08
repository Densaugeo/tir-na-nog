Create a non-resident key:

```
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
    pubKeyCredParams: [ {type: "public-key", alg: -7} ],
  }
});
```

credential.id // 'Y4CNZMvxzgqhDXxgJrjdPR5DlRPZ9nilCNJYNsypNcvcPLkg_FgMnlbnXqKkJErUnKpHnyF1fH6a7WNFo7cv4Q' - looks like a public key, though I haven't found any confirmation for that
credential.response // Appears to be an optional thing for 'attestation'

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

The resulting login_response.response.authenticatorData and login_response.response.signature remain the same for repeated calls. However,
varying the challenge changes login_response.response.signature

Create a resident key:

```
credential_2 = await navigator.credentials.create({
  publicKey: {
    challenge: new Uint8Array([117, 61, 252, 231, 191, 241]),
    rp: { id: "mozilla.org", name: "ACME Corporation" },
    user: {
      id: new Uint8Array([79, 252, 83, 72, 214, 7, 89, 26]),
      name: "jamiedoe",
      displayName: "Jamie Doe"
    },
    pubKeyCredParams: [ {type: "public-key", alg: -7} ],
    authenticatorSelection: {
      residentKey: 'required',
    },
  }
});
```
