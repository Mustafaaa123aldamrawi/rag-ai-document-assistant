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
