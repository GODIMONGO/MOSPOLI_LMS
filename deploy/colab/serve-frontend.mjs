#!/usr/bin/env node
import fs from 'node:fs'
import http from 'node:http'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(__dirname, '../..')
const staticDir = path.resolve(process.env.STATIC_DIR ?? path.join(repoRoot, 'dist'))
const port = Number(process.env.FRONTEND_PORT ?? 5173)
const upstream = process.env.AI_NAVIGATION_UPSTREAM ?? 'http://127.0.0.1:3001'

const mimeTypes = new Map([
  ['.css', 'text/css; charset=utf-8'],
  ['.html', 'text/html; charset=utf-8'],
  ['.ico', 'image/x-icon'],
  ['.js', 'text/javascript; charset=utf-8'],
  ['.json', 'application/json; charset=utf-8'],
  ['.map', 'application/json; charset=utf-8'],
  ['.png', 'image/png'],
  ['.svg', 'image/svg+xml'],
  ['.txt', 'text/plain; charset=utf-8'],
  ['.woff', 'font/woff'],
  ['.woff2', 'font/woff2'],
])

const server = http.createServer(async (request, response) => {
  try {
    const url = new URL(request.url ?? '/', `http://${request.headers.host ?? 'localhost'}`)

    if (url.pathname.startsWith('/api/')) {
      proxyApi(request, response, url)
      return
    }

    await serveStatic(response, url.pathname)
  } catch (error) {
    response.writeHead(500, { 'Content-Type': 'text/plain; charset=utf-8' })
    response.end(error instanceof Error ? error.message : 'Internal server error')
  }
})

server.listen(port, '0.0.0.0', () => {
  console.log(`frontend static/proxy server listening on :${port}`)
  console.log(`serving ${staticDir}`)
  console.log(`proxying /api/* to ${upstream}`)
})

function proxyApi(request, response, url) {
  const target = new URL(url.pathname + url.search, upstream)
  const headers = { ...request.headers, host: target.host }

  const proxyRequest = http.request(
    target,
    {
      method: request.method,
      headers,
    },
    (proxyResponse) => {
      response.writeHead(proxyResponse.statusCode ?? 502, proxyResponse.headers)
      proxyResponse.pipe(response)
    },
  )

  proxyRequest.on('error', (error) => {
    response.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' })
    response.end(JSON.stringify({ error: 'Bad gateway', message: error.message }))
  })

  request.pipe(proxyRequest)
}

async function serveStatic(response, pathname) {
  const requestedPath = decodeURIComponent(pathname)
  const normalizedPath = requestedPath === '/' ? '/index.html' : requestedPath
  const filePath = path.resolve(staticDir, `.${normalizedPath}`)

  if (!filePath.startsWith(staticDir + path.sep) && filePath !== staticDir) {
    response.writeHead(403, { 'Content-Type': 'text/plain; charset=utf-8' })
    response.end('Forbidden')
    return
  }

  const resolvedPath = await resolveFile(filePath)
  const contentType = mimeTypes.get(path.extname(resolvedPath)) ?? 'application/octet-stream'
  response.writeHead(200, {
    'Content-Type': contentType,
    'Cache-Control': resolvedPath.endsWith('index.html') ? 'no-cache' : 'public, max-age=31536000, immutable',
  })
  fs.createReadStream(resolvedPath).pipe(response)
}

async function resolveFile(filePath) {
  try {
    const stats = await fs.promises.stat(filePath)
    if (stats.isFile()) {
      return filePath
    }
  } catch {
    // Fall through to SPA fallback.
  }

  return path.join(staticDir, 'index.html')
}
