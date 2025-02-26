 // Variable global para almacenar el total original
// Variable global para almacenar el total original
let totalOriginal = 0;

// Aplica un descuento fijo en porcentaje (5% o 10%)
function aplicarDescuento(porcentaje) {
    const totalElement = document.getElementById('total-pagar');
    const descuento = totalOriginal * (porcentaje / 100);
    const totalConDescuento = totalOriginal - descuento;

    // Actualizar el total a cobrar
    totalElement.innerText = totalConDescuento.toFixed(2);
    document.getElementById('pago-con').value = totalConDescuento.toFixed(2);

    // Recalcular el Precio_Valor de cada producto en la tabla
    const filas = document.querySelectorAll('#tabla_productos tr');
    filas.forEach(fila => {
        const precioValorCell = fila.cells[3]; // Columna de Precio_Valor (índice 3)
        const precioOriginal = parseFloat(precioValorCell.getAttribute('data-precio-original')); // Precio original sin descuento

        // Si no se ha guardado el precio original, guardarlo
        if (!precioOriginal) {
            precioValorCell.setAttribute('data-precio-original', precioValorCell.textContent.replace('$', ''));
        }

        // Calcular el nuevo Precio_Valor con el descuento
        const nuevoPrecio = precioOriginal * (1 - porcentaje / 100);
        precioValorCell.textContent = `$${nuevoPrecio.toFixed(2)}`; // Actualizar el valor en la tabla
    });
}
 // Muestra el input para ingresar un descuento personalizado
 function mostrarDescuentoPersonalizado() {
   document.getElementById('descuento-personalizado').style.display = 'block';
 }

 // Aplica el descuento ingresado por el usuario
// Aplica el descuento ingresado por el usuario
function aplicarDescuentoPersonalizado() {
  const inputDescuento = document.getElementById('input-descuento');
  const porcentaje = parseFloat(inputDescuento.value);

  if (!isNaN(porcentaje) && porcentaje >= 0 && porcentaje <= 100) {
      aplicarDescuento(porcentaje); // Aplicar el descuento
      document.getElementById('descuento-personalizado').style.display = 'none'; // Ocultar el input
  } else {
      alert('Ingrese un porcentaje válido entre 0 y 100.');
  }
}
 // Evento para calcular el total y mostrar el modal de cobro
document.getElementById('cobrar').addEventListener('click', () => {
    // Verificar si hay productos en la tabla
    if (Object.keys(productosEnTabla).length === 0) {
        alert("No hay productos en la tabla. Agrega productos antes de cobrar."); // Mensaje de alerta
        return; // Salir de la función sin mostrar el modal
    }

    let total = 0;

    // Recorremos los productos en la tabla
    for (const codigo in productosEnTabla) {
        const row = productosEnTabla[codigo];
        const precio = parseFloat(row.cells[3].textContent.replace('$', '')); // Precio en la columna 3
        const cantidad = parseInt(row.cells[6].textContent); // Cantidad en la columna 6
        total += precio * cantidad;
    }

    // Asignamos el total calculado a la variable global totalOriginal
    totalOriginal = total;

    // Mostrar el total en el modal y actualizar el input "pago-con"
    document.getElementById('total-pagar').innerText = totalOriginal.toFixed(2);
    document.getElementById('pago-con').value = totalOriginal.toFixed(2); // Por defecto, igual al total
    document.getElementById('su-cambio').innerText = '0.00';

    // Mostrar el modal de cobro
    document.getElementById('modal-overlay').style.display = 'flex';
});

 // Actualizar el cambio al modificar el "pago con"
 document.getElementById('pago-con').addEventListener('input', (event) => {
   const total = parseFloat(document.getElementById('total-pagar').innerText);
   const pagoCon = parseFloat(event.target.value) || 0;
   const cambio = pagoCon - total;
   document.getElementById('su-cambio').innerText = cambio >= 0 ? cambio.toFixed(2) : '0.00';
 });

 // Cerrar el modal usando una clase común
 document.querySelectorAll('.cerrar-modal').forEach(button => {
   button.addEventListener('click', () => {
     document.getElementById('modal-overlay').style.display = 'none';
   });
 });