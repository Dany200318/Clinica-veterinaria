from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from usuarios.roles import administrador_o_veterinario, todo_el_personal

from .forms import PacienteForm, PropietarioForm, VacunaForm
from .models import Paciente, Propietario, Vacuna


def _filtro_propietarios(q):
    return (Q(nombre__icontains=q) | Q(telefono__icontains=q) | Q(email__icontains=q)
            | Q(dpi__icontains=q) | Q(zona__icontains=q))


def _filtro_pacientes(q):
    return (Q(nombre__icontains=q) | Q(raza__icontains=q) | Q(microchip__icontains=q)
            | Q(propietario__nombre__icontains=q) | Q(propietario__telefono__icontains=q))


# ---------------------------------------------------------------------------
# Búsqueda general (RF-07, HU-05)
# ---------------------------------------------------------------------------
@todo_el_personal
def buscar(request):
    q = request.GET.get('q', '').strip()
    propietarios = pacientes = []
    if q:
        propietarios = Propietario.objects.filter(_filtro_propietarios(q)).annotate(
            num_pacientes=Count('pacientes'))[:20]
        pacientes = Paciente.objects.filter(_filtro_pacientes(q)).select_related('propietario')[:20]
    return render(request, 'pacientes/buscar.html', {
        'q': q, 'propietarios': propietarios, 'pacientes': pacientes,
    })


# ---------------------------------------------------------------------------
# Propietarios (RF-05)
# ---------------------------------------------------------------------------
@todo_el_personal
def lista_propietarios(request):
    q = request.GET.get('q', '').strip()
    propietarios = Propietario.objects.annotate(num_pacientes=Count('pacientes'))
    if q:
        propietarios = propietarios.filter(_filtro_propietarios(q))
    pagina = Paginator(propietarios.order_by('nombre'), 15).get_page(request.GET.get('page'))
    return render(request, 'pacientes/propietarios/lista.html', {'pagina': pagina, 'q': q})


@todo_el_personal
def crear_propietario(request):
    if request.method == 'POST':
        form = PropietarioForm(request.POST)
        if form.is_valid():
            propietario = form.save()
            messages.success(request, f'Propietario "{propietario}" registrado correctamente.')
            if 'guardar_y_paciente' in request.POST:
                return redirect(f"{_url('crear_paciente')}?propietario={propietario.pk}")
            return redirect('detalle_propietario', pk=propietario.pk)
    else:
        form = PropietarioForm()
    return render(request, 'pacientes/propietarios/form.html', {'form': form, 'titulo': 'Nuevo propietario'})


@todo_el_personal
def editar_propietario(request, pk):
    propietario = get_object_or_404(Propietario, pk=pk)
    if request.method == 'POST':
        form = PropietarioForm(request.POST, instance=propietario)
        if form.is_valid():
            form.save()
            messages.success(request, 'Propietario actualizado correctamente.')
            return redirect('detalle_propietario', pk=pk)
    else:
        form = PropietarioForm(instance=propietario)
    return render(request, 'pacientes/propietarios/form.html', {
        'form': form, 'titulo': f'Editar propietario: {propietario}', 'propietario': propietario,
    })


@todo_el_personal
def detalle_propietario(request, pk):
    propietario = get_object_or_404(Propietario, pk=pk)
    pacientes = propietario.pacientes.annotate(num_citas=Count('citas'))
    from citas.models import Cita
    citas = (Cita.objects.filter(paciente__propietario=propietario)
             .select_related('paciente', 'veterinario').order_by('-fecha_cita', '-hora_inicio')[:10])
    return render(request, 'pacientes/propietarios/detalle.html', {
        'propietario': propietario, 'pacientes': pacientes, 'citas': citas,
    })


@administrador_o_veterinario
def eliminar_propietario(request, pk):
    propietario = get_object_or_404(Propietario, pk=pk)
    if request.method == 'POST':
        try:
            propietario.delete()
            messages.success(request, 'Propietario eliminado.')
            return redirect('lista_propietarios')
        except ProtectedError:
            messages.error(request, 'No se puede eliminar: el propietario tiene pacientes registrados. '
                                    'Elimine o reasigne primero sus pacientes.')
            return redirect('detalle_propietario', pk=pk)
    return render(request, 'pacientes/confirmar_eliminar.html', {
        'objeto': propietario, 'tipo': 'propietario',
        'volver': _url('detalle_propietario', pk),
        'advertencia': f'Tiene {propietario.pacientes.count()} paciente(s) asociado(s).'
        if propietario.pacientes.exists() else '',
    })


# ---------------------------------------------------------------------------
# Pacientes (RF-06 a RF-08)
# ---------------------------------------------------------------------------
@todo_el_personal
def lista_pacientes(request):
    q = request.GET.get('q', '').strip()
    especie = request.GET.get('especie', '')
    pacientes = Paciente.objects.select_related('propietario')
    if q:
        pacientes = pacientes.filter(_filtro_pacientes(q))
    if especie:
        pacientes = pacientes.filter(especie=especie)
    pagina = Paginator(pacientes.order_by('nombre'), 15).get_page(request.GET.get('page'))
    return render(request, 'pacientes/pacientes/lista.html', {
        'pagina': pagina, 'q': q, 'especie': especie, 'especies': Paciente.ESPECIE_CHOICES,
    })


@todo_el_personal
def crear_paciente(request):
    if request.method == 'POST':
        form = PacienteForm(request.POST)
        if form.is_valid():
            paciente = form.save()
            messages.success(request, f'Paciente "{paciente.nombre}" registrado correctamente.')
            if 'guardar_y_cita' in request.POST:
                return redirect(f"{_url('crear_cita')}?paciente={paciente.pk}")
            return redirect('ficha_paciente', pk=paciente.pk)
    else:
        inicial = {}
        propietario_id = request.GET.get('propietario')
        if propietario_id and propietario_id.isdigit():
            inicial['propietario'] = propietario_id
        form = PacienteForm(initial=inicial)
    return render(request, 'pacientes/pacientes/form.html', {'form': form, 'titulo': 'Nuevo paciente'})


@todo_el_personal
def editar_paciente(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    if request.method == 'POST':
        form = PacienteForm(request.POST, instance=paciente)
        if form.is_valid():
            form.save()
            messages.success(request, 'Paciente actualizado correctamente.')
            return redirect('ficha_paciente', pk=pk)
    else:
        form = PacienteForm(instance=paciente)
    return render(request, 'pacientes/pacientes/form.html', {
        'form': form, 'titulo': f'Editar paciente: {paciente.nombre}', 'paciente': paciente,
    })


@todo_el_personal
def ficha_paciente(request, pk):
    """Carnet del paciente con alergias resaltadas e historial de citas (RF-08, HU-10)."""
    paciente = get_object_or_404(Paciente.objects.select_related('propietario'), pk=pk)
    hoy = timezone.localdate()
    citas = paciente.citas.select_related('veterinario').order_by('-fecha_cita', '-hora_inicio')
    proximas = [c for c in citas if c.fecha_cita >= hoy and c.estado in ('pendiente', 'confirmada')]
    proximas.reverse()
    historial = [c for c in citas if c not in proximas]
    return render(request, 'pacientes/pacientes/ficha.html', {
        'paciente': paciente,
        'proximas': proximas,
        'historial': historial,
        'vacunas': paciente.vacunas.all(),
        'total_citas': len(citas),
        'completadas': sum(1 for c in citas if c.estado == 'completada'),
    })


@administrador_o_veterinario
def eliminar_paciente(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    if request.method == 'POST':
        try:
            propietario_id = paciente.propietario_id
            paciente.delete()
            messages.success(request, 'Paciente eliminado.')
            return redirect('detalle_propietario', pk=propietario_id)
        except ProtectedError:
            messages.error(request, 'No se puede eliminar: el paciente tiene citas registradas '
                                    'que forman parte de su historial clínico.')
            return redirect('ficha_paciente', pk=pk)
    return render(request, 'pacientes/confirmar_eliminar.html', {
        'objeto': paciente, 'tipo': 'paciente', 'volver': _url('ficha_paciente', pk),
        'advertencia': 'Tiene citas registradas; no podrá eliminarse.' if paciente.citas.exists() else '',
    })


# ---------------------------------------------------------------------------
# Vacunas
# ---------------------------------------------------------------------------
@todo_el_personal
def crear_vacuna(request, paciente_id):
    paciente = get_object_or_404(Paciente, pk=paciente_id)
    if request.method == 'POST':
        form = VacunaForm(request.POST, instance=Vacuna(paciente=paciente))
        if form.is_valid():
            form.save()
            messages.success(request, 'Vacuna registrada correctamente.')
            return redirect('ficha_paciente', pk=paciente.pk)
    else:
        form = VacunaForm(initial={'fecha_aplicacion': timezone.localdate()})
    return render(request, 'pacientes/vacunas/form.html', {
        'form': form, 'paciente': paciente, 'titulo': f'Registrar vacuna — {paciente.nombre}',
    })


@todo_el_personal
def editar_vacuna(request, pk):
    vacuna = get_object_or_404(Vacuna.objects.select_related('paciente'), pk=pk)
    if request.method == 'POST':
        form = VacunaForm(request.POST, instance=vacuna)
        if form.is_valid():
            form.save()
            messages.success(request, 'Vacuna actualizada.')
            return redirect('ficha_paciente', pk=vacuna.paciente_id)
    else:
        form = VacunaForm(instance=vacuna)
    return render(request, 'pacientes/vacunas/form.html', {
        'form': form, 'paciente': vacuna.paciente, 'titulo': f'Editar vacuna — {vacuna.paciente.nombre}',
    })


@administrador_o_veterinario
def eliminar_vacuna(request, pk):
    vacuna = get_object_or_404(Vacuna, pk=pk)
    paciente_id = vacuna.paciente_id
    if request.method == 'POST':
        vacuna.delete()
        messages.success(request, 'Registro de vacuna eliminado.')
        return redirect('ficha_paciente', pk=paciente_id)
    return render(request, 'pacientes/confirmar_eliminar.html', {
        'objeto': vacuna, 'tipo': 'registro de vacuna', 'volver': _url('ficha_paciente', paciente_id),
    })


def _url(nombre, *args):
    from django.urls import reverse
    return reverse(nombre, args=args)
