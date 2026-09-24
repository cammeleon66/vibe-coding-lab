[CmdletBinding()]
param(
    [string]$Subscription = "ME-MngEnvMCAP670682-simonecammel-1",
    [string]$Location = "westeurope",
    [string]$Prefix = "oncology-collab-demo",
    [string]$OwnerEmail = "admin@MngEnvMCAP670682.onmicrosoft.com",
    [int]$BudgetAmount = 35,
    [int]$ExpiryDays = 14,
    [switch]$ResumeAfterBase,
    [switch]$ReuseExistingImage,
    [string]$ApplicationImageTag = "",
    [string]$DemoAccessCode = ""
)

$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repoRoot

function Invoke-AzureCli {
    param([Parameter(Mandatory)][string[]]$Arguments)

    $output = & az @Arguments
    if ($LASTEXITCODE -ne 0) {
        $safeArguments = @(
            foreach ($argument in $Arguments) {
                if (
                    $argument -match
                    "^(eventGridWebhookSecret|demoAccessCode|demoSessionSecret)="
                ) {
                    "$($Matches[1])=<REDACTED>"
                }
                else {
                    $argument
                }
            }
        )
        throw "Azure CLI failed: az $($safeArguments -join ' ')"
    }
    return $output
}

function Invoke-AzureCliJson {
    param([Parameter(Mandatory)][string[]]$Arguments)

    $output = Invoke-AzureCli -Arguments $Arguments
    return ($output -join "`n") | ConvertFrom-Json
}

[void](Invoke-AzureCli -Arguments @("account", "set", "--subscription", $Subscription))
$account = Invoke-AzureCliJson -Arguments @(
    "account", "show", "--query", "{id:id,tenantId:tenantId}", "--output", "json"
)
$today = Get-Date
$expiry = $today.ToUniversalTime().AddDays($ExpiryDays).ToString("yyyy-MM-dd")
$budgetStart = Get-Date -Year $today.Year -Month $today.Month -Day 1
$budgetEnd = $budgetStart.AddYears(1)
$timestamp = $today.ToUniversalTime().ToString("yyyyMMddHHmmss")

Write-Host "Deploying approved base resources to $Subscription ($($account.id))..."
if ($ResumeAfterBase) {
    $baseDeploymentName = (
        @(
            Invoke-AzureCli -Arguments @(
                "deployment", "sub", "list",
                "--query", "sort_by([?starts_with(name, '$Prefix-base-') && properties.provisioningState == 'Succeeded'], &properties.timestamp)[-1].name",
                "--output", "tsv"
            )
        ) -join ""
    ).Trim()
    if ([string]::IsNullOrWhiteSpace($baseDeploymentName)) {
        throw "No successful base deployment exists to resume."
    }
    Write-Host "Reusing successful base deployment $baseDeploymentName."
    $base = Invoke-AzureCliJson -Arguments @(
        "deployment", "sub", "show",
        "--name", $baseDeploymentName,
        "--output", "json"
    )
}
else {
    $base = Invoke-AzureCliJson -Arguments @(
        "deployment", "sub", "create",
        "--name", "$Prefix-base-$timestamp",
        "--location", $Location,
        "--template-file", "$repoRoot\infra\main.bicep",
        "--parameters",
        "location=$Location",
        "prefix=$Prefix",
        "ownerEmail=$OwnerEmail",
        "expiryDate=$expiry",
        "budgetAmount=$BudgetAmount",
        "budgetStartDate=$($budgetStart.ToString('yyyy-MM-dd'))",
        "budgetEndDate=$($budgetEnd.ToString('yyyy-MM-dd'))",
        "--only-show-errors",
        "--output", "json"
    )
}
$outputs = $base.properties.outputs
$platformResourceGroup = $outputs.platformResourceGroupName.value
$milanResourceGroup = $outputs.milanResourceGroupName.value
if ($ResumeAfterBase) {
    $approvedExpiry = (
        Invoke-AzureCli -Arguments @(
            "group", "show",
            "--name", $platformResourceGroup,
            "--query", "tags.ExpiresOn",
            "--output", "tsv"
        )
    ).Trim()
    if ([string]::IsNullOrWhiteSpace($approvedExpiry)) {
        throw "The successful base deployment has no ExpiresOn tag."
    }
    $expiry = $approvedExpiry
    Write-Host "Preserving approved expiry date $expiry."
}
$acrName = $outputs.acrName.value
$acrLoginServer = $outputs.acrLoginServer.value
$imageTag = if ([string]::IsNullOrWhiteSpace($ApplicationImageTag)) {
    (git rev-parse --short HEAD).Trim()
}
else {
    $ApplicationImageTag.Trim()
}
$image = "$acrLoginServer/$Prefix`:$imageTag"

Write-Host "Building the application image in Azure Container Registry..."
if ($ReuseExistingImage) {
    $existingTag = (
        @(
            Invoke-AzureCli -Arguments @(
                "acr", "repository", "show-tags",
                "--name", $acrName,
                "--repository", $Prefix,
                "--query", "[?@ == '$imageTag'] | [0]",
                "--output", "tsv",
                "--only-show-errors"
            )
        ) -join ""
    ).Trim()
    if ($existingTag -ne $imageTag) {
        throw "Image $Prefix`:$imageTag does not exist in $acrName."
    }
    Write-Host "Reusing existing image $image."
}
else {
    $previousRunId = (
        @(
            Invoke-AzureCli -Arguments @(
                "acr", "task", "list-runs",
                "--registry", $acrName,
                "--query", "[0].runId",
                "--output", "tsv",
                "--only-show-errors"
            )
        ) -join ""
    ).Trim()
    $build = Invoke-AzureCliJson -Arguments @(
        "acr", "build",
        "--registry", $acrName,
        "--image", "$Prefix`:$imageTag",
        "--file", "$repoRoot\Dockerfile",
        $repoRoot,
        "--no-logs",
        "--no-wait",
        "--only-show-errors",
        "--output", "json"
    )
    $runId = $build.runId
    if ([string]::IsNullOrWhiteSpace($runId)) {
        for ($attempt = 1; $attempt -le 12; $attempt++) {
            $runId = (
                @(
                    Invoke-AzureCli -Arguments @(
                        "acr", "task", "list-runs",
                        "--registry", $acrName,
                        "--query", "[0].runId",
                        "--output", "tsv",
                        "--only-show-errors"
                    )
                ) -join ""
            ).Trim()
            if (
                -not [string]::IsNullOrWhiteSpace($runId) -and
                $runId -ne $previousRunId
            ) {
                break
            }
            Start-Sleep -Seconds 5
        }
    }
    if ([string]::IsNullOrWhiteSpace($runId) -or $runId -eq $previousRunId) {
        throw "Azure Container Registry did not expose the queued build run ID."
    }
    do {
        Start-Sleep -Seconds 10
        $buildStatus = (
            Invoke-AzureCli -Arguments @(
                "acr", "task", "show-run",
                "--registry", $acrName,
                "--run-id", $runId,
                "--query", "status",
                "--output", "tsv",
                "--only-show-errors"
            )
        ).Trim()
        Write-Host "ACR build $runId status: $buildStatus"
    } while ($buildStatus -in @("Queued", "Started", "Running"))
    if ($buildStatus -ne "Succeeded") {
        throw "ACR build $runId finished with status $buildStatus."
    }
}

$secretBytes = New-Object byte[] 32
[Security.Cryptography.RandomNumberGenerator]::Fill($secretBytes)
$eventGridSecret = [Convert]::ToBase64String($secretBytes)
$sessionSecretBytes = New-Object byte[] 32
[Security.Cryptography.RandomNumberGenerator]::Fill($sessionSecretBytes)
$demoSessionSecret = [Convert]::ToBase64String($sessionSecretBytes)
if ([string]::IsNullOrWhiteSpace($DemoAccessCode)) {
    $accessCodeBytes = New-Object byte[] 8
    [Security.Cryptography.RandomNumberGenerator]::Fill($accessCodeBytes)
    $DemoAccessCode = "EURO-" + [Convert]::ToHexString($accessCodeBytes)
}

Write-Host "Deploying the Container App..."
$blobContributorRole = "Storage Blob Data Contributor"
$temporaryAssignments = @()
try {
    foreach ($accountName in @($outputs.milanAccountName.value, $outputs.utrechtAccountName.value)) {
        $scope = (
            Invoke-AzureCli -Arguments @(
                "storage", "account", "show",
                "--name", $accountName,
                "--query", "id",
                "--output", "tsv"
            )
        ).Trim()
        $assignment = Invoke-AzureCliJson -Arguments @(
            "role", "assignment", "create",
            "--assignee-object-id", $outputs.identityPrincipalId.value,
            "--assignee-principal-type", "ServicePrincipal",
            "--role", $blobContributorRole,
            "--scope", $scope,
            "--only-show-errors",
            "--output", "json"
        )
        $temporaryAssignments += $assignment.id
    }
    Start-Sleep -Seconds 60
    $app = Invoke-AzureCliJson -Arguments @(
        "deployment", "group", "create",
        "--name", "$Prefix-app-$timestamp",
        "--resource-group", $platformResourceGroup,
        "--template-file", "$repoRoot\infra\application.bicep",
        "--parameters",
        "prefix=$Prefix",
        "image=$image",
        "acrLoginServer=$acrLoginServer",
        "environmentName=$($outputs.environmentName.value)",
        "identityResourceId=$($outputs.identityResourceId.value)",
        "identityClientId=$($outputs.identityClientId.value)",
        "insightsName=$($outputs.insightsName.value)",
        "milanAccountUrl=$($outputs.milanAccountUrl.value)",
        "utrechtAccountUrl=$($outputs.utrechtAccountUrl.value)",
        "sharedAccountUrl=$($outputs.sharedAccountUrl.value)",
        "eventGridWebhookSecret=$eventGridSecret",
        "demoAccessCode=$DemoAccessCode",
        "demoSessionSecret=$demoSessionSecret",
        "ownerEmail=$OwnerEmail",
        "expiryDate=$expiry",
        "seedSyntheticFixtures=true",
        "--only-show-errors",
        "--output", "json"
    )

    $fqdn = $app.properties.outputs.fqdn.value
    $appName = $app.properties.outputs.applicationName.value
    $applicationUrl = "https://$fqdn"
    [void](Invoke-AzureCli -Arguments @(
        "containerapp", "auth", "update",
        "--resource-group", $platformResourceGroup,
        "--name", $appName,
        "--enabled", "false",
        "--yes",
        "--only-show-errors",
        "--output", "none"
    ))
    $ready = $false
    for ($attempt = 1; $attempt -le 30; $attempt++) {
        $preflightDetail = "not reachable"
        try {
            $demoWebSession = New-Object Microsoft.PowerShell.Commands.WebRequestSession
            [void](Invoke-RestMethod `
                -Uri "$applicationUrl/api/demo-access" `
                -Method Post `
                -ContentType "application/json" `
                -Body (@{ code = $DemoAccessCode } | ConvertTo-Json -Compress) `
                -WebSession $demoWebSession `
                -TimeoutSec 20)
            $preflight = Invoke-RestMethod `
                -Uri "$applicationUrl/api/preflight" `
                -WebSession $demoWebSession `
                -TimeoutSec 20
            if ($preflight.ready) {
                $ready = $true
                break
            }
            $failedChecks = @(
                $preflight.checks |
                    Where-Object { $_.required -and $_.status -ne "pass" } |
                    ForEach-Object { "$($_.id): $($_.detail)" }
            )
            $preflightDetail = $failedChecks -join "; "
        }
        catch {
            $preflightDetail = $_.Exception.Message
        }
        if ($attempt -lt 30) {
            Write-Host "Preflight attempt $attempt not ready: $preflightDetail"
            Start-Sleep -Seconds 10
        }
    }
    if (-not $ready) {
        throw "The private-networked Container App did not pass preflight."
    }
    [void](Invoke-AzureCli -Arguments @(
        "containerapp", "update",
        "--resource-group", $platformResourceGroup,
        "--name", $appName,
        "--set-env-vars", "SEED_AZURE_FIXTURES=false",
        "--only-show-errors",
        "--output", "none"
    ))
}
finally {
    foreach ($assignmentId in $temporaryAssignments) {
        [void](Invoke-AzureCli -Arguments @(
            "role", "assignment", "delete", "--ids", $assignmentId, "--only-show-errors"
        ))
    }
}

Write-Host "Creating the Event Grid evidence-delivery subscription..."
$milanStorageId = (
    Invoke-AzureCli -Arguments @(
        "storage", "account", "show",
        "--name", $outputs.milanAccountName.value,
        "--query", "id",
        "--output", "tsv"
    )
).Trim()
$systemTopics = Invoke-AzureCliJson -Arguments @(
    "eventgrid", "system-topic", "list",
    "--resource-group", $milanResourceGroup,
    "--output", "json"
)
$systemTopicName = @(
    $systemTopics |
        Where-Object { $_.source -eq $milanStorageId } |
        Select-Object -First 1 -ExpandProperty name
)[0]
if ([string]::IsNullOrWhiteSpace($systemTopicName)) {
    $systemTopicName = "$Prefix-milan-source"
    [void](Invoke-AzureCli -Arguments @(
        "eventgrid", "system-topic", "create",
        "--resource-group", $milanResourceGroup,
        "--name", $systemTopicName,
        "--source", $milanStorageId,
        "--topic-type", "Microsoft.Storage.StorageAccounts",
        "--location", $Location,
        "--only-show-errors",
        "--output", "none"
    ))
}
else {
    Write-Host "Reusing existing storage system topic $systemTopicName."
}
[void](Invoke-AzureCli -Arguments @(
    "deployment", "group", "create",
    "--name", "$Prefix-events-$timestamp",
    "--resource-group", $milanResourceGroup,
    "--template-file", "$repoRoot\infra\event-grid.bicep",
    "--parameters",
    "systemTopicName=$systemTopicName",
    "endpointUrl=$applicationUrl/api/event-grid/evidence-arrivals",
    "eventGridWebhookSecret=$eventGridSecret",
    "--only-show-errors",
    "--output", "none"
))

Write-Host "Verifying the complete Azure rehearsal through Event Grid..."
& "$repoRoot\.venv\Scripts\python.exe" "$repoRoot\scripts\verify_azure_rehearsal.py" `
    --base-url $applicationUrl `
    --access-code $DemoAccessCode
if ($LASTEXITCODE -ne 0) {
    throw "The deployed Azure rehearsal failed end-to-end verification."
}

$displayName = "$Prefix-presenter"
$existingAppId = (
    @(
        Invoke-AzureCli -Arguments @(
            "ad", "app", "list",
            "--display-name", $displayName,
            "--query", "[0].appId",
            "--output", "tsv"
        )
    ) -join ""
).Trim()
if (-not [string]::IsNullOrWhiteSpace($existingAppId)) {
    [void](Invoke-AzureCli -Arguments @(
        "ad", "app", "delete",
        "--id", $existingAppId,
        "--only-show-errors"
    ))
}

Write-Host "Azure deployment complete: $applicationUrl"
Write-Host "Shared demo access code: $DemoAccessCode"
Write-Host "Expiry tag: $expiry. Fabric and Azure OpenAI remain disabled."
