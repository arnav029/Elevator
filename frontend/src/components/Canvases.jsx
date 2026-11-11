import { useEffect, useRef } from 'react'
import { drawPixels, drawSprite, drawWindow } from '../draw'
import { SPRITES } from '../sprites'
import { timeOfDay } from '../constants'

export function PixelArt({ pixels, className = '', style }) {
  const ref = useRef(null)
  useEffect(() => {
    if (ref.current) drawPixels(ref.current, pixels)
  }, [pixels])
  return <canvas ref={ref} className={`pixelated ${className}`} style={style} />
}

export function Sprite({ name, className = '', style }) {
  const ref = useRef(null)
  useEffect(() => {
    if (ref.current && SPRITES[name]) drawSprite(ref.current, SPRITES[name])
  }, [name])
  return <canvas ref={ref} className={`pixelated sprite sprite-${name} ${className}`} style={style} />
}

export function WindowView({ view, floor }) {
  const ref = useRef(null)
  useEffect(() => {
    let raf
    let last = 0
    const start = performance.now()
    const loop = (now) => {
      if (now - last > 120 && ref.current) {
        last = now
        drawWindow(ref.current, { view, floor, tod: timeOfDay(), t: (now - start) / 1000 })
      }
      raf = requestAnimationFrame(loop)
    }
    raf = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(raf)
  }, [view, floor])
  return (
    <div className={`window window-${view}`}>
      <canvas ref={ref} className="pixelated" />
      <div className="window-cross" />
    </div>
  )
}
