targetScope = 'subscription'

param location string = 'westeurope'
param prefix string = 'oncology-collab-demo'
param ownerEmail string
param expiryDate string
param budgetAmount int = 10
param budgetStartDate string
param budgetEndDate string

var commonTags = {
  Application: 'European oncology collaboration demo'
  DataClassification: 'Synthetic'
  Environment: 'Demo'
  ExpiresOn: expiryDate
  Owner: ownerEmail
  Purpose: 'Cross-border oncology collaboration demonstration'
}
var platformResourceGroupName = '${prefix}-platform-rg'
var milanResourceGroupName = '${prefix}-milan-rg'
var utrechtResourceGroupName = '${prefix}-utrecht-rg'
var suffix = uniqueString(subscription().id, prefix)
var blobContributorRole = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
var blobReaderRole = '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1'

resource platformResourceGroup 'Microsoft.Resources/resourceGroups@2025-04-01' = {
  name: platformResourceGroupName
  location: location
  tags: commonTags
}

resource milanResourceGroup 'Microsoft.Resources/resourceGroups@2025-04-01' = {
  name: milanResourceGroupName
  location: location
  tags: commonTags
}

resource utrechtResourceGroup 'Microsoft.Resources/resourceGroups@2025-04-01' = {
  name: utrechtResourceGroupName
  location: location
  tags: commonTags
}

module platform 'platform.bicep' = {
  name: 'platform'
  scope: platformResourceGroup
  params: {
    location: location
    prefix: prefix
    tags: commonTags
  }
}

module milan 'storage.bicep' = {
  name: 'milan-storage'
  scope: milanResourceGroup
  params: {
    location: location
    storageAccountName: take('ocdmilan${suffix}', 24)
    containerName: 'source'
    principalId: platform.outputs.identityPrincipalId
    roleDefinitionId: blobContributorRole
    tags: commonTags
  }
}

module utrecht 'storage.bicep' = {
  name: 'utrecht-storage'
  scope: utrechtResourceGroup
  params: {
    location: location
    storageAccountName: take('ocdutrecht${suffix}', 24)
    containerName: 'source'
    principalId: platform.outputs.identityPrincipalId
    roleDefinitionId: blobReaderRole
    tags: commonTags
  }
}

module shared 'storage.bicep' = {
  name: 'shared-storage'
  scope: platformResourceGroup
  params: {
    location: location
    storageAccountName: take('ocdshared${suffix}', 24)
    containerName: 'collaboration'
    principalId: platform.outputs.identityPrincipalId
    roleDefinitionId: blobContributorRole
    tags: commonTags
  }
}

resource budget 'Microsoft.Consumption/budgets@2023-11-01' = {
  name: '${prefix}-monthly-budget'
  properties: {
    amount: budgetAmount
    category: 'Cost'
    timeGrain: 'Monthly'
    timePeriod: {
      startDate: budgetStartDate
      endDate: budgetEndDate
    }
    notifications: {
      Actual80: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 80
        thresholdType: 'Actual'
        contactEmails: [
          ownerEmail
        ]
      }
      Forecast100: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 100
        thresholdType: 'Forecasted'
        contactEmails: [
          ownerEmail
        ]
      }
    }
  }
}

output platformResourceGroupName string = platformResourceGroup.name
output milanResourceGroupName string = milanResourceGroup.name
output utrechtResourceGroupName string = utrechtResourceGroup.name
output acrName string = platform.outputs.acrName
output acrLoginServer string = platform.outputs.acrLoginServer
output environmentName string = platform.outputs.environmentName
output identityClientId string = platform.outputs.identityClientId
output identityResourceId string = platform.outputs.identityResourceId
output insightsName string = platform.outputs.insightsName
output insightsConnectionString string = platform.outputs.insightsConnectionString
output milanAccountName string = milan.outputs.accountName
output milanAccountUrl string = milan.outputs.accountUrl
output utrechtAccountName string = utrecht.outputs.accountName
output utrechtAccountUrl string = utrecht.outputs.accountUrl
output sharedAccountName string = shared.outputs.accountName
output sharedAccountUrl string = shared.outputs.accountUrl
