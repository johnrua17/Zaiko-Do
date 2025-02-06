// Manejar el registro de la venta
document.getElementById('registrar_venta').addEventListener('click', async () => {
    const botonRegistrar = document.getElementById('registrar_venta');

    // Verificar que haya productos en la tabla
    if (Object.keys(productosEnTabla).length === 0) {
        alert('No hay productos agregados para registrar la venta.');
        return;
    }

    // Recolectar los productos desde productosEnTabla
    const productos = Object.values(productosEnTabla).map(row => {
        return {
            Codigo_de_barras: row.cells[0].textContent,
            Nombre: row.cells[1].textContent,
            Descripcion: row.cells[2].textContent,
            Precio_Valor: parseFloat(row.cells[3].textContent.replace('$', '')),
            Precio_Costo: parseFloat(row.cells[4].textContent.replace('$', '')),
            Stock: parseInt(row.cells[6].textContent),
            Categoria: row.cells[5].textContent
        };
    });

    // Obtener datos del modal
    const total = parseFloat(document.getElementById('total-pagar').innerText);
    const pagoCon = parseFloat(document.getElementById('pago-con').value);
    const metodoPago = document.querySelector('input[name="metodo-pago"]:checked').value;

    // Datos del cliente
    const clienteNombre = document.getElementById('cliente-nombre').value.trim();
    const clienteCC = document.getElementById('cliente-cc').value.trim();

    // Datos para crédito
    const identificacion = document.getElementById('identificacion').value.trim();
    const nombre = document.getElementById('nombres').value.trim();
    const contacto = document.getElementById('contacto').value.trim();
    const nota = document.getElementById('nota').value.trim();

    // Desactivar el botón para evitar múltiples envíos
    botonRegistrar.disabled = true;

    try {
        // Primera solicitud: Registrar la venta
        const response = await fetch('/ventas/registrar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                productos: productos,
                metodo_pago: metodoPago,
                pagocon: pagoCon,
                cliente: metodoPago === 'credito' ? nombre : (clienteNombre || "Consumidor Final"),
                idcliente: metodoPago === 'credito' ? identificacion : (clienteCC || "222222222222"),
                contacto: metodoPago === 'credito' ? contacto : "",
                nota: metodoPago === 'credito' ? nota : "",
                credito: metodoPago === 'credito' ? 1 : 0,
            }),
        });

        if (!response.ok) throw new Error('Error al registrar la venta.');

        const data = await response.json();

        if (data.success) {
            // Si la venta se registró correctamente, extraer los valores devueltos
            const { idventa, fecha } = data;

            // Segunda solicitud: Agregar productos a la venta
            const agregarProductosResponse = await fetch('/ventas/agregar_productos', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    idventa: idventa,
                    productos: productos,
                    fecha: fecha
                }),
            });

            if (!agregarProductosResponse.ok) throw new Error('Error al agregar productos.');

            const productosData = await agregarProductosResponse.json();
            
            if (productosData.success) {
                alert('Venta y productos registrados correctamente.');

                // Limpiar la tabla y los campos del modal
                document.getElementById('tabla_productos').innerHTML = ''; // Limpiar la tabla
                productosEnTabla = {}; // Vaciar el objeto
                document.getElementById('modal-overlay').style.display = 'none'; // Cerrar el modal
            } else {
                alert(productosData.error);
            }
        } else {
            alert(data.error);
        }
    } catch (error) {
        console.error(error);
        alert('Ocurrió un error al registrar la venta.');
    } finally {
        botonRegistrar.disabled = false; // Habilitar el botón nuevamente
    }
});
