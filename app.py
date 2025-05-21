from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response, send_file
from flask_pymongo import PyMongo, DESCENDING
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import datetime
import pdfkit
import openpyxl
from io import BytesIO
import os
from functools import wraps
from urllib.parse import quote_plus

# Configuración de la aplicación
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configuración de MongoDB Atlas


password = quote_plus("GA239XY562HwXPyL")  # Escapa caracteres especiales si los hay
app.config["MONGO_URI"] = f"mongodb+srv://angaritacamila05:{password}@ferreteriadb.nnmpeau.mongodb.net/?retryWrites=true&w=majority&appName=ferreteriaDB"


# Inicializar la conexión a MongoDB
try:
    mongo = PyMongo(app)
    # Intentar una operación simple para verificar la conexión
    mongo.cx.server_info()
    print("✅ Conexión a MongoDB exitosa.")
except Exception as e:
    print(f"❌ Error al conectar con MongoDB: {e}")

# Context processor para variables globales
@app.context_processor
def inject_global_vars():
    return dict(
        show_register=True  # Controla visibilidad del enlace de registro
    )

# Decorador para rutas que requieren autenticación
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor inicie sesión primero', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# ------------------------------------------
# Rutas de Autenticación (Corregidas)
# ------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash('Por favor complete todos los campos', 'danger')
            return redirect(url_for('login'))
        
        user = mongo.db.users.find_one({'username': username})
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['username'] = user['username']
            session['role'] = user.get('role', 'user')
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        
        flash('Usuario o contraseña incorrectos', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        # Validaciones
        if not all([username, password, confirm_password]):
            flash('Todos los campos son requeridos', 'danger')
            return redirect(url_for('register'))
            
        if password != confirm_password:
            flash('Las contraseñas no coinciden', 'danger')
            return redirect(url_for('register'))
            
        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres', 'danger')
            return redirect(url_for('register'))
            
        if mongo.db.users.find_one({'username': username}):
            flash('El nombre de usuario ya está en uso', 'danger')
            return redirect(url_for('register'))
        
        # Crear nuevo usuario
        hashed_password = generate_password_hash(password)
        
        mongo.db.users.insert_one({
            'username': username,
            'password': hashed_password,
            'role': 'user',
            'created_at': datetime.utcnow()
        })
        
        flash('Registro exitoso. Por favor inicie sesión', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('Sesión cerrada correctamente', 'info')
    return redirect(url_for('login'))

# ------------------------------------------
# Módulo de Productos (CRUD Completo)
# ------------------------------------------
@app.route('/products')
@login_required
def products():
    search = request.args.get('search', '')
    page = int(request.args.get('page', 1))
    per_page = 10
    
    query = {'nombre': {'$regex': search, '$options': 'i'}} if search else {}
    
    productos = list(mongo.db.productos.find(query).skip((page-1)*per_page).limit(per_page))
    total = mongo.db.productos.count_documents(query)
    
    return render_template('products.html', 
                         productos=productos,
                         page=page,
                         total_pages=(total // per_page) + 1,
                         search=search)

@app.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        try:
            producto = {
                'nombre': request.form.get('nombre'),
                'descripcion': request.form.get('descripcion'),
                'precio': float(request.form.get('precio', 0)),
                'costo': float(request.form.get('costo', 0)),
                'stock': int(request.form.get('stock', 0)),
                'stock_minimo': int(request.form.get('stock_minimo', 0)),
                'categoria': request.form.get('categoria'),
                'proveedor': request.form.get('proveedor'),
                'codigo_barras': request.form.get('codigo_barras'),
                'fecha_actualizacion': datetime.utcnow(),
                'creado_por': session['user_id']
            }
            
            mongo.db.productos.insert_one(producto)
            flash('Producto añadido correctamente', 'success')
            return redirect(url_for('products'))
        
        except Exception as e:
            flash(f'Error al agregar producto: {str(e)}', 'danger')
    
    categorias = mongo.db.categorias.find()
    proveedores = mongo.db.proveedores.find()
    return render_template('add_product.html', 
                         categorias=categorias,
                         proveedores=proveedores)

@app.route('/edit_product/<id>', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    if request.method == 'POST':
        try:
            mongo.db.productos.update_one(
                {'_id': ObjectId(id)},
                {'$set': {
                    'nombre': request.form.get('nombre'),
                    'descripcion': request.form.get('descripcion'),
                    'precio': float(request.form.get('precio', 0)),
                    'costo': float(request.form.get('costo', 0)),
                    'stock': int(request.form.get('stock', 0)),
                    'stock_minimo': int(request.form.get('stock_minimo', 0)),
                    'categoria': request.form.get('categoria'),
                    'proveedor': request.form.get('proveedor'),
                    'codigo_barras': request.form.get('codigo_barras'),
                    'fecha_actualizacion': datetime.utcnow()
                }}
            )
            flash('Producto actualizado correctamente', 'success')
            return redirect(url_for('products'))
        
        except Exception as e:
            flash(f'Error al actualizar producto: {str(e)}', 'danger')
    
    producto = mongo.db.productos.find_one({'_id': ObjectId(id)})
    categorias = mongo.db.categorias.find()
    proveedores = mongo.db.proveedores.find()
    
    return render_template('edit_product.html', 
                         producto=producto,
                         categorias=categorias,
                         proveedores=proveedores)

@app.route('/delete_product/<id>')
@login_required
def delete_product(id):
    try:
        mongo.db.productos.delete_one({'_id': ObjectId(id)})
        flash('Producto eliminado correctamente', 'success')
    except Exception as e:
        flash(f'Error al eliminar producto: {str(e)}', 'danger')
    
    return redirect(url_for('products'))

# ------------------------------------------
# Módulo de Clientes (CRUD)
# ------------------------------------------
@app.route('/customers')
@login_required
def customers():
    search = request.args.get('search', '')
    query = {'nombre': {'$regex': search, '$options': 'i'}} if search else {}
    clientes = list(mongo.db.clientes.find(query).sort('nombre', 1))
    return render_template('customers.html', clientes=clientes, search=search)

@app.route('/add_customer', methods=['GET', 'POST'])
@login_required
def add_customer():
    if request.method == 'POST':
        try:
            cliente = {
                'nombre': request.form.get('nombre'),
                'direccion': request.form.get('direccion'),
                'telefono': request.form.get('telefono'),
                'email': request.form.get('email'),
                'tipo_documento': request.form.get('tipo_documento'),
                'numero_documento': request.form.get('numero_documento'),
                'fecha_registro': datetime.utcnow(),
                'creado_por': session['user_id']
            }
            
            mongo.db.clientes.insert_one(cliente)
            flash('Cliente añadido correctamente', 'success')
            return redirect(url_for('customers'))
        
        except Exception as e:
            flash(f'Error al agregar cliente: {str(e)}', 'danger')
    
    return render_template('add_customer.html')

# ------------------------------------------
# Módulo de Ventas (Mejorado)
# ------------------------------------------
@app.route('/sales')
@login_required
def sales():
    search = request.args.get('search', '')
    query = {}
    if search:
        query['$or'] = [
            {'cliente_id': {'$regex': search, '$options': 'i'}},
            {'productos.nombre': {'$regex': search, '$options': 'i'}}
        ]
    
    ventas = list(mongo.db.ventas.find(query).sort('fecha', DESCENDING).limit(50))
    return render_template('sales.html', ventas=ventas, search=search)

@app.route('/new_sale', methods=['GET', 'POST'])
@login_required
def new_sale():
    if request.method == 'POST':
        try:
            productos_vendidos = []
            total = 0
            
            for i in range(int(request.form.get('product_count', 0))):
                product_id = request.form.get(f'product_{i}_id')
                cantidad = int(request.form.get(f'product_{i}_cantidad', 0))
                
                producto = mongo.db.productos.find_one({'_id': ObjectId(product_id)})
                
                if producto:
                    if producto['stock'] < cantidad:
                        flash(f'Stock insuficiente para {producto["nombre"]}', 'danger')
                        return redirect(url_for('new_sale'))
                    
                    subtotal = producto['precio'] * cantidad
                    total += subtotal
                    
                    productos_vendidos.append({
                        'producto_id': product_id,
                        'nombre': producto['nombre'],
                        'precio': producto['precio'],
                        'cantidad': cantidad,
                        'subtotal': subtotal
                    })
            
            venta = {
                'cliente_id': request.form.get('cliente_id'),
                'productos': productos_vendidos,
                'total': total,
                'impuesto': total * 0.18,
                'metodo_pago': request.form.get('metodo_pago'),
                'fecha': datetime.utcnow(),
                'vendedor_id': session['user_id'],
                'estado': 'completada'
            }
            
            # Actualizar stock
            for producto in productos_vendidos:
                mongo.db.productos.update_one(
                    {'_id': ObjectId(producto['producto_id'])},
                    {'$inc': {'stock': -producto['cantidad']}}
                )
            
            mongo.db.ventas.insert_one(venta)
            flash('Venta registrada correctamente', 'success')
            return redirect(url_for('sales'))
        
        except Exception as e:
            flash(f'Error al registrar venta: {str(e)}', 'danger')
    
    productos = list(mongo.db.productos.find({'stock': {'$gt': 0}}))
    clientes = list(mongo.db.clientes.find())
    return render_template('new_sale.html', 
                         productos=productos,
                         clientes=clientes)

# ------------------------------------------
# Módulo de Reportes (Mejorado)
# ------------------------------------------
@app.route('/reports')
@login_required
def reports():
    return render_template('reports.html')

@app.route('/generate_inventory_report')
@login_required
def generate_inventory_report():
    try:
        formato = request.args.get('formato', 'pdf')
        productos = list(mongo.db.productos.find().sort('nombre', 1))
        
        if formato == 'pdf':
            rendered = render_template('report_inventory_pdf.html', 
                                      productos=productos,
                                      fecha=datetime.now().strftime('%Y-%m-%d'))
            
            pdf = pdfkit.from_string(rendered, False)
            
            response = make_response(pdf)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = 'attachment; filename=reporte_inventario.pdf'
            return response
        
        elif formato == 'excel':
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Inventario"
            
            # Encabezados
            headers = ['Código', 'Nombre', 'Precio', 'Stock', 'Stock Mínimo', 'Categoría', 'Proveedor']
            ws.append(headers)
            
            # Datos
            for p in productos:
                ws.append([
                    p.get('codigo_barras', ''),
                    p['nombre'],
                    p['precio'],
                    p['stock'],
                    p.get('stock_minimo', 0),
                    p['categoria'],
                    p.get('proveedor', '')
                ])
            
            # Ajustar anchos de columna
            for col in ws.columns:
                max_length = 0
                column = col[0].column_letter
                for cell in col:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = (max_length + 2) * 1.2
                ws.column_dimensions[column].width = adjusted_width
            
            buffer = BytesIO()
            wb.save(buffer)
            buffer.seek(0)
            
            return send_file(
                buffer,
                as_attachment=True,
                download_name='reporte_inventario.xlsx',
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
    
    except Exception as e:
        flash(f'Error al generar reporte: {str(e)}', 'danger')
        return redirect(url_for('reports'))

# ------------------------------------------
# Dashboard y rutas principales (Mejorado)
# ------------------------------------------
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Estadísticas generales
    total_productos = mongo.db.productos.count_documents({})
    total_clientes = mongo.db.clientes.count_documents({})
    
    # Ventas de hoy
    hoy = datetime.combine(datetime.today(), datetime.min.time())
    ventas_hoy = mongo.db.ventas.count_documents({'fecha': {'$gte': hoy}})
    
    # Productos con bajo stock
    productos_bajo_stock = list(mongo.db.productos.find({
        '$expr': {'$lt': ['$stock', '$stock_minimo']}
    }).limit(5))
    
    # Últimas ventas
    ultimas_ventas = list(mongo.db.ventas.find().sort('fecha', DESCENDING).limit(5))
    
    return render_template('dashboard.html',
                         total_productos=total_productos,
                         total_clientes=total_clientes,
                         ventas_hoy=ventas_hoy,
                         productos_bajo_stock=productos_bajo_stock,
                         ultimas_ventas=ultimas_ventas)

# ------------------------------------------
# Configuración y arranque
# ------------------------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)