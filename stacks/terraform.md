# Terraform / Infrastructure as Code — Code Review Checklist

> Check sibling modules for existing patterns before flagging a convention (see Consistency Check step). Report an item only with a concrete trigger → effect in the changed code. A problem that `terraform validate`, TFLint, or a scanner such as Checkov, tfsec or Trivy configured in the repository already reports is not a finding. Read the Terraform version from `required_version` and the provider versions from `required_providers` and `.terraform.lock.hcl`; an item that depends on a version names it. When the change comes with a plan, the plan shows the effect; otherwise reason from the configuration and say what the finding depends on.

## State and Secrets

- **Secrets stored in state**: Terraform stores the values of resource arguments and outputs in the state and plan files in plain text, including values marked `sensitive`, so anyone who can read the state can read the database passwords and keys in it. Report a change that adds such a value while the state is readable by more people than the operators, for example a committed `*.tfstate` file, a local backend in a CI job that uploads its workspace, or a backend bucket that the change makes widely readable. **Not a finding:** write-only arguments (Terraform 1.11+, such as `password_wo` on `aws_db_instance`) and ephemeral values (Terraform 1.10+), which Terraform does not store in state or plan files.
- **State without locking**: the `s3` backend locks the state only when `use_lockfile = true` (or the deprecated `dynamodb_table`) is set. Without a lock, two runs that apply at the same time, such as two CI pipelines, can overwrite each other's state and lose track of the resources that one of them created. **Not a finding:** backends that lock without extra arguments, such as `gcs`, `azurerm` and HCP Terraform, and a single runner that the repository configures to apply one run at a time.

## Destruction and Replacement

- **Changed resource addresses**: renaming a resource or module block, moving a resource into or out of a module, or switching between `count` and `for_each` changes the address of each instance. Without a `moved` block (Terraform 1.1+), Terraform plans to destroy the object at the old address and create a new one. That replaces the object's identity and anything that other systems refer to by ID. Data is lost only when the destroy succeeds and no guard keeps it: a database, volume or bucket with effective provider-side deletion protection, or a non-empty bucket without `force_destroy`, makes the apply fail instead, and a provider's final snapshot or backup can preserve the data. `prevent_destroy` protects only while its lifecycle rule is effective for the instance being destroyed. Terraform does not record it in state, and a block that is renamed or removed takes its rule with it, so a `prevent_destroy` on the new block does not protect the object at the old address. Add a `moved` block from each old address to the new one. **Not a finding:** a `moved` block that already covers the change.
- **`count` over a list**: instances of a resource with `count` are identified by their index, so removing an element from the middle of the list moves every later element to a lower index. Terraform then plans to change each later instance to the arguments of the next element (replacing those whose changed argument forces replacement) and to destroy the last one. Use `for_each` over a set or map keyed by a stable value. **Not a finding:** `count` as an on/off switch (`count = var.enabled ? 1 : 0`) and lists that only grow at the end.
- **Replacement of resources that hold data**: changing an argument that the provider cannot update in place (the plan marks it `# forces replacement`) destroys and recreates the object. Report it for a resource that holds data or that clients reach by a fixed name or address, when the change has no migration or backup step. `lifecycle { prevent_destroy = true }` makes Terraform reject a plan that destroys such an object, so the run fails rather than losing data, but it does not stop a plan that removes the resource block from the configuration; a rejected migration is still a broken change, not an irreversible loss; `create_before_destroy` fails for resource types that require unique names when the name does not change.

**Bad** — renaming the block from `aws_ebs_volume.data` makes Terraform destroy the volume, with its data, and create an empty one:

```hcl
resource "aws_ebs_volume" "orders_data" {
  availability_zone = "eu-west-1a"
  size              = 200
  type              = "gp3"
}
```

**Good** — the `moved` block tells Terraform that the existing volume now has a new address:

```hcl
resource "aws_ebs_volume" "orders_data" {
  availability_zone = "eu-west-1a"
  size              = 200
  type              = "gp3"
}

moved {
  from = aws_ebs_volume.data
  to   = aws_ebs_volume.orders_data
}
```

**Bad** — removing `"orders"` from the list makes Terraform plan to replace `this[0]` and `this[1]` with the next names and to destroy `this[2]`:

```hcl
variable "queues" {
  type    = list(string)
  default = ["orders", "payments", "emails"]
}

resource "aws_sqs_queue" "this" {
  count = length(var.queues)
  name  = "acme-${var.queues[count.index]}"
}
```

**Good** — each queue is keyed by its name, so removing one name destroys only that queue (when existing instances move from `count`, add a `moved` block from each index to its key):

```hcl
variable "queues" {
  type    = set(string)
  default = ["orders", "payments", "emails"]
}

resource "aws_sqs_queue" "this" {
  for_each = var.queues
  name     = "acme-${each.key}"
}
```

## Providers and Modules

- **Floating module sources**: the dependency lock file records provider versions, not module versions. A registry module without `version`, or a Git source without `ref`, gets the newest release or the default branch on every `terraform init`, so a fresh CI checkout can apply module changes that nobody reviewed. **Not a finding:** local path modules (`./modules/network`), and a version constraint, which limits upgrades to the versions it allows.
- **Dependency lock file removed**: deleting `.terraform.lock.hcl` from version control, or ignoring it, in a root configuration that is planned or applied (including test and example roots that run `terraform init`) lets every `terraform init` there select the newest provider version that matches the constraints, so a new provider release can change the next plan without any change in the repository. The lock file belongs to the root configuration, not to a reusable child module. **Not a finding:** a lock file beside a child module that no planned or applied root uses, since the callers' root configurations select the providers.

## Access and Exposure

- **Wildcard IAM permissions**: a policy that the change creates or widens with `"Action": "*"` or a service wildcard such as `"s3:*"` on `"Resource": "*"`, attached to a role that runs application code (a Lambda function, an ECS task or an EC2 instance profile), gives whoever controls that code every action that the wildcard covers, including ones added to AWS later, unless the effective policy evaluation blocks it. The effective permissions are the intersection of identity-based policies with any permissions boundary, session policy and applicable SCP, and an explicit deny in any of them overrides an allow. An applicable SCP is not a deny by itself: an SCP that allows the claimed action, like a boundary that exists, blocks it only when it excludes or denies that action or resource. Report the concrete action or resource that remains allowed after those apply. **Not a finding:** administrator roles that only people assume, when the repository documents that purpose.
- **Ingress open to the internet**: a security group rule that allows `0.0.0.0/0` or `::/0` to a database, cache, SSH or RDP port exposes that service to the internet when the resource also has a public address. **Not a finding:** ports of a public load balancer or web server, and resources without a public address or route from the internet.

## Conventions, not defects

- Resource naming schemes, tags, file layout and the choice between `jsonencode` and `aws_iam_policy_document` follow the repository's conventions; they are findings only when a name or tag that another system depends on changes.
- Reviewing plan output is a process step, not a code finding; report the concrete destroy or replace risk from the items above instead.

## Sources

- Sensitive data, ephemeral values and write-only arguments: https://developer.hashicorp.com/terraform/language/manage-sensitive-data, https://developer.hashicorp.com/terraform/language/manage-sensitive-data/write-only
- Backend locking: https://developer.hashicorp.com/terraform/language/backend/s3, https://developer.hashicorp.com/terraform/language/backend/gcs, https://developer.hashicorp.com/terraform/language/backend/azurerm
- `moved` blocks: https://developer.hashicorp.com/terraform/language/modules/develop/refactoring
- `count` and `for_each`: https://developer.hashicorp.com/terraform/language/meta-arguments/count, https://developer.hashicorp.com/terraform/language/meta-arguments/for_each
- `prevent_destroy` and `create_before_destroy`: https://developer.hashicorp.com/terraform/language/meta-arguments/lifecycle
- Dependency lock file: https://developer.hashicorp.com/terraform/language/files/dependency-lock; module sources: https://developer.hashicorp.com/terraform/language/modules/sources
- IAM least privilege: https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html; effective permissions with boundaries, SCPs and explicit denies: https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_boundaries.html#access_policies_boundaries-eval-logic; security groups: https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html

## Precedents

- **References order resources**: Terraform creates a resource after every resource whose attributes it references. Do not report a missing `depends_on` when one resource references the other. **Exception:** dependencies that no reference expresses, such as an IAM policy attachment that must exist before a function using that role runs.
- **`sensitive = true` hides values in plan and apply output**: Terraform redacts sensitive variables and outputs in the human-readable output of `terraform plan` and `terraform apply`. Do not report those values as printed in CI logs by `plan` or `apply`. **Exception:** `terraform output` run for a named output or with `-raw` or `-json`, `terraform show -json` and other machine-readable plan or state output, the state file, which stores them in plain text, values passed through `nonsensitive()`, values that a provisioner, `local-exec` command or external script prints, and runs with `TF_LOG` or `TF_LOG_PROVIDER` set to `DEBUG` or `TRACE`, whose logs can include sensitive values.
- **New S3 buckets are private and encrypted by default**: since 2023, AWS turns on Block Public Access, disables ACLs and encrypts objects with SSE-S3 for buckets created in an AWS account. Do not report an `aws_s3_bucket` that this configuration creates on AWS, without encryption or public-access resources, as public or unencrypted. **Exception:** a bucket brought under management with `terraform import` or an `import` block, which may predate the defaults, an S3-compatible endpoint such as MinIO, LocalStack or R2, which does not apply the AWS defaults, an `aws_s3_bucket_public_access_block` that sets any option to `false`, a bucket policy or ACL that grants access to everyone, and requirements for KMS-managed keys.
