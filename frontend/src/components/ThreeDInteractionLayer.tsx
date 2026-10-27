import React, { useEffect, useRef } from 'react'
import * as THREE from 'three'

interface ThreeDInteractionLayerProps {
  className?: string
  interactive?: boolean
}

export const ThreeDInteractionLayer: React.FC<ThreeDInteractionLayerProps> = ({
  className = '',
  interactive = true,
}) => {
  const mountRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    const container = mountRef.current
    if (!container) return

    // 1. Scene, Camera, Renderer
    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(
      60,
      container.clientWidth / container.clientHeight,
      0.1,
      1000
    )
    camera.position.z = 32

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true })
    renderer.setSize(container.clientWidth, container.clientHeight)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    container.appendChild(renderer.domElement)

    // 2. Color Palettes (Neon Magenta, Cyan, Lime)
    const COLOR_SETS = [
      { magenta: 0xf967fb, cyan: 0x06b6d4, lime: 0xa3e635 },
      { magenta: 0xa3e635, cyan: 0xf967fb, lime: 0x06b6d4 },
      { magenta: 0x06b6d4, cyan: 0xa3e635, lime: 0xf967fb },
    ]
    let colorSetIndex = 0

    // 3. Create Reactive Spline Tubes
    const tubeGroup = new THREE.Group()
    scene.add(tubeGroup)

    const tubes: Array<{
      mesh: THREE.Mesh
      material: THREE.MeshStandardMaterial
      initialPoints: THREE.Vector3[]
      speed: number
    }> = []

    const tubeConfigs = [
      { color: COLOR_SETS[0].magenta, radius: 0.35, speed: 0.008, offset: 0 },
      { color: COLOR_SETS[0].cyan,    radius: 0.30, speed: 0.012, offset: Math.PI / 3 },
      { color: COLOR_SETS[0].lime,    radius: 0.28, speed: 0.010, offset: (Math.PI * 2) / 3 },
      { color: COLOR_SETS[0].magenta, radius: 0.22, speed: 0.014, offset: Math.PI },
      { color: COLOR_SETS[0].cyan,    radius: 0.25, speed: 0.009, offset: (Math.PI * 4) / 3 },
    ]

    tubeConfigs.forEach((cfg) => {
      const points: THREE.Vector3[] = []
      const numPoints = 12
      for (let i = 0; i < numPoints; i++) {
        const u = i / (numPoints - 1)
        const angle = u * Math.PI * 2 + cfg.offset
        const x = Math.sin(angle) * 14 + Math.sin(u * Math.PI * 4) * 4
        const y = (u - 0.5) * 28 + Math.cos(angle * 2) * 3
        const z = Math.cos(angle) * 12 + Math.sin(u * Math.PI * 3) * 5
        points.push(new THREE.Vector3(x, y, z))
      }

      const curve = new THREE.CatmullRomCurve3(points, true)
      const geometry = new THREE.TubeGeometry(curve, 64, cfg.radius, 8, true)
      const material = new THREE.MeshStandardMaterial({
        color: cfg.color,
        emissive: cfg.color,
        emissiveIntensity: 0.6,
        roughness: 0.2,
        metalness: 0.8,
        wireframe: false,
      })

      const mesh = new THREE.Mesh(geometry, material)
      tubeGroup.add(mesh)
      tubes.push({
        mesh,
        material,
        initialPoints: points,
        speed: cfg.speed,
      })
    })

    // Ambient & Point Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.4)
    scene.add(ambientLight)

    const light1 = new THREE.PointLight(0xf967fb, 2, 80)
    light1.position.set(20, 20, 20)
    scene.add(light1)

    const light2 = new THREE.PointLight(0x06b6d4, 2, 80)
    light2.position.set(-20, -20, 20)
    scene.add(light2)

    const light3 = new THREE.PointLight(0xa3e635, 1.5, 80)
    light3.position.set(0, 10, -10)
    scene.add(light3)

    // 4. Interaction Listeners (Mouse Move & Click)
    const mouse = { x: 0, y: 0, targetX: 0, targetY: 0 }
    let pulseScale = 1.0

    const onMouseMove = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect()
      mouse.targetX = ((e.clientX - rect.left) / rect.width) * 2 - 1
      mouse.targetY = -(((e.clientY - rect.top) / rect.height) * 2 - 1)
    }

    const onClick = () => {
      // Trigger color spectrum shift on click
      colorSetIndex = (colorSetIndex + 1) % COLOR_SETS.length
      const nextPalette = COLOR_SETS[colorSetIndex]
      pulseScale = 1.25

      tubes.forEach((t, idx) => {
        const targetColor =
          idx % 3 === 0
            ? nextPalette.magenta
            : idx % 3 === 1
            ? nextPalette.cyan
            : nextPalette.lime
        t.material.color.setHex(targetColor)
        t.material.emissive.setHex(targetColor)
      })
    }

    if (interactive) {
      window.addEventListener('mousemove', onMouseMove)
      window.addEventListener('click', onClick)
    }

    // 5. Responsive Resize
    const onResize = () => {
      if (!container) return
      camera.aspect = container.clientWidth / container.clientHeight
      camera.updateProjectionMatrix()
      renderer.setSize(container.clientWidth, container.clientHeight)
    }
    window.addEventListener('resize', onResize)

    // 6. Animation Loop
    let animId: number
    const clock = new THREE.Clock()

    const animate = () => {
      animId = requestAnimationFrame(animate)
      const elapsedTime = clock.getElapsedTime()

      // Smooth mouse follow
      mouse.x += (mouse.targetX - mouse.x) * 0.05
      mouse.y += (mouse.targetY - mouse.y) * 0.05

      // Tube group rotation & parallax
      tubeGroup.rotation.y = elapsedTime * 0.12 + mouse.x * 0.6
      tubeGroup.rotation.x = Math.sin(elapsedTime * 0.08) * 0.2 - mouse.y * 0.5
      tubeGroup.rotation.z = Math.cos(elapsedTime * 0.05) * 0.1

      // Dynamic scale decay after click
      if (pulseScale > 1.0) {
        pulseScale += (1.0 - pulseScale) * 0.08
      }
      tubeGroup.scale.set(pulseScale, pulseScale, pulseScale)

      renderer.render(scene, camera)
    }
    animate()

    // 7. Cleanup
    return () => {
      cancelAnimationFrame(animId)
      window.removeEventListener('resize', onResize)
      if (interactive) {
        window.removeEventListener('mousemove', onMouseMove)
        window.removeEventListener('click', onClick)
      }
      tubes.forEach((t) => {
        t.mesh.geometry.dispose()
        t.material.dispose()
      })
      renderer.dispose()
      if (renderer.domElement.parentNode === container) {
        container.removeChild(renderer.domElement)
      }
    }
  }, [interactive])

  return (
    <div
      ref={mountRef}
      className={`absolute inset-0 pointer-events-none overflow-hidden z-0 ${className}`}
      aria-hidden="true"
    />
  )
}
