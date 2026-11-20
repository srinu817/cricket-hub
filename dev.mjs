import { spawn } from 'node:child_process'
import { resolve } from 'node:path'

const children = [
  spawn(process.env.PYTHON || 'python', ['-m', 'uvicorn', 'backend.app.main:app', '--host', '127.0.0.1', '--port', '8787'], { stdio: 'inherit', env: process.env }),
  spawn(process.execPath, [resolve('node_modules/vite/bin/vite.js')], { stdio: 'inherit', env: process.env }),
]
let stopping = false

function stop(code = 0) {
  if (stopping) return
  stopping = true
  for (const child of children) if (child.exitCode === null) child.kill()
  process.exitCode = code
}

for (const child of children) {
  child.on('error', error => {
    console.error('Could not start Cricket Hub development services:', error.message)
    stop(1)
  })
  child.on('exit', code => {
    if (!stopping) stop(code || 0)
  })
}

process.on('SIGINT', () => stop(0))
process.on('SIGTERM', () => stop(0))
