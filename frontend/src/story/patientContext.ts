import type { JourneySnapshot, StoryScene } from '../api/types'

export interface PatientContext {
  name: string
  id: string
  detail: string
  institution: string
}

/** The patient shown in the banner for the scene on screen. */
export function patientContext(snapshot: JourneySnapshot, scene: StoryScene): PatientContext | null {
  if (scene.chapter === 'local') {
    const exchange = snapshot.regional_exchange
    return {
      name: exchange.patient_label,
      id: exchange.case_id,
      detail: 'Colorectal cancer with liver metastases',
      institution: exchange.requesting_institution,
    }
  }
  if (scene.chapter === 'cross_border') {
    const patient =
      snapshot.patients.find((item) => item.case_id === snapshot.selected_patient_id) ?? null
    if (!patient) return null
    return {
      name: patient.display_name,
      id: patient.case_id,
      detail: `${patient.age_band} · ${patient.diagnosis}`,
      institution: 'Istituto Nazionale dei Tumori, Milan',
    }
  }
  return null
}
