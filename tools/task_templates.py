"""Track A Task Templates — Phase 6, Plan 02 of Primordial v2.0.

Three task template classes for Track A experiments:
1. CodingTaskTemplate (A1): Multi-file refactoring with provenance chains
2. DebuggingTaskTemplate (A2): Bug-fix chains with hypothesis-test-revise loops
3. SpecificationTaskTemplate (A3): Spec compliance with requirement tracing

Each template:
- Produces unique, non-trivial content per iteration
- Builds genuine provenance chains (each artifact references predecessors)
- Generates enough tokens to reach the 80K LLM compaction threshold
- Embeds forge artifact IDs naturally in the task context

Convention assertions (project-specific — physics conventions N/A):
  artifact_id_format = "artifact:<run>:stage:<seat>:<revision>"
  compaction_disambiguation = "forge compaction = lossless hash-verified;
    LLM compaction = lossy semantic; unqualified 'compaction' FORBIDDEN"
  all_metrics_dimensionless = True
"""

import hashlib
from typing import Any

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from compaction_experiment import inject_artifact_markers


# --- Base Class ---

class TaskTemplate:
    """Base class for Track A task templates.

    Subclasses must implement:
    - _iteration_prompts: list of iteration prompt templates
    - category: str identifying the task category
    - track: str identifying the experimental track (default "A")
    """

    category: str = "generic"
    track: str = "A"

    def __init__(self, run_id: str = "default"):
        self.run_id = run_id
        self._artifacts: list[dict] = []  # {id, iteration, source_refs}
        self._generated_ids: set[str] = set()

    def generate_iteration(self, iteration: int) -> str:
        """Generate a user prompt for this iteration.

        Each iteration:
        1. Builds on the previous iteration's context
        2. Injects a forge artifact ID for survival tracking
        3. References previous artifacts via source_refs

        Args:
            iteration: Zero-based iteration index.

        Returns:
            User prompt string with embedded forge provenance.
        """
        prompt_text = self._get_iteration_prompt(iteration)

        # Inject artifact marker
        marked_text, artifact_id = inject_artifact_markers(
            prompt_text, self.run_id, iteration
        )
        self._generated_ids.add(artifact_id)

        # Build source_refs chain
        source_refs = []
        if self._artifacts:
            # Reference the most recent artifact
            source_refs.append(self._artifacts[-1]["id"])
            # For deeper chains, also reference 2-back when available
            if len(self._artifacts) >= 3 and iteration % 3 == 0:
                source_refs.append(self._artifacts[-3]["id"])

        self._artifacts.append({
            "id": artifact_id,
            "iteration": iteration,
            "source_refs": source_refs,
        })

        # Embed source_refs naturally in the prompt
        if source_refs:
            refs_text = ", ".join(f"[ref: {ref}]" for ref in source_refs)
            marked_text += f"\n\nBuilding on previous work: {refs_text}"

        return marked_text

    def expected_tokens_per_iteration(self) -> int:
        """Approximate tokens per response (for threshold estimation)."""
        return 700  # Conservative estimate

    def validate_provenance_depth(self, min_depth: int = 5) -> bool:
        """Check that the provenance chain has sufficient depth.

        Walks the source_refs chain from the last artifact to the first,
        counting the maximum chain depth.

        Args:
            min_depth: Minimum required chain depth.

        Returns:
            True if max chain depth >= min_depth.
        """
        if not self._artifacts:
            return False

        # Build adjacency: child -> parents
        id_to_artifact = {a["id"]: a for a in self._artifacts}

        # Walk from last artifact backwards
        max_depth = 0
        for artifact in self._artifacts:
            depth = self._chain_depth(artifact["id"], id_to_artifact, set())
            max_depth = max(max_depth, depth)

        return max_depth >= min_depth

    def _chain_depth(self, artifact_id: str, index: dict, visited: set) -> int:
        """Recursively compute chain depth for an artifact."""
        if artifact_id in visited or artifact_id not in index:
            return 0
        visited.add(artifact_id)
        artifact = index[artifact_id]
        if not artifact["source_refs"]:
            return 1
        max_parent_depth = 0
        for ref in artifact["source_refs"]:
            parent_depth = self._chain_depth(ref, index, visited)
            max_parent_depth = max(max_parent_depth, parent_depth)
        return 1 + max_parent_depth

    def inject_provenance(self, text: str, run_id: str, iteration: int) -> tuple[str, str]:
        """Delegate to compaction_experiment.inject_artifact_markers."""
        return inject_artifact_markers(text, run_id, iteration)

    def get_artifacts(self) -> list[dict]:
        """Return all generated artifacts with their provenance chains."""
        return list(self._artifacts)

    def get_unique_ids(self) -> set[str]:
        """Return all unique artifact IDs generated."""
        return set(self._generated_ids)

    def _get_iteration_prompt(self, iteration: int) -> str:
        """Get the prompt for a specific iteration. Override in subclasses."""
        prompts = self._iteration_prompts()
        idx = iteration % len(prompts)
        return prompts[idx]

    def _iteration_prompts(self) -> list[str]:
        """Return the list of iteration prompt templates. Override in subclasses."""
        return [f"Generic task step {i+1}." for i in range(20)]


# --- A1: Coding Task Template ---

class CodingTaskTemplate(TaskTemplate):
    """Multi-file refactoring tasks with deep provenance chains.

    20 iterations covering a complete authentication system build:
    data model -> migrations -> middleware -> API handlers -> RBAC ->
    tests -> rate limiting -> OAuth -> audit logging -> password reset ->
    integration tests -> session management -> 2FA -> API docs ->
    profile management -> GDPR deletion -> load tests -> admin dashboard ->
    webhooks -> deployment.

    Each iteration references artifacts from previous steps, building
    a provenance chain that accumulates forge artifacts naturally.

    Expected: ~500-1000 tokens per response, reaching 80K threshold
    in ~15-20 iterations with model responses included.
    """

    category = "coding"
    track = "A"

    def _iteration_prompts(self) -> list[str]:
        return [
            # 0: Data model
            (
                "Design the data model for a user authentication system with "
                "role-based access control. Include all entities (User, Role, "
                "Permission, Session, AuditLog), their relationships (many-to-many "
                "for User-Role, one-to-many for User-Session), field types with "
                "constraints (email UNIQUE NOT NULL, password_hash VARCHAR(255), "
                "created_at TIMESTAMP DEFAULT NOW()), and indexes for common "
                "query patterns (email lookup, session token lookup, role membership). "
                "Use PostgreSQL-specific types where beneficial (UUID for primary keys, "
                "JSONB for flexible metadata, ENUM for status fields). Document the "
                "rationale for each design decision."
            ),
            # 1: Migration SQL
            (
                "Write the database migration SQL for the authentication system "
                "designed in the previous step. Include CREATE TABLE statements with "
                "all constraints, CREATE INDEX for performance-critical queries, "
                "foreign key relationships with CASCADE/SET NULL policies, seed data "
                "for default roles (admin, moderator, user, guest) and permissions "
                "(read, write, delete, manage_users, manage_roles), and a rollback "
                "migration that drops everything in reverse dependency order. Use "
                "transaction wrapping for atomicity. Add CHECK constraints for email "
                "format validation and password hash length."
            ),
            # 2: Middleware
            (
                "Implement the JWT token generation and validation middleware. "
                "Include: (1) Token generation with RS256 signing using rotating key "
                "pairs, (2) Access token with 15-minute expiry containing user_id, "
                "roles, and permissions claims, (3) Refresh token with 7-day expiry "
                "stored in httpOnly secure cookie, (4) Token validation middleware "
                "that checks expiry, signature, and revocation status against a Redis "
                "blacklist, (5) Token refresh endpoint that validates the refresh "
                "token and issues a new access/refresh pair with rotation, (6) Error "
                "handling for expired (401), malformed (400), and revoked (403) tokens."
            ),
            # 3: API handlers
            (
                "Write the API endpoint handlers for login, register, logout, and "
                "token refresh. Login: validate credentials against bcrypt hash, "
                "check account status (active/suspended/deleted), rate limit to 5 "
                "attempts per minute per IP, return access + refresh tokens. Register: "
                "validate email format and uniqueness, enforce password policy (min 12 "
                "chars, mixed case, number, special), hash with bcrypt cost=12, create "
                "user with default 'user' role, send verification email. Logout: "
                "revoke current access token (add to Redis blacklist), clear refresh "
                "cookie. Token refresh: validate refresh token, check it hasn't been "
                "used before (rotation detection), issue new pair."
            ),
            # 4: RBAC
            (
                "Design and implement the role-based access control (RBAC) system. "
                "Define a permission hierarchy: superadmin > admin > moderator > user > "
                "guest. Permissions are granular actions (user:read, user:write, "
                "user:delete, role:manage, audit:read, settings:manage). Roles bundle "
                "permissions with inheritance (admin inherits all moderator permissions). "
                "Implement: (1) Permission checking middleware that extracts roles from "
                "JWT claims and resolves effective permissions including inheritance, "
                "(2) Decorator-based route protection (@require_permission('user:write')), "
                "(3) Resource-level access control (users can edit own profile but not "
                "others unless admin), (4) Role assignment/revocation API endpoints."
            ),
            # 5: Unit tests
            (
                "Write comprehensive unit tests for the authentication middleware. "
                "Cover: (1) Valid token generation and verification round-trip, "
                "(2) Expired token rejection with correct error code, (3) Malformed "
                "token rejection (truncated, wrong algorithm, missing claims), "
                "(4) Revoked token detection via Redis blacklist, (5) Refresh token "
                "rotation (old refresh token becomes invalid after use), (6) Rate "
                "limiting enforcement (6th attempt within window returns 429), "
                "(7) RBAC permission resolution with role inheritance, (8) Edge cases: "
                "empty roles array, null permissions claim, concurrent refresh attempts. "
                "Use pytest fixtures for database setup/teardown, mock Redis for "
                "blacklist tests, and parameterized tests for permission matrix."
            ),
            # 6: Rate limiting
            (
                "Implement rate limiting for all authentication endpoints. Use a "
                "sliding window algorithm backed by Redis sorted sets. Configure: "
                "login = 5 requests per minute per IP + 20 per hour per account, "
                "register = 3 per hour per IP, token refresh = 10 per minute per user, "
                "password reset = 3 per hour per email. Implement token bucket for "
                "burst tolerance on non-critical endpoints. Add response headers: "
                "X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset. "
                "Return 429 Too Many Requests with Retry-After header when exceeded. "
                "Include IP-based blocking for repeated violations (auto-block after "
                "50 failed logins in 1 hour, manual review required for unblock)."
            ),
            # 7: OAuth
            (
                "Write the OAuth2 integration for Google and GitHub SSO. Implement "
                "the authorization code flow: (1) /auth/google and /auth/github "
                "redirect to provider with client_id, redirect_uri, scope, and "
                "PKCE challenge, (2) Callback handler validates state parameter, "
                "exchanges code for tokens using client_secret, (3) Fetch user profile "
                "from provider API (email, name, avatar), (4) Link to existing account "
                "by email or create new account, (5) Handle edge cases: email not "
                "verified by provider, email already registered with password auth, "
                "provider returns insufficient scopes. Store provider tokens encrypted "
                "in user_oauth_connections table. Support account unlinking."
            ),
            # 8: Audit logging
            (
                "Design the audit logging system for all authentication events. "
                "Structured JSON log format with fields: timestamp, event_type "
                "(login_success, login_failure, logout, token_refresh, password_change, "
                "role_change, account_created, account_deleted), actor_id, target_id, "
                "ip_address, user_agent, geolocation (via GeoIP2), risk_score (based "
                "on IP reputation and behavioral signals), session_id, metadata (JSON "
                "blob for event-specific data). Write to both PostgreSQL (queryable, "
                "30-day retention) and CloudWatch/ELK (long-term, 1-year retention). "
                "Include real-time alerting rules: 10+ failed logins = notify admin, "
                "login from new country = notify user, role escalation = notify security."
            ),
            # 9: Password reset
            (
                "Implement the password reset flow with email verification. Steps: "
                "(1) User submits email to /auth/reset-password, (2) Generate "
                "cryptographically random 32-byte token, store SHA-256 hash in "
                "password_reset_tokens table with 1-hour expiry, (3) Send email "
                "with reset link containing the raw token (not hash), (4) User "
                "clicks link, frontend validates token via GET /auth/verify-reset-token, "
                "(5) User submits new password via POST /auth/reset-password/confirm "
                "with token, (6) Validate new password meets policy, hash with bcrypt, "
                "update user record, invalidate all existing sessions, delete used "
                "token. Rate limit: 3 reset requests per hour per email. Prevent "
                "timing attacks on token validation (constant-time comparison)."
            ),
            # 10: Integration tests
            (
                "Write integration tests for the complete authentication flow. "
                "Test the full lifecycle: register -> verify email -> login -> "
                "access protected resource -> refresh token -> logout. Test "
                "error paths: register with existing email -> login with wrong "
                "password -> access after logout -> refresh with revoked token. "
                "Test concurrent scenarios: two sessions for same user, simultaneous "
                "login and password change, race condition on token refresh. "
                "Use testcontainers for PostgreSQL and Redis. Verify audit log "
                "entries are created for each event. Check rate limiting with "
                "rapid sequential requests. Verify CORS headers on all endpoints. "
                "Test with both valid and expired SSL certificates."
            ),
            # 11: Session management
            (
                "Design the session management system with multi-device support. "
                "Session model: session_id (UUID), user_id, device_fingerprint "
                "(hashed), ip_address, user_agent, created_at, last_active_at, "
                "expires_at, is_active. Features: (1) List all active sessions for "
                "a user via GET /auth/sessions, (2) Revoke specific session via "
                "DELETE /auth/sessions/:id, (3) Revoke all sessions except current "
                "via POST /auth/sessions/revoke-others, (4) Forced logout of all "
                "sessions on password change, (5) Session activity tracking (update "
                "last_active_at on each authenticated request via middleware), "
                "(6) Automatic cleanup of expired sessions via cron job (daily), "
                "(7) Maximum 5 concurrent sessions per user (oldest revoked on new login)."
            ),
            # 12: 2FA
            (
                "Implement two-factor authentication using TOTP (RFC 6238). "
                "Setup flow: (1) User enables 2FA via POST /auth/2fa/enable, "
                "(2) Generate 160-bit secret, encode as base32, create otpauth:// "
                "URI, (3) Return QR code (PNG via qrcode library) and 8 backup "
                "codes (random 8-digit numbers, stored as bcrypt hashes), "
                "(4) User verifies setup by entering a code from their authenticator "
                "app, (5) On success, mark 2FA as active. Login modification: after "
                "password verification, if 2FA is enabled, return intermediate token "
                "and prompt for TOTP code or backup code. Verify TOTP with 1-step "
                "time window tolerance. Each backup code is single-use. Provide "
                "recovery flow for lost device (admin can disable 2FA after identity "
                "verification)."
            ),
            # 13: API docs
            (
                "Write the API documentation for all authentication endpoints using "
                "OpenAPI 3.0 specification. Include: (1) All endpoints with HTTP "
                "method, path, description, (2) Request body schemas with validation "
                "rules (email format, password policy, TOTP format), (3) Response "
                "schemas for success and error cases with example values, "
                "(4) Authentication requirements per endpoint (public, authenticated, "
                "admin-only), (5) Rate limiting documentation per endpoint, "
                "(6) Error code catalog (AUTH_001 through AUTH_050) with human-readable "
                "messages, HTTP status codes, and resolution steps, (7) Webhook event "
                "schemas, (8) SDK usage examples in Python, JavaScript, and Go."
            ),
            # 14: Profile management
            (
                "Design the user profile management system. Endpoints: "
                "GET /users/me (current user profile), PATCH /users/me (update "
                "profile fields), POST /users/me/avatar (upload avatar with "
                "image validation: max 5MB, JPEG/PNG/WebP, resize to 256x256), "
                "POST /users/me/email (initiate email change with verification), "
                "DELETE /users/me (initiate account deletion). Profile fields: "
                "display_name (2-50 chars, alphanumeric + spaces), bio (max 500 chars), "
                "timezone (IANA format), locale (BCP 47), notification_preferences "
                "(JSON with email/push/sms toggles per event type). Email change: "
                "send verification to new email, require password confirmation, "
                "update only after new email is verified, keep old email as recovery "
                "for 30 days."
            ),
            # 15: GDPR deletion
            (
                "Implement GDPR-compliant account deletion with data export. "
                "Data export (Right of Access): GET /users/me/export returns a "
                "ZIP containing JSON files for profile, sessions, audit log, OAuth "
                "connections, and any user-generated content. Processing time: async "
                "with webhook notification when ready, expires after 7 days. "
                "Account deletion (Right to Erasure): POST /users/me/delete initiates "
                "30-day grace period. During grace period: account is deactivated, "
                "login is blocked, data is retained. After 30 days: PII is scrubbed "
                "(email hashed, name replaced with 'Deleted User #NNN'), audit logs "
                "are retained with anonymized actor_id, sessions and OAuth connections "
                "are hard-deleted. Implement undo within grace period via email link."
            ),
            # 16: Load tests
            (
                "Write load tests for authentication endpoints using Locust or k6. "
                "Scenarios: (1) Steady state: 100 concurrent users, mix of 60% "
                "token validation, 20% login, 10% register, 10% refresh. Target: "
                "p95 < 100ms for token validation, p95 < 500ms for login. "
                "(2) Spike test: 0 to 1000 users in 30 seconds. Verify graceful "
                "degradation (rate limiting kicks in, no 500 errors). (3) Soak test: "
                "50 users for 4 hours. Check for memory leaks, connection pool "
                "exhaustion, and Redis memory growth. (4) Stress test: increase "
                "until failure. Document breaking point. Report: throughput (rps), "
                "latency percentiles (p50/p95/p99), error rate, resource utilization "
                "(CPU/memory/connections). Compare with and without rate limiting."
            ),
            # 17: Admin dashboard
            (
                "Design the admin dashboard for user management. Views: "
                "(1) User list with search (by email, name, role), filter (active/ "
                "suspended/deleted, role, created date range), sort (name, created_at, "
                "last_login), pagination (25/50/100 per page). (2) User detail: "
                "profile info, role assignments, session list, audit log, OAuth "
                "connections, 2FA status. (3) Bulk operations: suspend/activate "
                "multiple users, assign role to selection, export to CSV. "
                "(4) System metrics: active sessions count, login success/failure "
                "rate (24h rolling), new registrations (7d chart), top failed "
                "login IPs. Admin API endpoints require admin role. All actions "
                "create audit log entries. Implement optimistic locking for "
                "concurrent admin edits."
            ),
            # 18: Webhooks
            (
                "Implement webhook notifications for authentication events. "
                "Configuration: POST /admin/webhooks with url, events (array of "
                "event types to subscribe), secret (for HMAC-SHA256 signature). "
                "Delivery: on each matching event, POST to registered URL with "
                "JSON body containing event_type, timestamp, payload, and "
                "X-Webhook-Signature header (HMAC of body using shared secret). "
                "Retry logic: 3 attempts with exponential backoff (1s, 10s, 100s). "
                "Mark webhook as failing after 10 consecutive failures, notify admin. "
                "Delivery tracking: store delivery attempts with status code, "
                "response time, and body preview (first 500 chars). Provide "
                "GET /admin/webhooks/:id/deliveries for debugging. Implement "
                "webhook testing endpoint that sends a test event."
            ),
            # 19: Deployment
            (
                "Write the deployment guide for the authentication system. "
                "Environment variables: DATABASE_URL, REDIS_URL, JWT_PRIVATE_KEY "
                "(base64-encoded), JWT_PUBLIC_KEY, GOOGLE_CLIENT_ID, GOOGLE_SECRET, "
                "GITHUB_CLIENT_ID, GITHUB_SECRET, SMTP_HOST, SMTP_PORT, FROM_EMAIL, "
                "SENTRY_DSN, LOG_LEVEL. Docker: multi-stage Dockerfile (build + "
                "runtime), docker-compose for local dev (app + postgres + redis). "
                "Kubernetes: Deployment, Service, Ingress, ConfigMap, Secrets, "
                "HPA (scale on CPU 70%), PDB (minAvailable: 1). Health checks: "
                "/health (shallow - process alive), /health/ready (deep - DB + Redis "
                "connected). Monitoring: Prometheus metrics (request_duration, "
                "active_sessions, login_attempts), Grafana dashboards, PagerDuty "
                "alerts for error rate > 1% or p99 > 2s."
            ),
        ]


# --- A2: Debugging Task Template ---

class DebuggingTaskTemplate(TaskTemplate):
    """Bug-fix chains with hypothesis-test-fail-revise loops.

    Pattern per bug: hypothesize -> test -> observe failure -> revise -> test again.
    3-4 bugs total, 5-8 steps per bug chain.

    Each hypothesis is a forge artifact linked to the previous hypothesis
    and test result, building deep provenance chains naturally.

    Expected: ~400-800 tokens per response.
    """

    category = "debugging"
    track = "A"

    def _iteration_prompts(self) -> list[str]:
        return [
            # Bug 1: Memory leak in connection pool
            # Step 0: Initial bug report
            (
                "Bug report: The application's memory usage grows linearly over time, "
                "reaching 2GB after 24 hours of operation. The growth rate is approximately "
                "80MB per hour. No individual request appears to leak — the growth is "
                "gradual and continuous. The application uses a PostgreSQL connection pool "
                "(max 20 connections), Redis for caching, and handles approximately "
                "500 requests per minute. Analyze the bug report and form your initial "
                "hypothesis about the root cause. Consider: connection pool behavior, "
                "cache eviction policy, request handler cleanup, middleware state "
                "accumulation, and logging buffer growth."
            ),
            # Step 1: Hypothesis 1
            (
                "Based on the initial analysis, test hypothesis H1: 'The connection pool "
                "is not releasing connections back to the pool after errors, causing new "
                "connections to be created that are never cleaned up.' Design a test: "
                "instrument the connection pool with logging to track acquire/release "
                "counts. Run 1000 requests with 5% error injection. Compare active "
                "connection count before and after. Expected if H1 is correct: active "
                "connections should grow monotonically. Expected if H1 is wrong: active "
                "connections should oscillate around the pool size."
            ),
            # Step 2: Test result (H1 fails)
            (
                "Test results for H1: Connection pool acquire count = 1000, release "
                "count = 1000, including error cases. Active connections at start: 5, "
                "at end: 5. The connection pool correctly releases connections on both "
                "success and error paths. H1 is REFUTED. Memory growth continued during "
                "the test (+3MB over 1000 requests). New observation: memory profiler "
                "shows the growth is in Python objects, not in the connection pool's "
                "C-level structures. The largest growing category is 'dict' objects. "
                "Form a revised hypothesis H2 based on this new evidence."
            ),
            # Step 3: Hypothesis 2
            (
                "Revised hypothesis H2: 'Request-scoped middleware is accumulating state "
                "in a module-level dictionary that is never pruned. Each request adds "
                "an entry (e.g., request_id -> metadata) but no cleanup runs to remove "
                "completed requests.' Test design: add a decorator that tracks the size "
                "of all module-level dicts in the middleware chain before and after each "
                "request. Run 500 requests and plot dict sizes over time. Additionally, "
                "inspect the middleware source code for any dict.setdefault() or dict[] = "
                "patterns without corresponding del or pop operations."
            ),
            # Step 4: Test result (H2 partial)
            (
                "Test results for H2: Found a module-level `_request_contexts` dict in "
                "the rate limiting middleware. Size at start: 0, after 500 requests: 487. "
                "Entries are request_id -> {timestamp, ip, path, rate_data}. Entries are "
                "NEVER removed. However, each entry is only ~200 bytes, so 487 entries = "
                "~100KB. This explains ~4MB per hour but NOT the 80MB per hour observed. "
                "H2 is PARTIALLY CONFIRMED — this is A leak but not THE leak. Additional "
                "investigation: the memory profiler shows a second growing category: "
                "'function' objects. This is unusual — function objects shouldn't grow. "
                "Form hypothesis H3 to explain the function object growth."
            ),
            # Step 5: Hypothesis 3
            (
                "Hypothesis H3: 'The audit logging middleware creates closure functions "
                "for each request (lambda or nested def for deferred logging) that "
                "capture the request/response objects in their closure scope, preventing "
                "garbage collection of the entire request context.' Test design: "
                "(1) Use gc.get_referrers() to trace what is keeping function objects "
                "alive, (2) Instrument the audit logger to count closure creations vs "
                "executions, (3) Check if the deferred logging queue has a bounded size "
                "or grows unboundedly. If H3 is correct, the closure count should match "
                "the function object growth rate, and each closure should reference "
                "large request/response objects."
            ),
            # Step 6: Test result (H3 confirmed)
            (
                "Test results for H3: CONFIRMED. The audit logging middleware creates a "
                "closure for each request: `def log_later(): logger.info(request, response)`. "
                "These closures are appended to a deferred_logs list that is processed by "
                "a background thread every 60 seconds. However, if the background thread "
                "falls behind (logging takes > 60s for a batch), the list grows without "
                "bound. Each closure captures the full request and response objects (~150KB "
                "each). gc.get_referrers() confirms: 5000 closure objects each holding "
                "references to request/response pairs = ~1.5GB. The background thread's "
                "processing time was 45s for 30K entries, but the list was growing at "
                "30K entries per minute. Fix: (1) Bound the deferred_logs list to 10K "
                "entries, (2) Drop oldest entries when full, (3) Use weak references for "
                "request/response in closures, (4) Fix the _request_contexts leak from H2."
            ),
            # Bug 2: Race condition in token refresh
            # Step 7: Bug report
            (
                "Bug report: Users occasionally get logged out unexpectedly. It happens "
                "more frequently when using the app from multiple browser tabs. The "
                "client-side code refreshes the access token when it's within 60 seconds "
                "of expiry. Multiple tabs can trigger refresh simultaneously. The server "
                "implements refresh token rotation: the old refresh token is invalidated "
                "when a new one is issued. Analyze this concurrency scenario and form "
                "hypothesis H4 about why multi-tab usage causes unexpected logouts. "
                "Consider the ordering of: tab A reads refresh token, tab B reads "
                "refresh token, tab A sends refresh request, tab A receives new tokens, "
                "tab B sends refresh request with now-invalidated token."
            ),
            # Step 8: H4 test
            (
                "Hypothesis H4: 'Refresh token rotation without concurrency handling "
                "causes a TOCTOU race condition. Tab A and Tab B both read the same "
                "refresh token from the cookie. Tab A refreshes first, invalidating "
                "the old token and setting a new one. Tab B's refresh request arrives "
                "with the now-invalidated old token, which the server rejects as a "
                "potential token theft (rotation violation), revoking ALL sessions for "
                "the user.' Test: simulate concurrent refresh requests with a 100ms "
                "delay between them using the same refresh token. Predict: second "
                "request returns 401 and all_sessions_revoked=true. Fix options: "
                "(1) Grace period for old refresh tokens (accept for 30s after rotation), "
                "(2) Client-side locking (BroadcastChannel API), (3) Idempotent refresh "
                "(same input token returns same output within window)."
            ),
            # Step 9: H4 confirmed + fix
            (
                "Test results for H4: CONFIRMED. Concurrent refresh simulation: "
                "Request A (t=0ms): success, new tokens issued. Request B (t=100ms): "
                "401 with error='refresh_token_reuse', all 3 active sessions revoked. "
                "This matches the production symptom exactly. Implementing fix option 3 "
                "(idempotent refresh): store a mapping of old_refresh_token_hash -> "
                "new_token_pair with 30-second TTL in Redis. If a refresh request arrives "
                "with an old token that was JUST rotated (within 30s), return the same "
                "new tokens instead of treating it as theft. After 30s, revert to strict "
                "rotation detection. Add metrics: concurrent_refresh_count and "
                "grace_period_hits to monitor the fix effectiveness."
            ),
            # Bug 3: Timezone-dependent test failures
            # Step 10: Bug report
            (
                "Bug report: The CI pipeline intermittently fails on token expiry tests. "
                "Tests pass locally (UTC+2) but fail on CI (UTC). The failure is in "
                "test_token_expires_after_15_minutes: it generates a token, advances time "
                "by 16 minutes using freezegun, and asserts the token is expired. The "
                "assertion sometimes passes and sometimes fails with 'token still valid "
                "at t+16m'. Analyze the timezone and time-handling code. Form hypothesis "
                "H5 about why the test is flaky."
            ),
            # Step 11: H5 test
            (
                "Hypothesis H5: 'The token generation uses datetime.now() (local time) "
                "but the validation uses datetime.utcnow() (UTC). When local time is "
                "ahead of UTC (positive offset), the token's iat claim is in the future "
                "relative to UTC, effectively extending the token's lifetime by the "
                "timezone offset. With UTC+2, a 15-minute token actually expires at "
                "t+17m UTC, so the t+16m test sometimes catches it before true expiry.' "
                "Test: print the iat and exp claims in both local and UTC. Compare with "
                "the validation time. If H5 is correct: iat_local - iat_utc = 2 hours, "
                "and exp_utc should be 2 hours later than expected."
            ),
            # Step 12: H5 confirmed + fix
            (
                "Test results for H5: CONFIRMED. Token generation: iat = datetime.now() "
                "= 2026-03-28 14:00:00 (UTC+2). Token validation: now = datetime.utcnow() "
                "= 2026-03-28 12:00:00 (UTC). The iat is 2 hours in the 'future' from "
                "the validator's perspective. Since JWT exp = iat + 15min = 14:15:00, "
                "but the validator checks against 12:00:00 UTC, the token appears to "
                "have ~2h15m remaining. Fix: replace ALL datetime.now() with "
                "datetime.now(timezone.utc) throughout the codebase. Replace ALL "
                "datetime.utcnow() with datetime.now(timezone.utc) (utcnow is deprecated "
                "in Python 3.12+). Add a linting rule to prevent bare datetime.now() "
                "usage. Update all token-related tests to use timezone-aware datetimes."
            ),
            # Bug 4: SQL injection via sort parameter
            # Step 13: Bug report
            (
                "Security bug report: Automated security scanner flagged a potential "
                "SQL injection vulnerability in the user search endpoint. The endpoint "
                "accepts a 'sort' query parameter (e.g., ?sort=created_at&order=desc) "
                "that is used to construct the ORDER BY clause. The scanner sent "
                "?sort=created_at;DROP TABLE users-- and received a 500 Internal Server "
                "Error instead of a 400 Bad Request, suggesting the input reaches the "
                "SQL parser. Analyze the vulnerability and form hypothesis H6 about the "
                "injection vector and its exploitability."
            ),
            # Step 14: H6 analysis
            (
                "Hypothesis H6: 'The sort parameter is interpolated directly into the "
                "SQL query string via f-string or .format(), bypassing the ORM's "
                "parameterized query protection. The ORDER BY clause cannot use "
                "parameterized queries in most ORMs (parameters are for values, not "
                "identifiers), so the developer used string interpolation as a shortcut.' "
                "Test: (1) Review the user search endpoint code for raw SQL or ORM "
                "raw() calls, (2) Attempt injection with: ?sort=1; SELECT pg_sleep(5)--, "
                "measure response time (if >5s, injection confirmed), (3) Check if "
                "the ORM's query builder has an orderBy method that accepts column "
                "references safely. Fix: create an allowlist of sortable columns "
                "{created_at, email, display_name, last_login} and reject any sort "
                "parameter not in the allowlist with 400 Bad Request."
            ),
            # Step 15: H6 confirmed + fix
            (
                "Test results for H6: CONFIRMED. Found in user_search.py line 42: "
                "query = f\"SELECT * FROM users WHERE active=true ORDER BY {sort_param} "
                "{order_param}\". The pg_sleep injection test: response time was 5.3s "
                "(vs normal 0.05s), confirming arbitrary SQL execution. Severity: "
                "CRITICAL — attacker can read arbitrary data, modify records, or drop "
                "tables. Fix implemented: (1) Allowlist of sortable columns: "
                "ALLOWED_SORT = {'created_at', 'email', 'display_name', 'last_login'}, "
                "(2) Validate sort_param in ALLOWED_SORT before use, (3) Validate "
                "order_param in {'asc', 'desc'}, (4) Use parameterized identifier "
                "quoting: sql.Identifier(sort_param), (5) Added integration test that "
                "attempts 10 common SQL injection payloads and verifies all return 400. "
                "Also audited all other endpoints for similar patterns — found 2 more "
                "in admin dashboard."
            ),
            # Steps 16-19: Wrap-up and review
            (
                "Bug fix review: Summarize all 4 bugs found, their root causes, fixes "
                "applied, and tests added. Bug 1 (memory leak): unbounded closure list "
                "in audit logger + leaked request contexts in rate limiter. Fix: bounded "
                "list + weak refs + cleanup. Bug 2 (race condition): refresh token "
                "rotation without concurrency handling. Fix: idempotent refresh with "
                "30s grace period. Bug 3 (timezone): mixing datetime.now() and utcnow(). "
                "Fix: timezone-aware datetimes throughout. Bug 4 (SQL injection): "
                "f-string interpolation of user input into SQL. Fix: column allowlist + "
                "parameterized identifiers. Document the systemic patterns: all 4 bugs "
                "stem from implicit assumptions (GC will clean up, only one tab exists, "
                "server is in UTC, ORM prevents injection). Recommend: explicit cleanup, "
                "concurrent-by-default design, timezone-aware-by-default, allowlist-by-default."
            ),
            (
                "Regression test suite: Write a comprehensive regression test for each "
                "of the 4 bugs fixed. Memory leak regression: run 10K requests and verify "
                "memory growth < 1MB (was 80MB/hr = ~1.3MB per 1K requests). Race condition "
                "regression: concurrent refresh from 5 simulated tabs, verify no session "
                "revocation. Timezone regression: generate and validate tokens in 5 "
                "timezones (UTC-12, UTC-5, UTC, UTC+5, UTC+12), verify consistent 15-minute "
                "expiry. SQL injection regression: attempt 20 injection payloads on all "
                "user-facing endpoints with ORDER BY or WHERE clauses, verify all return "
                "400 or are parameterized. Add these to the CI pipeline as non-negotiable "
                "gate tests."
            ),
            (
                "Post-mortem analysis: For each bug, trace how it was introduced, how "
                "long it existed before detection, and what process change would have "
                "prevented it. Memory leak: introduced in commit abc123 when audit logging "
                "was added, existed for 3 months. Prevention: memory profiling in CI "
                "(run 1K requests, assert RSS growth < 5MB). Race condition: existed "
                "since initial token refresh implementation. Prevention: concurrent test "
                "scenarios in the auth test suite from day 1. Timezone: existed since "
                "initial token code. Prevention: ban datetime.now() in linting rules, "
                "require timezone-aware datetimes. SQL injection: introduced when search "
                "was added. Prevention: mandatory parameterized queries lint rule, "
                "SQL injection test suite for all endpoints accepting user input."
            ),
            (
                "Architecture hardening recommendations based on the debugging session: "
                "(1) Resource lifecycle management: every allocated resource (connection, "
                "closure, context dict entry) must have an explicit deallocation path. "
                "Use context managers or try/finally. (2) Concurrency-first design: "
                "assume multi-client access from the start. Use idempotency keys for "
                "state-changing operations. (3) Time handling policy: all internal times "
                "in UTC, convert to local only at presentation layer. Use monotonic clock "
                "for durations, wall clock only for display. (4) Input validation at the "
                "boundary: every external input (query params, headers, body) validated "
                "against an allowlist before reaching any internal logic. No raw SQL "
                "construction with user input, ever."
            ),
        ]


# --- A3: Specification Task Template ---

class SpecificationTaskTemplate(TaskTemplate):
    """Specification compliance tasks with requirement tracing.

    A specification document with 10+ numbered requirements.
    Each iteration implements one requirement, producing a child
    artifact linked to the requirement artifact.

    Expected: ~500-1000 tokens per response.
    """

    category = "specification"
    track = "A"

    def _iteration_prompts(self) -> list[str]:
        return [
            # 0: Specification document
            (
                "Here is the technical specification for a real-time notification "
                "system. Each requirement is numbered and must be implemented and "
                "verified independently.\n\n"
                "REQ-001: The system SHALL deliver push notifications to mobile "
                "devices (iOS and Android) within 500ms of the triggering event.\n"
                "REQ-002: The system SHALL support at least 10,000 concurrent "
                "WebSocket connections per server instance.\n"
                "REQ-003: Notification delivery SHALL be guaranteed at-least-once. "
                "Duplicate detection is the client's responsibility.\n"
                "REQ-004: The system SHALL support notification priority levels: "
                "critical (immediate), high (within 1s), normal (within 5s), "
                "low (batched every 60s).\n"
                "REQ-005: The system SHALL persist all notifications for 30 days "
                "in a queryable store.\n"
                "REQ-006: The system SHALL support user-configurable notification "
                "preferences (per-channel muting, do-not-disturb schedules).\n"
                "REQ-007: The system SHALL provide a REST API for sending "
                "notifications with JSON schema validation.\n"
                "REQ-008: The system SHALL encrypt all notification payloads in "
                "transit (TLS 1.3) and at rest (AES-256-GCM).\n"
                "REQ-009: The system SHALL support notification templates with "
                "variable interpolation and localization (i18n).\n"
                "REQ-010: The system SHALL provide real-time delivery status "
                "tracking (sent, delivered, read, failed) via webhook callbacks.\n"
                "REQ-011: The system SHALL handle graceful degradation when "
                "downstream push services (APNs, FCM) are unavailable.\n"
                "REQ-012: The system SHALL support A/B testing of notification "
                "content with configurable audience splits.\n\n"
                "Analyze the specification. Identify dependencies between requirements. "
                "Propose an implementation order that respects dependencies."
            ),
            # 1: REQ-001 (push delivery)
            (
                "Implement REQ-001: Push notification delivery within 500ms. "
                "Design the push delivery pipeline: (1) Event ingestion via message "
                "queue (Redis Streams or Kafka), (2) Fan-out to device tokens via "
                "connection to APNs (HTTP/2) and FCM (HTTP v1 API), (3) Parallel "
                "delivery to multiple devices per user, (4) Latency measurement: "
                "timestamp at event creation, at queue dequeue, at push service "
                "submission, and at push service acknowledgment. Target p95 < 500ms "
                "end-to-end. Implementation: use asyncio for non-blocking I/O, "
                "connection pooling for APNs/FCM, and pre-resolved DNS. Include "
                "metrics: delivery_latency_ms histogram, push_success_rate counter, "
                "queue_depth gauge."
            ),
            # 2: REQ-002 (WebSocket connections)
            (
                "Implement REQ-002: Support 10,000 concurrent WebSocket connections. "
                "Architecture: (1) Use asyncio + websockets library for the WebSocket "
                "server, (2) Connection registry: ConcurrentDict mapping user_id -> "
                "set[WebSocket], (3) Heartbeat: ping every 30s, disconnect after 3 "
                "missed pongs, (4) Backpressure: if a client's send buffer exceeds 1MB, "
                "disconnect with code 1008 (policy violation), (5) Load testing: use "
                "autobahn-testsuite and custom load generator (10K connections, 100 "
                "messages/second broadcast). Capacity planning: each WebSocket connection "
                "uses ~30KB memory (headers + buffers + TLS state), so 10K connections = "
                "~300MB. Set kernel tuning: net.core.somaxconn=65535, "
                "fs.file-max=1000000, ulimit -n 100000."
            ),
            # 3: REQ-003 (at-least-once delivery)
            (
                "Implement REQ-003: At-least-once notification delivery guarantee. "
                "Design: (1) Every notification gets a unique notification_id (UUIDv7 "
                "for time-ordered), (2) Notifications are persisted to PostgreSQL before "
                "delivery attempt, (3) Delivery status tracked: pending -> sending -> "
                "sent -> confirmed | failed, (4) Failed deliveries retry with exponential "
                "backoff: 1s, 5s, 30s, 5m, 30m (max 5 retries), (5) Dead letter queue "
                "for permanently failed notifications (device unregistered, invalid token), "
                "(6) Idempotency: delivery workers use SELECT FOR UPDATE SKIP LOCKED to "
                "prevent duplicate processing. Client-side dedup: include notification_id "
                "in payload, client maintains a 24-hour seen-ID set."
            ),
            # 4: REQ-004 (priority levels)
            (
                "Implement REQ-004: Notification priority levels. Design: (1) Four "
                "priority queues: critical (Redis Stream, consumer group with immediate "
                "processing), high (Redis Stream, 1s max batch), normal (Redis Stream, "
                "5s batch), low (PostgreSQL table, cron-based batch every 60s). "
                "(2) Priority preemption: critical notifications interrupt low-priority "
                "batch processing. (3) Worker pool allocation: 50% for critical, 30% "
                "for high, 15% for normal, 5% for low (configurable). (4) SLA monitoring: "
                "alert if critical p99 > 200ms, high p99 > 1s, normal p99 > 5s. "
                "(5) Priority escalation: if a normal notification hasn't been delivered "
                "after 30s, escalate to high. (6) Rate limiting per priority: critical "
                "= unlimited, high = 1000/min per user, normal = 100/min, low = 10/min."
            ),
            # 5: REQ-005 (persistence)
            (
                "Implement REQ-005: 30-day notification persistence. Design: "
                "(1) PostgreSQL table: notifications (id UUIDv7, user_id, channel, "
                "priority, title, body_encrypted, metadata JSONB, created_at, "
                "delivered_at, read_at, expired_at). (2) Partitioning: by created_at "
                "month, automatic partition creation/drop. (3) Indexes: (user_id, "
                "created_at DESC) for inbox queries, (user_id, read_at IS NULL) for "
                "unread count, (delivered_at IS NULL) for pending deliveries. "
                "(4) Query API: GET /notifications?user_id=X&since=2026-03-01"
                "&limit=50&unread_only=true, paginated by cursor (notification_id). "
                "(5) Retention: pg_cron job drops partitions older than 30 days. "
                "(6) Archive: before dropping, export partition to S3 as compressed "
                "Parquet for analytics (90-day S3 retention)."
            ),
            # 6: REQ-006 (user preferences)
            (
                "Implement REQ-006: User-configurable notification preferences. "
                "Schema: notification_preferences (user_id PK, channel_mutes JSONB, "
                "dnd_schedule JSONB, digest_preference ENUM('immediate', 'hourly', "
                "'daily'), quiet_hours_start TIME, quiet_hours_end TIME, timezone TEXT). "
                "channel_mutes example: {'marketing': true, 'security': false, "
                "'social': true}. dnd_schedule example: {'weekdays': {'start': '22:00', "
                "'end': '07:00'}, 'weekends': {'start': '23:00', 'end': '09:00'}}. "
                "API: GET /users/:id/notification-preferences, PUT to update. "
                "Enforcement: before delivery, check (1) channel not muted, (2) not in "
                "DND window (respecting user's timezone), (3) critical priority bypasses "
                "DND. During DND, normal/low notifications are queued and delivered as "
                "digest when DND ends."
            ),
            # 7: REQ-007 (REST API)
            (
                "Implement REQ-007: REST API for sending notifications. Endpoint: "
                "POST /api/v1/notifications. Request body schema (JSON Schema): "
                "{ user_ids: [string], channel: string (required), priority: enum "
                "(critical|high|normal|low, default=normal), title: string (1-200 chars, "
                "required), body: string (1-10000 chars), template_id: string (optional), "
                "template_vars: object (optional), metadata: object (optional), "
                "scheduled_at: ISO 8601 datetime (optional, for delayed delivery) }. "
                "Response: 202 Accepted with { notification_id, status: 'queued', "
                "estimated_delivery_ms }. Validation: JSON Schema validation with "
                "ajv, rate limiting (1000 notifications per minute per API key), "
                "authentication via API key in X-API-Key header. Batch endpoint: "
                "POST /api/v1/notifications/batch for up to 1000 notifications in "
                "one request."
            ),
            # 8: REQ-008 (encryption)
            (
                "Implement REQ-008: Notification encryption in transit and at rest. "
                "In transit: TLS 1.3 with HSTS, certificate pinning for mobile clients. "
                "WebSocket uses wss:// only. At rest: (1) Notification body encrypted "
                "with AES-256-GCM before PostgreSQL storage, (2) Encryption key per "
                "user derived from a master key via HKDF-SHA256 with user_id as info, "
                "(3) Master key stored in AWS KMS / HashiCorp Vault, rotated quarterly, "
                "(4) Key rotation: new notifications use new key, old notifications "
                "re-encrypted in background job (batch of 1000, rate-limited to avoid "
                "DB load). Schema change: add key_version column to notifications table. "
                "Decryption: happens at read time in the API layer, never cached in "
                "plaintext. Push notification payloads: use platform-specific encryption "
                "(APNs: built-in TLS, FCM: symmetric key per device token)."
            ),
            # 9: REQ-009 (templates + i18n)
            (
                "Implement REQ-009: Notification templates with i18n. Template model: "
                "notification_templates (id, name, channel, title_template, body_template, "
                "variables JSONB, created_at, updated_at). Variable interpolation: "
                "Jinja2-style {{ variable_name }} with auto-escaping. Localization: "
                "notification_translations (template_id, locale BCP-47, title, body). "
                "Fallback chain: exact locale (fr-CA) -> language (fr) -> default (en). "
                "API: CRUD for templates at /api/v1/templates. When sending via "
                "template_id: resolve locale from user preferences, fetch translation, "
                "interpolate variables, validate result. Pre-render and cache translated "
                "templates (Redis, 5-minute TTL). Support pluralization via ICU "
                "MessageFormat. Provide template preview endpoint for testing before "
                "deployment."
            ),
            # 10: REQ-010 (delivery status tracking)
            (
                "Implement REQ-010: Real-time delivery status tracking. Status model: "
                "notification_status (notification_id, status ENUM(queued, sending, sent, "
                "delivered, read, failed), timestamp, metadata JSONB). Status transitions: "
                "queued -> sending -> sent -> delivered -> read (happy path), "
                "any -> failed (error path). Webhook callbacks: POST to registered URL "
                "when status changes, with payload { notification_id, old_status, "
                "new_status, timestamp, error_code (if failed), device_info }. "
                "Webhook registration: POST /api/v1/webhooks/delivery-status with "
                "{ url, secret, events: ['sent', 'delivered', 'read', 'failed'] }. "
                "Real-time WebSocket feed: subscribe to status updates for specific "
                "notification_ids via ws://host/status?ids=a,b,c. Retry failed webhooks "
                "3 times with exponential backoff."
            ),
            # 11: REQ-011 (graceful degradation)
            (
                "Implement REQ-011: Graceful degradation for push service outages. "
                "Circuit breaker pattern: per-service (APNs, FCM) circuit breaker with "
                "states (closed, open, half-open). Thresholds: open after 50% failure "
                "rate in 60-second window (min 10 requests), half-open after 30s, "
                "close after 5 consecutive successes. When circuit is open: (1) Queue "
                "notifications to retry buffer (Redis sorted set, score = timestamp), "
                "(2) Attempt alternative channels (email, SMS) for critical priority, "
                "(3) Notify ops team via PagerDuty, (4) Update /health/ready to report "
                "degraded status. Recovery: when circuit closes, drain retry buffer "
                "(oldest first, rate-limited to 50% of normal throughput to prevent "
                "thundering herd). Monitoring: circuit_breaker_state gauge, "
                "fallback_delivery_count counter, retry_buffer_depth gauge."
            ),
            # 12: REQ-012 (A/B testing)
            (
                "Implement REQ-012: A/B testing for notification content. Experiment "
                "model: notification_experiments (id, name, status ENUM(draft, active, "
                "completed, cancelled), start_date, end_date, variants JSONB, "
                "audience_filter JSONB, metrics JSONB). Variant definition: "
                "{ variant_id: 'A', weight: 0.5, template_id: 'tmpl-1', "
                "template_vars_override: {} }. Audience assignment: deterministic hash "
                "(MD5(user_id + experiment_id) mod 100) mapped to variant weights. "
                "Ensures same user always gets same variant. Metrics collection: "
                "per-variant delivery_rate, open_rate, click_rate, conversion_rate. "
                "Statistical analysis: chi-squared test for proportions, require p < 0.05 "
                "and minimum 1000 deliveries per variant before declaring winner. "
                "API: CRUD for experiments, GET /experiments/:id/results for live metrics."
            ),
            # 13-19: Integration, testing, deployment
            (
                "Integration test suite: Write end-to-end tests for the notification "
                "system. Test scenarios: (1) Send critical notification -> verify delivery "
                "within 500ms (REQ-001), (2) Connect 100 WebSocket clients -> broadcast -> "
                "verify all receive within 1s (REQ-002), (3) Kill the worker mid-delivery -> "
                "restart -> verify notification is retried and delivered (REQ-003), "
                "(4) Send mixed priority notifications -> verify ordering matches priority "
                "(REQ-004), (5) Send notification -> query via API -> verify persistence "
                "(REQ-005), (6) Set DND -> send normal notification -> verify queued, "
                "send critical -> verify delivered immediately (REQ-006). Use testcontainers "
                "for PostgreSQL, Redis, and mock push services."
            ),
            (
                "Security audit for the notification system. Check: (1) All API endpoints "
                "require authentication (API key or JWT), (2) Rate limiting enforced on all "
                "endpoints, (3) Notification body encryption verified (read from DB directly, "
                "confirm ciphertext), (4) TLS 1.3 only (reject TLS 1.2 and below), "
                "(5) WebSocket connections authenticated on handshake, (6) Template variable "
                "interpolation does not allow code injection (test with {{ __import__('os') }}), "
                "(7) User can only query own notifications (verify IDOR protection), "
                "(8) Admin endpoints restricted to admin role only, (9) Webhook URLs "
                "validated (no private IPs, no localhost, SSRF protection), (10) API keys "
                "are revocable and audited."
            ),
            (
                "Performance optimization for the notification system. Profile and optimize: "
                "(1) Database: EXPLAIN ANALYZE on the 5 most common queries. Add missing "
                "indexes. Consider partial indexes for unread_only queries. (2) Redis: "
                "monitor memory usage, configure maxmemory with allkeys-lru eviction. "
                "Use pipelining for batch operations. (3) WebSocket: implement message "
                "compression (permessage-deflate). Use binary frames for structured data. "
                "(4) Push delivery: batch APNs requests (up to 100 per HTTP/2 connection). "
                "Use FCM topic messaging for broadcast scenarios. (5) Serialization: "
                "replace json.dumps with orjson for 3x speedup. (6) Connection pooling: "
                "tune PostgreSQL pool size based on load test results."
            ),
            (
                "Monitoring and alerting setup for the notification system. Prometheus "
                "metrics: notification_delivery_latency_seconds (histogram, labels: "
                "channel, priority), notification_delivery_total (counter, labels: "
                "channel, priority, status), websocket_connections_active (gauge), "
                "notification_queue_depth (gauge, labels: priority), "
                "circuit_breaker_state (gauge, labels: service). Grafana dashboards: "
                "(1) Overview: delivery rate, latency p50/p95/p99, error rate, active "
                "connections. (2) Per-channel breakdown. (3) A/B experiment results. "
                "Alerts: delivery_error_rate > 1% for 5 min -> warning, > 5% -> critical. "
                "queue_depth > 10000 -> warning. websocket_connections > 8000 (80% capacity) "
                "-> warning. circuit_breaker open -> critical."
            ),
            (
                "Disaster recovery plan for the notification system. Scenarios: "
                "(1) Database failure: automated failover to read replica (< 30s), "
                "promote replica to primary. RPO: 0 (synchronous replication). "
                "RTO: < 2 minutes. (2) Redis failure: notifications queued in PostgreSQL "
                "fallback queue, delivered when Redis recovers. In-memory WebSocket "
                "connections maintained (no state in Redis for active connections). "
                "(3) Complete datacenter loss: DNS failover to secondary region (< 5 min), "
                "warm standby with cross-region replication. Accept 30s of notification "
                "loss (async replication lag). (4) Push service (APNs/FCM) outage: "
                "circuit breaker + retry buffer (REQ-011). Queue up to 1 million "
                "notifications for 4 hours. (5) DDoS: rate limiting at CDN layer "
                "(Cloudflare), API key revocation, WebSocket connection limits."
            ),
            (
                "Deployment and operations guide. Kubernetes manifests: Deployment "
                "(3 replicas, rolling update strategy, resource limits 512Mi/500m), "
                "Service (ClusterIP), Ingress (TLS termination, WebSocket support via "
                "nginx annotation), HPA (scale on custom metric: queue_depth_per_worker, "
                "target 500), PDB (minAvailable: 2). Helm chart with values for: "
                "replica count, resource limits, Redis/PostgreSQL connection strings, "
                "push service credentials, encryption master key reference, log level. "
                "CI/CD: GitHub Actions pipeline: lint -> test -> build -> push image -> "
                "deploy to staging -> run integration tests -> promote to production. "
                "Canary deployment: 10% traffic for 15 minutes before full rollout. "
                "Rollback: one-click via Helm rollback, automated on error rate > 5%."
            ),
            # 19: Compliance verification
            (
                "Compliance verification matrix: map each requirement (REQ-001 through "
                "REQ-012) to its implementation, tests, and verification evidence. "
                "For each requirement, document: (1) Implementation location (file, "
                "class, method), (2) Unit test coverage (test file, test names), "
                "(3) Integration test coverage, (4) Performance test evidence (latency "
                "numbers, throughput measurements), (5) Security review status. "
                "Create a traceability matrix: each row is a requirement, columns are "
                "design doc section, implementation PR, test PR, review approval, "
                "deployment verification. Flag any requirement that lacks full coverage. "
                "Generate a compliance report suitable for audit: requirement text, "
                "implementation status (complete/partial/not-started), evidence links, "
                "risk assessment for partial implementations, and remediation timeline "
                "for gaps. Include sign-off fields for engineering lead and QA lead."
            ),
        ]
