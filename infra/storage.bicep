param location string
param storageAccountName string
param containerName string
param principalId string
param roleDefinitionId string
param writeContainerName string = ''
param tags object

resource storage 'Microsoft.Storage/storageAccounts@2025-06-01' = {
  name: storageAccountName
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    defaultToOAuthAuthentication: true
    minimumTlsVersion: 'TLS1_2'
    publicNetworkAccess: 'Enabled'
    supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2025-06-01' = {
  parent: storage
  name: 'default'
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: 7
    }
  }
}

resource container 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = {
  parent: blobService
  name: containerName
  properties: {
    publicAccess: 'None'
  }
}

resource readRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storage
  name: guid(storage.id, principalId, roleDefinitionId)
  properties: {
    principalId: principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitionId)
  }
}

resource writeContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = if (!empty(writeContainerName)) {
  parent: blobService
  name: writeContainerName
  properties: {
    publicAccess: 'None'
  }
}

resource writeRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(writeContainerName)) {
  scope: writeContainer
  name: guid(writeContainer.id, principalId, 'BlobDataContributor')
  properties: {
    principalId: principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
    )
  }
}

output accountName string = storage.name
output accountUrl string = storage.properties.primaryEndpoints.blob
output containerName string = container.name
output writeContainerName string = !empty(writeContainerName) ? writeContainer.name : ''
