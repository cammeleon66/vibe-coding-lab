[CmdletBinding()]
param(
    [string]$Subscription = "ME-MngEnvMCAP670682-simonecammel-1",
    [string]$Location = "westeurope",
    [string]$Prefix = "oncology-collab-demo",
    [string]$OwnerEmail = "admin@MngEnvMCAP670682.onmicrosoft.com",
    [int]$BudgetAmount = 10,
    [int]$ExpiryDays = 14
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
        throw "Azure CLI failed: az $($Arguments -join ' ')"
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
$outputs = $base.properties.outputs
$platformResourceGroup = $outputs.platformResourceGroupName.value
$milanResourceGroup = $outputs.milanResourceGroupName.value
$acrName = $outputs.acrName.value
$acrLoginServer = $outputs.acrLoginServer.value
$imageTag = (git rev-parse --short HEAD).Trim()
$image = "$acrLoginServer/$Prefix`:$imageTag"

$storageAccess = Invoke-AzureCliJson -Arguments @(
    "storage", "account", "show",
    "--name", $outputs.milanAccountName.value,
    "--resource-group", $milanResourceGroup,
    "--query", "{publicNetworkAccess:publicNetworkAccess}",
    "--output", "json"
)
if ($storageAccess.publicNetworkAccess -ne "Enabled") {
    throw (
        "The subscription forced Blob publicNetworkAccess=$($storageAccess.publicNetworkAccess). " +
        "Private networking requires separate architecture and cost approval before deployment."
    )
}

$deployerObjectId = (
    Invoke-AzureCli -Arguments @("ad", "signed-in-user", "show", "--query", "id", "--output", "tsv")
).Trim()
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
            "--assignee-object-id", $deployerObjectId,
            "--assignee-principal-type", "User",
            "--role", $blobContributorRole,
            "--scope", $scope,
            "--only-show-errors",
            "--output", "json"
        )
        $temporaryAssignments += $assignment.id
    }
    Start-Sleep -Seconds 30
    Write-Host "Uploading approved synthetic fixtures through Microsoft Entra..."
    & "$repoRoot\.venv\Scripts\python.exe" "$repoRoot\scripts\upload_azure_fixtures.py" `
        --milan-account-url $outputs.milanAccountUrl.value `
        --utrecht-account-url $outputs.utrechtAccountUrl.value
    if ($LASTEXITCODE -ne 0) {
        throw "Synthetic fixture upload failed."
    }
}
finally {
    foreach ($assignmentId in $temporaryAssignments) {
        [void](Invoke-AzureCli -Arguments @(
            "role", "assignment", "delete", "--ids", $assignmentId, "--only-show-errors"
        ))
    }
}

Write-Host "Building the application image in Azure Container Registry..."
[void](Invoke-AzureCli -Arguments @(
    "acr", "build",
    "--registry", $acrName,
    "--image", "$Prefix`:$imageTag",
    "--file", "$repoRoot\Dockerfile",
    $repoRoot,
    "--only-show-errors",
    "--output", "none"
))

$secretBytes = New-Object byte[] 32
[Security.Cryptography.RandomNumberGenerator]::Fill($secretBytes)
$eventGridSecret = [Convert]::ToBase64String($secretBytes)

Write-Host "Deploying the Container App..."
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
    "ownerEmail=$OwnerEmail",
    "expiryDate=$expiry",
    "--only-show-errors",
    "--output", "json"
)

$fqdn = $app.properties.outputs.fqdn.value
$appName = $app.properties.outputs.applicationName.value
$applicationUrl = "https://$fqdn"

Write-Host "Creating the Event Grid evidence-delivery subscription..."
[void](Invoke-AzureCli -Arguments @(
    "deployment", "group", "create",
    "--name", "$Prefix-events-$timestamp",
    "--resource-group", $milanResourceGroup,
    "--template-file", "$repoRoot\infra\event-grid.bicep",
    "--parameters",
    "prefix=$Prefix",
    "storageAccountName=$($outputs.milanAccountName.value)",
    "endpointUrl=$applicationUrl/api/event-grid/evidence-arrivals",
    "eventGridWebhookSecret=$eventGridSecret",
    "ownerEmail=$OwnerEmail",
    "expiryDate=$expiry",
    "--only-show-errors",
    "--output", "none"
))

$displayName = "$Prefix-presenter"
$existingAppId = (
    Invoke-AzureCli -Arguments @(
        "ad", "app", "list",
        "--display-name", $displayName,
        "--query", "[0].appId",
        "--output", "tsv"
    )
).Trim()
if ([string]::IsNullOrWhiteSpace($existingAppId)) {
    $clientId = (
        Invoke-AzureCli -Arguments @(
            "ad", "app", "create",
            "--display-name", $displayName,
            "--sign-in-audience", "AzureADMyOrg",
            "--web-redirect-uris", "$applicationUrl/.auth/login/aad/callback",
            "--query", "appId",
            "--output", "tsv"
        )
    ).Trim()
    [void](Invoke-AzureCli -Arguments @(
        "ad", "sp", "create", "--id", $clientId, "--only-show-errors", "--output", "none"
    ))
}
else {
    $clientId = $existingAppId
    [void](Invoke-AzureCli -Arguments @(
        "ad", "app", "update",
        "--id", $clientId,
        "--web-redirect-uris", "$applicationUrl/.auth/login/aad/callback",
        "--only-show-errors",
        "--output", "none"
    ))
}

$clientSecret = (
    Invoke-AzureCli -Arguments @(
        "ad", "app", "credential", "reset",
        "--id", $clientId,
        "--display-name", "container-app-auth",
        "--years", "1",
        "--query", "password",
        "--output", "tsv"
    )
).Trim()

[void](Invoke-AzureCli -Arguments @(
    "containerapp", "secret", "set",
    "--resource-group", $platformResourceGroup,
    "--name", $appName,
    "--secrets", "entra-client-secret=$clientSecret",
    "--only-show-errors",
    "--output", "none"
))
[void](Invoke-AzureCli -Arguments @(
    "containerapp", "auth", "microsoft", "update",
    "--resource-group", $platformResourceGroup,
    "--name", $appName,
    "--client-id", $clientId,
    "--client-secret-name", "entra-client-secret",
    "--tenant-id", $account.tenantId,
    "--yes",
    "--only-show-errors",
    "--output", "none"
))
[void](Invoke-AzureCli -Arguments @(
    "containerapp", "auth", "update",
    "--resource-group", $platformResourceGroup,
    "--name", $appName,
    "--enabled", "true",
    "--action", "RedirectToLoginPage",
    "--redirect-provider", "azureactivedirectory",
    "--require-https", "true",
    "--excluded-paths", "/api/health", "/api/event-grid/evidence-arrivals",
    "--yes",
    "--only-show-errors",
    "--output", "none"
))

Write-Host "Azure deployment complete: $applicationUrl"
Write-Host "Expiry tag: $expiry. Fabric and Azure OpenAI remain disabled."
