import { useState } from 'react'
import { EuropeMap, type MapLink, type MapNode, type MapView } from '../components/EuropeMap'

const nodes: MapNode[] = [
  { id: 'uroc', label: 'Utrecht Regional Oncology Centre', short: 'Utrecht', lon: 5.08, lat: 52.1, step: 0, country: 'NL', highlight: true },
  { id: 'stadshaven', label: 'Stadshaven Hospital', lon: 5.2, lat: 52.05, step: 0, country: 'NL' },
  { id: 'amsterdam', label: 'Amsterdam', lon: 4.9, lat: 52.37, step: 1, country: 'NL' },
  { id: 'rotterdam', label: 'Rotterdam', lon: 4.48, lat: 51.92, step: 1, country: 'NL' },
  { id: 'nijmegen', label: 'Nijmegen', lon: 5.86, lat: 51.84, step: 1, country: 'NL' },
  { id: 'groningen', label: 'Groningen', lon: 6.57, lat: 53.22, step: 1, country: 'NL' },
  { id: 'maastricht', label: 'Maastricht', lon: 5.69, lat: 50.85, step: 1, country: 'NL' },
  { id: 'essen', label: 'Essen', lon: 7.01, lat: 51.46, step: 2, country: 'DE' },
  { id: 'heidelberg', label: 'Heidelberg', lon: 8.67, lat: 49.4, step: 2, country: 'DE' },
  { id: 'berlin', label: 'Berlin', lon: 13.4, lat: 52.52, step: 2, country: 'DE' },
  { id: 'milan', label: 'Milan', short: 'Milan', lon: 9.19, lat: 45.46, step: 2, country: 'IT', highlight: true },
  { id: 'bologna', label: 'Bologna', lon: 11.34, lat: 44.49, step: 2, country: 'IT' },
  { id: 'rome', label: 'Rome', lon: 12.5, lat: 41.9, step: 2, country: 'IT' },
  { id: 'paris', label: 'Paris', lon: 2.35, lat: 48.86, step: 3, country: 'EU' },
  { id: 'brussels', label: 'Brussels', lon: 4.35, lat: 50.85, step: 3, country: 'EU' },
  { id: 'barcelona', label: 'Barcelona', lon: 2.17, lat: 41.39, step: 3, country: 'EU' },
  { id: 'lisbon', label: 'Lisbon', lon: -9.14, lat: 38.72, step: 3, country: 'EU' },
  { id: 'vienna', label: 'Vienna', lon: 16.37, lat: 48.21, step: 3, country: 'EU' },
  { id: 'warsaw', label: 'Warsaw', lon: 21.0, lat: 52.23, step: 3, country: 'EU' },
  { id: 'copenhagen', label: 'Copenhagen', lon: 12.57, lat: 55.68, step: 3, country: 'EU' },
  { id: 'stockholm', label: 'Stockholm', lon: 18.07, lat: 59.33, step: 3, country: 'EU' },
]

const links: MapLink[] = [
  { from: 'uroc', to: 'stadshaven', step: 0 },
  { from: 'uroc', to: 'amsterdam', step: 1 },
  { from: 'uroc', to: 'rotterdam', step: 1 },
  { from: 'uroc', to: 'nijmegen', step: 1 },
  { from: 'uroc', to: 'groningen', step: 1 },
  { from: 'nijmegen', to: 'maastricht', step: 1 },
  { from: 'nijmegen', to: 'essen', step: 2 },
  { from: 'essen', to: 'berlin', step: 2 },
  { from: 'essen', to: 'heidelberg', step: 2 },
  { from: 'heidelberg', to: 'milan', step: 2 },
  { from: 'milan', to: 'bologna', step: 2 },
  { from: 'bologna', to: 'rome', step: 2 },
  { from: 'milan', to: 'uroc', step: 3, highlight: true },
  { from: 'brussels', to: 'paris', step: 3 },
  { from: 'brussels', to: 'uroc', step: 3 },
  { from: 'paris', to: 'barcelona', step: 3 },
  { from: 'barcelona', to: 'lisbon', step: 3 },
  { from: 'heidelberg', to: 'vienna', step: 3 },
  { from: 'berlin', to: 'warsaw', step: 3 },
  { from: 'berlin', to: 'copenhagen', step: 3 },
  { from: 'copenhagen', to: 'stockholm', step: 3 },
]

interface NetworkScope {
  scope: string
  view: MapView
  summary: string
}

const scopes: NetworkScope[] = [
  { scope: 'Utrecht', view: { lon: [4.85, 5.45], lat: [51.93, 52.22] }, summary: '2 centres connected' },
  { scope: 'Netherlands', view: { lon: [3.2, 7.6], lat: [50.5, 53.6] }, summary: '7 centres connected' },
  { scope: 'Germany and Italy', view: { lon: [1.5, 16.5], lat: [40.8, 54.2] }, summary: '13 centres connected' },
  { scope: 'Europe', view: { lon: [-11, 24], lat: [37, 61] }, summary: '21 centres connected' },
]

const centres: { name: string; country: string; contact: string; step: number }[] = [
  { name: 'Utrecht Regional Oncology Centre', country: 'NL', contact: 'Dr Sophie Bakker', step: 0 },
  { name: 'Stadshaven Hospital Utrecht', country: 'NL', contact: 'Dr Noor Jansen', step: 0 },
  { name: 'Amsterdam oncology centre', country: 'NL', contact: 'Regional oncology team', step: 1 },
  { name: 'Rotterdam oncology centre', country: 'NL', contact: 'Regional oncology team', step: 1 },
  { name: 'Nijmegen oncology centre', country: 'NL', contact: 'Regional oncology team', step: 1 },
  { name: 'Groningen oncology centre', country: 'NL', contact: 'Regional oncology team', step: 1 },
  { name: 'Maastricht oncology centre', country: 'NL', contact: 'Regional oncology team', step: 1 },
  { name: 'Heidelberg oncology centre', country: 'DE', contact: 'Dr Katrin Weber', step: 2 },
  { name: 'Essen oncology centre', country: 'DE', contact: 'Dr Jonas Richter', step: 2 },
  { name: 'Berlin oncology centre', country: 'DE', contact: 'Oncology team', step: 2 },
  { name: 'Istituto Nazionale dei Tumori, Milan', country: 'IT', contact: 'Dr Luca Bianchi', step: 2 },
  { name: 'Bologna oncology centre', country: 'IT', contact: 'Dr Chiara Rossi', step: 2 },
  { name: 'Rome oncology centre', country: 'IT', contact: 'Oncology team', step: 2 },
  { name: 'UMC Utrecht', country: 'NL', contact: 'Dr Eva van Dijk', step: 3 },
  { name: 'Paris, Brussels, Barcelona, Lisbon', country: 'FR · BE · ES · PT', contact: 'Oncology teams', step: 3 },
  { name: 'Vienna, Warsaw, Copenhagen, Stockholm', country: 'AT · PL · DK · SE', contact: 'Oncology teams', step: 3 },
]

const policies = [
  'Patient data remains at the source institution.',
  'Each institution operates its own exchange assistant.',
  'Every release requires approval by a named clinician.',
  'Only approved summaries are exchanged, with provenance links.',
]

export function ScaleNetworkScene() {
  const [step, setStep] = useState(0)
  const current = scopes[step]
  const visible = centres.filter((centre) => centre.step <= step)
  return (
    <div className="scene-stack">
      <div className="segmented" role="group" aria-label="Network scope">
        {scopes.map((item, index) => (
          <button
            key={item.scope}
            type="button"
            aria-pressed={index === step}
            onClick={() => setStep(index)}
          >
            {item.scope}
          </button>
        ))}
      </div>
      <div className="network-layout">
        <section className="panel">
          <h2 className="panel-title">
            Network overview · {current.scope}
            <span className="panel-title-meta">{current.summary}</span>
          </h2>
          <div className="map-frame">
            <EuropeMap nodes={nodes} links={links} step={step} view={current.view} />
          </div>
        </section>
        <section className="panel">
          <h2 className="panel-title">Network policy</h2>
          <p className="panel-note">Identical for every connected centre.</p>
          <ul className="plain-list">
            {policies.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      </div>
      <section className="panel">
        <h2 className="panel-title">Connected centres ({visible.length})</h2>
        <table className="grid">
          <thead>
            <tr>
              <th scope="col">Centre</th>
              <th scope="col">Country</th>
              <th scope="col">Contact</th>
              <th scope="col">Exchange assistant</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((centre) => (
              <tr key={centre.name} className={centre.step === step ? 'row-new' : ''}>
                <td>{centre.name}</td>
                <td>{centre.country}</td>
                <td>{centre.contact}</td>
                <td>
                  <span className="badge success">Connected</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  )
}