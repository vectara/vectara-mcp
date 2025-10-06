# Security Policy and Guidelines for Vectara MCP Server

The Vectara trust and security center, including our security policy, can be found at
[https://vectara.com/legal/security-at-vectara/](https://vectara.com/legal/security-at-vectara/).

## Reporting a Vulnerability

Please send security vulnerability reports to security@vectara.com.

---

## MCP Server Security Guidelines

### Overview

The Vectara MCP Server prioritizes security with a "secure by default" approach. This document outlines security best practices, transport layer considerations, and deployment guidelines.

### Transport Security Comparison

#### HTTP/SSE Transport (Default - Recommended)
✅ **Advantages:**
- Transport-layer encryption (HTTPS)
- Bearer token authentication
- Rate limiting protection
- CORS origin validation
- Session management with cryptographic IDs
- Audit logging capabilities

⚠️ **Considerations:**
- Requires proper TLS certificate configuration
- Network-exposed endpoints need firewall rules
- Token management overhead

#### STDIO Transport (Local Development Only)
⚠️ **Security Risks:**
- No transport-layer authentication
- API keys visible in process memory
- Credentials may leak to shell history
- No encryption between processes
- Vulnerable to local privilege escalation

✅ **Acceptable Use Cases:**
- Local development environments
- Claude Desktop (isolated desktop application)
- CI/CD testing pipelines (isolated containers)

### Authentication

#### Bearer Token Authentication (HTTP/SSE)

The server validates bearer tokens from multiple sources:

1. **Authorization Header** (Recommended)
```bash
Authorization: Bearer <token>
```

2. **X-API-Key Header** (Alternative)
```bash
X-API-Key: <token>
```

#### Token Management

```bash
# Primary API key (used for both Vectara API and MCP auth)
export VECTARA_API_KEY="vaa_xxxxxxxxxxxxx"

# Additional authorized tokens (comma-separated)
export VECTARA_AUTHORIZED_TOKENS="token1,token2,token3"
```

#### Disabling Authentication

⚠️ **WARNING**: Never disable authentication in production!

```bash
# Development only - creates security vulnerability
python -m vectara_mcp --no-auth
```

### CORS Configuration

#### Default Configuration
```bash
# Restricts to localhost by default
VECTARA_ALLOWED_ORIGINS="http://localhost:*"
```

#### Production Configuration
```bash
# Whitelist specific domains
VECTARA_ALLOWED_ORIGINS="https://app.example.com,https://admin.example.com"
```

#### Security Headers

The server automatically adds these security headers:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000`
- `Content-Security-Policy: default-src 'self'`

### Rate Limiting

Default: 100 requests per minute per client

The built-in rate limiter prevents:
- DoS attacks
- Resource exhaustion
- API abuse

### Production Deployment Checklist

#### 1. Use HTTPS (Required)

Deploy behind a reverse proxy with TLS:

```nginx
server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Authorization $http_authorization;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### 2. Environment Variables

```bash
# Production environment file (.env.production)
VECTARA_API_KEY="vaa_production_key"
VECTARA_AUTHORIZED_TOKENS="client1_token,client2_token"
VECTARA_ALLOWED_ORIGINS="https://app.example.com"
VECTARA_AUTH_REQUIRED="true"
```

#### 3. Network Security

```bash
# Firewall rules (iptables example)
# Allow HTTPS only
iptables -A INPUT -p tcp --dport 443 -j ACCEPT
# Block direct access to MCP port
iptables -A INPUT -p tcp --dport 8000 -s 127.0.0.1 -j ACCEPT
iptables -A INPUT -p tcp --dport 8000 -j DROP
```

#### 4. Container Security (Docker)

```dockerfile
FROM python:3.11-slim

# Run as non-root user
RUN useradd -m -u 1000 mcp-user
USER mcp-user

# Copy application
WORKDIR /app
COPY --chown=mcp-user:mcp-user . .

# Install dependencies
RUN pip install --user vectara-mcp

# Use secrets at runtime (not build time)
CMD ["python", "-m", "vectara_mcp"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  vectara-mcp:
    image: vectara-mcp:latest
    environment:
      - VECTARA_API_KEY=${VECTARA_API_KEY}
    secrets:
      - vectara_tokens
    ports:
      - "127.0.0.1:8000:8000"
    restart: unless-stopped

secrets:
  vectara_tokens:
    external: true
```

### Common Security Mistakes to Avoid

#### ❌ DON'T: Expose STDIO to Network
```bash
# NEVER DO THIS
socat TCP-LISTEN:8080,fork EXEC:"python -m vectara_mcp --stdio"
```

#### ❌ DON'T: Disable Auth in Production
```bash
# NEVER DO THIS IN PRODUCTION
python -m vectara_mcp --no-auth --host 0.0.0.0
```

#### ❌ DON'T: Store Keys in Code
```python
# NEVER DO THIS
API_KEY = "vaa_hardcoded_key_12345"
```

#### ❌ DON'T: Use Wildcard CORS
```bash
# AVOID THIS
VECTARA_ALLOWED_ORIGINS="*"
```

### Security Incident Response

If you suspect a security breach:

1. **Immediately rotate all API keys**
```bash
# Revoke compromised keys in Vectara Console
# Generate new keys
# Update VECTARA_API_KEY and VECTARA_AUTHORIZED_TOKENS
```

2. **Review audit logs**
```bash
grep "401\|403" /var/log/vectara-mcp/audit.log
```

3. **Check for unauthorized access**
```bash
# Review unique IPs
awk '{print $1}' access.log | sort -u
```

4. **Update and patch**
```bash
pip install --upgrade vectara-mcp
```

### Compliance Considerations

#### Data Privacy
- No user queries or responses are stored by default
- API keys are only held in memory (not persisted)
- No telemetry or analytics collection

#### Regulatory Compliance
- Supports audit logging for compliance requirements
- Compatible with SOC2, HIPAA deployment patterns
- Allows data residency configuration via corpus selection

### Regular Security Maintenance

#### Weekly
- Review authentication logs
- Check for unusual access patterns
- Verify rate limiting is functioning

#### Monthly
- Rotate API tokens
- Update dependencies: `pip list --outdated`
- Review CORS and firewall rules

#### Quarterly
- Security audit of deployment
- Penetration testing (if applicable)
- Update TLS certificates before expiry

### Additional Resources

- [OWASP Security Guidelines](https://owasp.org/)
- [MCP Security Best Practices](https://modelcontextprotocol.io/docs/concepts/security)
- [Vectara Security Documentation](https://docs.vectara.com/docs/learn/security)

---

Remember: Security is not a one-time configuration but an ongoing process. Stay vigilant and keep your systems updated.