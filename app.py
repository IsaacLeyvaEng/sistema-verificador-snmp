from flask import Flask, render_template, request, redirect, url_for
import pymysql

app = Flask(__name__)

# ==========================================
# CONFIGURACIÓN BASE DE DATOS
# ==========================================

DB_HOST_MASTER = "localhost"
DB_HOST_SLAVE = "localhost"
DB_USER = "admin"
DB_PASSWORD = "admin"
DB_NAME = "monitoreo"
DB_PORT_MASTER = 3306
DB_PORT_SLAVE = 3307

# ==========================================
# GESTIÓN DE CONEXIÓN CON FAILOVER
# ==========================================

def obtener_conexion():
    """Intenta conectar al Maestro, si falla, conecta al Esclavo y asegura que la tabla exista."""
    try:
        # Intento con Maestro
        conn = pymysql.connect(
            host=DB_HOST_MASTER,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT_MASTER,
            connect_timeout=3
        )
        # Asegurar tabla (opcional pero recomendado)
        verificar_y_crear_tabla(conn)
        return conn, "MAESTRO (Local)"
    except Exception as e:
        print(f"MAESTRO CAÍDO: {e}. Reintentando con ESCLAVO...")
        try:
            # Intento con Esclavo
            conn = pymysql.connect(
                host=DB_HOST_SLAVE,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                port=DB_PORT_SLAVE,
                connect_timeout=3
            )
            verificar_y_crear_tabla(conn)
            return conn, "ESCLAVO (Docker Failover)"
        except Exception as e2:
            print(f"ERROR CRÍTICO: Ambas bases de datos están caídas. {e2}")
            return None, None

def verificar_y_crear_tabla(conexion):
    """Crea la tabla si no existe para evitar errores de lectura."""
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS registro_metricas (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    servicio_origen VARCHAR(100),
                    consumo_ram VARCHAR(100),
                    consumo_cpu VARCHAR(100),
                    ancho_banda VARCHAR(100),
                    fecha_registro VARCHAR(100),
                    base_datos VARCHAR(50)
                )
            """)
            # También necesitamos la tabla usuarios para el login
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    usuario VARCHAR(255),
                    password VARCHAR(255)
                )
            """)
            # Insertar usuario admin por defecto si no hay ninguno
            cursor.execute("SELECT COUNT(*) FROM usuarios")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO usuarios (usuario, password) VALUES (%s, %s)", ("admin", "admin"))
            conexion.commit()
    except Exception as e:
        print(f"Error al verificar tablas: {e}")

# ==========================================
# VALIDAR LOGIN
# ==========================================

def validar_usuario(usuario, password):

    conexion, host_activo = obtener_conexion()
    if not conexion:
        return False

    cursor = conexion.cursor()
    # ... resto del código

    cursor.execute(
        "SELECT * FROM usuarios WHERE usuario=%s AND password=%s",
        (usuario, password)
    )

    resultado = cursor.fetchone()

    cursor.close()
    conexion.close()

    return resultado is not None

# ==========================================
# LOGIN
# ==========================================

@app.route("/", methods=["GET", "POST"])
def login():

    mensaje = ""

    if request.method == "POST":

        usuario = request.form["usuario"]
        password = request.form["password"]

        if validar_usuario(usuario, password):
            return redirect(url_for("dashboard"))

        mensaje = "Usuario o contraseña incorrectos"

    return render_template("login.html", mensaje=mensaje)

# ==========================================
# DASHBOARD
# ==========================================

@app.route("/dashboard")
def dashboard():
    # 1. Intentar conectar a ambas
    conn_m, status_m = conectar_especifica(DB_HOST_MASTER, DB_PORT_MASTER, "MAESTRO")
    conn_s, status_s = conectar_especifica(DB_HOST_SLAVE, DB_PORT_SLAVE, "ESCLAVO")

    all_metricas = []
    
    # 2. Extraer datos de las que estén disponibles
    if conn_m:
        with conn_m.cursor() as cur:
            cur.execute("SELECT servicio_origen, consumo_ram, consumo_cpu, ancho_banda, fecha_registro, base_datos FROM registro_metricas")
            all_metricas.extend(cur.fetchall())
        conn_m.close()
    
    if conn_s:
        with conn_s.cursor() as cur:
            cur.execute("SELECT servicio_origen, consumo_ram, consumo_cpu, ancho_banda, fecha_registro, base_datos FROM registro_metricas")
            all_metricas.extend(cur.fetchall())
        conn_s.close()

    # 3. Eliminar duplicados y ordenar
    # Usamos un diccionario con la fecha como clave para quedarnos solo con una versión de cada registro
    metricas_unicas = {}
    for m in all_metricas:
        fecha = m[4]
        # Si ya existe, preferimos la que diga "MAESTRO" para que se vea más limpio, 
        # a menos que sea un registro de FAILOVER
        if fecha not in metricas_unicas or m[5] == "ESCLAVO (FAILOVER)":
            metricas_unicas[fecha] = m

    # Convertir a lista y ordenar por fecha descendente
    metricas_finales = sorted(metricas_unicas.values(), key=lambda x: x[4], reverse=True)[:30]

    # 4. Calcular promedios sobre la lista unificada
    if metricas_finales:
        promedio_ram = sum(float(m[1]) for m in metricas_finales) / len(metricas_finales)
        promedio_cpu = sum(float(m[2]) for m in metricas_finales) / len(metricas_finales)
        promedio_red = sum(float(m[3]) for m in metricas_finales) / len(metricas_finales)
        max_ram = max(float(m[1]) for m in metricas_finales)
        max_cpu = max(float(m[2]) for m in metricas_finales)
        max_red = max(float(m[3]) for m in metricas_finales)
    else:
        promedio_ram = promedio_cpu = promedio_red = max_ram = max_cpu = max_red = 0

    # Determinar host activo para el banner
    host_para_banner = "MAESTRO (Local)" if status_m else "ESCLAVO (Docker Failover)"

    return render_template(
        "dashboard.html",
        metricas=metricas_finales,
        promedio_ram=round(promedio_ram, 2),
        promedio_disco=round(promedio_cpu, 2),
        promedio_red=round(promedio_red, 2),
        max_ram=round(max_ram, 2),
        max_disco=round(max_cpu, 2),
        max_red=round(max_red, 2),
        db_status=host_para_banner
    )

def conectar_especifica(host, port, nombre):
    try:
        conn = pymysql.connect(host=host, port=port, user=DB_USER, password=DB_PASSWORD, database=DB_NAME, connect_timeout=2)
        verificar_y_crear_tabla(conn)
        return conn, nombre
    except:
        return None, None

# ==========================================
# INICIO
# ==========================================

if __name__ == "__main__":
    app.run(
        debug=True,
        host="0.0.0.0"
    )
