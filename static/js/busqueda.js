 // Buscar producto por código de barras
 async function buscarProductoCodigo() {
    const codigoBarras = document.getElementById('buscar_codigo_barras').value;

    if (!codigoBarras) {
        alert('Por favor, ingresa un código de barras.')
        
        return;
    }

    try {
        const response = await fetch('/buscar_producto_codigo', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ codigo_barras: codigoBarras }),
        });

        if (!response.ok) throw new Error('Error al buscar producto por código de barras.');

        const data = await response.json();

        if (data.error) {
            alert(data.error);
            // Usamos SweetAlert2 para mostrar la advertencia
            // Swal.fire({
            //     title: 'Advertencia',
            //     text: data.error,
            //     icon: 'warning',
            //     confirmButtonText: 'Entendido'
            // });
            return;
        }

        const producto = data.producto;
        console.log(producto)
        // Llamamos a la función de verificación que ya se encargará de mostrar advertencias si corresponde
        verificarProducto(producto);

    } catch (error) {
        console.error(error);
        // Swal.fire({
        //     title: 'Error',
        //     text: 'Ocurrió un error al buscar el producto.',
        //     icon: 'error',
        //     confirmButtonText: 'Aceptar'
        // });
    }
}

function Boton(){
    alert("Pronto podrás disfrutar de esta funcionalidad...")
}
// Asignar el evento de clic al botón de búsqueda
document.getElementById('buscar_producto_codigo').addEventListener('click', buscarProductoCodigo);
document.getElementById('modificar_valor').addEventListener('click', Boton);
document.getElementById('eliminar_producto').addEventListener('click', Boton);





// Busqueda de productos por nombre, categoria o descripcion


document.getElementById('buscar_productos').addEventListener('click', () => {
    document.getElementById('buscador_contenedor').style.display = 'block';
    // console.log("holaaa")
});

document.getElementById('cerrar_buscador').addEventListener('click', () => {
    document.getElementById('buscador_contenedor').style.display = 'none';
});

// Buscar productos dinámicamente al escribir en el input
document.getElementById('buscador_input').addEventListener('input', async (e) => {
    const terminoBusqueda = e.target.value.trim();

    if (!terminoBusqueda) {
        document.getElementById('resultados_busqueda').innerHTML = '';
        return;
    }

    try {
        const response = await fetch('/buscar_productoss', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ termino_busqueda: terminoBusqueda }),
        });

        if (!response.ok) throw new Error('Error al buscar productos');

        const data = await response.json();

        if (data.error) {
            document.getElementById('resultados_busqueda').innerHTML = `<p>${data.error}</p>`;
            return;
        }

        // Mostrar resultados con botón "Agregar a la venta"
        const resultadosHtml = data.productos.map(prod => `
            <div style="padding: 10px; border-bottom: 1px solid #ccc;">
                <strong>${prod.Nombre}</strong> (${prod.Codigo_de_barras})<br>
                <small>${prod.Descripcion}</small><br>
                Precio: $${prod.Precio_Valor}<br>
                Cantidad disponible: ${prod.Cantidad}<br>
                <button 
                    class="agregar-venta-btn" 
                    data-producto='${JSON.stringify(prod)}'
                >
                    Agregar a la venta
                </button>
            </div>
        `).join('');
        document.getElementById('resultados_busqueda').innerHTML = resultadosHtml;

        // Agregar evento a los botones de "Agregar a la venta"
        document.querySelectorAll('.agregar-venta-btn').forEach(btn => {
            btn.addEventListener('click', (event) => {
                const producto = JSON.parse(event.target.getAttribute('data-producto'));
                // La función verificarProducto se encargará de mostrar la advertencia si no hay stock.
                verificarProducto(producto);
            });
        });
    } catch (error) {
        console.error(error);
        document.getElementById('resultados_busqueda').innerHTML = '<p>Ocurrió un error al buscar productos.</p>';
    }
});