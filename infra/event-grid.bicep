param location string = resourceGroup().location
param prefix string = 'oncology-collab-demo'
param storageAccountName string
@secure()
param endpointUrl string
@secure()
param eventGridWebhookSecret string
param ownerEmail string
param expiryDate string

var tags = {
  Application: 'European oncology collaboration demo'
  DataClassification: 'Synthetic'
  Environment: 'Demo'
  ExpiresOn: expiryDate
  Owner: ownerEmail
  Purpose: 'Cross-border oncology collaboration demonstration'
}

resource storage 'Microsoft.Storage/storageAccounts@2025-06-01' existing = {
  name: storageAccountName
}

resource systemTopic 'Microsoft.EventGrid/systemTopics@2025-02-15' = {
  name: '${prefix}-milan-source'
  location: location
  tags: tags
  properties: {
    source: storage.id
    topicType: 'Microsoft.Storage.StorageAccounts'
  }
}

resource evidenceSubscription 'Microsoft.EventGrid/systemTopics/eventSubscriptions@2025-02-15' = {
  parent: systemTopic
  name: 'late-evidence'
  properties: {
    destination: {
      endpointType: 'WebHook'
      properties: {
        endpointUrl: endpointUrl
        deliveryAttributeMappings: [
          {
            name: 'X-Event-Grid-Secret'
            type: 'Static'
            properties: {
              isSecret: true
              value: eventGridWebhookSecret
            }
          }
        ]
      }
    }
    eventDeliverySchema: 'EventGridSchema'
    filter: {
      includedEventTypes: [
        'Microsoft.Storage.BlobCreated'
      ]
      subjectBeginsWith: '/blobServices/default/containers/events/blobs/'
    }
    retryPolicy: {
      eventTimeToLiveInMinutes: 30
      maxDeliveryAttempts: 10
    }
  }
}
