import { contextBridge, ipcRenderer } from "electron"

contextBridge.exposeInMainWorld("scout", {
  pickFolder: () => ipcRenderer.invoke("pick-folder"),
  validateRepo: (path: string) => ipcRenderer.invoke("validate-repo", path),
  getRepos: () => ipcRenderer.invoke("get-repos"),
  addRepo: (path: string) => ipcRenderer.invoke("add-repo", path),
  removeRepo: (id: string) => ipcRenderer.invoke("remove-repo", id),
  setActiveRepo: (id: string) => ipcRenderer.invoke("set-active-repo", id),
  readLog: (path: string) => ipcRenderer.invoke("read-log", path),
  indexStatus: (path: string) => ipcRenderer.invoke("index-status", path),
  restartClaude: () => ipcRenderer.invoke("restart-claude"),
  revealInFinder: (path: string) => ipcRenderer.invoke("reveal-in-finder", path),
})
