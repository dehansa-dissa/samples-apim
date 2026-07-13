# Custom Authorization Token - Sample Validation Backend

A sample backend server for testing the "Passing a Custom Authorization Token
to the Backend" feature. It accepts **any path and method**, and authorizes a
request only when the header is exactly:

```
Authorization: Bearer 1234
```

On success it returns HTTP 200 with `"Request Received."`; otherwise HTTP 401.
Every response also echoes back the headers the backend actually received, so
you can verify what the gateway forwarded.

## Run

```bash
python3 server.py          # listens on port 8080
python3 server.py 9090     # or pick a port
```

Incoming requests and their headers are printed directly to the terminal.

## Use as the API endpoint

In the API Publisher, set the API's endpoint to:

```
http://localhost:8080/custom-auth-header/validate-header
```

(Use your machine's LAN IP instead of `localhost` if the gateway runs in
Docker/Kubernetes or on another host - e.g. `http://host.docker.internal:8080/...`
for Docker Desktop on macOS.)

## Test methods

### 1. Test the backend directly (no gateway)

```bash
# Expected: 200 "Request Received."
curl -i -H "Authorization: Bearer 1234" http://localhost:8080/custom-auth-header/validate-header

# Expected: 401 invalid_token
curl -i -H "Authorization: Bearer some-app-token" http://localhost:8080/custom-auth-header/validate-header

# Expected: 401 missing_token
curl -i http://localhost:8080/custom-auth-header/validate-header
```

### 2. Test through the gateway WITHOUT the policy (baseline)

Before attaching the TokenExchange policy, invoke the API:

```bash
curl -k -H "Authorization: Bearer <access-token>" -H "Custom: Bearer 1234" \
  https://localhost:8243/testcustomheader/1.0.0
```

Expected: **401** from the backend, and the echoed headers should show either
no `Authorization` header (gateway dropped it) plus a `Custom` header still
present. This confirms the baseline behavior.

### 3. Test through the gateway WITH the policy attached

Attach the **Custom Authorization Token** policy (tokenExchange.j2) to the
resource, deploy a new revision, then run the same command:

```bash
curl -k -H "Authorization: Bearer <access-token>" -H "Custom: Bearer 1234" \
  https://localhost:8243/testcustomheader/1.0.0
```

Expected: **200** with `"Request Received."`. In `received_headers`, verify:

- `Authorization` is `Bearer 1234` (swapped in from `Custom`)
- `Custom` is absent (removed by the sequence)
- the original application access token appears nowhere

### 4. Negative tests through the gateway

```bash
# Wrong custom token -> backend 401 invalid_token
curl -k -H "Authorization: Bearer <access-token>" -H "Custom: Bearer 9999" \
  https://localhost:8243/testcustomheader/1.0.0

# Missing Custom header -> backend 401 missing_token
curl -k -H "Authorization: Bearer <access-token>" \
  https://localhost:8243/testcustomheader/1.0.0

# Invalid access token -> 401 from the GATEWAY (never reaches the backend;
# server console shows no request)
curl -k -H "Authorization: Bearer garbage" -H "Custom: Bearer 1234" \
  https://localhost:8243/testcustomheader/1.0.0
```

### 5. Debugging tips

- The server console log tells you whether a request reached the backend at
  all, and with which headers - the fastest way to tell a gateway-side 401
  from a backend-side 401.
- If the deployed revision doesn't reflect the policy, redeploy the revision -
  policies attached after deployment are not applied until a new revision is
  deployed.
