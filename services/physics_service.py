import math
from datetime import datetime

# Semivida del I-131 en días (fuente: IAEA Nuclear Data Section)
SEMIVIDA_I131_DIAS = 8.02
# Constante de decaimiento en horas
LAMBDA_I131_HORAS = math.log(2) / (SEMIVIDA_I131_DIAS * 24)

def calcular_actividad(actividad_inicial, fecha_calibracion, fecha_calculo):
    """
    Calcula la actividad del I-131 en un momento dado.
    A(t) = A0 * e^(-λt)
    """
    delta_horas = (fecha_calculo - fecha_calibracion).total_seconds() / 3600

    if delta_horas < 0:
        raise ValueError("La fecha de cálculo no puede ser anterior a la fecha de calibración.")

    actividad_final = actividad_inicial * math.exp(-LAMBDA_I131_HORAS * delta_horas)
    return round(actividad_final, 4)

def porcentaje_remanente(actividad_inicial, actividad_final):
    """Retorna qué porcentaje de la dosis original queda."""
    if actividad_inicial == 0:
        return 0.0
    return round((actividad_final / actividad_inicial) * 100, 2)

def horas_para_actividad_objetivo(actividad_actual, actividad_objetivo):
    """
    Calcula cuántas horas faltan para llegar a un valor objetivo.
    Útil para planificar tiempos de descarte.
    """
    if actividad_objetivo <= 0 or actividad_actual <= 0:
        raise ValueError("Las actividades deben ser positivas.")
    if actividad_objetivo >= actividad_actual:
        return 0.0

    horas = -math.log(actividad_objetivo / actividad_actual) / LAMBDA_I131_HORAS
    return round(horas, 2)
