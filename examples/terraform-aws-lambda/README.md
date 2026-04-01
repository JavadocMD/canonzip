# Terraform AWS Lambda Example

Demonstrates using **canonzip** to deploy an AWS Lambda function with Terraform
such that changes are detected if and only if the source code actually changes.

## Why canonzip?

Standard zip utilities don't always produce the same zip twice.
File timestamp changes or differences in file traversal order can lead
to zip files appearing different even when the content is identical.
Especially if you or your team use different operating systems!

If you are trying to zip the source code of a Lambda function, this can cause
Terraform to think there's always a change and thus redeploy the function
unnecessarily, every time you apply. canonzip eliminates this by guaranteeing
byte-identical zips for identical content.

## Why not Terraform's `archive_file`?

For certain use-cases, archive_file may of course be perfectly fine.
Just make sure to set the `output_file_mode` option in order to ensure
cross-platform repeatability. canonzip does have two unique advantages:
it can leverage your existing gitignore patterns for excludes, and it can
be used outside of Terraform for more involved build scripting. Additionally,
dome projects may benefit from being able to compute hashes without writing
the full zip file, but in a way where the hash and the zip file share similar
identity properties (either they both change or neither does). Whether you
find these features useful is up to you.

## How it works

- `main.tf` is the Terraform file
- `src/handler.py` is the source code for the function

When you apply:

1. The `external` data source runs `canonzip zip --json`, which zips up the
   function code and outputs the hash so it can be read into Terraform state.
2. `aws_lambda_function.source_code_hash` is set to this hash.
   Terraform only plans an update when the hash (and therefore the source)
   truly changed, no matter who computed the hash or when!

## Try it out

You can deploy this yourself to test it, assuming you've installed:

- AWS CLI (and connected it to an AWS account)
- Terraform
- canonzip

In a terminal in this directory, run:

```bash
terraform init
terraform apply
```

You can invoke the function from the AWS Console or from the CLI with:

```bash
aws lambda invoke --function-name canonzip-example --region us-east-1 \
   --output off /dev/stdout
```

(`/dev/stdout` might not work as an output destination for all platforms,
you can also specify a file.)

Run `terraform apply` a second time without editing the source and Terraform
will detect no changes &mdash; nothing to update. But if you can edit
`src/handler.py` and run `terraform apply` again, it will deploy the update.

And of course you can `terraform destroy` when you're done to clean up.
