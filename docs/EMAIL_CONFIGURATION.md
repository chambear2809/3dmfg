# Email Configuration

FilaOps can send transactional emails for password resets and notifications.

## Environment Variables

Add to your `.env` file:

```ini
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=noreply@yourcompany.com
SMTP_FROM_NAME=Your Company Name
SMTP_TLS=true
```

## Gmail Setup

1. Enable 2-Factor Authentication on your Google account
2. Generate an App Password: <https://myaccount.google.com/apppasswords>
3. Use the App Password (not your regular password) for SMTP_PASSWORD

## Disabling Email

If SMTP is not configured, FilaOps will:
- Keep password reset requests pending without sending email
- Require manual admin recovery unless you explicitly enable the dev-only
  `ALLOW_INSECURE_PASSWORD_RESET_WITHOUT_SMTP=true` override outside production

For a full description of how password resets work with and without SMTP, see [First-Run Setup and Password Reset](FIRST-RUN-SETUP.md#password-reset-flow).
