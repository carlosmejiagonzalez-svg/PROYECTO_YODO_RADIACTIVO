from datetime import datetime
import pandas as pd
import streamlit as st
from config import ESTADOS_VALIDOS
from services.data_service import (
    actualizar_paciente, borrar_paciente, cargar_datos,
    reasignar_dosis, registrar_paciente, reset_completo,
    agendar_paciente,
)
from services.pdf_service import generar_pdf_pedido, generar_pdf_trazabilidad
from services.physics_service import calcular_actividad, horas_para_actividad_objetivo, porcentaje_remanente


def render_programacion():
    c1, c2 = st.columns([1, 2])

    with c1:
        st.subheader("📝 Nuevo Registro")
        with st.form("f_reg", clear_on_submit=True):
            nombre = st.text_input("Nombre completo").strip().upper()
            cedula = st.text_input("Cédula").strip()
            entidad = st.text_input("Entidad").strip().upper()
            dosis = st.number_input("Dosis (mCi)", min_value=0.0, step=0.5, format="%.1f")
            fecha = st.date_input("Fecha Toma de Cápsula").strftime("%d/%m/%Y")
            submitted = st.form_submit_button("➕ Agregar Paciente", use_container_width=True)

        if submitted:
            if not nombre or not cedula or not entidad or dosis <= 0:
                st.warning("⚠️ Completa todos los campos y asegúrate que la dosis sea mayor a 0.")
            else:
                ok = registrar_paciente(nombre, cedula, entidad, dosis, fecha)
                if ok:
                    st.session_state.lista_local = cargar_datos()
                    st.rerun()

        st.divider()
        st.caption("⚠️ Zona de peligro")

        if "confirmar_reset" not in st.session_state:
            st.session_state.confirmar_reset = False

        if not st.session_state.confirmar_reset:
            if st.button("🚨 LIMPIAR / RESET", use_container_width=True, type="secondary"):
                st.session_state.confirmar_reset = True
                st.rerun()
        else:
            st.error("¿Confirmas que quieres borrar **todos** los registros? Esta acción no se puede deshacer.")
            col_si, col_no = st.columns(2)
            if col_si.button("✅ Sí, borrar todo", use_container_width=True, type="primary"):
                ok = reset_completo()
                if ok:
                    st.session_state.lista_local = []
                st.session_state.confirmar_reset = False
                st.rerun()
            if col_no.button("❌ Cancelar", use_container_width=True):
                st.session_state.confirmar_reset = False
                st.rerun()

    with c2:
        lista = st.session_state.lista_local
        if not lista:
            st.info("No hay pacientes registrados aún.")
            return

        df = pd.DataFrame(lista)

        if "Agendado" not in df.columns:
            df["Agendado"] = "NO"

        pendientes = df[df["Agendado"] != "SI"].copy().reset_index(drop=True)
        agendados = df[
            (df["Agendado"] == "SI") &
            (~df["Estado"].isin(["CANCELADO", "DECAIMIENTO"]))
        ].copy().reset_index(drop=True)

        # ═══════════════════════════════════════════
        # SECCIÓN 1 — Pendientes por agendar
        # ═══════════════════════════════════════════
        st.subheader(f"🕐 Pendientes por agendar ({len(pendientes)})")

        if pendientes.empty:
            st.info("No hay pacientes pendientes por agendar.")
        else:
            for idx, fila in pendientes.iterrows():
                col_info, col_agendar, col_borrar = st.columns([4, 2, 1])
                col_info.markdown(
                    f"**{fila['Nombre']}** · {fila['Entidad']} · "
                    f"`{fila['mCI']} mCi` · 📅 {fila.get('Fecha_Capsula', '')}"
                )
                if col_agendar.button(
                    "📅 Agendar",
                    key=f"ag_{idx}_{fila['ID']}",
                    use_container_width=True
                ):
                    ok = agendar_paciente(str(fila["ID"]))
                    if ok:
                        st.session_state.lista_local = cargar_datos()
                        st.rerun()
                if col_borrar.button(
                    "🗑️",
                    key=f"del_p_{idx}_{fila['ID']}",
                    help="Eliminar paciente"
                ):
                    ok = borrar_paciente(str(fila["ID"]))
                    if ok:
                        st.session_state.lista_local = cargar_datos()
                        st.rerun()

        st.divider()

        # ═══════════════════════════════════════════
        # SECCIÓN 2 — Pedido de esta semana
        # ═══════════════════════════════════════════
        st.subheader(f"📋 Pedido de esta semana ({len(agendados)})")

        if agendados.empty:
            st.info("No hay pacientes agendados para esta semana.")
        else:
            LIMITE_MCI = 150.0
            total_mci = pd.to_numeric(agendados["mCI"], errors="coerce").sum()
            restante = LIMITE_MCI - total_mci
            porcentaje = min((total_mci / LIMITE_MCI) * 100, 100)

            col_met, col_pdf = st.columns([1, 2])
            with col_met:
                st.metric(
                    "Total mCi Pedido",
                    f"{total_mci:.1f} mCi",
                    delta=f"{restante:.1f} mCi disponibles",
                    delta_color="normal" if restante > 0 else "inverse",
                )
            with col_pdf:
                pdf_bytes = generar_pdf_pedido(lista)
                st.download_button(
                    "📄 Descargar Pedido PDF",
                    data=pdf_bytes,
                    file_name="pedido.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

            # ── Barra de progreso con alerta ──
            st.progress(int(porcentaje))

            if total_mci >= LIMITE_MCI:
                st.error(f"🚨 **LÍMITE ALCANZADO** — El pedido ha llegado a {total_mci:.1f} mCi. No se pueden agendar más pacientes para esta semana.")
            elif total_mci >= LIMITE_MCI * 0.85:
                st.warning(f"⚠️ **ATENCIÓN** — Llevas {total_mci:.1f} mCi de {LIMITE_MCI:.0f} mCi permitidos. Solo quedan {restante:.1f} mCi disponibles.")
            else:
                st.success(f"✅ Capacidad disponible: {restante:.1f} mCi restantes de {LIMITE_MCI:.0f} mCi permitidos.")

            st.write("")
            for idx, fila in agendados.iterrows():
                col_info, col_borrar = st.columns([5, 1])
                col_info.markdown(
                    f"**{fila['Nombre']}** · {fila['Entidad']} · "
                    f"`{fila['mCI']} mCi` · 📅 {fila.get('Fecha_Capsula', '')}"
                )
                if col_borrar.button(
                    "🗑️",
                    key=f"del_a_{idx}_{fila['ID']}",
                    help="Eliminar paciente"
                ):
                    ok = borrar_paciente(str(fila["ID"]))
                    if ok:
                        st.session_state.lista_local = cargar_datos()
                        st.rerun()


def render_inventario():
    lista = st.session_state.lista_local
    if not lista:
        st.info("No hay datos para mostrar.")
        return

    # Solo mostrar pacientes que ya fueron agendados
    lista_agendados = [p for p in lista if str(p.get("Agendado", "NO")) == "SI"]

    if not lista_agendados:
        st.info("No hay pacientes agendados aún. Agenda pacientes desde la pestaña de Programación.")
        return

    pdf_bytes = generar_pdf_trazabilidad(lista_agendados)
    st.download_button(
        "📑 Reporte de Trazabilidad Completo (PDF)",
        data=pdf_bytes,
        file_name="trazabilidad.pdf",
        mime="application/pdf",
    )

    st.divider()

    for idx, p in enumerate(lista_agendados):
        estado_actual = p.get("Estado", "PENDIENTE")
        emoji = {
            "PENDIENTE AGENDAR": "🕐",
            "PENDIENTE": "🟡",
            "RECIBIDO": "🔵",
            "ADMINISTRADA": "✅",
            "CANCELADO": "🔴",
            "DECAIMIENTO": "☢️",
        }.get(estado_actual, "⚪")

        with st.expander(f"{emoji} {p['Nombre']} | {p['ID']} | {estado_actual}"):
            col_a, col_b = st.columns(2)

            with col_a:
                st.markdown("**Actualizar estado**")
                nuevo_estado = st.selectbox(
                    "Estado", ESTADOS_VALIDOS,
                    index=ESTADOS_VALIDOS.index(estado_actual) if estado_actual in ESTADOS_VALIDOS else 0,
                    key=f"s_{idx}",
                )

                fecha_admin_str = ""
                if nuevo_estado == "ADMINISTRADA":
                    fecha_admin_str = st.date_input(
                        "Fecha Administración", key=f"fa_{idx}"
                    ).strftime("%d/%m/%Y")

                notas_valor = str(p.get("Notas", ""))
                notas_valor = "" if notas_valor.lower() == "nan" else notas_valor
                obs = st.text_area("Notas / Motivo", value=notas_valor, key=f"o_{idx}")

                if st.button("💾 Guardar Cambios", key=f"g_{idx}"):
                    ok = actualizar_paciente(str(p["ID"]), nuevo_estado, obs, fecha_admin_str)
                    if ok:
                        st.session_state.lista_local = cargar_datos()
                        st.rerun()

            with col_b:
                if estado_actual == "CANCELADO":
                    st.info("🔄 Reasignación de Dosis")
                    rn = st.text_input("Nombre nuevo paciente", key=f"rn_{idx}").strip().upper()
                    ri = st.text_input("ID nuevo paciente", key=f"ri_{idx}").strip()
                    re = st.text_input("Entidad", value=p.get("Entidad", ""), key=f"re_{idx}").strip().upper()
                    rd = st.number_input("mCi a reasignar", value=float(p.get("mCI", 0)), key=f"rd_{idx}")

                    if st.button("✅ Confirmar Traspaso", key=f"tr_{idx}"):
                        if not rn or not ri:
                            st.warning("Completa nombre e ID del nuevo paciente.")
                        else:
                            historial = f"Dosis cedida por {p['Nombre']}. Motivo: {obs}"
                            ok = reasignar_dosis(
                                str(p["ID"]), rn, ri, re, rd,
                                str(p.get("Fecha_Capsula", "")), historial
                            )
                            if ok:
                                st.session_state.lista_local = cargar_datos()
                                st.rerun()
                else:
                    st.markdown("**Información del registro**")
                    st.write(f"📅 Fecha Cápsula: `{p.get('Fecha_Capsula', '—')}`")
                    st.write(f"📅 Fecha Recepción: `{p.get('Fecha_Recepcion', '—')}`")
                    st.write(f"📅 Fecha Admin.: `{p.get('Fecha_Administracion', '—')}`")
                    st.write(f"💊 Dosis: `{p.get('mCI', '—')} mCi`")


def render_calculadora():
    st.header("🧮 Calculadora de Decaimiento I-131")
    st.caption("A(t) = A₀ · e^(−λt) | T½ = 8.02 días (IAEA)")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Datos de calibración")
        ai = st.number_input("Actividad Inicial (mCi)", value=100.0, min_value=0.01, format="%.2f")
        fc = st.date_input("Fecha Calibración", key="fc")
        hc = st.time_input("Hora Calibración", key="hc")

    with col2:
        st.subheader("Fecha objetivo")
        ff = st.date_input("Fecha Cálculo", key="ff")
        hf = st.time_input("Hora Cálculo", key="hf")

    st.divider()

    dt_calibracion = datetime.combine(fc, hc)
    dt_calculo = datetime.combine(ff, hf)

    try:
        af = calcular_actividad(ai, dt_calibracion, dt_calculo)
        pct = porcentaje_remanente(ai, af)

        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Actividad Final", f"{af} mCi")
        col_m2.metric("Actividad Inicial", f"{ai} mCi")
        col_m3.metric("% Remanente", f"{pct}%", delta=f"{pct - 100:.1f}%")

        st.divider()
        st.subheader("⏱️ ¿Cuándo llega a un umbral?")
        umbral = st.number_input("Actividad umbral (mCi)", value=1.0, min_value=0.01, format="%.2f")
        if umbral < af:
            horas = horas_para_actividad_objetivo(af, umbral)
            dias = round(horas / 24, 1)
            st.info(f"⏳ Faltan aproximadamente **{horas} horas** ({dias} días) para llegar a {umbral} mCi.")
        else:
            st.success("✅ La actividad actual ya está por debajo del umbral indicado.")

    except ValueError as e:
        st.error(f"⚠️ {e}")
