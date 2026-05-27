import { app, BrowserWindow, ipcMain, dialog, shell } from "electron"
import { execSync } from "child_process"
import * as path from "path"
import * as fs from "fs"
import * as os from "os"

const isDev = process.env.NODE_ENV === "development"

// ── Window ────────────────────────────────────────────────────────────────────

function createWindow() {
  const win = new BrowserWindow({
    width: 1100,
    height: 720,
    minWidth: 800,
    minHeight: 600,
    titleBarStyle: "hiddenInset",
    backgroundColor: "#0c0c0d",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  if (isDev) {
    win.loadURL("http://localhost:5173")
  } else {
    win.loadFile(path.join(__dirname, "../dist/index.html"))
  }
}

app.whenReady().then(createWindow)
app.on("window-all-closed", () => { if (process.platform !== "darwin") app.quit() })
app.on("activate", () => { if (BrowserWindow.getAllWindows().length === 0) createWindow() })

// ── Scout state (~/.scout/repos.json) ─────────────────────────────────────────
// Stores all known repos. Claude Desktop config only has ONE active scout entry.

const SCOUT_STATE_PATH = path.join(os.homedir(), ".scout", "repos.json")
const CLAUDE_CONFIG_PATH = path.join(
  os.homedir(),
  "Library/Application Support/Claude/claude_desktop_config.json"
)
const SCOUT_MCP_KEY = "scout"

interface RepoEntry {
  id: string
  name: string
  path: string
  mcpBin: string
}

interface ScoutState {
  repos: RepoEntry[]
  activeId: string | null
}

function readState(): ScoutState {
  try {
    if (!fs.existsSync(SCOUT_STATE_PATH)) return { repos: [], activeId: null }
    return JSON.parse(fs.readFileSync(SCOUT_STATE_PATH, "utf-8"))
  } catch {
    return { repos: [], activeId: null }
  }
}

function writeState(state: ScoutState): void {
  fs.mkdirSync(path.dirname(SCOUT_STATE_PATH), { recursive: true })
  fs.writeFileSync(SCOUT_STATE_PATH, JSON.stringify(state, null, 2), "utf-8")
}

// ── Claude Desktop config ─────────────────────────────────────────────────────

function readClaudeConfig(): Record<string, any> {
  try {
    if (!fs.existsSync(CLAUDE_CONFIG_PATH)) return {}
    return JSON.parse(fs.readFileSync(CLAUDE_CONFIG_PATH, "utf-8"))
  } catch {
    return {}
  }
}

function writeClaudeConfig(config: Record<string, any>): void {
  fs.mkdirSync(path.dirname(CLAUDE_CONFIG_PATH), { recursive: true })
  fs.writeFileSync(CLAUDE_CONFIG_PATH, JSON.stringify(config, null, 2), "utf-8")
}

function activateRepoInConfig(repo: RepoEntry): void {
  const config = readClaudeConfig()
  if (!config.mcpServers) config.mcpServers = {}
  config.mcpServers[SCOUT_MCP_KEY] = {
    command: repo.mcpBin,
    args: [repo.path],
    env: readEnvKeys(repo.path),
  }
  writeClaudeConfig(config)
}

function deactivateScoutInConfig(): void {
  const config = readClaudeConfig()
  if (config.mcpServers?.[SCOUT_MCP_KEY]) {
    delete config.mcpServers[SCOUT_MCP_KEY]
    writeClaudeConfig(config)
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function findScoutMcp(repoPath: string): string {
  const candidates = [
    path.join(repoPath, ".venv/bin/scout-mcp"),
    path.join(repoPath, "venv/bin/scout-mcp"),
    "/usr/local/bin/scout-mcp",
  ]
  for (const c of candidates) {
    if (fs.existsSync(c)) return c
  }
  try {
    return execSync("which scout-mcp", { encoding: "utf-8" }).trim()
  } catch {
    return "scout-mcp"
  }
}

function readEnvKeys(repoPath: string): Record<string, string> {
  const envPath = path.join(repoPath, ".env")
  const env: Record<string, string> = {}
  if (!fs.existsSync(envPath)) return env
  try {
    const lines = fs.readFileSync(envPath, "utf-8").split("\n")
    for (const line of lines) {
      const match = line.match(/^(DEEPSEEK_API_KEY|OPENAI_API_KEY)=(.+)$/)
      if (match) env[match[1]] = match[2].trim()
    }
  } catch {}
  return env
}

// ── IPC handlers ──────────────────────────────────────────────────────────────

ipcMain.handle("pick-folder", async () => {
  const result = await dialog.showOpenDialog({
    properties: ["openDirectory"],
    title: "Select a git repository",
    buttonLabel: "Add Repository",
  })
  return result.canceled ? null : result.filePaths[0]
})

ipcMain.handle("validate-repo", async (_event, repoPath: string) => {
  try {
    execSync(`git -C "${repoPath}" rev-parse --show-toplevel`, { encoding: "utf-8" })
    return { valid: true, name: path.basename(repoPath) }
  } catch {
    return { valid: false, name: null }
  }
})

ipcMain.handle("get-repos", async () => {
  return readState()
})

ipcMain.handle("add-repo", async (_event, repoPath: string) => {
  const state = readState()
  const name = path.basename(repoPath)
  const id = `scout-${name.toLowerCase().replace(/[^a-z0-9]/g, "-")}-${Date.now()}`
  const mcpBin = findScoutMcp(repoPath)
  const repo: RepoEntry = { id, name, path: repoPath, mcpBin }

  if (!state.repos.find((r) => r.path === repoPath)) {
    state.repos.push(repo)
  }
  state.activeId = id
  writeState(state)
  activateRepoInConfig(repo)
  return state
})

ipcMain.handle("remove-repo", async (_event, id: string) => {
  const state = readState()
  state.repos = state.repos.filter((r) => r.id !== id)

  if (state.activeId === id) {
    state.activeId = state.repos.length > 0 ? state.repos[0].id : null
    if (state.activeId) {
      activateRepoInConfig(state.repos.find((r) => r.id === state.activeId)!)
    } else {
      deactivateScoutInConfig()
    }
  }

  writeState(state)
  return state
})

// Switch active repo — rewrites Claude Desktop config immediately
ipcMain.handle("set-active-repo", async (_event, id: string) => {
  const state = readState()
  const repo = state.repos.find((r) => r.id === id)
  if (!repo) return state
  state.activeId = id
  writeState(state)
  activateRepoInConfig(repo)
  return state
})

ipcMain.handle("read-log", async (_event, repoPath: string) => {
  const logPath = path.join(repoPath, ".scout", "scout.log")
  if (!fs.existsSync(logPath)) return null
  return fs.readFileSync(logPath, "utf-8")
})

ipcMain.handle("index-status", async (_event, repoPath: string) => {
  const indexPath = path.join(repoPath, ".scout", "embedding_index.json")
  if (!fs.existsSync(indexPath)) return { exists: false, fresh: false }
  try {
    const indexMtime = fs.statSync(indexPath).mtimeMs
    const head = execSync(`git -C "${repoPath}" rev-parse HEAD`, { encoding: "utf-8" }).trim()
    const headTime = execSync(`git -C "${repoPath}" log -1 --format=%ct HEAD`, { encoding: "utf-8" }).trim()
    return { exists: true, fresh: indexMtime >= parseInt(headTime) * 1000, head: head.slice(0, 7) }
  } catch {
    return { exists: true, fresh: true }
  }
})

ipcMain.handle("restart-claude", async () => {
  try {
    const { spawn } = require("child_process")
    spawn("osascript", ["-e", 'quit app "Claude"'], { detached: true, stdio: "ignore" }).unref()
    await new Promise((r) => setTimeout(r, 2000))
    spawn("open", ["-a", "Claude"], { detached: true, stdio: "ignore" }).unref()
    return true
  } catch {
    return false
  }
})

ipcMain.handle("reveal-in-finder", async (_event, filePath: string) => {
  shell.showItemInFolder(filePath)
})
