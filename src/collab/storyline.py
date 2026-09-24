"""The demonstration storyline: an ordered set of scenes, one per screen.

The storyline owns *where* the audience is in the story. The referral journey owns
*what* happened clinically. Each scene names the person responsible, the condition
for moving on, and the agent work that is visible on screen.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from collab.models import (
    AgentBriefView,
    AgentStepView,
    ChapterId,
    DemoState,
    FederatedSourceId,
    HandoffView,
    JourneyRole,
    RegionalSourceId,
    SceneId,
    StoryActorView,
    StoryChapterView,
    StorylineView,
    StorySceneView,
    StoryStatus,
    SystemCallView,
)

SOPHIE = StoryActorView(
    name="Dr Sophie Bakker",
    role="Medical oncologist",
    institution="Utrecht Regional Oncology Centre",
    kind="clinician",
)
NOOR = StoryActorView(
    name="Dr Noor Jansen",
    role="Treating oncologist",
    institution="Stadshaven Hospital Utrecht",
    kind="clinician",
)
NETWORK = StoryActorView(
    name="European Oncology Exchange",
    role="Federated care network",
    institution="Hospitals across Europe",
    kind="network",
)
LUCA = StoryActorView(
    name="Dr Luca Bianchi",
    role="Referring medical oncologist",
    institution="Istituto Nazionale dei Tumori, Milan",
    kind="clinician",
)
EVA = StoryActorView(
    name="Dr Eva van Dijk",
    role="Receiving colorectal specialist",
    institution="UMC Utrecht",
    kind="clinician",
)

CHAPTERS: tuple[tuple[ChapterId, str, str], ...] = (
    (ChapterId.LOCAL, "A problem around the corner", "Two hospitals in Utrecht"),
    (ChapterId.NETWORK, "The same pattern, wider", "Utrecht to Europe"),
    (ChapterId.CROSS_BORDER, "One referral across borders", "Milan to Utrecht"),
)


@dataclass(frozen=True)
class Scene:
    id: SceneId
    chapter: ChapterId
    title: str
    actor: StoryActorView
    workspace: JourneyRole | None
    advance_label: str | None
    blocked_reason: Callable[[DemoState], str | None]


def _never(_: DemoState) -> str | None:
    return None


def _milan_checks_complete(state: DemoState) -> bool:
    checks = state.referral_journey.source_checks
    return all(
        source_id in checks and checks[source_id].status == "complete"
        for source_id in FederatedSourceId
    )


def _latest_update_approved(state: DemoState) -> bool:
    journey = state.referral_journey
    return (
        journey.update_available_version is not None
        and journey.update_available_version in journey.update_approved_versions
    )


SCENES: tuple[Scene, ...] = (
    Scene(
        SceneId.LOCAL_PROBLEM,
        ChapterId.LOCAL,
        "The MRI is at the hospital around the corner",
        SOPHIE,
        None,
        "Ask the exchange agent to find it",
        _never,
    ),
    Scene(
        SceneId.LOCAL_SEARCH,
        ChapterId.LOCAL,
        "The agent asks Stadshaven's own systems",
        SOPHIE,
        None,
        "Send the sharing request to Dr Noor Jansen",
        lambda state: (
            None
            if all(
                source_id in state.referral_journey.regional_exchange.source_checks
                for source_id in RegionalSourceId
            )
            else "The agent must query both Stadshaven systems first."
        ),
    ),
    Scene(
        SceneId.LOCAL_APPROVAL,
        ChapterId.LOCAL,
        "Stadshaven decides what may cross",
        NOOR,
        None,
        "Show what Utrecht receives",
        lambda state: (
            None
            if state.referral_journey.regional_exchange.sharing_approved
            else "Dr Noor Jansen must approve the sharing request first."
        ),
    ),
    Scene(
        SceneId.LOCAL_RESULT,
        ChapterId.LOCAL,
        "Today's treatment review can go ahead",
        SOPHIE,
        None,
        "Now scale the same pattern",
        _never,
    ),
    Scene(
        SceneId.SCALE_NETWORK,
        ChapterId.NETWORK,
        "From Utrecht to a European network",
        NETWORK,
        None,
        "Follow one referral from Milan to Utrecht",
        _never,
    ),
    Scene(
        SceneId.CROSS_PATIENT,
        ChapterId.CROSS_BORDER,
        "Milan needs a second opinion",
        LUCA,
        JourneyRole.MILAN,
        "Let the agent check Milan's own sources",
        lambda state: (
            None
            if state.referral_journey.selected_patient_id is not None
            else "Select the patient who needs the referral first."
        ),
    ),
    Scene(
        SceneId.CROSS_SOURCES,
        ChapterId.CROSS_BORDER,
        "The agent checks what Milan already holds",
        LUCA,
        JourneyRole.MILAN,
        "Frame the clinical question",
        lambda state: (
            None
            if _milan_checks_complete(state)
            else "The agent must finish checking all three Milan sources first."
        ),
    ),
    Scene(
        SceneId.CROSS_QUESTION,
        ChapterId.CROSS_BORDER,
        "Dr Bianchi frames the question",
        LUCA,
        JourneyRole.MILAN,
        "Find the right expert centre",
        lambda state: (
            None
            if state.referral_journey.clinical_question is not None
            else "Confirm the clinical question first."
        ),
    ),
    Scene(
        SceneId.CROSS_DESTINATION,
        ChapterId.CROSS_BORDER,
        "Choosing the expert centre",
        LUCA,
        JourneyRole.MILAN,
        "Prepare the referral package",
        lambda state: (
            None
            if state.referral_journey.selected_centre_id is not None
            else "Select the receiving centre first."
        ),
    ),
    Scene(
        SceneId.CROSS_PACKAGE,
        ChapterId.CROSS_BORDER,
        "Approve exactly what crosses the border",
        LUCA,
        JourneyRole.MILAN,
        "Hand over to Dr Eva van Dijk in Utrecht",
        lambda state: (
            None
            if state.referral_journey.package is not None
            and state.referral_journey.package.approved
            else "Dr Bianchi must approve and send case version 1 first."
        ),
    ),
    Scene(
        SceneId.UTRECHT_REVIEW,
        ChapterId.CROSS_BORDER,
        "Utrecht reviews and asks for imaging",
        EVA,
        JourneyRole.UTRECHT,
        "Hand back to Dr Luca Bianchi in Milan",
        lambda state: (
            None
            if state.referral_journey.evidence_request is not None
            else "Dr van Dijk must request the missing imaging first."
        ),
    ),
    Scene(
        SceneId.MILAN_UPDATE,
        ChapterId.CROSS_BORDER,
        "New imaging arrives in Milan",
        LUCA,
        JourneyRole.MILAN,
        "Hand over to Dr Eva van Dijk in Utrecht",
        lambda state: (
            None
            if _latest_update_approved(state)
            else "Dr Bianchi must approve case version 2 first."
        ),
    ),
    Scene(
        SceneId.UTRECHT_MDO,
        ChapterId.CROSS_BORDER,
        "Utrecht completes the specialist review",
        EVA,
        JourneyRole.UTRECHT,
        "Return the outcome to Milan",
        lambda state: (
            None
            if state.referral_journey.mdo_outcome is not None
            else "Dr van Dijk must accept the case into the MDO first."
        ),
    ),
    Scene(
        SceneId.CLOSING_OUTCOME,
        ChapterId.CROSS_BORDER,
        "The loop is closed",
        LUCA,
        JourneyRole.MILAN,
        None,
        _never,
    ),
)

_INDEX = {scene.id: index for index, scene in enumerate(SCENES)}

# Every clinical action belongs to the scene in which the audience sees it happen.
ACTION_SCENES: dict[str, frozenset[SceneId]] = {
    "query_regional_source": frozenset({SceneId.LOCAL_SEARCH}),
    "approve_regional_exchange": frozenset({SceneId.LOCAL_APPROVAL}),
    "select_patient": frozenset({SceneId.CROSS_PATIENT}),
    "query_source": frozenset({SceneId.CROSS_SOURCES}),
    "confirm_referral_question": frozenset({SceneId.CROSS_QUESTION}),
    "query_expert_directory": frozenset({SceneId.CROSS_DESTINATION}),
    "select_destination": frozenset({SceneId.CROSS_DESTINATION}),
    "query_requirements": frozenset({SceneId.CROSS_PACKAGE}),
    "prepare_referral_package": frozenset({SceneId.CROSS_PACKAGE}),
    "approve_referral_package": frozenset({SceneId.CROSS_PACKAGE}),
    "acknowledge_case_version": frozenset({SceneId.UTRECHT_REVIEW, SceneId.UTRECHT_MDO}),
    "record_provisional_opinion": frozenset({SceneId.UTRECHT_REVIEW}),
    "request_evidence": frozenset({SceneId.UTRECHT_REVIEW}),
    "receive_evidence_update": frozenset({SceneId.MILAN_UPDATE}),
    "approve_evidence_update": frozenset({SceneId.MILAN_UPDATE}),
    "record_final_opinion": frozenset({SceneId.UTRECHT_MDO}),
    "accept_mdo_outcome": frozenset({SceneId.UTRECHT_MDO}),
}

HANDOFF_CARRIED: dict[SceneId, str] = {
    SceneId.LOCAL_APPROVAL: "A sharing request for Sanne's diagnosis summary and MRI report",
    SceneId.LOCAL_RESULT: "The approved diagnosis summary and MRI report",
    SceneId.UTRECHT_REVIEW: "Approved case version 1 with source provenance",
    SceneId.MILAN_UPDATE: "A named request for the baseline CT and restaging MRI",
    SceneId.UTRECHT_MDO: "Approved case version 2 with the imaging update",
    SceneId.CLOSING_OUTCOME: "The specialist opinion, MDO schedule and next responsibility",
}


def scene(scene_id: SceneId) -> Scene:
    return SCENES[_INDEX[scene_id]]


def scene_index(scene_id: SceneId) -> int:
    return _INDEX[scene_id]


def next_scene(scene_id: SceneId) -> Scene | None:
    index = _INDEX[scene_id] + 1
    return SCENES[index] if index < len(SCENES) else None


def action_allowed(action_type: str, current: SceneId) -> bool:
    allowed = ACTION_SCENES.get(action_type)
    return allowed is None or current in allowed


def build_view(state: DemoState) -> StorylineView:
    current = scene(state.referral_journey.scene)
    current_index = _INDEX[current.id]
    blocked = current.blocked_reason(state)
    terminal = next_scene(current.id) is None
    return StorylineView(
        chapters=_chapters(current.chapter),
        scenes=[
            StorySceneView(
                id=item.id,
                chapter=item.chapter,
                title=item.title,
                status=_status(index, current_index),
                actor=item.actor,
            )
            for index, item in enumerate(SCENES)
        ],
        current_scene=current.id,
        current_index=current_index,
        actor=current.actor,
        can_advance=not terminal and blocked is None,
        advance_label=current.advance_label,
        blocked_reason=None if terminal else blocked,
        agent=_agent_brief(current.id, state),
        handoff=_handoff(current_index),
        system_calls=_system_calls(state),
    )


def _status(index: int, current_index: int) -> StoryStatus:
    if index < current_index:
        return "complete"
    if index == current_index:
        return "current"
    return "upcoming"


def _chapters(current: ChapterId) -> list[StoryChapterView]:
    order = [chapter_id for chapter_id, _, _ in CHAPTERS]
    current_index = order.index(current)
    return [
        StoryChapterView(
            id=chapter_id,
            title=title,
            scope=scope,
            status=_status(index, current_index),
        )
        for index, (chapter_id, title, scope) in enumerate(CHAPTERS)
    ]


def _handoff(current_index: int) -> HandoffView | None:
    if current_index == 0:
        return None
    current = SCENES[current_index]
    previous = SCENES[current_index - 1]
    carried = HANDOFF_CARRIED.get(current.id)
    if carried is None or previous.actor.institution == current.actor.institution:
        return None
    return HandoffView(from_actor=previous.actor, to_actor=current.actor, carried=carried)


def _step(label: str, detail: str, done: bool, call: str | None = None) -> AgentStepView:
    return AgentStepView(
        label=label,
        detail=detail,
        status="done" if done else "pending",
        call=call,
    )


def _agent_brief(scene_id: SceneId, state: DemoState) -> AgentBriefView | None:
    journey = state.referral_journey
    exchange = journey.regional_exchange
    if scene_id in {
        SceneId.LOCAL_PROBLEM,
        SceneId.LOCAL_SEARCH,
        SceneId.LOCAL_APPROVAL,
        SceneId.LOCAL_RESULT,
    }:
        summary_check = exchange.source_checks.get(RegionalSourceId.UTRECHT_PATIENT_SUMMARY)
        imaging_check = exchange.source_checks.get(RegionalSourceId.UTRECHT_IMAGING)
        searched = summary_check is not None and imaging_check is not None
        steps = [
            _step(
                "Locate the hospital that holds the MRI",
                "The regional index points to Stadshaven Hospital Utrecht.",
                True,
            ),
            _step(
                "Ask Stadshaven's patient-summary service",
                "Diagnosis summary and a regional sharing directive found."
                if summary_check
                else "Not asked yet.",
                summary_check is not None,
                summary_check.endpoint if summary_check else None,
            ),
            _step(
                "Ask Stadshaven's imaging archive",
                "MRI report of 24 September 2026 found; images stay at Stadshaven."
                if imaging_check
                else "Not asked yet.",
                imaging_check is not None,
                imaging_check.endpoint if imaging_check else None,
            ),
            _step(
                "Draft a sharing request for Dr Noor Jansen",
                "Only the diagnosis summary and MRI report are requested."
                if searched
                else "Waiting for both answers.",
                searched,
            ),
            _step(
                "Deliver the approved answer to Utrecht",
                f"Approved by {exchange.approved_by}."
                if exchange.sharing_approved
                else "Waiting for a clinician at Stadshaven to decide.",
                exchange.sharing_approved,
            ),
        ]
        if scene_id == SceneId.LOCAL_PROBLEM:
            summary = (
                "I know which hospital holds Sanne's latest MRI, but I cannot see it yet. "
                "I will ask Stadshaven's systems for what exists."
            )
        elif not searched:
            summary = "Asking Stadshaven's own systems. Nothing is copied into a shared database."
        elif not exchange.sharing_approved:
            summary = (
                "I found the MRI report. Releasing it is a clinical decision, so I have "
                "asked Dr Noor Jansen."
            )
        else:
            summary = "Delivered. Utrecht can read the MRI report; the images stay at Stadshaven."
        return AgentBriefView(
            name="Utrecht exchange agent",
            works_for="Dr Sophie Bakker · Utrecht Regional Oncology Centre",
            summary=summary,
            steps=steps,
        )
    if scene_id == SceneId.SCALE_NETWORK:
        return None
    if scene_id in {SceneId.UTRECHT_REVIEW, SceneId.UTRECHT_MDO}:
        return _utrecht_brief(scene_id, state)
    return _milan_brief(scene_id, state)


def _milan_brief(scene_id: SceneId, state: DemoState) -> AgentBriefView:
    journey = state.referral_journey
    name = "Milan exchange agent"
    works_for = "Dr Luca Bianchi · Istituto Nazionale dei Tumori, Milan"
    if scene_id in {SceneId.CROSS_PATIENT, SceneId.CROSS_SOURCES}:
        steps = []
        for source_id in FederatedSourceId:
            check = journey.source_checks.get(source_id)
            label = {
                FederatedSourceId.MILAN_EHR: "Check Milan's electronic health record",
                FederatedSourceId.MILAN_DOCUMENTS: "Check Milan's document store",
                FederatedSourceId.MILAN_PACS: "Check Milan's imaging archive",
            }[source_id]
            if check is None:
                detail = "Not asked yet."
            elif check.status == "failed":
                detail = check.error or "The source could not be reached."
            else:
                available_labels = [
                    record.label for record in check.records if record.status == "available"
                ]
                missing_labels = [
                    record.label for record in check.records if record.status == "missing"
                ]
                detail = (
                    f"{len(available_labels)} of {len(check.records)} expected records available."
                )
                if missing_labels:
                    detail += f" Missing: {', '.join(missing_labels)}."
            steps.append(
                _step(
                    label,
                    detail,
                    check is not None and check.status == "complete",
                    check.endpoint if check else None,
                )
            )
        summary = (
            "Pick the patient and I will check what Milan already holds, source by source."
            if journey.selected_patient_id is None
            else "Every source was checked in place. Missing evidence stays visible."
            if _milan_checks_complete(state)
            else "Checking Milan's systems in place."
        )
        return AgentBriefView(name=name, works_for=works_for, summary=summary, steps=steps)
    if scene_id == SceneId.CROSS_QUESTION:
        return AgentBriefView(
            name=name,
            works_for=works_for,
            summary="I drafted a question from the record. Dr Bianchi decides what is asked.",
            steps=[
                _step("Check all Milan sources", "Evidence inventory complete.", True),
                _step(
                    "Draft a referral question",
                    "Based on response to conversion therapy and liver metastases.",
                    True,
                ),
                _step(
                    "Question confirmed by Dr Bianchi",
                    journey.clinical_question or "Waiting for Dr Bianchi.",
                    journey.clinical_question is not None,
                ),
            ],
        )
    if scene_id == SceneId.CROSS_DESTINATION:
        chosen = next(
            (item for item in journey.destinations if item.centre_id == journey.selected_centre_id),
            None,
        )
        return AgentBriefView(
            name=name,
            works_for=works_for,
            summary=(
                "I rank centres and explain why. Dr Bianchi chooses."
                if chosen is None
                else f"Dr Bianchi chose {chosen.centre_name}."
            ),
            steps=[
                _step(
                    "Search the expert directory",
                    f"{len(journey.destinations)} matching centres found."
                    if journey.destinations
                    else "Not searched yet.",
                    bool(journey.destinations),
                    "GET /directory/v1/centres?tumour=colorectal&focus=liver"
                    if journey.destinations
                    else None,
                ),
                _step(
                    "Explain each match",
                    "Clinical fit, evidence formats, language and availability."
                    if journey.destinations
                    else "Waiting for results.",
                    bool(journey.destinations),
                ),
                _step(
                    "Destination chosen by Dr Bianchi",
                    "Selected." if journey.selected_centre_id else "Waiting for Dr Bianchi.",
                    journey.selected_centre_id is not None,
                ),
            ],
        )
    if scene_id == SceneId.CROSS_PACKAGE:
        package = journey.package
        present = sum(item.status == "present" for item in journey.requirements)
        return AgentBriefView(
            name=name,
            works_for=works_for,
            summary=(
                "Case version 1 is ready. Only Dr Bianchi can send it."
                if package is not None and not package.approved
                else "Sent. Utrecht receives exactly the approved version."
                if package is not None
                else "I compare Utrecht's requirements with what Milan holds."
            ),
            steps=[
                _step(
                    "Fetch Utrecht's referral requirements",
                    f"{len(journey.requirements)} requirements returned."
                    if journey.requirements
                    else "Not fetched yet.",
                    bool(journey.requirements),
                    "GET /utrecht/referral-requirements/colorectal-liver"
                    if journey.requirements
                    else None,
                ),
                _step(
                    "Compare with Milan's evidence",
                    f"{present} of {len(journey.requirements)} present; missing items stay visible."
                    if journey.requirements
                    else "Waiting for requirements.",
                    bool(journey.requirements),
                ),
                _step(
                    "Draft case version 1 with provenance",
                    f"{package.provenance_links} provenance links attached."
                    if package
                    else "Not drafted yet.",
                    package is not None,
                ),
                _step(
                    "Approved and sent by Dr Bianchi",
                    "Sent to Utrecht."
                    if package and package.approved
                    else "Waiting for Dr Bianchi.",
                    package is not None and package.approved,
                ),
            ],
        )
    if scene_id == SceneId.MILAN_UPDATE:
        available = journey.update_available_version is not None
        return AgentBriefView(
            name=name,
            works_for=works_for,
            summary=(
                "Watching Milan's imaging archive for the studies Utrecht asked for."
                if not available
                else "Case version 2 is ready with a clear diff. Dr Bianchi decides."
                if not _latest_update_approved(state)
                else "Case version 2 released to Utrecht."
            ),
            steps=[
                _step(
                    "Watch the imaging archive for the requested studies",
                    "Baseline CT and restaging MRI arrived."
                    if available
                    else "Waiting for the imaging event.",
                    available,
                    "Microsoft.Storage.BlobCreated → POST /api/evidence-arrivals"
                    if available
                    else None,
                ),
                _step(
                    "Prepare case version 2 and show what changed",
                    "Version 1 is kept unchanged." if available else "Waiting for imaging.",
                    available,
                ),
                _step(
                    "Approved by Dr Bianchi",
                    "Released to Utrecht."
                    if _latest_update_approved(state)
                    else "Waiting for Dr Bianchi.",
                    _latest_update_approved(state),
                ),
            ],
        )
    outcome = journey.mdo_outcome
    return AgentBriefView(
        name=name,
        works_for=works_for,
        summary="The outcome is back in Milan with a named next responsibility.",
        steps=[
            _step(
                "Receive Utrecht's outcome",
                f"Case version {outcome.case_version} accepted into the Utrecht MDO."
                if outcome
                else "Waiting for Utrecht.",
                outcome is not None,
            ),
            _step(
                "Assign the next responsibility",
                outcome.next_responsible_actor if outcome else "Waiting for Utrecht.",
                outcome is not None,
            ),
        ],
    )


def _utrecht_brief(scene_id: SceneId, state: DemoState) -> AgentBriefView:
    journey = state.referral_journey
    name = "Utrecht exchange agent"
    works_for = "Dr Eva van Dijk · UMC Utrecht"
    if scene_id == SceneId.UTRECHT_REVIEW:
        provenance = journey.package.provenance_links if journey.package else 0
        return AgentBriefView(
            name=name,
            works_for=works_for,
            summary=(
                "Case version 1 arrived with its provenance. The opinion is Dr van Dijk's."
                if journey.evidence_request is None
                else "Imaging request sent to Milan. I will tell Dr van Dijk when it arrives."
            ),
            steps=[
                _step("Receive case version 1", "Delivered from Milan.", True),
                _step(
                    "Check provenance links",
                    f"{provenance} links back to Milan's source records.",
                    True,
                ),
                _step(
                    "Acknowledged by Dr van Dijk",
                    "Version 1 confirmed."
                    if 1 in journey.acknowledged_versions
                    else "Waiting for Dr van Dijk.",
                    1 in journey.acknowledged_versions,
                ),
                _step(
                    "Provisional opinion by Dr van Dijk",
                    "Recorded." if journey.provisional_opinion else "Waiting for Dr van Dijk.",
                    journey.provisional_opinion is not None,
                ),
                _step(
                    "Send the imaging request to Milan",
                    ", ".join(journey.evidence_request.requested_evidence)
                    if journey.evidence_request
                    else "Waiting for Dr van Dijk.",
                    journey.evidence_request is not None,
                ),
            ],
        )
    version = journey.update_available_version or 2
    return AgentBriefView(
        name=name,
        works_for=works_for,
        summary=(
            f"Case version {version} arrived. Version 1 is still available for comparison."
            if journey.mdo_outcome is None
            else "Outcome recorded and returned to Milan."
        ),
        steps=[
            _step(f"Receive case version {version}", "Delivered from Milan.", True),
            _step(
                "Acknowledged by Dr van Dijk",
                f"Version {version} confirmed."
                if version in journey.acknowledged_versions
                else "Waiting for Dr van Dijk.",
                version in journey.acknowledged_versions,
            ),
            _step(
                "Final opinion by Dr van Dijk",
                "Recorded." if journey.final_opinion else "Waiting for Dr van Dijk.",
                journey.final_opinion is not None,
            ),
            _step(
                "MDO acceptance by Dr van Dijk",
                journey.mdo_outcome.scheduled_for
                if journey.mdo_outcome
                else "Waiting for Dr van Dijk.",
                journey.mdo_outcome is not None,
            ),
        ],
    )


def _system_calls(state: DemoState) -> list[SystemCallView]:
    journey = state.referral_journey
    exchange = journey.regional_exchange
    calls = [
        SystemCallView(
            id=check.source_id.value,
            scene=SceneId.LOCAL_SEARCH,
            system=check.source_label,
            endpoint=check.endpoint,
            status="200 OK",
            detail=(
                f"{len(check.records)} source-linked records found at {check.owner_institution}."
            ),
        )
        for source_id in RegionalSourceId
        if (check := exchange.source_checks.get(source_id)) is not None
    ]
    for source_id in FederatedSourceId:
        milan_check = journey.source_checks.get(source_id)
        if milan_check is None:
            continue
        available = sum(record.status == "available" for record in milan_check.records)
        calls.append(
            SystemCallView(
                id=source_id.value,
                scene=SceneId.CROSS_SOURCES,
                system=milan_check.source_label,
                endpoint=milan_check.endpoint,
                status="200 OK" if milan_check.status == "complete" else "Failed",
                detail=(
                    f"{available} of {len(milan_check.records)} expected records available."
                    if milan_check.status == "complete"
                    else milan_check.error or "The source request failed."
                ),
            )
        )
    if journey.destinations:
        calls.append(
            SystemCallView(
                id="expert-directory",
                scene=SceneId.CROSS_DESTINATION,
                system="Synthetic European expert directory",
                endpoint="GET /directory/v1/centres?tumour=colorectal&focus=liver",
                status="200 OK",
                detail=f"{len(journey.destinations)} bounded destination matches returned.",
            )
        )
    if journey.requirements:
        calls.append(
            SystemCallView(
                id="utrecht-requirements",
                scene=SceneId.CROSS_PACKAGE,
                system="UMC Utrecht referral requirements",
                endpoint="GET /utrecht/referral-requirements/colorectal-liver",
                status="200 OK",
                detail=f"{len(journey.requirements)} requirements returned.",
            )
        )
    if journey.update_available_version is not None:
        calls.append(
            SystemCallView(
                id="evidence-arrival",
                scene=SceneId.MILAN_UPDATE,
                system="Milan imaging archive event",
                endpoint="Microsoft.Storage.BlobCreated → POST /api/evidence-arrivals",
                status="200 OK",
                detail=f"Prepared immutable case version {journey.update_available_version}.",
            )
        )
    return calls
