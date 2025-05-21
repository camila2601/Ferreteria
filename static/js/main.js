document.addEventListener('DOMContentLoaded', function() {
    // Funcionalidad para mensajes flash
    const flashMessages = document.querySelectorAll('.flash');
    if (flashMessages.length > 0) {
        flashMessages.forEach(message => {
            setTimeout(() => {
                message.style.opacity = '0';
                setTimeout(() => message.remove(), 300);
            }, 5000);
        });
    }

    // Manejo de formularios de reportes
    const reportForms = document.querySelectorAll('.report-form');
    reportForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const fechaInicio = this.querySelector('input[name="fecha_inicio"]').value;
            const fechaFin = this.querySelector('input[name="fecha_fin"]').value;
            
            if (new Date(fechaFin) < new Date(fechaInicio)) {
                e.preventDefault();
                alert('La fecha fin no puede ser anterior a la fecha inicio');
            }
        });
    });

    // Validación de stock en formulario de ventas
    const saleForm = document.querySelector('form[action="{{ url_for(\'new_sale\') }}"]');
    if (saleForm) {
        saleForm.addEventListener('submit', function(e) {
            let valid = true;
            const productInputs = this.querySelectorAll('input[name^="product_"]');
            
            productInputs.forEach(input => {
                if (input.name.includes('cantidad')) {
                    const productId = input.name.split('_')[1];
                    const stock = parseInt(document.querySelector(`input[name="product_${productId}_stock"]`).value);
                    const cantidad = parseInt(input.value);
                    
                    if (cantidad > stock) {
                        valid = false;
                        alert(`No hay suficiente stock para el producto ${productId}`);
                    }
                }
            });
            
            if (!valid) {
                e.preventDefault();
            }
        });
    }
});

// Función para agregar producto en nueva venta
function addProductRow() {
    const container = document.getElementById('product-rows');
    const index = container.children.length;
    
    const row = document.createElement('div');
    row.className = 'product-row';
    row.innerHTML = `
        <select name="product_${index}_id" required>
            <option value="">Seleccionar producto</option>
        </select>
        <input type="number" name="product_${index}_cantidad" min="1" value="1" required>
        <span class="subtotal">$0.00</span>
        <button type="button" class="btn btn-danger btn-sm" onclick="removeProductRow(this)">
            <i class="fas fa-times"></i>
        </button>
        <input type="hidden" name="product_${index}_stock" value="0">
        <input type="hidden" name="product_${index}_price" value="0">
    `;
    
    container.appendChild(row);

    // Supón que tienes una variable global `window.productos` con los productos
    const select = row.querySelector('select');
    if (window.productos && Array.isArray(window.productos)) {
        window.productos.forEach(producto => {
            const option = document.createElement('option');
            option.value = producto._id;
            option.dataset.stock = producto.stock;
            option.dataset.price = producto.precio;
            option.textContent = `${producto.nombre} - Stock: ${producto.stock} - $${Number(producto.precio).toFixed(2)}`;
            select.appendChild(option);
        });
    }

    const cantidadInput = row.querySelector('input[type="number"]');
    
    select.addEventListener('change', updateProductInfo);
    cantidadInput.addEventListener('input', updateSubtotal);
    
    // Actualizar contador de productos
    document.querySelector('input[name="product_count"]').value = index + 1;
}

function removeProductRow(button) {
    const row = button.closest('.product-row');
    row.remove();
    
    // Renumerar los productos restantes
    const container = document.getElementById('product-rows');
    const rows = container.querySelectorAll('.product-row');
    
    rows.forEach((row, index) => {
        const inputs = row.querySelectorAll('[name^="product_"]');
        inputs.forEach(input => {
            const name = input.name.replace(/product_\d+_/, `product_${index}_`);
            input.name = name;
        });
    });
    
    // Actualizar contador de productos
    document.querySelector('input[name="product_count"]').value = rows.length;
    calculateTotal();
}

function updateProductInfo(e) {
    const select = e.target;
    const option = select.options[select.selectedIndex];
    const row = select.closest('.product-row');
    
    if (option.value) {
        const stock = option.dataset.stock;
        const price = option.dataset.price;
        
        row.querySelector('input[name$="_stock"]').value = stock;
        row.querySelector('input[name$="_price"]').value = price;
        
        // Actualizar cantidad máxima
        const cantidadInput = row.querySelector('input[type="number"]');
        cantidadInput.max = stock;
        cantidadInput.value = Math.min(1, stock);
        
        updateSubtotal({target: cantidadInput});
    } else {
        row.querySelector('input[name$="_stock"]').value = 0;
        row.querySelector('input[name$="_price"]').value = 0;
        row.querySelector('.subtotal').textContent = '$0.00';
    }
    
    calculateTotal();
}

function updateSubtotal(e) {
    const input = e.target;
    const row = input.closest('.product-row');
    const price = parseFloat(row.querySelector('input[name$="_price"]').value);
    const quantity = parseInt(input.value) || 0;
    const subtotal = price * quantity;
    
    row.querySelector('.subtotal').textContent = `$${subtotal.toFixed(2)}`;
    calculateTotal();
}

function calculateTotal() {
    const subtotals = document.querySelectorAll('.subtotal');
    let total = 0;
    
    subtotals.forEach(subtotal => {
        const value = parseFloat(subtotal.textContent.replace('$', '')) || 0;
        total += value;
    });
    
        document.getElementById('total').textContent = `$${total.toFixed(2)}`;
    }