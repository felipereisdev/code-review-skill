# Terraform / Infrastructure as Code — Code Review Checklist

- **No accidental destruction**: `terraform plan` output reviewed; no unexpected `destroy` or replacement operations
- **State locking**: remote state backend configured with locking to prevent concurrent modifications
- **Versioned modules**: module sources pinned to a specific version or commit, not a mutable branch
- **Sensitive outputs**: sensitive values marked with `sensitive = true`; not logged in CI output
- **Least privilege**: IAM roles and policies grant only the permissions required
- **Resource naming**: resources follow a consistent naming convention that includes environment

## Precedents

- **References order resources**: Terraform creates a resource after every resource whose attributes it references. Do not report a missing `depends_on` when one resource references the other. **Exception:** dependencies that no reference expresses, such as an IAM policy attachment that must exist before a function using that role runs.
- **`sensitive = true` hides values in plan and apply output**: Terraform redacts sensitive variables and outputs in the human-readable output of `terraform plan` and `terraform apply`. Do not report those values as printed in CI logs by `plan` or `apply`. **Exception:** `terraform output` run for a named output or with `-raw` or `-json`, `terraform show -json` and other machine-readable plan or state output, the state file, which stores them in plain text, values passed through `nonsensitive()`, values that a provisioner, `local-exec` command or external script prints, and runs with `TF_LOG` or `TF_LOG_PROVIDER` set to `DEBUG` or `TRACE`, whose logs can include sensitive values.
- **New S3 buckets are private and encrypted by default**: since 2023, AWS turns on Block Public Access, disables ACLs and encrypts objects with SSE-S3 for buckets created in an AWS account. Do not report an `aws_s3_bucket` that this configuration creates on AWS, without encryption or public-access resources, as public or unencrypted. **Exception:** a bucket brought under management with `terraform import` or an `import` block, which may predate the defaults, an S3-compatible endpoint such as MinIO, LocalStack or R2, which does not apply the AWS defaults, an `aws_s3_bucket_public_access_block` that sets any option to `false`, a bucket policy or ACL that grants access to everyone, and requirements for KMS-managed keys.
