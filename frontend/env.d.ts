/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_DATA_URL?: string
  readonly VITE_REOLINK_API_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
