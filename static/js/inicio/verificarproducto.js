// Objeto para rastrear productos en la tabla
let productosEnTabla = {};


// Función para verificar y agregar un producto a la tabla
function verificarProducto(producto) {
    const productosBody = document.getElementById('tabla_productos'); // Referencia al cuerpo de la tabla

    // Verificar si el producto ya está en la tabla
    if (productosEnTabla[producto.Codigo_de_barras]) {
        const existingRow = productosEnTabla[producto.Codigo_de_barras];
        const cantidadActual = parseInt(existingRow.cells[6].textContent); // Columna de cantidad (índice 6)
        const nuevaCantidad = cantidadActual + 1;

        // Verificar si la nueva cantidad supera el stock disponible
        if (nuevaCantidad <= producto.Stock) {
            existingRow.cells[6].textContent = nuevaCantidad; // Actualizar la cantidad
        } else {
            alert(`El producto "${producto.Nombre}" ha alcanzado el límite de stock disponible.`)
    
        }
    } else {
        // Si el producto no está en la tabla, crear una nueva fila
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${producto.Codigo_de_barras}</td>
            <td>${producto.Nombre}</td>
            <td>${producto.Descripcion}</td>
            <td data-precio-original="${producto.Precio_Valor}">$${producto.Precio_Valor}</td> <!-- Guardar el precio original -->
            <td>${producto.Stock}</td> <!-- Stock disponible -->
            <td>${producto.Categoria}</td>
            <td>1</td> <!-- Cantidad inicial -->
            <td style="visibility:collapse; display:none;">$${producto.Precio_Costo}</td>
        `;
        productosBody.appendChild(row);

        // Guardar la fila en el objeto productosEnTabla para llevar el seguimiento
        productosEnTabla[producto.Codigo_de_barras] = row;
        console.log('productos en tabla')
        console.log(Object.values(productosEnTabla))
        // Agregar el evento de clic a la nueva fila
        row.addEventListener('click', seleccionarFila);

    }
}
