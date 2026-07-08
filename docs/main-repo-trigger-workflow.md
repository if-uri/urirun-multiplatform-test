# Main Repository Trigger Workflow

Copy this workflow into the main `if-uri/urirun` repository when you want a
successful main-repo build to trigger this external black-box harness.

The workflow calls `repository_dispatch` on
`if-uri/urirun-multiplatform-test` and passes the exact commit SHA being tested.
It does not copy files from the main repository. The harness clones and installs
`urirun` by using the payload values as `URIRUN_REPO_URL` and `URIRUN_REF`.

```yaml
name: trigger multiplatform smoke

on:
  workflow_run:
    workflows:
      - ci
    types:
      - completed
  workflow_dispatch:

jobs:
  trigger:
    if: github.event_name == 'workflow_dispatch' || github.event.workflow_run.conclusion == 'success'
    runs-on: ubuntu-latest
    permissions:
      contents: read

    steps:
      - name: Trigger urirun multiplatform harness
        env:
          GH_TOKEN: ${{ secrets.URIRUN_MULTIPLATFORM_TEST_TOKEN }}
          TARGET_REPO: if-uri/urirun-multiplatform-test
          URIRUN_REPO_URL: https://github.com/if-uri/urirun.git
          URIRUN_REF: ${{ github.event.workflow_run.head_sha || github.sha }}
        run: |
          gh api \
            --method POST \
            -H "Accept: application/vnd.github+json" \
            /repos/$TARGET_REPO/dispatches \
            -f event_type=urirun-main-ci \
            -f client_payload[urirun_repo_url]="$URIRUN_REPO_URL" \
            -f client_payload[urirun_ref]="$URIRUN_REF" \
            -f client_payload[sha]="$URIRUN_REF" \
            -f client_payload[get_urirun_site_mode]=production-site \
            -f client_payload[allow_remote_install]=false
```

Required secret:

- `URIRUN_MULTIPLATFORM_TEST_TOKEN` - a fine-grained GitHub token that can call
  repository dispatch on `if-uri/urirun-multiplatform-test`.

The triggered run executes:

- `linux-docker / ubuntu-latest`
- `windows-runner / windows-latest`
- `macos-runner / macos-latest`
- `linux-installer-gui / ubuntu-latest`
- `windows-installer-gui / windows-latest`
- `macos-installer-gui / macos-latest`

Keep `allow_remote_install=false` unless the trigger runs in a trusted release
environment where executing remote installer scripts is explicitly allowed.
