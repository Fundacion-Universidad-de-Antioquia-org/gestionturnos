from __future__ import annotations
import datetime as dt
import holidays

# Cache por año para hacerlo eficiente
_CO_HOLIDAYS_CACHE: dict[int, set[dt.date]] = {}

def es_festivo_o_domingo(fecha: dt.date | str) -> bool:
    """Devuelve True si la fecha (date o 'YYYY-MM-DD') es domingo o festivo nacional en Colombia."""
    if isinstance(fecha, str):
        fecha = dt.date.fromisoformat(fecha)  # 'YYYY-MM-DD' -> date

    if fecha.weekday() == 6:  # domingo
        return True

    y = fecha.year
    if y not in _CO_HOLIDAYS_CACHE:
        _CO_HOLIDAYS_CACHE[y] = set(holidays.CountryHoliday("CO", years=y).keys())

    return fecha in _CO_HOLIDAYS_CACHE[y]