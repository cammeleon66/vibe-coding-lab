[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$Subscription = "ME-MngEnvMCAP670682-simonecammel-1",
    [string]$Prefix = "oncology-collab-demo"
)

$ErrorActionPreference = "Stop"
az account set --subscription $Subscription

$resourceGroups = @(
    "$Prefix-milan-rg",
    "$Prefix-utrecht-rg",
    "$Prefix-platform-rg"
)
foreach ($resourceGroup in $resourceGroups) {
    if ($PSCmdlet.ShouldProcess($resourceGroup, "Delete approved demo resource group")) {
        az group delete --name $resourceGroup --yes --no-wait --only-show-errors
    }
}

$budgetId = az consumption budget list `
    --query "[?name=='$Prefix-monthly-budget'].id | [0]" `
    --output tsv
if (-not [string]::IsNullOrWhiteSpace($budgetId) -and
    $PSCmdlet.ShouldProcess($budgetId, "Delete demo budget")) {
    az resource delete --ids $budgetId --only-show-errors
}

$applicationId = az ad app list `
    --display-name "$Prefix-presenter" `
    --query "[0].appId" `
    --output tsv
if (-not [string]::IsNullOrWhiteSpace($applicationId) -and
    $PSCmdlet.ShouldProcess($applicationId, "Delete demo Entra application")) {
    az ad app delete --id $applicationId --only-show-errors
}
