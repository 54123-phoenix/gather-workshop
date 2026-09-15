import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const root = fileURLToPath(new URL('../', import.meta.url))
const commands = [
  ['uv', ['run', '--project', 'api', 'uvicorn', 'app:app', '--app-dir', 'api', '--host', '127.0.0.1', '--port', '8765', '--reload', '--reload-dir', 'api']],
  [process.execPath, ['node_modules/vite/bin/vite.js']],
]
const children = []
let stopping = false

function stop(code = 0) {
  if (stopping) return
  stopping = true
  for (const child of children) child.kill('SIGTERM')
  process.exitCode = code
}

for (const [command, args] of commands) {
  const child = spawn(command, args, { cwd: root, stdio: 'inherit' })
  children.push(child)
  child.on('error', (error) => {
    console.error(`Unable to start ${command}: ${error.message}`)
    stop(1)
  })
  child.on('exit', (code) => stop(code ?? 1))
}
process.on('SIGINT', () => stop())
process.on('SIGTERM', () => stop())
