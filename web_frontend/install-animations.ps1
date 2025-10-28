param(
  [switch]$Include3D = $false,
  [switch]$ForceLegacyPeerDeps = $false
)

# PowerShell script to install recommended React animation libraries for this project
# Usage:
#   1) Open PowerShell
#   2) cd to this folder (web_frontend)
#   3) Run: ./install-animations.ps1
# Optional:
#   -Include3D            # also install React Three Fiber + Drei (pinned for React 18)
#   -ForceLegacyPeerDeps  # add --legacy-peer-deps to npm install to bypass peer conflicts

$ErrorActionPreference = "Stop"

# Ensure we run from the folder where package.json lives
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

if (!(Test-Path -Path (Join-Path $scriptDir 'package.json'))) {
  Write-Error "package.json not found. Run this script from the 'web_frontend' folder."
  exit 1
}

Write-Host "Installing core animation libraries..." -ForegroundColor Cyan

$common = @(
  'framer-motion',
  '@react-spring/web',
  'gsap',
  '@gsap/react',
  'lottie-react',
  '@rive-app/react-canvas',
  'animejs',
  'react-transition-group',
  'lenis',
  'canvas-confetti'
)

# Build the base install command
$npmArgs = @('install') + $common

# Optionally include 3D stack with versions compatible with React 18
if ($Include3D) {
  Write-Host "Including 3D stack (@react-three/fiber, three, drei) pinned for React 18..." -ForegroundColor Yellow
  # Pinned versions to avoid React 19 peer requirements
  $npmArgs += @(
    '@react-three/fiber@8.15.16',
    'three@0.154.0',
    '@react-three/drei@9.80.3'
  )
}

if ($ForceLegacyPeerDeps) {
  $npmArgs += '--legacy-peer-deps'
}

Write-Host ("npm " + ($npmArgs -join ' ')) -ForegroundColor DarkGray
npm $npmArgs
if ($LASTEXITCODE -ne 0) { throw "npm install (core) failed with exit code $LASTEXITCODE" }

Write-Host "\nOptional CSS-based animations: animate.css (installing)..." -ForegroundColor Cyan
if ($ForceLegacyPeerDeps) {
  npm install animate.css --legacy-peer-deps
} else {
  npm install animate.css
}
if ($LASTEXITCODE -ne 0) { throw "npm install animate.css failed with exit code $LASTEXITCODE" }

# Tailwind requires config; we install dev deps but leave setup to the developer
Write-Host "\nInstalling Tailwind CSS dev dependencies (optional scaffold)..." -ForegroundColor Yellow
if ($ForceLegacyPeerDeps) {
  npm install -D tailwindcss postcss autoprefixer --legacy-peer-deps
} else {
  npm install -D tailwindcss postcss autoprefixer
}
if ($LASTEXITCODE -ne 0) { throw "npm install tailwind dev deps failed with exit code $LASTEXITCODE" }

Write-Host "\nAll animation libraries installed successfully." -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Green
Write-Host "  - Start dev server: npm run dev"
Write-Host "  - Import and use the libraries in your components as needed."
Write-Host "  - If you still face ERESOLVE issues, try re-running with -ForceLegacyPeerDeps or clean node_modules + package-lock.json"
