# Informe Técnico: Implementación de Redundancia y Alta Disponibilidad (HA)
## Proyecto: Sistema de Monitoreo SNMP Verificador

Este informe detalla la reingeniería aplicada al sistema de recolección de métricas para transformar una arquitectura de punto único de fallo en un sistema robusto de alta disponibilidad con redundancia de datos.

---

### 1. Diagnóstico Inicial y Objetivos
El sistema original dependía exclusivamente de una instancia local de MariaDB. Si este servicio fallaba, se perdía la capacidad de recolección y la visibilidad del monitoreo. 
**Objetivos:**
*   Eliminar el punto único de fallo mediante un nodo de respaldo en Docker.
*   Garantizar la integridad del historial de métricas (cero pérdida de datos).
*   Proporcionar una interfaz de usuario que informe el estado de salud de la infraestructura de datos.

---

### 2. Infraestructura de Datos Híbrida
Se implementó una arquitectura mixta para optimizar recursos:
*   **Servidor Primario (Maestro):** MariaDB instalado directamente en el Host (puerto 3306). Es la fuente de datos preferida por su baja latencia.
*   **Servidor de Respaldo (Esclavo):** Contenedor Docker `db_esclavo` (MariaDB 10.5) configurado en el puerto 3307. Este nodo actúa como un "Hot Standby", listo para asumir la carga en cualquier milisegundo.

---

### 3. Ingeniería de Sincronización: Doble Escritura (Dual Write)
A diferencia de una replicación tradicional de base de datos que puede ser compleja de mantener, se optó por una **estrategia de Doble Escritura a nivel de aplicación**:
*   **Lógica del Recolector:** El script `recolector.py` fue reprogramado para que en cada ciclo de ejecución (10s) abra conexiones independientes a ambos nodos.
*   **Independencia de Fallos:** Si el Maestro falla, el recolector no se detiene; simplemente registra el error en consola y asegura el guardado en el Esclavo. Esto garantiza que el historial esté completo en al menos uno de los nodos en todo momento.
*   **Persistencia de Origen:** Cada registro incluye una columna `base_datos` que identifica el estado del sistema en el momento de la captura (`MAESTRO` o `ESCLAVO (FAILOVER)`).

---

### 4. Inteligencia de Failover en la Capa de Aplicación
Se implementó una "capa de abstracción" en la conexión que permite una transición transparente:
*   **Detección de Salud:** La aplicación Flask realiza un "heartbeat" (chequeo de latencia) a la base de datos local.
*   **Conmutación Automática:** Si el latido falla, el sistema conmuta internamente todas las consultas hacia el puerto 3307.
*   **Recuperación Automática (Failback):** En cuanto el servicio local vuelve a estar en línea, el sistema lo detecta y prioriza nuevamente el nodo Maestro, manteniendo la eficiencia operativa.

---

### 5. Vista Unificada y Deduplicación de Datos
Para resolver el problema de los "huecos" en el historial cuando el Maestro está apagado, se implementó una **Lógica de Combinación en Memoria**:
*   **Merge de Resultados:** Al cargar el Dashboard, Flask extrae los datos de ambos nodos simultáneamente.
*   **Filtro de Duplicados:** Mediante un algoritmo de diccionario en Python, el sistema identifica registros idénticos por su marca de tiempo (Timestamp) y genera una lista única.
*   **Cálculos Dinámicos:** Los promedios de CPU (antes disco), RAM y Red se calculan en tiempo real sobre la lista unificada, garantizando que los gráficos no muestren caídas artificiales por falta de datos en un nodo específico.

---

### 6. Experiencia de Usuario y Visualización Crítica
Se transformó el Dashboard en un centro de comando operativo:
*   **Alertas Visuales Animadas:** Se creó un banner de estado con animaciones CSS (`keyframes`) que utiliza un parpadeo de advertencia cuando el sistema opera en modo de emergencia.
*   **Trazabilidad por Colores:** La tabla de métricas utiliza etiquetas CSS condicionales. Los registros capturados durante un failover se resaltan en color ámbar, permitiendo al administrador identificar rápidamente periodos de inestabilidad en la red.
*   **Consistencia de Datos:** Se estandarizaron los tipos de datos a `VARCHAR(100)` para mantener la compatibilidad con el esquema original, utilizando conversiones de tipo (`CAST`) en el motor SQL para no perder la capacidad de análisis estadístico.

---

### 7. Guía de Pruebas de Resiliencia
Para validar el sistema:
1.  **Estado OK:** Ambos nodos encendidos. Verificación de registros marcados como `MAESTRO` en ambas bases de datos.
2.  **Modo Emergencia:** Ejecutar `sudo systemctl stop mariadb`. Observar el banner rojo en el Dashboard y el etiquetado `FAILOVER` en el recolector.
3.  **Recuperación:** Ejecutar `sudo systemctl start mariadb`. Observar el retorno automático al color verde y la persistencia de los datos capturados durante la caída.

---
**Implementado por:** Gemini CLI Agent
**Fecha:** 30 de Mayo, 2026
