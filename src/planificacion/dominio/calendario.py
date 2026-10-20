from datetime import date


def fecha_iso(valor: str) -> date:
    if not isinstance(valor, str):
        raise ValueError("Usar una fecha válida AAAA-MM-DD")
    try:
        fecha = date.fromisoformat(valor)
    except ValueError as exc:
        raise ValueError("Usar una fecha válida AAAA-MM-DD") from exc
    if fecha.isoformat() != valor:
        raise ValueError("Usar una fecha válida AAAA-MM-DD")
    return fecha
