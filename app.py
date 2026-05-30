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
                    fecha_registro VARCHAR(100)
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

    conexion, host_activo = obtener_conexion()
    if not conexion:
        return "Error: No se pudo conectar a ninguna base de datos.", 500

    cursor = conexion.cursor()

    # Últimos registros
    cursor.execute("""
        SELECT
            servicio_origen,
            consumo_ram,
            consumo_cpu,
            ancho_banda,
            fecha_registro
        FROM registro_metricas
        ORDER BY fecha_registro DESC
        LIMIT 20
    """)

    metricas = cursor.fetchall()

    # Promedio RAM
    cursor.execute("""
        SELECT AVG(CAST(consumo_ram AS DECIMAL(10,2)))
        FROM registro_metricas
    """)
    promedio_ram = cursor.fetchone()[0] or 0

    # Promedio CPU
    cursor.execute("""
        SELECT AVG(CAST(consumo_cpu AS DECIMAL(10,2)))
        FROM registro_metricas
    """)
    promedio_disco = cursor.fetchone()[0] or 0

    # Promedio Red
    cursor.execute("""
        SELECT AVG(CAST(ancho_banda AS DECIMAL(10,2)))
        FROM registro_metricas
    """)
    promedio_red = cursor.fetchone()[0] or 0

    # Máximo RAM
    cursor.execute("""
        SELECT MAX(CAST(consumo_ram AS DECIMAL(10,2)))
        FROM registro_metricas
    """)
    max_ram = cursor.fetchone()[0] or 0

    # Máximo CPU
    cursor.execute("""
        SELECT MAX(CAST(consumo_cpu AS DECIMAL(10,2)))
        FROM registro_metricas
    """)
    max_disco = cursor.fetchone()[0] or 0

    # Máximo Red
    cursor.execute("""
        SELECT MAX(CAST(ancho_banda AS DECIMAL(10,2)))
        FROM registro_metricas
    """)
    max_red = cursor.fetchone()[0] or 0

    conexion.close()

    return render_template(
        "dashboard.html",
        metricas=metricas,
        promedio_ram=round(float(promedio_ram), 2),
        promedio_disco=round(float(promedio_disco), 2),
        promedio_red=round(float(promedio_red), 2),
        max_ram=round(float(max_ram), 2),
        max_disco=round(float(max_disco), 2),
        max_red=round(float(max_red), 2),
        db_status=host_activo
    )

# ==========================================
# INICIO
# ==========================================

if __name__ == "__main__":
    app.run(
        debug=True,
        host="0.0.0.0"
    )
