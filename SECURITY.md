# Security Policy

## Overview

This document outlines security best practices and guidelines for the SAP RAG Chat Application. All contributors must follow these guidelines to maintain the security and integrity of the project.

## Reporting Security Issues

If you discover a security vulnerability in this project, please report it immediately:

1. **Do not** open a public issue on GitHub
2. **Do** send an email to the maintainers with details of the vulnerability
3. **Do** include steps to reproduce the vulnerability
4. **Do** include the impact and potential mitigation if known

## Security Best Practices

### Secrets Management

**Never commit secrets to version control.** This includes:

- API keys (Mistral, GCP, or any other service)
- Passwords and credentials
- Private encryption keys
- Service account JSON files
- Database connection strings
- Any other sensitive authentication material

#### ✅ Do:

- Use environment variables for all secrets
- Use `.env.example` to document required variables (with placeholder values)
- Add `.env` to `.gitignore`
- Use secret management services (GCP Secret Manager, AWS Secrets Manager, etc.) for production
- Use Pydantic's `SecretStr` type for sensitive fields

#### ❌ Don't:

- Hardcode secrets in source files
- Commit `.env` files
- Use default/fallback values that are real secrets
- Log sensitive information
- Store secrets in client-side code

### Environment Variables

All configuration that varies between environments (development, staging, production) should be managed through environment variables.

**Required variables (see `.env.example` for template):**

```bash
# GCP Configuration
GCP_PROJECT=your-gcp-project
BQ_DATASET=your-dataset
BUCKET=your-bucket-name
GCP_SA_KEY_BASE64=your-base64-encoded-service-account-key

# Mistral Configuration
MISTRAL_API_KEY=your-mistral-api-key
MISTRAL_BASE_URL=http://localhost:11434/v1  # Optional for local

# Application Configuration
APP_HOST=127.0.0.1
APP_PORT=8000
DEBUG=false
```

### Authentication

- **GCP**: Use Application Default Credentials (ADC) or service account keys via environment variables
- **Mistral**: API key via environment variable
- **Never** embed authentication tokens in client-side code

### Dependency Security

- Regularly update dependencies to patch known vulnerabilities
- Use `uv lock` to update lock files when dependencies change
- Review dependency changes before merging PRs
- Prefer well-maintained, popular packages

### Code Security

- Validate all external inputs (API requests, user input, etc.)
- Use type hints and Pydantic validation for data structures
- Sanitize outputs to prevent injection attacks
- Use parameterized queries for databases (BigQuery uses parameterized queries)
- Never use string formatting or concatenation for SQL queries

### API Security

- **Rate Limiting**: Consider adding rate limiting for public endpoints
- **CORS**: Currently configured for localhost only - review for production
- **Input Validation**: All API inputs are validated via Pydantic models
- **Error Handling**: Don't expose internal errors to clients
- **Authentication**: Add proper authentication for production deployments

### Data Security

- **Citations**: Ensure all LLM responses include proper source citations
- **Corpus Data**: Documentation data is public SAP content, but ensure no private data is ingested
- **User Data**: Conversation history is client-side only (stateless backend)

## Security Features

### Implemented

1. **Secret Type Safety**: Pydantic `SecretStr` for API keys prevents accidental logging
2. **Environment Configuration**: All secrets loaded from environment variables
3. **Parameterized Queries**: BigQuery client uses parameterized queries with `ML.DISTANCE`
4. **Input Validation**: Pydantic models validate all API inputs
5. **CORS Restrictions**: Limited to localhost origins
6. **Stateless Design**: No server-side session storage, reducing data exposure

### Recommended for Production

1. **Authentication Layer**: Add JWT or OAuth2 authentication
2. **Rate Limiting**: Implement per-user rate limiting
3. **Audit Logging**: Log security-relevant events (without sensitive data)
4. **Secret Rotation**: Implement regular rotation of API keys
5. **DDoS Protection**: Add protection against denial of service attacks
6. **HTTPS**: Always use HTTPS in production

## Pre-commit Hooks

This repository uses pre-commit hooks to prevent accidental secret commits. See `.pre-commit-config.yaml` for configuration.

To install pre-commit hooks:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## Security Checklist for PRs

Before merging a pull request, ensure:

- [ ] No secrets or credentials in code
- [ ] No `.env` files committed
- [ ] Sensitive data properly redacted from logs
- [ ] Dependencies updated and lock files regenerated
- [ ] Input validation added for new API endpoints
- [ ] Error handling doesn't expose sensitive information
- [ ] Pre-commit hooks pass
- [ ] Security review completed for significant changes

## Incident Response

In the event of a security incident:

1. **Containment**: Immediately revoke any compromised credentials
2. **Assessment**: Determine the scope and impact of the incident
3. **Remediation**: Patch the vulnerability
4. **Communication**: Notify affected parties as appropriate
5. **Post-mortem**: Document the incident and lessons learned

## Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [GCP Security Best Practices](https://cloud.google.com/security/best-practices)
- [Python Security](https://wiki.python.org/moin/Security)
- [12 Factor App: Config](https://12factor.net/config)

## License

This security policy is part of the SAP RAG Chat Application project and is provided for informational purposes.
