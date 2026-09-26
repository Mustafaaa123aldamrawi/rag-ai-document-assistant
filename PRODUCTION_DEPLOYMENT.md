# Production Deployment Checklist

## Backend

Set these environment variables before starting the API:

- `AVIA_ENV=production`
- `AVIA_DATABASE_URL` for managed PostgreSQL
- `AVIA_AUTH_MODE=jwt`
- `AVIA_CORS_ORIGINS` with explicit origins; wildcard is rejected
- `AVIA_JWT_JWKS_URL` or a configured JWT verification key
- `AVIA_JWT_ISSUER` and `AVIA_JWT_AUDIENCE` when required by the auth provider
- `AVIA_STORAGE_MODE=s3`
- `AVIA_STORAGE_BUCKET`
- `AVIA_STORAGE_REGION` when required
- `AVIA_STORAGE_ENDPOINT` for a non-default S3-compatible endpoint
- `AVIA_ACCOUNT_DELETE_PROVIDER=supabase`
- `AVIA_SUPABASE_URL`
- `AVIA_SUPABASE_SERVICE_ROLE_KEY` (server only; never expose this in the mobile app)
- `AVIA_SUPPORT_EMAIL` for privacy and deletion requests
- `AVIA_PUBLIC_BASE_URL` using HTTPS; this publishes `/privacy` and `/account-deletion`
- `HF_TOKEN` for visual drawing review
- `TAVILY_API_KEY` where web-grounded AV research is enabled

The API rejects insecure production configuration.

## Mobile

Configure EAS build environment values for:

- `EXPO_PUBLIC_API_URL`
- `EXPO_PUBLIC_SUPABASE_URL`
- `EXPO_PUBLIC_SUPABASE_ANON_KEY`

The mobile app persists the Supabase session and attaches its access token as a Bearer JWT to API requests.

## Release Quality Gate

Before a store build:

1. Backend regression tests must pass.
2. Mobile TypeScript check must pass.
3. Production health check must show JWT auth and managed persistence.
4. Test signup, login, logout, token refresh, project isolation, drawing upload, report generation, and report download with two separate users.
5. Verify private drawing/report objects are not publicly readable without authorization.
6. Test in-app account deletion with a disposable user and verify projects, reports, drawing analyses, private artifacts, and the auth identity are removed.
7. Verify the public `/privacy` and `/account-deletion` pages load over HTTPS and use the real support email.
8. Use the deployed `/privacy` URL for App Store / Play privacy disclosures and the `/account-deletion` URL for Google Play's external deletion resource.
