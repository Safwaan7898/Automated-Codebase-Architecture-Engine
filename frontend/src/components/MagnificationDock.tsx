/**
 * MagnificationDock Component
 * 
 * A fixed-slot macOS-inspired dock component with fluid magnification effects,
 * spring physics, and tooltips. Built with Framer Motion.
 * 
 * Each icon sits in a FIXED-size slot (hit area never moves). Magnification animates
 * ONLY transform: scale on an inner element with transform-origin: bottom center.
 * Container width and height stay strictly constant.
 */

import {
  motion,
  MotionValue,
  useMotionValue,
  useSpring,
  useTransform,
  useReducedMotion,
  type SpringOptions,
  AnimatePresence,
} from 'framer-motion'
import React, { Children, cloneElement, useEffect, useRef, useState } from 'react'

export type DockItemData = {
  icon: React.ReactNode
  label: React.ReactNode
  onClick: () => void
  active?: boolean
  className?: string
}

export type DockProps = {
  items: DockItemData[]
  className?: string
  distance?: number
  panelHeight?: number
  baseItemSize?: number
  dockHeight?: number
  magnification?: number
  spring?: SpringOptions
}

type DockItemProps = {
  className?: string
  children: React.ReactNode
  onClick?: () => void
  active?: boolean
  mouseX: MotionValue<number>
  spring: SpringOptions
  distance: number
  baseItemSize: number
  magnification: number
}

function DockItem({
  children,
  className = '',
  onClick,
  active = false,
  mouseX,
  spring,
  distance,
  magnification,
  baseItemSize,
}: DockItemProps) {
  const slotRef = useRef<HTMLDivElement>(null)
  const isHovered = useMotionValue(0)
  const shouldReduceMotion = useReducedMotion()

  const mouseDistance = useTransform(mouseX, (val) => {
    const rect = slotRef.current?.getBoundingClientRect()
    if (!rect || val === Infinity) return Infinity
    return val - (rect.left + rect.width / 2)
  })

  const maxScale = baseItemSize > 0 ? magnification / baseItemSize : 1.45
  const targetScale = useTransform(
    mouseDistance,
    [-distance, 0, distance],
    [1, maxScale, 1],
    { clamp: true }
  )

  const springScale = useSpring(targetScale, spring)
  const scale = shouldReduceMotion ? 1 : springScale

  return (
    <div
      ref={slotRef}
      className="relative flex items-end justify-center flex-shrink-0"
      style={{
        width: baseItemSize,
        height: baseItemSize,
        overflow: 'visible',
      }}
      data-testid="dock-slot"
    >
      <motion.button
        type="button"
        style={{
          scale,
          transformOrigin: 'bottom center',
          width: baseItemSize,
          height: baseItemSize,
          willChange: 'transform',
          background: active ? undefined : 'var(--dock-item-bg)',
          borderColor: active ? undefined : 'var(--dock-item-border)',
          color: active ? undefined : 'var(--dock-item-text)',
        }}
        onHoverStart={() => isHovered.set(1)}
        onHoverEnd={() => isHovered.set(0)}
        onFocus={() => isHovered.set(1)}
        onBlur={() => isHovered.set(0)}
        onClick={onClick}
        className={`relative inline-flex items-center justify-center rounded-2xl cursor-pointer border transition-colors duration-150 select-none ${
          active
            ? 'bg-gradient-to-b from-[#ffffff] via-[#cccccc] to-[#888888] text-black shadow-[0_0_20px_rgba(204,255,0,0.6)] border-[#CCFF00]'
            : 'shadow-lg hover:border-[#CCFF00]/60'
        } ${className}`}
        tabIndex={0}
        aria-haspopup="true"
        data-testid="dock-item-inner"
      >
        {Children.map(children, (child) =>
          React.isValidElement(child)
            ? cloneElement(child as React.ReactElement<{ isHovered?: MotionValue<number>; active?: boolean }>, {
                isHovered,
                active,
              })
            : child
        )}
        {active && (
          <span className="absolute -bottom-1.5 w-1.5 h-1.5 rounded-full bg-[#CCFF00] shadow-[0_0_6px_#CCFF00]" />
        )}
      </motion.button>
    </div>
  )
}

type DockLabelProps = {
  className?: string
  children: React.ReactNode
  isHovered?: MotionValue<number>
}

function DockLabel({ children, className = '', isHovered }: DockLabelProps) {
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    if (!isHovered) return
    const unsubscribe = isHovered.on('change', (latest) => {
      setIsVisible(latest === 1)
    })
    return () => unsubscribe()
  }, [isHovered])

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ opacity: 0, y: 0, scale: 0.9 }}
          animate={{ opacity: 1, y: -10, scale: 1 }}
          exit={{ opacity: 0, y: 0, scale: 0.9 }}
          transition={{ duration: 0.15 }}
          className={`${className} absolute -top-9 left-1/2 w-fit whitespace-pre rounded-lg border px-2.5 py-1 text-[11px] font-mono tracking-wider shadow-lg backdrop-blur-md pointer-events-none z-50`}
          role="tooltip"
          style={{
            x: '-50%',
            background: 'var(--dock-tooltip-bg)',
            borderColor: 'var(--dock-tooltip-border)',
            color: 'var(--dock-tooltip-text)',
          }}
        >
          {children}
        </motion.div>
      )}
    </AnimatePresence>
  )
}

type DockIconProps = {
  className?: string
  children: React.ReactNode
  isHovered?: MotionValue<number>
  active?: boolean
}

function DockIcon({ children, className = '', active = false }: DockIconProps) {
  return (
    <div
      className={`flex items-center justify-center transition-colors duration-150 ${
        active ? 'text-black' : 'text-inherit'
      } ${className}`}
    >
      {children}
    </div>
  )
}

export function MagnificationDock({
  items,
  className = '',
  spring = { stiffness: 300, damping: 28 },
  magnification = 58,
  distance = 160,
  panelHeight = 56,
  baseItemSize = 40,
}: DockProps) {
  const mouseX = useMotionValue(Infinity)

  return (
    <div
      style={{ overflow: 'visible' }}
      className="flex max-w-full items-center justify-center pointer-events-auto select-none"
      data-testid="magnification-dock-wrapper"
    >
      <div
        onMouseMove={(e) => {
          mouseX.set(e.clientX)
        }}
        onMouseLeave={() => {
          mouseX.set(Infinity)
        }}
        className={`${className} flex items-center w-fit gap-2.5 rounded-full border backdrop-blur-2xl px-3`}
        style={{
          height: panelHeight,
          background: 'var(--dock-bg)',
          borderColor: 'var(--dock-border)',
          boxShadow: 'var(--dock-shadow)',
          overflow: 'visible',
        }}
        role="toolbar"
        aria-label="Application dock"
        data-testid="magnification-dock-container"
      >
        {items.map((item, index) => (
          <DockItem
            key={index}
            onClick={item.onClick}
            active={item.active}
            className={item.className}
            mouseX={mouseX}
            spring={spring}
            distance={distance}
            magnification={magnification}
            baseItemSize={baseItemSize}
          >
            <DockIcon active={item.active}>{item.icon}</DockIcon>
            <DockLabel>{item.label}</DockLabel>
          </DockItem>
        ))}
      </div>
    </div>
  )
}

export default MagnificationDock
