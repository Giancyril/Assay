# scripts/commit-stage.ps1
param (
    [Parameter(Mandatory=$true)]
    [string]$Message
)
git add -A
git commit -m "$Message"
