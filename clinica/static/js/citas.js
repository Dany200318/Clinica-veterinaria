/*
 * Muestra los horarios ocupados del veterinario en la fecha elegida y advierte
 * si la hora seleccionada se traslapa (HU-07). La validación definitiva se hace
 * en el servidor al guardar (RF-10).
 */
(function () {
    const form = document.getElementById('form-cita');
    if (!form) return;

    const url = form.dataset.urlDisponibilidad;
    const excluir = form.dataset.excluir || '';
    const vet = document.getElementById('id_veterinario');
    const fecha = document.getElementById('id_fecha_cita');
    const inicio = document.getElementById('id_hora_inicio');
    const fin = document.getElementById('id_hora_fin');
    const panel = document.getElementById('panel-disponibilidad');
    const DURACION = parseInt(form.dataset.duracion || '30', 10); // minutos asumidos sin hora fin
    let ocupados = [];

    const aMinutos = (h) => {
        if (!h) return null;
        const [hh, mm] = h.split(':').map(Number);
        return hh * 60 + mm;
    };

    function hayConflicto() {
        const ini = aMinutos(inicio.value);
        if (ini === null) return null;
        const f = aMinutos(fin.value) ?? ini + DURACION;
        return ocupados.find(o => ini < aMinutos(o.fin) && aMinutos(o.inicio) < f) || null;
    }

    function pintar() {
        if (!vet.value || !fecha.value) { panel.classList.add('d-none'); return; }
        panel.classList.remove('d-none', 'alert-danger', 'alert-success', 'alert-light');
        const conflicto = hayConflicto();
        let html = '';
        if (conflicto) {
            panel.classList.add('alert-danger');
            html += `<strong><i class="bi bi-exclamation-octagon-fill"></i> Horario ocupado:</strong> ya existe una cita de ` +
                    `${conflicto.inicio} a ${conflicto.fin} (${conflicto.paciente}). Elija otra hora.<br>`;
        } else {
            panel.classList.add(ocupados.length ? 'alert-light' : 'alert-success');
        }
        if (ocupados.length) {
            html += '<i class="bi bi-clock"></i> Horarios ocupados ese día: ' +
                ocupados.map(o => `<span class="badge text-bg-secondary me-1">${o.inicio}–${o.fin} ${o.paciente}</span>`).join('');
        } else {
            html += '<i class="bi bi-check-circle"></i> El veterinario no tiene citas ese día: todos los horarios están libres.';
        }
        panel.innerHTML = html;
    }

    async function consultar() {
        if (!vet.value || !fecha.value) { ocupados = []; pintar(); return; }
        const params = new URLSearchParams({ veterinario: vet.value, fecha: fecha.value, excluir });
        try {
            const r = await fetch(`${url}?${params}`, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
            ocupados = r.ok ? (await r.json()).ocupados : [];
        } catch (e) {
            ocupados = [];
        }
        pintar();
    }

    vet.addEventListener('change', consultar);
    fecha.addEventListener('change', consultar);
    inicio.addEventListener('change', pintar);
    fin.addEventListener('change', pintar);
    consultar();
})();
