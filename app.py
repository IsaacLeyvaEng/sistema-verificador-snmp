from flask import Flask, render_template, request, redirect, url_for
import pymysql

app = Flask(__name__)

# ==========================================
# CONFIGURACIÓN BASE DE DATOS
# ==========================================

DB_HOST = "localhost"
DB_USER = "admin"
DB_PASSWORD = "admin"
DB_NAME = "monitoreo"
DB_PORT = 3306

# ==========================================
# VALIDAR LOGIN
# ==========================================

def validar_usuario(usuario, password):

    conexion = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT
    )

    cursor = conexion.cursor()

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

    conexion = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT
    )

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
        SELECT AVG(consumo_ram)
        FROM registro_metricas
    """)
    promedio_ram = cursor.fetchone()[0] or 0

    # Promedio Disco
    cursor.execute("""
        SELECT AVG(consumo_cpu)
        FROM registro_metricas
    """)
    promedio_disco = cursor.fetchone()[0] or 0

    # Promedio Red
    cursor.execute("""
        SELECT AVG(ancho_banda)
        FROM registro_metricas
    """)
    promedio_red = cursor.fetchone()[0] or 0

    # Máximo RAM
    cursor.execute("""
        SELECT MAX(consumo_ram)
        FROM registro_metricas
    """)
    max_ram = cursor.fetchone()[0] or 0

    # Máximo Disco
    cursor.execute("""
        SELECT MAX(consumo_cpu)
        FROM registro_metricas
    """)
    max_disco = cursor.fetchone()[0] or 0

    # Máximo Red
    cursor.execute("""
        SELECT MAX(ancho_banda)
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
        max_red=round(float(max_red), 2)
    )

# ==========================================
# INICIO
# ==========================================

if __name__ == "__main__":
    app.run(
        debug=True,
        host="0.0.0.0"
    )
