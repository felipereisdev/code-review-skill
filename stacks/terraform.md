# Terraform / Infrastructure as Code — Code Review Checklist

- **No accidental destruction**: `terraform plan` output reviewed; no unexpected `destroy` or replacement operations
- **State locking**: remote state backend configured with locking to prevent concurrent modifications
- **Versioned modules**: module sources pinned to a specific version or commit, not a mutable branch
- **Sensitive outputs**: sensitive values marked with `sensitive = true`; not logged in CI output
- **Least privilege**: IAM roles and policies grant only the permissions required
- **Resource naming**: resources follow a consistent naming convention that includes environment
