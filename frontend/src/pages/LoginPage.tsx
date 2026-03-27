import { useState, useEffect, useRef, useCallback } from 'react'
import { Eye, EyeOff, Loader2, Shield } from 'lucide-react'

interface LoginPageProps {
  onLogin: (username: string, password: string) => Promise<unknown>
}

// ── Particle Animation ───────────────────────────────────────────

interface Particle {
  x: number; y: number
  vx: number; vy: number
  radius: number; opacity: number
}

function useParticles(canvasRef: React.RefObject<HTMLCanvasElement | null>) {
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let animId: number
    const particles: Particle[] = []
    const PARTICLE_COUNT = 80
    const CONNECTION_DIST = 160
    const COLORS = ['16, 185, 129', '6, 182, 212', '59, 130, 246'] // emerald, cyan, blue

    function resize() {
      canvas!.width = window.innerWidth
      canvas!.height = window.innerHeight
    }
    resize()
    window.addEventListener('resize', resize)

    // Init particles
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.6,
        vy: (Math.random() - 0.5) * 0.6,
        radius: Math.random() * 1.8 + 1.2,
        opacity: Math.random() * 0.4 + 0.4,
      })
    }

    function draw() {
      ctx!.clearRect(0, 0, canvas!.width, canvas!.height)

      // Draw connections
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x
          const dy = particles[i].y - particles[j].y
          const dist = Math.sqrt(dx * dx + dy * dy)
          if (dist < CONNECTION_DIST) {
            const alpha = (1 - dist / CONNECTION_DIST) * 0.3
            ctx!.strokeStyle = `rgba(${COLORS[i % COLORS.length]}, ${alpha})`
            ctx!.lineWidth = 0.5
            ctx!.beginPath()
            ctx!.moveTo(particles[i].x, particles[i].y)
            ctx!.lineTo(particles[j].x, particles[j].y)
            ctx!.stroke()
          }
        }
      }

      // Draw and update particles
      for (const p of particles) {
        ctx!.beginPath()
        ctx!.arc(p.x, p.y, p.radius, 0, Math.PI * 2)
        ctx!.fillStyle = `rgba(${COLORS[0]}, ${p.opacity})`
        ctx!.fill()

        p.x += p.vx
        p.y += p.vy

        if (p.x < 0 || p.x > canvas!.width) p.vx *= -1
        if (p.y < 0 || p.y > canvas!.height) p.vy *= -1
      }

      animId = requestAnimationFrame(draw)
    }
    draw()

    return () => {
      cancelAnimationFrame(animId)
      window.removeEventListener('resize', resize)
    }
  }, [canvasRef])
}

// ── Login Page Component ─────────────────────────────────────────

export function LoginPage({ onLogin }: LoginPageProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useParticles(canvasRef)

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    if (!username.trim() || !password) return

    setError('')
    setLoading(true)
    try {
      await onLogin(username.trim(), password)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }, [username, password, onLogin])

  return (
    <div className="fixed inset-0 flex items-center justify-center" style={{ background: '#131825' }}>
      {/* Particle canvas */}
      <canvas ref={canvasRef} className="fixed inset-0 z-0" />

      {/* Login modal */}
      <div className="relative z-10 w-full max-w-sm mx-4 animate-fade-up">
        <div className="rounded-2xl border border-[#3a4560] bg-[#1e2538]/95 backdrop-blur-xl shadow-2xl shadow-emerald-500/5 p-8">

          {/* Logo / Brand */}
          <div className="text-center mb-8">
            <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 border border-emerald-500/20 flex items-center justify-center shadow-lg shadow-emerald-500/10">
              <img src="/logo.png" alt="Restorex" className="w-10 h-10 rounded-lg" onError={(e) => {
                // Fallback to icon if logo not found
                (e.target as HTMLImageElement).style.display = 'none';
                (e.target as HTMLImageElement).parentElement!.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="rgb(16, 185, 129)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10"/></svg>'
              }} />
            </div>
            <h1 className="text-xl font-bold text-white tracking-tight">Restorex</h1>
            <p className="text-xs text-[#a0afc0] mt-1">Sign in to your account</p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Username */}
            <div className="space-y-1.5">
              <label className="text-[10px] font-semibold text-[#a0afc0] uppercase tracking-wider">Username</label>
              <input
                type="text"
                value={username}
                onChange={e => setUsername(e.target.value)}
                placeholder="admin"
                autoFocus
                autoComplete="username"
                className="w-full px-4 py-3 rounded-xl text-sm bg-[#1a2035] border border-[#3a4560] text-white placeholder:text-[#607085] focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20 transition-all"
              />
            </div>

            {/* Password */}
            <div className="space-y-1.5">
              <label className="text-[10px] font-semibold text-[#a0afc0] uppercase tracking-wider">Password</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  autoComplete="current-password"
                  className="w-full px-4 py-3 pr-11 rounded-xl text-sm bg-[#1a2035] border border-[#3a4560] text-white placeholder:text-[#607085] focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20 transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[#7080a0] hover:text-[#c0c8d8] transition-colors"
                >
                  {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            {/* Error */}
            {error && (
              <div className="px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/20">
                <p className="text-xs text-red-400">{error}</p>
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={loading || !username.trim() || !password}
              className="w-full py-3 rounded-xl text-sm font-bold bg-gradient-to-r from-emerald-600 to-emerald-500 text-white hover:from-emerald-500 hover:to-emerald-400 disabled:opacity-40 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/20"
            >
              {loading ? (
                <><Loader2 size={16} className="animate-spin" /> Signing in...</>
              ) : (
                <><Shield size={16} /> Sign In</>
              )}
            </button>
          </form>

          {/* Footer */}
          <p className="text-center text-[10px] text-[#607890] mt-6">
            Protected by JWT Authentication
          </p>
        </div>
      </div>
    </div>
  )
}
