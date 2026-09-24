"""Synthetic reference data. Every name, identifier and number here is fictional."""

from __future__ import annotations

from datetime import date
from typing import Any

DIAGNOSIS_DATE = date(2024, 5, 21)
PATIENT_ID = "umcu-00482913"

SITES: dict[str, dict[str, str]] = {
    "nl": {
        "name": "UMC Utrecht",
        "country": "Netherlands",
        "environment": "UMC UTRECHT · CLINICAL ENVIRONMENT",
        "clinician": "Dr Pieter de Boer",
        "clinician_role": "Treating medical oncologist",
    },
    "de": {
        "name": "Universitätsklinikum Heidelberg",
        "country": "Germany",
        "environment": "HEIDELBERG · SECURE CLINICAL ENVIRONMENT",
        "clinician": "Dr Anna Müller",
        "clinician_role": "GI oncology expert",
    },
    "hub": {
        "name": "European federation hub",
        "country": "EU",
        "environment": "FEDERATION HUB · ROUTING, POLICY AND AUDIT",
        "clinician": "Federation operations",
        "clinician_role": "Control room",
    },
}

# Patient identifier strings used by tests to prove nothing identifying leaves NL.
DIRECT_IDENTIFIERS = (
    "Maria",
    "Janssen",
    "JANSSEN",
    "UMCU-00482913",
    "1969-03-14",
    "Oudegracht",
    "3511",
    "+31 30 555 0142",
    "SYN-BSN-0001",
    "pacs.umcutrecht.example",
    "Johan",
)

SUBJECT = {"reference": f"Patient/{PATIENT_ID}", "display": "Maria Janssen"}


def _resource(
    resource_type: str,
    resource_id: str,
    category: str,
    tab: str,
    effective: str,
    title: str,
    **fields: Any,
) -> dict[str, Any]:
    return {
        "resourceType": resource_type,
        "id": resource_id,
        "meta": {"category": category, "tab": tab, "title": title},
        "subject": SUBJECT,
        "effectiveDate": effective,
        **fields,
    }


def maria_record() -> list[dict[str, Any]]:
    """27 FHIR-shaped resources held only by UMC Utrecht."""
    narrative = {"status": "generated", "div": "Maria Janssen (UMCU-00482913), see chart."}
    return [
        {
            "resourceType": "Patient",
            "id": PATIENT_ID,
            "meta": {"category": "identifiers", "tab": "overview", "title": "Patient"},
            "identifier": [
                {"system": "urn:umcu:mrn", "value": "UMCU-00482913"},
                {"system": "urn:synthetic:bsn", "value": "SYN-BSN-0001"},
            ],
            "name": [{"family": "Janssen", "given": ["Maria"]}],
            "gender": "female",
            "birthDate": "1969-03-14",
            "address": [{"line": ["Oudegracht 112"], "postalCode": "3511 AV", "city": "Utrecht"}],
            "telecom": [{"system": "phone", "value": "+31 30 555 0142"}],
            "effectiveDate": "2024-05-02",
        },
        _resource(
            "RelatedPerson", "rp-partner", "identifiers", "overview", "2024-05-02",
            "Emergency contact", name="Johan Janssen", telecom="+31 6 5550 1180",
        ),
        _resource(
            "Coverage", "cov-1", "identifiers", "overview", "2024-05-02",
            "Insurance", payor="Synthetic Zorgverzekeraar", member="SYN-BSN-0001",
        ),
        _resource(
            "Practitioner", "pr-deboer", "identifiers", "overview", "2024-05-02",
            "Treating oncologist", name="Dr Pieter de Boer",
        ),
        _resource(
            "Organization", "org-umcu", "identifiers", "overview", "2024-05-02",
            "Organisation", name="UMC Utrecht (synthetic)",
        ),
        _resource(
            "Condition", "cond-primary", "diagnosis", "overview", "2024-05-21",
            "Primary diagnosis", text=narrative,
            code="Adenocarcinoma of the sigmoid colon", stage="cT3 N1 M1a (stage IVA)",
            clinicalStatus="active",
        ),
        _resource(
            "Condition", "cond-liver", "diagnosis", "overview", "2024-05-21",
            "Metastatic disease", code="Synchronous liver metastases (4 lesions)",
            bodySite="Liver", clinicalStatus="active",
        ),
        _resource(
            "Encounter", "enc-first", "full_ehr", "timeline", "2024-05-02",
            "First outpatient visit", reason="Change in bowel habit, anaemia", text=narrative,
        ),
        _resource(
            "Procedure", "proc-sigmoid", "full_ehr", "treatment", "2024-06-11",
            "Surgery", code="Laparoscopic sigmoid resection", outcome="R0 primary resection",
        ),
        _resource(
            "MedicationStatement", "med-line1", "treatment_history", "treatment", "2024-07-01",
            "First line", medication="FOLFOX + bevacizumab", line=1, cycles=12,
            outcome="Partial response, then progression (liver) after 8 months",
            endDate="2025-02-18", text=narrative,
        ),
        _resource(
            "MedicationStatement", "med-line2", "treatment_history", "treatment", "2025-03-04",
            "Second line", medication="FOLFIRI + bevacizumab", line=2, cycles=18,
            outcome="Stable disease, then progression (liver, new lung nodules)",
            endDate="2026-08-12",
        ),
        _resource(
            "DiagnosticReport", "dr-pathology", "pathology", "pathology", "2024-06-18",
            "Resection pathology", code="Colorectal resection pathology",
            conclusion="Moderately differentiated adenocarcinoma, pT3 pN1b, LVI present, "
            "margins clear.",
            contained=[{"resourceType": "Practitioner", "name": "Dr H. Visser (pathologist)"}],
            presentedForm=[{"url": "https://pacs.umcutrecht.example/reports/pa-24-1182.pdf"}],
            text=narrative,
        ),
        _resource(
            "Observation", "obs-kras", "molecular", "molecular", "2024-06-25",
            "KRAS", code="KRAS mutation analysis (NGS panel)", value="KRAS p.G12C detected",
            method="NGS, 52-gene panel",
        ),
        _resource(
            "Observation", "obs-msi", "molecular", "molecular", "2024-06-25",
            "Mismatch repair", code="MSI / MMR status", value="Microsatellite stable (pMMR)",
        ),
        _resource(
            "Observation", "obs-braf", "molecular", "molecular", "2024-06-25",
            "BRAF", code="BRAF V600E", value="Not detected",
        ),
        _resource(
            "ImagingStudy", "img-baseline", "full_ehr", "imaging", "2024-05-14",
            "Baseline CT", modality="CT", description="CT chest-abdomen-pelvis, staging",
            numberOfSeries=4, conclusion="Sigmoid tumour, four liver metastases.",
            dicomTags={"PatientName": "JANSSEN^MARIA", "PatientID": "UMCU-00482913",
                       "PatientBirthDate": "19690314"},
        ),
        _resource(
            "ImagingStudy", "img-progression", "relevant_imaging", "imaging", "2026-08-12",
            "Restaging CT", modality="CT", description="CT chest-abdomen-pelvis, restaging",
            numberOfSeries=5,
            conclusion="Progression: two enlarging liver lesions, three new lung nodules "
            "(max 9 mm).",
            dicomTags={"PatientName": "JANSSEN^MARIA", "PatientID": "UMCU-00482913",
                       "PatientBirthDate": "19690314"},
            presentedForm=[{"url": "https://pacs.umcutrecht.example/studies/ct-26-5521"}],
        ),
        _resource(
            "Observation", "obs-cea-1", "labs", "timeline", "2024-05-10",
            "CEA at diagnosis", code="CEA", value="48 µg/L",
        ),
        _resource(
            "Observation", "obs-cea-2", "labs", "timeline", "2025-02-10",
            "CEA at first progression", code="CEA", value="31 µg/L",
        ),
        _resource(
            "Observation", "obs-cea-3", "labs", "timeline", "2026-08-05",
            "CEA now", code="CEA", value="64 µg/L",
        ),
        _resource(
            "Observation", "obs-ecog", "performance_status", "overview", "2026-08-20",
            "Performance status", code="ECOG performance status", value="ECOG 1",
        ),
        _resource(
            "Condition", "cond-htn", "comorbidities", "overview", "2019-01-10",
            "Comorbidity", code="Essential hypertension", clinicalStatus="active",
        ),
        _resource(
            "MedicationStatement", "med-amlodipine", "comorbidities", "treatment", "2019-01-10",
            "Comedication", medication="Amlodipine 5 mg", line=0,
        ),
        _resource(
            "AllergyIntolerance", "allergy-1", "full_ehr", "overview", "2020-03-01",
            "Allergy", code="Penicillin (rash)",
        ),
        _resource(
            "DocumentReference", "doc-mdo", "full_ehr", "mdo", "2026-08-19",
            "Local MDO note",
            summary="UMC Utrecht colorectal MDO: progression after two lines. Local options "
            "limited; KRAS G12C. Request European peer review on later-line strategy.",
            text=narrative,
        ),
        _resource(
            "DocumentReference", "doc-letter", "full_ehr", "timeline", "2026-08-21",
            "Clinic letter", summary="Discussed progression with Maria Janssen and partner.",
            text=narrative,
        ),
        _resource(
            "Appointment", "appt-next", "full_ehr", "timeline", "2026-10-02",
            "Next appointment", description="Outpatient review, UMC Utrecht",
        ),
    ]


SHARING_CATEGORIES: list[dict[str, Any]] = [
    {"id": "diagnosis", "label": "Diagnosis and stage", "default": True, "shareable": True},
    {"id": "treatment_history", "label": "Systemic treatment history", "default": True,
     "shareable": True},
    {"id": "pathology", "label": "Pathology report (structured)", "default": True,
     "shareable": True},
    {"id": "molecular", "label": "Molecular profile", "default": True, "shareable": True},
    {"id": "relevant_imaging", "label": "Relevant imaging (latest restaging)", "default": True,
     "shareable": True},
    {"id": "labs", "label": "Tumour markers (CEA)", "default": False, "shareable": True},
    {"id": "performance_status", "label": "Performance status", "default": False,
     "shareable": True},
    {"id": "comorbidities", "label": "Comorbidities and comedication", "default": False,
     "shareable": True},
    {"id": "full_ehr", "label": "Full EHR (notes, letters, all imaging)", "default": False,
     "shareable": False},
    {"id": "identifiers", "label": "Direct identifiers (name, MRN, address, contacts)",
     "default": False, "shareable": False},
]

EXPERTS: list[dict[str, Any]] = [
    {
        "id": "exp-heidelberg-mueller",
        "site": "de",
        "clinician": "Dr Anna Müller",
        "institution": "Universitätsklinikum Heidelberg",
        "country": "Germany",
        "expertise": "Later-line metastatic colorectal cancer; KRAS G12C targeted therapy trials",
        "tags": ["kras", "g12c", "colorectal", "cancer", "mcrc", "gi", "targeted"],
        "connected": True,
        "services": ["peer_review", "cohort_aggregate"],
    },
    {
        "id": "exp-milan-bianchi",
        "site": "milan",
        "clinician": "Dr Luca Bianchi",
        "institution": "Fondazione IRCCS Istituto Nazionale dei Tumori, Milan",
        "country": "Italy",
        "expertise": "Colorectal cancer molecular tumour board; KRAS-mutant disease",
        "tags": ["kras", "g12c", "colorectal", "cancer", "molecular"],
        "connected": False,
        "services": [],
    },
    {
        "id": "exp-antwerp-peeters",
        "site": "antwerp",
        "clinician": "Dr Els Peeters",
        "institution": "Antwerp University Hospital (UZA)",
        "country": "Belgium",
        "expertise": "Colorectal liver metastases; KRAS G12C early-phase studies",
        "tags": ["kras", "g12c", "colorectal", "cancer", "liver"],
        "connected": False,
        "services": [],
    },
    {
        "id": "exp-oxford-whitfield",
        "site": "oxford",
        "clinician": "Dr Sarah Whitfield",
        "institution": "Oxford University Hospitals",
        "country": "United Kingdom",
        "expertise": "Thoracic oncology; EGFR and ALK-positive lung cancer",
        "tags": ["lung", "nsclc", "egfr", "alk", "cancer"],
        "connected": False,
        "services": [],
    },
]

CATALOGUE_ONLY_SITES = [
    {"site": "milan", "name": "Istituto Nazionale dei Tumori, Milan"},
    {"site": "antwerp", "name": "Antwerp University Hospital"},
    {"site": "oxford", "name": "Oxford University Hospitals"},
]

ARM_LABELS = {
    "A": "Option A · KRAS G12C inhibitor combination",
    "B": "Option B · standard later-line chemotherapy",
    "C": "Other / clinical trial",
}


def _cohort(
    site: str, matching_arms: list[tuple[str, int, int, list[float]]], filler: int
) -> dict[str, list[dict[str, Any]]]:
    """OMOP-shaped tables. `matching_arms`: (arm, n, responders, pfs months per patient)."""
    person: list[dict[str, Any]] = []
    condition: list[dict[str, Any]] = []
    measurement: list[dict[str, Any]] = []
    drug_era: list[dict[str, Any]] = []
    outcome: list[dict[str, Any]] = []
    next_id = 1

    def add(diagnosis: str, kras: str, prior_lines: int, arm: str | None,
            responder: bool, pfs: float | None) -> None:
        nonlocal next_id
        person_id = next_id
        next_id += 1
        person.append({"person_id": person_id, "year_of_birth": 1950 + person_id % 25,
                       "gender_concept": "F" if person_id % 2 else "M"})
        condition.append({"person_id": person_id, "condition_concept": diagnosis})
        measurement.append({"person_id": person_id, "measurement_concept": "KRAS",
                            "value_as_concept": kras})
        for line in range(1, prior_lines + 1):
            drug_era.append({"person_id": person_id, "line_number": line, "regimen": "chemo"})
        if arm is not None:
            drug_era.append({"person_id": person_id, "line_number": prior_lines + 1,
                             "regimen": f"arm_{arm}"})
            outcome.append({"person_id": person_id, "best_response":
                            "PR" if responder else "SD/PD", "pfs_months": pfs})

    for arm, count, responders, pfs_values in matching_arms:
        for index in range(count):
            add("metastatic_colorectal_cancer", "G12C", 2 + index % 2, arm,
                index < responders, pfs_values[index % len(pfs_values)])
    diagnoses = ["metastatic_colorectal_cancer", "colon_cancer_stage_ii", "rectal_cancer",
                 "pancreatic_cancer"]
    variants = ["G12D", "G12V", "WT", "G12C"]
    for index in range(filler):
        diagnosis = diagnoses[index % 4]
        kras = variants[(index // 4) % 4]
        # G12C metastatic filler patients have fewer than two prior lines.
        prior = 1 if (diagnosis == diagnoses[0] and kras == "G12C") else index % 3
        add(diagnosis, kras, prior, None, False, None)
    return {"site": [{"site": site}], "person": person, "condition_occurrence": condition,
            "measurement": measurement, "drug_era": drug_era, "outcome": outcome}


def heidelberg_cohort() -> dict[str, list[dict[str, Any]]]:
    return _cohort(
        "de",
        [("A", 17, 7, [5.8, 6.4, 4.9, 7.1]), ("B", 18, 2, [2.1, 2.6, 1.9, 3.0]),
         ("C", 3, 1, [4.0])],
        162,
    )


def utrecht_cohort() -> dict[str, list[dict[str, Any]]]:
    return _cohort(
        "nl",
        [("A", 6, 2, [5.1, 6.0, 4.4]), ("B", 5, 1, [2.4, 2.0]), ("C", 2, 0, [3.1])],
        127,
    )


SYNTHETIC_OPINION = (
    "Synthetic peer-review opinion for discussion at the local MDO. Given KRAS G12C, "
    "MSS status, ECOG 1 and progression after oxaliplatin- and irinotecan-based lines, a "
    "KRAS G12C inhibitor combination is a reasonable option to discuss, or trial "
    "enrolment where available. Final treatment decision rests with the treating team."
)
