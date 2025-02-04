// Buscar producto por codigo de barras

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