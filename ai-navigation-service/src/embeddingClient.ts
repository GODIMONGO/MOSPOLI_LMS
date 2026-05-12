import { config } from './config.js'

const MOCK_DIMENSIONS = 64

export async function createEmbedding(input: string): Promise<number[]> {
  if (config.embeddingMock) {
    return createMockEmbedding(input)
  }

  const attempts = Number(process.env.EMBEDDING_RETRY_ATTEMPTS ?? 60)
  const delayMs = Number(process.env.EMBEDDING_RETRY_DELAY_MS ?? 2000)
  const endpoints = [
    {
      url: `${config.embeddingBaseUrl.replace(/\/$/, '')}/v1/embeddings`,
      body: { model: config.embeddingModel, input },
      parse: (payload: unknown) => {
        const data = payload as { data?: Array<{ embedding?: number[] }> }
        return data.data?.[0]?.embedding
      },
    },
    {
      url: `${config.embeddingBaseUrl.replace(/\/$/, '')}/embedding`,
      body: { content: input },
      parse: (payload: unknown) => {
        const data = payload as { embedding?: number[] }
        return data.embedding
      },
    },
  ]

  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    for (const endpoint of endpoints) {
      try {
        const controller = new AbortController()
        const timeout = setTimeout(() => controller.abort(), 15000)
        const response = await fetch(endpoint.url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(endpoint.body),
          signal: controller.signal,
        })
        clearTimeout(timeout)

        if (!response.ok) {
          continue
        }

        const embedding = endpoint.parse(await response.json())
        if (Array.isArray(embedding) && embedding.length > 0) {
          return normalizeVector(embedding)
        }
      } catch {
        continue
      }
    }

    if (attempt < attempts) {
      await sleep(delayMs)
    }
  }

  if (config.allowEmbeddingFallback) {
    return createMockEmbedding(input)
  }

  throw new Error('Embedding server is unavailable')
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function createMockEmbedding(input: string): number[] {
  const vector = new Array<number>(MOCK_DIMENSIONS).fill(0)
  for (let i = 0; i < input.length; i++) {
    vector[i % MOCK_DIMENSIONS] += input.charCodeAt(i)
  }
  const norm = Math.sqrt(vector.reduce((sum, v) => sum + v * v, 0))
  return norm === 0 ? vector : vector.map((v) => v / norm)
}

export function normalizeVector(vector: number[]): number[] {
  const norm = Math.sqrt(vector.reduce((sum, value) => sum + value * value, 0))
  if (norm === 0) {
    return vector
  }
  return vector.map((value) => value / norm)
}
