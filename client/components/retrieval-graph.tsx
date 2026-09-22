"use client"

import { useEffect, useRef } from "react"
import type * as THREE_NS from "three"

type Three = typeof THREE_NS

const NODE_COUNT = 220
const RADIUS = 1.6
const LINKS_PER_QUERY = 3
const EVENT_DURATION = 3.4 // seconds per "error → fix" cycle
const EMERALD = 0x10b981
const EMERALD_BRIGHT = 0x34d399
const RED = 0xef4444

/**
 * Hero background: a slowly rotating cloud of reference-code "chunks".
 * Periodically an error node appears, links to its nearest references,
 * and turns green — the retrieve-then-fix loop the app performs.
 */
export function RetrievalGraph({ className }: { className?: string }) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    let disposed = false
    let cleanup = () => {}

    import("three").then((THREE) => {
      if (disposed) return
      cleanup = mountScene(THREE, container)
    })

    return () => {
      disposed = true
      cleanup()
    }
  }, [])

  return <div ref={containerRef} aria-hidden="true" className={className} />
}

function mountScene(THREE: Three, container: HTMLElement) {
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.domElement.style.display = "block"
  container.appendChild(renderer.domElement)

  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 50)
  camera.position.z = 6

  const group = new THREE.Group()
  group.rotation.x = 0.35
  scene.add(group)

  const sprite = makeDotTexture(THREE)
  const nodes = fibonacciSphere(THREE, NODE_COUNT, RADIUS)

  // Reference nodes
  const nodeGeometry = new THREE.BufferGeometry().setFromPoints(nodes)
  const nodeMaterial = new THREE.PointsMaterial({
    color: EMERALD,
    size: 0.07,
    map: sprite,
    transparent: true,
    opacity: 0.85,
    depthWrite: false,
  })
  group.add(new THREE.Points(nodeGeometry, nodeMaterial))

  // Faint nearest-neighbour mesh
  const edgePositions: number[] = []
  nodes.forEach((a, i) => {
    nearest(nodes, a, 2, i).forEach((j) => {
      if (j > i) edgePositions.push(a.x, a.y, a.z, nodes[j].x, nodes[j].y, nodes[j].z)
    })
  })
  const edgeGeometry = new THREE.BufferGeometry()
  edgeGeometry.setAttribute("position", new THREE.Float32BufferAttribute(edgePositions, 3))
  const edgeMaterial = new THREE.LineBasicMaterial({ color: EMERALD, transparent: true, opacity: 0.12 })
  group.add(new THREE.LineSegments(edgeGeometry, edgeMaterial))

  // Two staggered error→fix queries keep the scene alive without clutter
  const queries = [createQuery(THREE, group, nodes, sprite), createQuery(THREE, group, nodes, sprite)]

  const pointer = { x: 0, y: 0 }
  const onPointerMove = (e: PointerEvent) => {
    pointer.x = (e.clientX / window.innerWidth) * 2 - 1
    pointer.y = (e.clientY / window.innerHeight) * 2 - 1
  }

  const resize = () => {
    const { clientWidth: w, clientHeight: h } = container
    if (!w || !h) return
    renderer.setSize(w, h)
    camera.aspect = w / h
    camera.updateProjectionMatrix()
    // Sit the sphere over the right-hand column on wide layouts
    const visibleWidth = 2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) * camera.position.z * camera.aspect
    group.position.x = camera.aspect > 1.3 ? visibleWidth * 0.22 : 0
    if (reducedMotion) renderer.render(scene, camera)
  }
  const resizeObserver = new ResizeObserver(resize)
  resizeObserver.observe(container)

  let elapsed = 0
  let last = performance.now()
  const tick = () => {
    const now = performance.now()
    const dt = Math.min((now - last) / 1000, 0.05)
    last = now
    elapsed += dt

    group.rotation.y += dt * 0.08
    group.rotation.x += (0.35 + pointer.y * 0.15 - group.rotation.x) * 0.03
    group.rotation.z += (pointer.x * 0.1 - group.rotation.z) * 0.03

    queries.forEach((q, i) => q.update(elapsed + i * (EVENT_DURATION / 2)))
    renderer.render(scene, camera)
  }

  if (reducedMotion) {
    // A single still frame showing one query mid-fix
    queries[0].update(EVENT_DURATION * 0.6)
    queries[1].update(0)
  } else {
    window.addEventListener("pointermove", onPointerMove, { passive: true })
  }
  resize()

  // Only animate while the hero is on screen
  const visibility = new IntersectionObserver(([entry]) => {
    if (reducedMotion) return
    if (entry.isIntersecting) {
      last = performance.now()
      renderer.setAnimationLoop(tick)
    } else {
      renderer.setAnimationLoop(null)
    }
  })
  visibility.observe(container)

  return () => {
    visibility.disconnect()
    resizeObserver.disconnect()
    window.removeEventListener("pointermove", onPointerMove)
    renderer.setAnimationLoop(null)
    queries.forEach((q) => q.dispose())
    nodeGeometry.dispose()
    nodeMaterial.dispose()
    edgeGeometry.dispose()
    edgeMaterial.dispose()
    sprite.dispose()
    renderer.dispose()
    renderer.domElement.remove()
  }
}

/** One error node that retrieves its nearest references and turns green. */
function createQuery(THREE: Three, parent: THREE_NS.Object3D, nodes: THREE_NS.Vector3[], sprite: THREE_NS.Texture) {
  const origin = new THREE.Vector3()
  let targets: THREE_NS.Vector3[] = []
  let cycle = -1

  const errorGeometry = new THREE.BufferGeometry().setFromPoints([origin])
  const errorMaterial = new THREE.PointsMaterial({ size: 0.2, map: sprite, transparent: true, depthWrite: false })
  const errorPoint = new THREE.Points(errorGeometry, errorMaterial)

  const linkPositions = new Float32Array(LINKS_PER_QUERY * 6)
  const linkGeometry = new THREE.BufferGeometry()
  linkGeometry.setAttribute("position", new THREE.BufferAttribute(linkPositions, 3))
  const linkMaterial = new THREE.LineBasicMaterial({ color: EMERALD_BRIGHT, transparent: true })
  const links = new THREE.LineSegments(linkGeometry, linkMaterial)

  const hitGeometry = new THREE.BufferGeometry().setFromPoints(Array.from({ length: LINKS_PER_QUERY }, () => origin))
  const hitMaterial = new THREE.PointsMaterial({
    color: EMERALD_BRIGHT,
    size: 0.14,
    map: sprite,
    transparent: true,
    depthWrite: false,
  })
  const hits = new THREE.Points(hitGeometry, hitMaterial)

  parent.add(links, hits, errorPoint)

  const red = new THREE.Color(RED)
  const green = new THREE.Color(EMERALD_BRIGHT)
  const tmp = new THREE.Vector3()

  const respawn = () => {
    origin.randomDirection().multiplyScalar(RADIUS * 1.45)
    errorGeometry.setFromPoints([origin])
    targets = nearest(nodes, origin, LINKS_PER_QUERY).map((i) => nodes[i])
    hitGeometry.setFromPoints(targets)
  }

  const update = (time: number) => {
    const n = Math.floor(time / EVENT_DURATION)
    if (n !== cycle) {
      cycle = n
      respawn()
    }
    const t = (time % EVENT_DURATION) / EVENT_DURATION

    const appear = smooth(range(t, 0, 0.15))
    const reach = smooth(range(t, 0.15, 0.45))
    const fix = smooth(range(t, 0.45, 0.65))
    const fade = 1 - smooth(range(t, 0.8, 1))

    errorMaterial.opacity = appear * fade
    errorMaterial.color.lerpColors(red, green, fix)
    errorMaterial.size = 0.2 + Math.sin(t * Math.PI * 6) * 0.03 * (1 - fix)

    targets.forEach((target, i) => {
      tmp.lerpVectors(origin, target, reach)
      origin.toArray(linkPositions, i * 6)
      tmp.toArray(linkPositions, i * 6 + 3)
    })
    linkGeometry.attributes.position.needsUpdate = true
    linkMaterial.opacity = 0.7 * appear * fade
    hitMaterial.opacity = smooth(range(t, 0.35, 0.5)) * fade
  }

  const dispose = () => {
    parent.remove(links, hits, errorPoint)
    ;[errorGeometry, linkGeometry, hitGeometry, errorMaterial, linkMaterial, hitMaterial].forEach((r) => r.dispose())
  }

  return { update, dispose }
}

function fibonacciSphere(THREE: Three, count: number, radius: number) {
  const golden = Math.PI * (3 - Math.sqrt(5))
  return Array.from({ length: count }, (_, i) => {
    const y = 1 - (i / (count - 1)) * 2
    const r = Math.sqrt(1 - y * y)
    const theta = golden * i
    const jitter = radius * (0.88 + Math.random() * 0.12)
    return new THREE.Vector3(Math.cos(theta) * r, y, Math.sin(theta) * r).multiplyScalar(jitter)
  })
}

function nearest(nodes: THREE_NS.Vector3[], from: THREE_NS.Vector3, k: number, skip = -1) {
  return nodes
    .map((p, i) => ({ i, d: i === skip ? Infinity : p.distanceToSquared(from) }))
    .sort((a, b) => a.d - b.d)
    .slice(0, k)
    .map(({ i }) => i)
}

function makeDotTexture(THREE: Three) {
  const size = 64
  const canvas = document.createElement("canvas")
  canvas.width = canvas.height = size
  const ctx = canvas.getContext("2d")!
  const g = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2)
  g.addColorStop(0, "rgba(255,255,255,1)")
  g.addColorStop(0.45, "rgba(255,255,255,0.9)")
  g.addColorStop(1, "rgba(255,255,255,0)")
  ctx.fillStyle = g
  ctx.fillRect(0, 0, size, size)
  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  return texture
}

const range = (t: number, a: number, b: number) => Math.min(Math.max((t - a) / (b - a), 0), 1)
const smooth = (t: number) => t * t * (3 - 2 * t)
