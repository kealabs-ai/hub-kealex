
def build_next_phases(phases, current_index: int) -> dict:
    upcoming = [
        {"ordem": index, "label": phase.label, "status": phase.status}
        for index, phase in enumerate(phases)
        if index > current_index
    ]
    return {
        "faseAtual": current_index,
        "faseAtualLabel": phases[current_index].label if current_index < len(phases) else None,
        "proximasFases": upcoming,
    }
