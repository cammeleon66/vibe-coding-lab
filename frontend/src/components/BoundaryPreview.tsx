import { ArrowRight, Lock } from 'lucide-react'

export function BoundaryPreview({
  crossesTitle,
  crosses,
  staysTitle,
  stays,
  note,
}: {
  crossesTitle: string
  crosses: string[]
  staysTitle: string
  stays: string[]
  note?: string
}) {
  return (
    <div className="boundary-preview">
      <section className="boundary-side crosses">
        <h3>
          <ArrowRight size={16} />
          {crossesTitle}
        </h3>
        <ul>
          {crosses.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>
      <section className="boundary-side stays">
        <h3>
          <Lock size={15} />
          {staysTitle}
        </h3>
        <ul>
          {stays.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        {note && <p>{note}</p>}
      </section>
    </div>
  )
}
