# Keycloak and API auth cheat sheet

Reference for getting a bearer token so `curl` calls run as you, not
anonymously. This Oasis uses the **central** Keycloak at `nomad-lab.eu`
(`oasis.uses_central_user_management: true`), so there is nothing to install or
configure locally. Keycloak docs: https://www.keycloak.org/documentation.

## The model in one paragraph

OAuth2 has four roles. You are the **resource owner**. `curl` (or the GUI) is
the **client**. Keycloak is the **authorization server**: it checks your
password and issues tokens. The NOMAD `app` is the **resource server**: it
trusts a token Keycloak signed and reads your identity from it. OIDC is OAuth2
plus a standard way to carry identity, which is what a JWT does.

## Get the auth config from NOMAD

```
API=http://localhost/nomad-oasis/api/v1
curl -s $API/info | python3 -m json.tool | grep -iA6 keycloak
```

You want three values from there (names may read as `server_url` /
`realm_name` / `client_id` or similar):

- `KC_URL`   the Keycloak base, e.g. `https://nomad-lab.eu/fairdi/keycloak/auth`
- `REALM`    e.g. `fairdi_nomad_prod`
- `CLIENT`   the public client id, e.g. `nomad_public`

The token endpoint is then:

```
TOKEN_URL="$KC_URL/realms/$REALM/protocol/openid-connect/token"
```

## Get a token, password flow

Works when the client has "direct access grants" enabled, which the public
NOMAD client historically does.

```
read -rsp 'NOMAD password: ' PW; echo
TOKEN=$(curl -s "$TOKEN_URL" \
  -d grant_type=password \
  -d client_id="$CLIENT" \
  -d username='you@example.org' \
  -d password="$PW" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
echo "${TOKEN:0:20}..."
```

`read -rsp` keeps the password off your shell history and screen. The response
also has `refresh_token` and `expires_in` (seconds, usually 300).

## Get a token, browser flow (fallback)

If the password flow returns `invalid_grant` or the client forbids it:

1. Log in to the GUI at `http://localhost/nomad-oasis/gui/`.
2. Open the browser dev tools, Network tab.
3. Trigger any action that calls the API (open your uploads).
4. Click an `api/v1/...` request, copy the `Authorization` header value after
   `Bearer `.
5. `export TOKEN=<that string>`. It expires in minutes; repeat when it does.

## Use it

```
curl -s $API/uploads -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

Same query with and without the header shows the difference: `owner: user`
returns your unpublished uploads with the token, and `[]` without it.

## Read what is in the token

A JWT is `header.payload.signature`, three base64url strings joined by dots.
The payload is readable:

```
echo "$TOKEN" | cut -d. -f2 | tr '_-' '/+' | base64 -d 2>/dev/null | python3 -m json.tool
```

Fields to know:

- `sub`                 your stable user id, the same value NOMAD stores as the
                        entry `main_author`
- `preferred_username`  your login name
- `exp`                 expiry, Unix seconds. `date -d @<exp>` to read it
- `iss`                 the issuer, must be your realm URL
- `aud` / `azp`         the client the token was minted for

You cannot forge or edit this: the `app` verifies the signature against
Keycloak's public key. Changing a byte makes the token invalid, not more
powerful.

## Refresh instead of re-entering the password

```
TOKEN=$(curl -s "$TOKEN_URL" \
  -d grant_type=refresh_token \
  -d client_id="$CLIENT" \
  -d refresh_token="$REFRESH" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
```

## Gotchas

- `401` from the API with a token you just got: it already expired (300 s), or
  the `iss` in it does not match what the `app` expects. Get a fresh one, and
  check `$API/info` really points at the same realm.
- `403` with a valid token: you are authenticated but not authorized for that
  resource. Not an auth-setup problem.
- The token is a password for five minutes. Do not commit it, do not paste it
  into an issue, do not put it in a URL (`-d`/header only).
- There is no local Keycloak container to restart. If auth is broken, the
  problem is the token, the `$API/info` config, or network egress from the VM
  to `nomad-lab.eu`.
- The GUI login and your `curl` token are independent. Logging out of the GUI
  does not invalidate a token you already copied; it just expires on its own.
