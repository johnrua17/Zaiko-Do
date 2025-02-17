document.addEventListener('keydown', function(event) {
    const focusedElement = document.activeElement;
    const codigoBarrasInput = document.getElementById('buscar_codigo_barras');

    // Permitir entrada desde lector de código de barras aunque el input esté deshabilitado
    if (event.key.length === 1 && codigoBarrasInput.disabled) {
        codigoBarrasInput.disabled = false;
        codigoBarrasInput.focus();
        setTimeout(() => {
            codigoBarrasInput.disabled = true;
        }, 0);
    }

    // Si se está escribiendo en un input (que no sea el de código) se permite la entrada normal,
    // pero se agrega funcionalidad especial para Escape
    if (focusedElement.tagName.toLowerCase() === 'input' && focusedElement.id !== 'buscar_codigo_barras') {
        if (event.key === 'Escape' || event.key === 'Esc') {
            // Buscar botones o elementos para cerrar formularios/modales
            document.querySelectorAll('.cerrar-modal, #cerrar_buscador').forEach(btn => btn.click());
        }
        return;
    }

    // Mapeo de teclas a funcionalidades
    if (event.key === 'r' || event.key === 'R') {
        if (focusedElement.id === 'buscar_codigo_barras') event.preventDefault();
        document.getElementById('buscar_producto_codigo').click();
    } else if (event.key === 'e' || event.key === 'E') {
        if (focusedElement.id === 'buscar_codigo_barras') event.preventDefault();
        document.getElementById('eliminar_producto').click();
    } else if (event.key === 'b' || event.key === 'B') {
        if (focusedElement.id === 'buscar_codigo_barras') event.preventDefault();
        document.getElementById('buscar_productos').click();
    } else if (event.key === 'c' || event.key === 'C') {
        if (focusedElement.id === 'buscar_codigo_barras') event.preventDefault();
        document.getElementById('cobrar').click();
    } else if (event.key === 'm' || event.key === 'M') {
        if (focusedElement.id === 'buscar_codigo_barras') event.preventDefault();
        document.getElementById('modificar_valor').click();
    } else if (event.key === 'Escape' || event.key === 'Esc') {
        // Cierra formularios o modales abiertos
        document.querySelectorAll('.cerrar-modal, #cerrar_buscador').forEach(btn => btn.click());
    }
});
