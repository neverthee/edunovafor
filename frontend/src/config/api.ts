const DEFAULT_API_ORIGIN = 'http://localhost:5001'

function trimTrailingSlash(url: string): string {
  return url.replace(/\/+$/, '')
}

const envOrigin = (import.meta.env.VITE_API_BASE_URL || '').trim()
const isLocalBrowser =
  typeof window !== 'undefined' &&
  ['localhost', '127.0.0.1'].includes(window.location.hostname)

// In local Vite dev, prefer the same-origin /api proxy instead of hard-coding
// localhost:5001 unless VITE_API_BASE_URL is explicitly configured.
export const API_ORIGIN = trimTrailingSlash(
  envOrigin || (isLocalBrowser ? '' : DEFAULT_API_ORIGIN)
)
export const API_BASE_URL = API_ORIGIN ? `${API_ORIGIN}/api` : '/api'
