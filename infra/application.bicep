param location string = resourceGroup().location
param prefix string = 'oncology-collab-demo'
param image string
param acrLoginServer string
param environmentName string
param identityResourceId string
param identityClientId string
param insightsName string
param milanAccountUrl string
param utrechtAccountUrl string
param sharedAccountUrl string
@secure()
param eventGridWebhookSecret string
param ownerEmail string
param expiryDate string
param mdoDemoUrl string = 'https://github.com/jochenvw/mdt-observatory'

var tags = {
  Application: 'European oncology collaboration demo'
  DataClassification: 'Synthetic'
  Environment: 'Demo'
  ExpiresOn: expiryDate
  Owner: ownerEmail
  Purpose: 'Cross-border oncology collaboration demonstration'
}

resource environment 'Microsoft.App/managedEnvironments@2025-01-01' existing = {
  name: environmentName
}

resource insights 'Microsoft.Insights/components@2020-02-02' existing = {
  name: insightsName
}

resource application 'Microsoft.App/containerApps@2025-01-01' = {
  name: prefix
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identityResourceId}': {}
    }
  }
  properties: {
    environmentId: environment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        allowInsecure: false
        external: true
        targetPort: 8000
        transport: 'auto'
      }
      registries: [
        {
          server: acrLoginServer
          identity: identityResourceId
        }
      ]
      secrets: [
        {
          name: 'event-grid-webhook-secret'
          value: eventGridWebhookSecret
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'collaboration'
          image: image
          env: [
            {
              name: 'APP_RUNTIME_MODE'
              value: 'azure'
            }
            {
              name: 'AZURE_CLIENT_ID'
              value: identityClientId
            }
            {
              name: 'MILAN_STORAGE_ACCOUNT_URL'
              value: milanAccountUrl
            }
            {
              name: 'UTRECHT_STORAGE_ACCOUNT_URL'
              value: utrechtAccountUrl
            }
            {
              name: 'SHARED_STORAGE_ACCOUNT_URL'
              value: sharedAccountUrl
            }
            {
              name: 'EVENT_GRID_WEBHOOK_SECRET'
              secretRef: 'event-grid-webhook-secret'
            }
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              value: insights.properties.ConnectionString
            }
            {
              name: 'MDO_DEMO_URL'
              value: mdoDemoUrl
            }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/api/health'
                port: 8000
                scheme: 'HTTP'
              }
              initialDelaySeconds: 10
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/api/health'
                port: 8000
                scheme: 'HTTP'
              }
              initialDelaySeconds: 5
              periodSeconds: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 1
        rules: [
          {
            name: 'http'
            http: {
              metadata: {
                concurrentRequests: '10'
              }
            }
          }
        ]
      }
    }
  }
}

output applicationName string = application.name
output fqdn string = application.properties.configuration.ingress.fqdn
