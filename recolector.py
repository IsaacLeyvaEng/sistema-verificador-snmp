from subprocess import getoutput
import pymysql
import time
from datetime import datetime
import re

# ==========================================
# CONEXION MYSQL
# ==========================================

DB_HOST = "localhost"
DB_USER = "admin"
DB_PASSWORD = "admin"
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

    comando = f"snmpget -v2c -c public 192.168.0.101 {oid}"
    #comando = f"snmpget -v2c -c public localhost {oid}"

    salida = getoutput(comando)
    try:
        valor = salida.split(":")[-1].strip()
        numero = re.search(r"-?\d+", valor)
        return int(numero.group()) if numero else 0

    except:
        return 0

# OBTENER NOMBRE DE SISTEMA
def obtener_oid_texto(oid, valor_por_defecto="SNMP-LINUX"):

    comando = f"snmpget -v2c -c public 192.168.0.101 {oid}"
    salida = getoutput(comando)

    try:
        if "=" in salida:
            parte_derecha = salida.split("=", 1)[1].strip()
        else:
            parte_derecha = salida.strip()

        if ":" in parte_derecha:
            texto = parte_derecha.split(":", 1)[1].strip()
        else:
            texto = parte_derecha

        texto = texto.strip().strip('"')
        return texto if texto else valor_por_defecto
    except:
        return valor_por_defecto

# ==========================================
# RECOLECTOR
# ==========================================
servicio_origen = obtener_oid_texto("1.3.6.1.2.1.1.5.0")

while True:

    try:

        # RAM DISPONIBLE
        ram_libre = obtener_oid("1.3.6.1.4.1.2021.4.6.0")

        # RAM TOTAL
        ram_total = obtener_oid("1.3.6.1.4.1.2021.4.5.0")

        # CPU IDLE
        cpu_idle = obtener_oid("1.3.6.1.4.1.2021.11.11.0")

        # TRAFICO RED
        #red = obtener_oid("1.3.6.1.2.1.2.2.1.10.2")
        red = obtener_oid("1.3.6.1.2.1.2.2.1.10.3")
        # ==========================================
        # CALCULOS
        # ==========================================

        if ram_total > 0:
            uso_ram = round(((ram_total - ram_libre) / ram_total) * 100, 2)
        else:
            uso_ram = 0

        uso_cpu = 100 - cpu_idle

        ancho_banda = round(red / 1000000, 2)

        #print("RAM:", uso_ram)
        #print("CPU:", uso_cpu)
        #print("RED:", ancho_banda)

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
            consumo_cpu,
            ancho_banda,
            fecha_registro
        )
        VALUES (%s,%s,%s,%s,%s)
        """

        valores = (
            servicio_origen,
            uso_ram,
            uso_cpu,
            ancho_banda,
            datetime.now()
        )

        cursor.execute(sql, valores)

        conexion.commit()

        conexion.close()

        print(f"Datos guardados correctamente - {datetime.now().strftime('%H:%M:%S')}")
        print("--------------------------------")

    except Exception as e:
        print("Error:", e)

    time.sleep(10)
    #time.sleep(10)
