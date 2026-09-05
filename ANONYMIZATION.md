# Anonymization Checklist

Use this checklist before sharing the artifact link during review.

## Files intentionally excluded

- Paper source files such as `main.tex` and `sections/`.
- Generated paper PDFs.
- LaTeX build outputs.
- Private notes and email drafts.
- Local `.env` files.

## Terms to hide if using an anonymization proxy

If using a service such as Anonymous GitHub, include author-identifying terms in
the replacement list. For this artifact, the repository itself should already
avoid such terms, but the following categories should still be checked:

- author names
- author email addresses
- institution names
- company names
- GitHub usernames
- local machine usernames
- internal project or system names

## Manual verification commands

From the repository root, run:

```sh
rg -n "AUTHOR_NAME|AUTHOR_EMAIL|INSTITUTION|COMPANY|LOCAL_USERNAME"
```

Replace the placeholders with the actual identifying terms that should not
appear in the anonymous artifact.

Also confirm that no API key appears:

```sh
rg -n "sk-ant|ANTHROPIC_API_KEY|api[_-]?key|secret|token"
```

The only expected match should be the placeholder in `.env.example` or
documentation telling users not to commit secrets.
