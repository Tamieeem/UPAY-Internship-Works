# JWT Auth — Security Analysis

This is a write-up of what can go wrong with the JWT auth system I built (register / login / logout / refresh / session revoke, with SimpleJWT on Django + DRF), where the real risks are, and two vulnerabilities I deliberately reproduced in my own code and then fixed. I've also listed the shortcuts I knowingly took for a learning project that would need fixing before any of this went to production.

## The root of almost every JWT problem: it's stateless

The whole appeal of JWT is that the server can verify a token by checking a signature, with no database lookup. That's also where most of the danger comes from. Because the server keeps no memory of what it issued, two things follow that shape everything below:

1. **You can't revoke an access token.** There's no server-side record to delete. Once it's out, it's valid until it expires — full stop.
2. **Claims are frozen at mint time.** Whatever I bake into a token (`role`, `account_ids`) is a snapshot of the user at the moment they logged in. If their role changes after that, the token keeps lying until it's reissued.

Everything in my system is either exploiting statelessness (custom claims, to skip DB lookups) or clawing it back where I couldn't live without it (the blacklist for logout, the `LoginSession` table for "log out other devices"). The security gaps all live at that seam.

## Token leakage

The JWT payload is base64-encoded, **not** encrypted. Signing proves the token wasn't tampered with; it does nothing to hide the contents. I confirmed this directly — pasting an access token into a decoder showed `role`, `account_ids`, `user_id`, and `exp` all in plain readable text. So rule one: never put anything secret in a claim. A role and a UUID are fine to expose; a balance or a card number would not be.

Where tokens actually leak in practice:

- **XSS + browser storage.** If the frontend keeps tokens in `localStorage`, any injected script can read them. `httpOnly` cookies are safer against XSS but bring their own CSRF tradeoffs — there's no free option, it's a choice.
- **Transport.** Over plain HTTP a token is trivially intercepted. HTTPS everywhere is non-negotiable for a fintech API.
- **Logs.** Tokens leaking into request logs or error trackers is a quieter, very common leak.

What makes leakage worse with JWT specifically is the no-revoke problem. A stolen **access** token works until it expires and I can't kill it early. A stolen **refresh** token is worse — it mints fresh access tokens for its entire lifetime, so a leaked refresh token is effectively days of access unless rotation catches it.

My mitigations: HTTPS only, short access-token lifetime (so a stolen access token dies fast on its own), and refresh rotation with blacklisting so each refresh token is single-use and a replayed one gets rejected.

## Expiry and token lifetime

Since I can't revoke access tokens, **expiry is the actual security control** — it's not a convenience setting, it's the thing standing between "token stolen" and "attacker locked out." The shorter the access lifetime, the smaller the window a stolen token is useful.

The tradeoff is real: short access lifetime means clients hit the refresh endpoint more often. The standard answer — and what I used — is short-lived access tokens (minutes) paired with longer-lived refresh tokens, so the user stays logged in without carrying a long-lived access token around.

Honest note: during development I bumped `ACCESS_TOKEN_LIFETIME` up to 30 minutes so Postman testing wasn't constantly expiring on me. That's a dev-only compromise. In production this is one of the most important knobs to tighten back down (5–15 minutes), precisely because it's the main mitigation for the no-revoke problem.

## Signing key rotation

Every token I issue is signed with one key. By default SimpleJWT signs with Django's `SECRET_KEY`. Two problems come out of this:

- **If that key leaks, the whole system is compromised.** An attacker who has the signing key can forge a valid token for *any* user with any claims — admin role included — and the server will happily accept it, because the signature checks out. This is the worst-case JWT failure.
- **Rotating the key invalidates every outstanding token at once.** The moment I change the signing key, every token signed with the old one fails verification — every user is effectively logged out. That makes rotation feel scary, so people avoid doing it, which is itself the problem.

Two things I'd do for production. First, set a dedicated `SIGNING_KEY` separate from `SECRET_KEY`, so I can rotate the JWT key without disturbing everything else in Django that depends on `SECRET_KEY`. Second, plan rotation with a grace window — keep the old key around as an accepted *verifying* key for a short period while new tokens are signed with the new key, so existing sessions drain out naturally instead of everyone getting kicked at once.

One more key-related risk worth naming: algorithm confusion. Classic JWT attacks abuse `alg: none` or trick a server that expects RS256 into verifying with HS256. SimpleJWT's defaults (HS256, explicit algorithm) aren't vulnerable to this out of the box, but it's a reason never to hand-roll JWT verification or accept the algorithm from the token header.

## Two vulnerabilities I reproduced and fixed in my own code

### 1. User enumeration via timing (email login backend)

**The vuln.** My custom email backend looks up the user by email, then checks the password. The naive version does nothing on a lookup miss:

```python
try:
    user = User.objects.get(email__iexact=email)
except User.DoesNotExist:
    return None   # vulnerable: returns immediately
```

**How you'd exploit it.** A real email with a wrong password runs the password hasher (slow). A nonexistent email returns instantly (no hash). By measuring response time, an attacker can tell which emails are registered — handing them a verified list of accounts to target. On a fintech app, "which emails have accounts here" is itself sensitive.

**The fix** (now in my code): run the hasher even on a miss, so both paths take roughly the same time.

```python
try:
    user = User.objects.get(email__iexact=email)
except User.DoesNotExist:
    User().set_password(password)   # waste the same time as a real check
    return None
```

Now "no such user" and "wrong password" are indistinguishable by timing, so the endpoint stops leaking which accounts exist.

### 2. Cross-user session revocation (IDOR)

**The vuln.** The revoke endpoint takes a session id and blacklists that session's token. The naive lookup fetches the session by id alone:

```python
session = LoginSession.objects.get(id=session_id)   # vulnerable: no owner check
```

**How you'd exploit it.** Session ids are just identifiers in the URL. Any authenticated user could `POST /api/auth/sessions/<someone-elses-id>/revoke/` and forcibly log another user out of their session — an Insecure Direct Object Reference. One user shouldn't be able to touch another user's sessions at all.

**The fix** (now in my code): scope the lookup to the requesting user, so a session that isn't theirs simply isn't found.

```python
session = get_object_or_404(
    LoginSession, id=session_id, user=request.user
)
```

This returns a 404 for someone else's session — which is also better than a 403, because it doesn't even confirm the id exists. It's the same server-side ownership principle the rest of the API already uses for accounts, applied to sessions.

## Shortcuts I took for learning that need attention before production

These were deliberate tradeoffs to keep a learning project moving, not oversights. Each is a "fine for now / fix before prod" item:

- **`auth.User` instead of a custom user model.** I enforced email uniqueness with a hand-written partial unique index, which gives the same guarantee. A greenfield production app should start with a custom user model with email as the login field, since swapping it later is painful.
- **Role derived from `is_superuser` / `is_staff` flags.** Those are Django-admin concepts, not business roles. Production should use Groups + Permissions (or a real role model), and — importantly — treat the token's `role` claim as a non-authoritative hint while doing the real permission check server-side against live data. Claims hint, the server decides.
- **SQLite `COLLATE NOCASE` for the email index.** It's ASCII-only. Production on Postgres should use a `LOWER()` functional index for proper Unicode case-folding.
- **`account_ids` in the token.** It's frozen state — open a new account and the token is stale until re-login. Production might drop it from the token entirely and fetch accounts live, since the staleness isn't worth the saved lookup.
- **A `jti`-matching wrinkle in session capture.** I mint a token inside `validate()` to read its `jti`, which could in principle differ from the token the user actually receives. The hardened version reads the `jti` off the token the parent already created. Known latent bug, worth fixing.
- **Client IP comes from `X-Forwarded-For`, which is spoofable.** Fine as telemetry for a session list; never to be used as a security control. Production must have the proxy overwrite the header.
- **No refresh-token reuse detection.** I have rotation + blacklist (the ingredients), but not the automated response: if an already-blacklisted refresh token shows up again, that means two parties hold it, and a mature system would treat that as a breach and invalidate the user's whole token family. SimpleJWT gives the signal (the reused token is rejected), not the automated response.
- **Signing key defaults to `SECRET_KEY`.** Production should use a dedicated `SIGNING_KEY` so it can be rotated independently.

## In one line

JWT trades server-side state for speed. My custom claims exploit that trade, my session table partially reverses it, and every item on the list above is a place where the trade left an exposure that's acceptable in a learning build but would need closing before real money moved through it.