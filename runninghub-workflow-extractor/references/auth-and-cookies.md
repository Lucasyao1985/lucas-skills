# Authentication Reference

## Credential Model

RunningHub uses two independent credential systems:

1. **Web JWT** - stored at localStorage key `Rh-Accesstoken`. The axios interceptor in chunk DPZWuLWl.js does:
   ```js
   const t = localStorage.getItem("Rh-Accesstoken")
   headers.Authorization = `Bearer ${t}`
   // team workspaces also add:
   headers["X-Team-Id"] = currentTeamId   // when not "0"/"null"
   ```
   Cookies mirror the same names domain-wide: `Rh-Accesstoken`, `Rh-Refreshtoken`, `Rh-Identify`, `userId`, plus locale/analytics cookies.

2. **ComfyUI accessKey** - separate system for history/output endpoints. Frontend obtains it via an internal comfyUI login call and stores `localStorage["Rh-Comfy-Auth"] = e.accessKey`, `Rh-Comfy-Expire-In = e.expire_in`. A Bearer JWT will NOT satisfy these endpoints.

## Getting Credentials From the User

Automated-browser login (Playwright) is typically blocked by risk control ("无法登入"). Recommended flow:

1. Ask the user to log in normally in their own browser at runninghub.ai.
2. Either:
   - F12 Console: `localStorage.getItem('Rh-Accesstoken')` - user pastes back the eyJ... JWT; or
   - Cookie export plugin: full JSON array of cookies (contains Rh-Accesstoken, Rh-Refreshtoken, Rh-Identify, userId).
3. Validate immediately with a cheap authenticated call; expect code 0.

JWT payload fields include sub (userId), exp, created, username, userRegion - decode locally to check expiry before troubleshooting.

## Handling Rules

- Never echo full tokens into reports/logs/screenshots; mask to first 10 chars.
- Pass tokens via argument or environment variable, never hardcode into scripts.
- When using cookie-file input, build a single Cookie header: `name1=value1; name2=value2; ...`
- Send `Origin` and a real browser `User-Agent`; some endpoints reject bare clients.

## Login-State Detection in Automated Browsers

Do not detect login by button text (localized, changes layout). Poll instead:
```js
const t = localStorage.getItem('Rh-Accesstoken');
return t && t.length > 20;   // true means logged in
```
A false positive from text-based detection once caused an entire session of "authenticated" calls that were actually anonymous.
