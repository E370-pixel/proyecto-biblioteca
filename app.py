import os
from flask import Flask, render_template, jsonify, request 
from flask_mysqldb import MySQL

# --- CONFIGURACIÓN DE LA APLICACIÓN ---
app = Flask(__name__)

# --- CONFIGURACIÓN DE LA BASE DE DATOS (REEMPLAZA CON TUS CREDENCIALES RDS) ---
# Se recomienda usar variables de entorno para estas credenciales en producción
app.config['MYSQL_HOST'] = 'mi-bd.cjs2kq4428y5.us-east-2.rds.amazonaws.com'
app.config['MYSQL_USER'] = 'admin'
app.config['MYSQL_PASSWORD'] = 'proyectoB2025'
app.config['MYSQL_DB'] = 'Biblioteca'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor' # Para obtener resultados como diccionarios

mysql = MySQL(app)

# --- MAPEO GLOBAL DE VISTAS SQL PARA LA API ---
SQL_QUERIES = {
    # DASHBOARD 1: USO Y FLUJO DE PRÉSTAMOS (Google Charts)
    'prestamos_vs_devoluciones_mes': "SELECT periodo, total_prestamos, total_devoluciones FROM vw_prestamos_vs_devoluciones_mes",
    'prestamos_por_tipo_usuario': "SELECT nombre_tipo_usuario, total_prestamos FROM vw_prestamos_por_tipo_usuario",
    'prestamos_tipo_material': "SELECT tipo_material, total_prestamos, periodo FROM vw_prestamos_tipo_material",
    
    # DASHBOARD 2: MULTAS, ATRASOS Y PAGOS (Google Charts)
    'multas_mensuales': "SELECT periodo, monto_total FROM vw_multas_mensuales",
    'estado_pago_multas': "SELECT estado_pago, cantidad, total_monto FROM vw_estado_pago_multas",
    'usuarios_con_mas_multas': "SELECT usuario, total_multas, cantidad_multas FROM vw_usuarios_con_mas_multas",
    'correlacion_atraso': "SELECT dias_atraso, monto FROM vw_correlacion_atraso", 
    
    # DASHBOARD 3: IMPACTO Y USO ACADÉMICO (Google Charts)
    'prestamos_por_departamento': "SELECT nombre, total_prestamos, fecha_prestamo FROM vw_prestamos_por_departamento",
    'frecuencia_prestamos': "SELECT dia_semana, prestamos, fecha_prestamo FROM vw_frecuencia_prestamos",
    'proporcion_material': "SELECT tipo_material, cantidad_prestamos FROM vw_proporcion_material",

    # DASHBOARD 4: CICLO DE USO DE MATERIALES (D3.js)
    'flujo_material': "SELECT recurso, idInventario, idPrestamo, idDevolucion FROM vw_flujo_material",
    # CORRECCIÓN DEFINITIVA (Se elimina fecha_prestamo de la vista agregada)
    'prestamos_por_dia': "SELECT dia_semana, tipo_material, total FROM vw_prestamos_por_dia", 
    'ciclo_vida_items': "SELECT idInventario, fecha_ingreso, primer_prestamo, ultima_devolucion FROM vw_ciclo_vida_items",
    
    # DASHBOARD 5: ADQUISICIONES, PROVEEDORES Y CATÁLOGO VIVO (D3.js)
    'flujo_proveedor_catalogo': "SELECT proveedor, recurso, cantidad, fecha_pedido, idPedido FROM vw_flujo_proveedor_catalogo", # Añadido idPedido para filtrar
    'categorias_materiales': "SELECT categoria, total_titulos FROM vw_categorias_materiales",
    'catalogo_incorporaciones': "SELECT periodo, proveedor, total_materiales FROM vw_catalogo_incorporaciones",

    # DASHBOARD 6: IMPACTO Y USO ACADÉMICO (D3.js) - Versión 2
    'relacion_prestamos_materiales': "SELECT estudiante, material, estado FROM vw_relacion_prestamos_materiales",
    'duracion_prestamos': "SELECT tipo_material, duracion_dias, fecha_prestamo FROM vw_duracion_prestamos", # Añadido fecha_prestamo para filtrado
    'distribucion_devoluciones': "SELECT estado_ejemplar, total_devoluciones FROM vw_distribucion_devoluciones",
}

# --- RUTAS DE LA PÁGINA WEB ---

@app.route('/')
def inicio():
    """Ruta para la página de Inicio con el Carrusel."""
    return render_template('index.html')

@app.route('/quienes-somos')
def quienes_somos():
    """Ruta para la página Quiénes Somos."""
    return render_template('quienes_somos.html')

@app.route('/historia')
def historia():
    """Ruta para la página Historia."""
    return render_template('historia.html')

@app.route('/mision-vision')
def mision_vision():
    """Ruta para la página Misión y Visión."""
    return render_template('mision_vision.html')

@app.route('/contactenos')
def contactenos():
    """Ruta para la página Contáctenos (con formularios estáticos)."""
    return render_template('contactenos.html')

@app.route('/dashboards')
def dashboards_main():
    """Ruta principal para la selección de Dashboards."""
    return render_template('dashboards/dashboards.html')

# --- RUTAS DE DASHBOARDS ESPECÍFICOS ---

# Google Charts
@app.route('/dashboards/uso-flujo-prestamos')
def uso_flujo_prestamos():
    """Ruta para el dashboard de Uso y Flujo de Préstamos."""
    return render_template('dashboards/uso_flujo_prestamos.html')

@app.route('/dashboards/multas-atrasos-pagos')
def multas_atrasos_pagos():
    """Ruta para el dashboard de Multas, Atrasos y Pagos."""
    return render_template('dashboards/multas_atrasos_pagos.html')

@app.route('/dashboards/impacto-uso-academico')
def impacto_uso_academico():
    """Ruta para el dashboard de Impacto y Uso Académico (Google Charts)."""
    return render_template('dashboards/impacto_uso_academico.html')

# D3.js Charts (Nuevas Rutas)
@app.route('/dashboards/ciclo-uso-materiales')
def ciclo_uso_materiales():
    """Ruta para el dashboard de Ciclo de Uso de Materiales (D3.js)."""
    return render_template('dashboards/ciclo_uso_materiales.html')

@app.route('/dashboards/adquisiciones-catalogo')
def adquisiciones_catalogo():
    """Ruta para el dashboard de Adquisiciones y Catálogo Vivo (D3.js)."""
    return render_template('dashboards/adquisiciones_catalogo.html')

@app.route('/dashboards/impacto-uso-academico-d3')
def impacto_uso_academico_d3():
    """Ruta para el dashboard de Impacto y Uso Académico (D3.js)."""
    return render_template('dashboards/impacto_uso_academico_d3.html')


# --- RUTA DE API DE DATOS (ENDPOINT ÚNICO) ---

@app.route('/api/data/<query_name>', methods=['GET'])
def get_data(query_name):
    
    # 1. Verificar que la query exista en el diccionario global
    if query_name not in SQL_QUERIES:
        return jsonify({"error": "Query not found"}), 404

    # 2. Obtener filtros de la URL
    mes = request.args.get('mes')
    material = request.args.get('material')
    anio = request.args.get('anio')
    usuario = request.args.get('usuario') 
    estado_multa = request.args.get('estado_multa')
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    # Nuevos Filtros D3
    proveedor = request.args.get('proveedor')
    categoria = request.args.get('categoria')


    base_query = SQL_QUERIES[query_name] 
    query_lower = base_query.lower() # Usamos esto para la verificación segura de columnas

    # 3. Construir la cláusula WHERE (Lógica de filtrado inteligente)
    where_clauses = []
    params = []

    # --- FILTROS DE USO GENERAL (Período: 'YYYY-MM') ---
    if material and 'tipo_material' in query_lower:
        where_clauses.append("tipo_material = %s")
        params.append(material)

    if mes and 'periodo' in query_lower:
        where_clauses.append("SUBSTR(periodo, 6, 2) = %s")
        params.append(mes)
        
    if anio and 'periodo' in query_lower:
        where_clauses.append("SUBSTR(periodo, 1, 4) = %s")
        params.append(anio)

    # --- FILTROS DE MULTAS Y PAGOS ---
    if usuario and 'usuario' in query_lower: 
        where_clauses.append("usuario = %s")
        params.append(usuario)

    if estado_multa and 'estado_pago' in query_lower:
        where_clauses.append("estado_pago = %s")
        params.append(estado_multa)
        
    # --- FILTROS DE ADQUISICIONES ---
    if proveedor and 'proveedor' in query_lower:
        where_clauses.append("proveedor = %s")
        params.append(proveedor)
        
    if categoria and 'categoria' in query_lower:
        where_clauses.append("categoria = %s")
        params.append(categoria)
        
    # --- FILTROS DE RANGO DE FECHAS ---
    
    # Identificar la columna de fecha relevante para el filtrado
    date_column = None
    
    # Prioridad 1: Columnas de fecha exactas (YYYY-MM-DD)
    if 'fecha_prestamo' in query_lower:
        date_column = 'fecha_prestamo'
    elif 'fecha_generacion' in query_lower: 
        date_column = 'fecha_generacion'
    elif 'fecha_ingreso' in query_lower:
        date_column = 'fecha_ingreso'
    elif 'fecha_pedido' in query_lower:
        date_column = 'fecha_pedido'
    # Prioridad 2: Columna de período (YYYY-MM) para vistas agregadas
    elif 'periodo' in query_lower:
         date_column = 'periodo' # Usar la columna de periodo si existe


    # Aplicar Filtro de FECHA INICIO
    if fecha_inicio and date_column:
        # Para columnas de FECHA, usamos >=
        if date_column != 'periodo':
             where_clauses.append(f"{date_column} >= %s")
             params.append(fecha_inicio)
        # Para la columna PERIODO (YYYY-MM), filtramos el año.
        # Asumimos que si se usa fecha_inicio/fin en una vista con 'periodo', 
        # se está usando el rango de fechas para inferir el rango de años/meses.
        # Por simplicidad y para evitar el error 'Unknown column', si es 'periodo',
        # solo filtraremos por año usando el inicio. (Esto puede requerir ajustes en tu front-end)
        else:
             where_clauses.append(f"SUBSTR({date_column}, 1, 4) >= SUBSTR(%s, 1, 4)")
             params.append(fecha_inicio)


    # Aplicar Filtro de FECHA FIN
    if fecha_fin and date_column:
        if date_column != 'periodo':
            where_clauses.append(f"{date_column} <= %s")
            params.append(fecha_fin)
        else:
            where_clauses.append(f"SUBSTR({date_column}, 1, 4) <= SUBSTR(%s, 1, 4)")
            params.append(fecha_fin)


    # 4. Ensamblar la consulta final
    if where_clauses:
        # Si hay filtros, envolvemos la consulta base en un subquery para aplicar la cláusula WHERE
        full_query = f"SELECT T1.* FROM ({base_query}) AS T1 WHERE {' AND '.join(where_clauses)}"
    else:
        full_query = base_query
        
    # 5. Ejecutar la consulta
    try:
        cur = mysql.connection.cursor()
        cur.execute(full_query, params)
        data = cur.fetchall()
        cur.close()

        return jsonify(data) 
        
    except Exception as e:
        # Imprime el error para depuración en el servidor y devuelve un 500 al cliente
        print(f"Database Query Error (API - {query_name}): {e}. Executing: {full_query} with params: {params}")
        # Retorna el detalle del error para que sepas exactamente qué columna falló
        return jsonify({"error": "Database query failed", "details": str(e), "query": full_query}), 500


# --- EJECUTAR APLICACIÓN ---
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)