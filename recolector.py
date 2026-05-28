from subprocess import getoutput
import pymysql
import time
from datetime import datetime

# ==========================================
# CONEXION MYSQL
# ==========================================

DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "root_password"
DB_NAME = "monitoreo"
DB_PORT = 3306

# CONEXION MYSQL

conexion = pymysql.connect(
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME,
    port=DB_PORT
)

cursor = conexion.cursor()

# ==========================================
# LIMPIAR TABLA AL INICIAR
# ==========================================

cursor.execute("DELETE FROM registro_metricas")
conexion.commit()

cursor.execute("ALTER TABLE registro_metricas AUTO_INCREMENT = 1")
conexion.commit()


# ==========================================
# FUNCION SNMP
# ==========================================

def obtener_oid(oid):

    comando = f"snmpget -v2c -c public localhost {oid}"

    salida = getoutput(comando)

    try:
        valor = salida.split(":")[-1].strip()
        return int(valor)

    except:
        return 0

# ==========================================
# RECOLECTOR
# ==========================================
while True:

    try:

        # RAM DISPONIBLE
        ram_libre = obtener_oid("1.3.6.1.4.1.2021.4.6.0")

        # RAM TOTAL
        ram_total = obtener_oid("1.3.6.1.4.1.2021.4.5.0")

        # CPU IDLE
        cpu_idle = obtener_oid("1.3.6.1.4.1.2021.11.11.0")

        # TRAFICO RED
        red = obtener_oid("1.3.6.1.2.1.2.2.1.10.2")

        # ==========================================
        # CALCULOS
        # ==========================================

        if ram_total > 0:
            uso_ram = round(((ram_total - ram_libre) / ram_total) * 100, 2)
        else:
            uso_ram = 0

        uso_cpu = 100 - cpu_idle

        ancho_banda = round(red / 1000000, 2)

        print("RAM:", uso_ram)
        print("CPU:", uso_cpu)
        print("RED:", ancho_banda)

        # ==========================================
        # GUARDAR MYSQL
        # ==========================================

        conexion = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT
        )

        cursor = conexion.cursor()

        sql = """
        INSERT INTO registro_metricas
        (
            servicio_origen,
            consumo_ram,
            consumo_disco,
            ancho_banda,
            fecha_registro
        )
        VALUES (%s,%s,%s,%s,%s)
        """

        valores = (
            "SNMP-LINUX",
            uso_ram,
            uso_cpu,
            ancho_banda,
            datetime.now()
        )

        cursor.execute(sql, valores)

        conexion.commit()

        conexion.close()

        print("Datos guardados correctamente")
        print("--------------------------------")

    except Exception as e:
        print("Error:", e)

    time.sleep(10)
