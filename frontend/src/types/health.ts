export interface HealthResponse {
  status: 'healthy'
  service: string
  version: string
  environment: string
  timestamp: string
}

