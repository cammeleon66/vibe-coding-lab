<#
.SYNOPSIS
Builds the fednet image and deploys the three federated services
(oncology-fed-nl, oncology-fed-de, oncology-fed-hub) into the existing
Container Apps environment. Idempotent; rotates signing keys on each run.
The legacy oncology-collab-demo app is left untouched as the rollback.
Secrets are never printed.
#>
param(
    [string]$ResourceGroup = 'oncology-collab-demo-platform-rg',
    [string]$Environment = 'oncology-collab-demo-env-2',
    [string]$Registry = 'ocdpscufetxrykg6',
    [string]$Identity = 'oncology-collab-demo-identity',
    [string]$StorageAccount = 'ocdsharedpscufetxrykg6',
    [string]$LegacyApp = 'oncology-collab-demo',
    [string]$Tag = (git rev-parse --short HEAD),
    [switch]$SkipBuild
)

$ErrorActionPreference = 'Stop'

function Invoke-Az {
    $output = & az @args
    if ($LASTEXITCODE -ne 0) { throw "az $($args[0..2] -join ' ') failed" }
    $output
}

function New-Secret { [Convert]::ToHexString([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32)).ToLower() }

$image = "$Registry.azurecr.io/oncology-fed:$Tag"
if (-not $SkipBuild) {
    Write-Host "Building $image"
    $runId = Invoke-Az acr build -r $Registry -t "oncology-fed:$Tag" --no-logs --query runId -o tsv .
    do {
        Start-Sleep -Seconds 15
        $state = Invoke-Az acr task show-run -r $Registry --run-id $runId --query status -o tsv
        Write-Host "  build $runId : $state"
    } while ($state -in @('Queued', 'Started', 'Running'))
    if ($state -ne 'Succeeded') { throw "Image build $runId ended with $state" }
}

$identityId = Invoke-Az identity show -n $Identity -g $ResourceGroup --query id -o tsv
$clientId = Invoke-Az identity show -n $Identity -g $ResourceGroup --query clientId -o tsv
$domain = Invoke-Az containerapp env show -n $Environment -g $ResourceGroup --query properties.defaultDomain -o tsv
$appInsights = Invoke-Az containerapp show -n $LegacyApp -g $ResourceGroup `
    --query "properties.template.containers[0].env[?name=='APPLICATIONINSIGHTS_CONNECTION_STRING'].value | [0]" -o tsv
$accessCode = Invoke-Az containerapp secret show -n $LegacyApp -g $ResourceGroup `
    --secret-name demo-access-code --query value -o tsv

foreach ($container in 'fed-nl', 'fed-de', 'fed-hub') {
    Invoke-Az storage container-rm create --storage-account $StorageAccount -g $ResourceGroup `
        -n $container --public-access off -o none 2>$null
}

$keyNames = 'nl-hub', 'hub-nl', 'ws-nl', 'admin-nl', 'de-hub', 'hub-de', 'ws-de', 'admin-de'
$keys = @{}
foreach ($name in $keyNames) { $keys[$name] = New-Secret }

$urls = @{
    hub = "https://oncology-fed-hub.$domain"
    nl  = "https://oncology-fed-nl.internal.$domain"
    de  = "https://oncology-fed-de.internal.$domain"
}

$services = @(
    @{ site = 'nl'; ingress = 'internal'; cpu = '0.25'; memory = '0.5Gi' },
    @{ site = 'de'; ingress = 'internal'; cpu = '0.25'; memory = '0.5Gi' },
    @{ site = 'hub'; ingress = 'external'; cpu = '0.5'; memory = '1Gi' }
)

foreach ($service in $services) {
    $site = $service.site
    $app = "oncology-fed-$site"
    $siteKeys = if ($site -eq 'hub') { $keyNames } else { $keyNames | Where-Object { $_ -match "(^|-)$site(-|$)" } }

    $secrets = @($siteKeys | ForEach-Object { "key-$_=$($keys[$_])" })
    $envVars = @(
        "SITE=$site", 'FED_RUNTIME=azure', "APP_VERSION=$Tag",
        "STORAGE_ACCOUNT_URL=https://$StorageAccount.blob.core.windows.net/",
        "STORAGE_CONTAINER=fed-$site", "AZURE_CLIENT_ID=$clientId",
        "APPLICATIONINSIGHTS_CONNECTION_STRING=$appInsights",
        "HUB_URL=$($urls.hub)", "NL_URL=$($urls.nl)", "DE_URL=$($urls.de)"
    )
    $envVars += $siteKeys | ForEach-Object { "FED_KEY_$($_.ToUpper().Replace('-', '_'))=secretref:key-$_" }
    if ($site -eq 'hub') {
        $secrets += "demo-access-code=$accessCode", "demo-session-secret=$(New-Secret)"
        $envVars += 'DEMO_ACCESS_CODE=secretref:demo-access-code', 'DEMO_SESSION_SECRET=secretref:demo-session-secret'
    }

    $exists = az containerapp show -n $app -g $ResourceGroup --query name -o tsv 2>$null
    if ($exists) {
        Write-Host "Updating $app"
        Invoke-Az containerapp secret set -n $app -g $ResourceGroup --secrets @secrets -o none
        Invoke-Az containerapp update -n $app -g $ResourceGroup --image $image `
            --revision-suffix "r$Tag-$(Get-Date -Format HHmmss)" --set-env-vars @envVars -o none
    } else {
        Write-Host "Creating $app"
        Invoke-Az containerapp create -n $app -g $ResourceGroup --environment $Environment `
            --image $image --registry-server "$Registry.azurecr.io" --registry-identity $identityId `
            --user-assigned $identityId --ingress $service.ingress --target-port 8000 `
            --cpu $service.cpu --memory $service.memory --min-replicas 0 --max-replicas 1 `
            --secrets @secrets --env-vars @envVars `
            --tags purpose=federated-demo expires=2026-10-07 -o none
    }
}

Write-Host "Hub: $($urls.hub)  (same access code as $LegacyApp)"
