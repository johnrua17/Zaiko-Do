// Manejar el registro de la venta
async function registrarVentas(imprimir = false) {
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
            Precio_Costo: parseFloat(row.cells[7].textContent.replace('$', '')),
            Cantidad: parseInt(row.cells[6].textContent),
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
                total_final: total,
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
                    fecha: fecha,
                    total_final: total,
                }),
            });

            if (!agregarProductosResponse.ok) throw new Error('Errorrrrrr al agregar productos.');

            const productosData = await agregarProductosResponse.json();
            
            if (productosData.success) {
                alert('Venta y productos registrados correctamente.');

                // Limpiar la tabla y los campos del modal
                document.getElementById('tabla_productos').innerHTML = ''; // Limpiar la tabla
                productosEnTabla = {}; // Vaciar el objeto
                document.getElementById('modal-overlay').style.display = 'none'; // Cerrar el modal
                // Si se debe imprimir, generar la factura POS
                if (imprimir) {
                    generarFacturaPOS(productos, total, metodoPago, pagoCon, clienteNombre, clienteCC);
                }
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
}


function generarFacturaPOS(productos, total, metodoPago, pagoCon, clienteNombre, clienteCC) {
    // Crear una nueva pestaña
    const pestañaFactura = window.open('', '_blank');

    // Crear el contenido de la factura
    const contenidoFactura = `
        <html>
            <head>
                <title>Factura POS</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        width: 300px;
                        padding: 10px;
                        margin: 0;
                    }
                    h2, p {
                        text-align: center;
                        margin: 5px 0;
                    }
                    table {
                        width: 100%;
                        border-collapse: collapse;
                    }
                    th, td {
                        border-bottom: 1px solid #000;
                        padding: 5px;
                    }
                    th {
                        text-align: left;
                    }
                    td {
                        text-align: right;
                    }
                    hr {
                        border: 1px dashed #000;
                    }
                </style>
            </head>
            <body>
                <h2>Zaiko Do</h2>
                <p>Factura POS</p>
                <p>Fecha: ${new Date().toLocaleDateString()}</p>
                <p>Hora: ${new Date().toLocaleTimeString()}</p>
                <hr>
                <p><strong>Cliente:</strong> ${clienteNombre || "Consumidor Final"}</p>
                <p><strong>Identificación:</strong> ${clienteCC || "222222222222"}</p>
                <hr>
                <h3>Productos</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Producto</th>
                            <th>Cant.</th>
                            <th>Precio</th>
                            <th>Subtotal</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${productos.map(producto => `
                            <tr>
                                <td>${producto.Nombre}</td>
                                <td style="text-align: center;">${producto.Cantidad}</td>
                                <td>$${producto.Precio_Valor.toFixed(2)}</td>
                                <td>$${(producto.Precio_Valor * producto.Cantidad).toFixed(2)}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
                <hr>
                <p><strong>Total:</strong> $${total.toFixed(2)}</p>
                <p><strong>Método de Pago:</strong> ${metodoPago}</p>
                <p><strong>Pagó con:</strong> $${pagoCon.toFixed(2)}</p>
                <p><strong>Cambio:</strong> $${(pagoCon - total).toFixed(2)}</p>
                <hr>
                <p>¡Gracias por su compra!</p>
                <p>Vuelva pronto</p>
                <script>
                    // Imprimir la factura automáticamente al cargar la pestaña
                    window.onload = () => {
                        window.print(); // Imprimir la factura
                    };

                    // Cerrar la pestaña después de imprimir o cancelar
                    window.onafterprint = () => {
                        window.close(); // Cerrar la pestaña
                    };
                </script>
            </body>
        </html>
    `;

    // Escribir el contenido en la nueva pestaña
    pestañaFactura.document.write(contenidoFactura);
    pestañaFactura.document.close();
}