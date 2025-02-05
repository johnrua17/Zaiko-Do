// Manejar el registro de la venta
document.getElementById('registrar_venta').addEventListener('click', async () => {
    const botonRegistrar = document.getElementById('registrar_venta');
    if (productosAgregados.length === 0) {
        alert('No hay productos agregados para registrar la venta.');
        return;
    }
    const total = parseFloat(document.getElementById('total-pagar').innerText);
    const pagoCon = parseFloat(document.getElementById('pago-con').value);
    const metodoPago = document.querySelector('input[name="metodo-pago"]:checked').value;
    
    // Recoger los datos del cliente (si se han ingresado)
    const clienteNombre = document.getElementById('cliente-nombre').value.trim();
    const clienteCC = document.getElementById('cliente-cc').value.trim();
    
    // Desactivar el botón para evitar múltiples envíos
    botonRegistrar.disabled = true;
    // console.log(pagoCon)
    // console.log(metodoPago)

    try {
        const response = await fetch('/ventas/registrar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                productos: productosAgregados, 
                metodo_pago: metodoPago,
                pagocon: pagoCon,
                // Si no se ingresa datos, se usan valores por defecto:
                cliente: clienteNombre || "Consumidor Final",
                idcliente: clienteCC || "222222222222"
            }),
        });

        if (!response.ok) throw new Error('Error al registrar la venta.');

        const data = await response.json();

        if (data.success) {
            // Registrar productos en detalleventas
            const agregarProductosResponse = await fetch('/ventas/agregar_productos', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    idventa: data.idventa,
                    productos: productosAgregados,
                    fecha: data.fecha,
                }),
            });

            if (!agregarProductosResponse.ok) throw new Error('Error al agregar productos.');

            const productosData = await agregarProductosResponse.json();
            if (productosData.success) {
                alert('Venta y productos registrados correctamente.');
                document.getElementById('modal-overlay').style.display = 'none';

                // Limpiar la tabla y los productos agregados
                productosAgregados.length = 0; // Vaciar el array
                document.getElementById('tabla_productos').innerHTML = ''; // Limpiar la tabla
            }
        } else {
            alert(data.error);
        }
    } catch (error) {
        console.error(error);
        alert('Ocurrió un error al registrar la venta.');
    } finally {
        // Habilitar el botón después de la respuesta del servidor
        botonRegistrar.disabled = false;
    }
});