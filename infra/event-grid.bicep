param systemTopicName string
@secure()
param endpointUrl string
@secure()
param eventGridWebhookSecret string

resource systemTopic 'Microsoft.EventGrid/systemTopics@2025-02-15' existing = {
  name: systemTopicName
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
