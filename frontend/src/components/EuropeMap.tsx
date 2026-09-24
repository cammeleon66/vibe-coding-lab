export interface MapNode {
  id: string
  label: string
  /** Label kept once the map has zoomed past this node's step. */
  short?: string
  lon: number
  lat: number
  step: number
  country: 'NL' | 'DE' | 'IT' | 'EU'
  highlight?: boolean
}

export interface MapLink {
  from: string
  to: string
  step: number
  highlight?: boolean
}

export interface MapView {
  lon: [number, number]
  lat: [number, number]
}

const WIDTH = 720
const HEIGHT = 520
const LAT_STRETCH = 1.6

const project = (lon: number, lat: number) => ({ x: lon, y: -lat * LAT_STRETCH })

function frame(view: MapView) {
  const topLeft = project(view.lon[0], view.lat[1])
  const bottomRight = project(view.lon[1], view.lat[0])
  const width = bottomRight.x - topLeft.x
  const height = bottomRight.y - topLeft.y
  const scale = Math.min(WIDTH / width, HEIGHT / height)
  return {
    scale,
    cx: topLeft.x + width / 2,
    cy: topLeft.y + height / 2,
  }
}

export function EuropeMap({
  nodes,
  links,
  step,
  view,
}: {
  nodes: MapNode[]
  links: MapLink[]
  step: number
  view: MapView
}) {
  const camera = frame(view)
  const place = (lon: number, lat: number) => {
    const point = project(lon, lat)
    return {
      x: WIDTH / 2 + (point.x - camera.cx) * camera.scale,
      y: HEIGHT / 2 + (point.y - camera.cy) * camera.scale,
    }
  }
  const byId = new Map(nodes.map((node) => [node.id, node]))
  const graticule = []
  for (let lon = -10; lon <= 30; lon += 5) {
    const a = place(lon, 34)
    const b = place(lon, 64)
    graticule.push(<line key={`lon${lon}`} x1={a.x} y1={a.y} x2={b.x} y2={b.y} />)
  }
  for (let lat = 35; lat <= 65; lat += 5) {
    const a = place(-12, lat)
    const b = place(32, lat)
    graticule.push(<line key={`lat${lat}`} x1={a.x} y1={a.y} x2={b.x} y2={b.y} />)
  }

  return (
    <svg
      className="europe-map"
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      role="img"
      aria-label={`Network map showing ${nodes.filter((node) => node.step <= step).length} participating hospitals`}
    >
      <g className="map-graticule">{graticule}</g>
      <g className="map-links">
        {links.map((link) => {
          const from = byId.get(link.from)
          const to = byId.get(link.to)
          if (!from || !to) return null
          const a = place(from.lon, from.lat)
          const b = place(to.lon, to.lat)
          const visible = link.step <= step
          const bend = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 - Math.hypot(b.x - a.x, b.y - a.y) * 0.18 }
          return (
            <path
              key={`${link.from}-${link.to}`}
              className={`${visible ? 'visible' : ''} ${link.highlight && step >= 3 ? 'highlight' : ''}`}
              d={`M ${a.x} ${a.y} Q ${bend.x} ${bend.y} ${b.x} ${b.y}`}
            />
          )
        })}
      </g>
      <g className="map-nodes">
        {nodes.map((node) => {
          const point = place(node.lon, node.lat)
          const visible = node.step <= step
          const fresh = node.step === step
          const label = fresh ? node.label : (node.short ?? '')
          return (
            <g
              key={node.id}
              className={`map-node ${node.country} ${visible ? 'visible' : ''} ${fresh ? 'fresh' : ''} ${node.highlight && step >= 3 ? 'highlight' : ''}`}
              transform={`translate(${point.x} ${point.y})`}
            >
              <circle className="halo" r={13} />
              <circle className="dot" r={5.5} />
              {label && (
                <text x={9} y={4}>
                  {label}
                </text>
              )}
            </g>
          )
        })}
      </g>
    </svg>
  )
}
