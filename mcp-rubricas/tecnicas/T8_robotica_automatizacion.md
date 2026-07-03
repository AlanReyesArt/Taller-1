# T8 - Rúbrica Técnica

Línea de Investigación: Robótica, automatización avanzada y sistemas inteligentes

Sublínea: Robótica y Automatización Avanzada

Puntaje Máximo: 7

Cantidad de Criterios: 60

---

# MATRIZ DE EVALUACIÓN

## Fundamento Técnico

ID-01
Descripción: Sustenta analíticamente la selección de la topología del robot, cinemática (ej. ruda, articulada, paralela) o bucles de control industrial basados en la dinámica del entorno y restricciones físicas del problema.
Puntaje: 0.1167

ID-02
Descripción: Fundamenta formalmente los modelos matemáticos de cinemática directa/inversa (ej. matrices de Denavit-Hartenberg), ecuaciones de la dinámica o leyes de control clásico/avanzado (ej. PID, MPC) aplicados.
Puntaje: 0.1167

ID-03
Descripción: Formaliza conceptualmente los esquemas de adquisición de variables físicas, acondicionamiento de señales analógicas o modelado de perturbaciones estocásticas mediante especificaciones en el documento.
Puntaje: 0.1167

ID-04
Descripción: Justifica el costo computacional, tiempos de muestreo y la complejidad algorítmica (notación Big O) de las subrutinas de control en tiempo real o procesamiento de trayectorias.
Puntaje: 0.1167

ID-05
Descripción: Analiza comparativamente el rendimiento analítico y los baselines operativos del diseño propuesto frente a configuraciones estándar o sistemas mecatrónicos del estado del arte.
Puntaje: 0.1167

## Arquitectura de Solución

ID-06
Descripción: Presenta un diagrama formal de la arquitectura de automatización y bloques de control, detallando explícitamente microcontroladores, controladores lógicos (PLCs), sensores, actuadores y flujos lógicos.
Puntaje: 0.1167

ID-07
Descripción: Detalla el pipeline de procesamiento de señales y flujo de variables de extremo a extremo, especificando la conversión analógica-digital, filtrado digital y transmisión de comandos.
Puntaje: 0.1167

ID-08
Descripción: Especifica las interfaces técnicas de integración, protocolos de comunicación industrial (ej. Modbus, CAN Bus, Profinet) y los tiempos de ciclo de bus del sistema embebido.
Puntaje: 0.1167

ID-09
Descripción: Describe formalmente la topología del hardware, esquemas de distribución de potencia eléctrica, aislamiento galvánico y conexionado físico de los elementos de control.
Puntaje: 0.1167

ID-10
Descripción: Detalla el diseño de la arquitectura del entorno de pruebas o HMI (Human-Machine Interface) encargado de la supervisión, adquisición de datos (SCADA) y control de estados de la planta.
Puntaje: 0.1167

## Tecnologías Utilizadas

ID-11
Descripción: Justifica técnicamente la selección del entorno mecatrónico, microcontroladores, procesadores embebidos y versiones específicas del runtime o firmware (ej. ESP32 con FreeRTOS, Arduino Core, ROS2 Humble).
Puntaje: 0.1167

ID-12
Descripción: Sustenta la adopción de librerías especializadas y drivers a nivel industrial para el control de movimiento, procesamiento de variables o abstracción de hardware (ej. AccelStepper, HAL, Micro-ROS).
Puntaje: 0.1167

ID-13
Descripción: Detalla las configuraciones electrónicas o de bajo nivel para la aceleración y precisión de tareas críticas (ej. interrupciones por hardware, temporizadores dedicados, registros de temporización PWM).
Puntaje: 0.1167

ID-14
Descripción: Justifica la selección de los sensores (ej. ultrasónicos, encoders de cuadratura, IMUs) y drivers de potencia/actuadores (ej. servomotores, puentes H, relés) optimizados para el torque y rango dinámico.
Puntaje: 0.1167

ID-15
Descripción: Especifica las herramientas informáticas empleadas para el diseño electrónico (PCB layouts), simulación física (ej. MATLAB/Simulink, Gazebo) o rastreo automatizado de telemetría física.
Puntaje: 0.1167

## Diseño e Implementación

ID-16
Descripción: Incluye diagramas técnicos explícitos referidos a esquemáticos electrónicos detallados, layouts de circuitos impresos (PCB) o planos de ensamblaje mecánico 3D del robot/planta.
Puntaje: 0.1167

ID-17
Descripción: Presenta el diseño lógico detallado de los bloques de filtrado digital (ej. filtros pasa-bajas, promedios móviles), sintonización de variables o algoritmos de odometría/posicionamiento.
Puntaje: 0.1167

ID-18
Descripción: Detalla la configuración de las técnicas y parámetros de sintonización de los lazos de control cerrados (ej. constantes Kp, Ki, Kd calibradas empírica o analíticamente).
Puntaje: 0.1167

ID-19
Descripción: Muestra fragmentos de código fuente críticos referidos a máquinas de estado finito (FSM), rutinas de servicio de interrupción (ISR), lazos de control embebidos o lectura directa de registros de sensores.
Puntaje: 0.1167

ID-20
Descripción: Detalla la implementación técnica de mecanismos para mitigar problemas físicos u operativos como el rebote de señales (debouncing), saturación del integrador (anti-windup) o desbalance de cargas eléctricas.
Puntaje: 0.1167

## Calidad Técnica

ID-21
Descripción: Demuestra la consistencia técnica e inmutabilidad en la gestión de tiempos del sistema distribuido o multitarea, previniendo condiciones de carrera en variables globales de control.
Puntaje: 0.1167

ID-22
Descripción: Reporta métricas de estabilidad electrónica y linealidad en el rango operativo de las señales analógicas (ej. atenuación de ruido de alta frecuencia, estabilidad de voltaje).
Puntaje: 0.1167

ID-23
Descripción: Aplica técnicas formales de protección y redundancia física (ej. diodos de marcha libre, optoacopladores, watchdog timers habilitados) para asegurar la integridad del hardware embebido.
Puntaje: 0.1167

ID-24
Descripción: Documenta de manera detallada las tramas de datos, contratos de payload seriales o inalámbricos y firmas de funciones de las librerías/APIs expuestas para el control remoto.
Puntaje: 0.1167

ID-25
Descripción: Detalla el control de versiones, trazabilidad histórica e inmutabilidad de los esquemáticos electrónicos, modelos CAD de simulación y bases de firmware del microcontrolador.
Puntaje: 0.1167

## Validación Técnica

ID-26
Descripción: Detalla la estrategia de validación experimental definiendo métricas matemáticas de error y rendimiento industrial (ej. error en estado estacionario, sobreimpulso máximo, tiempo de establecimiento, OEE).
Puntaje: 0.1167

ID-27
Descripción: Presenta gráficos analíticos formales (curvas de respuesta temporal, diagramas de Bode, histogramas de error posicional) que validen el rendimiento operativo de los entregables mecatrónicos.
Puntaje: 0.1167

ID-28
Descripción: Reporta los resultados numéricos consolidados de precisión analítica o repetibilidad física calculados sobre entornos de prueba dinámicos e independientes del ambiente aislado inicial.
Puntaje: 0.1167

ID-29
Descripción: Realiza pruebas de robustez técnica introduciendo perturbaciones externas forzadas, variaciones en la inercia de la carga o señales con ruido para documentar el nivel de tolerancia a fallos del control.
Puntaje: 0.1167

ID-30
Descripción: Evalúa y audita de forma automatizada o documental la presencia de condiciones inseguras (ej. paros de emergencia por hardware, límites lógicos de carrera) frente a restricciones operacionales lógicas de seguridad industrial.
Puntaje: 0.1167

## Resultados Técnicos

ID-31
Descripción: Reporta perfiles cuantitativos de rendimiento mediante curvas dinámicas de convergencia del error y respuesta transitoria del sistema a lo largo del tiempo o ciclos mecánicos de ejecución.
Puntaje: 0.1167

ID-32
Descripción: Detalla los tiempos netos de latencia de ejecución del lazo de control embebido medidos por ciclo de reloj u operación crítica (ej. frecuencia de refresco en Hz del bucle PID).
Puntaje: 0.1167

ID-33
Descripción: Muestra métricas cuantitativas del consumo exacto de recursos físicos o eléctricos (ej. corriente pico en amperios, potencia disipada, porcentaje de memoria flash o RAM embebida utilizada) bajo carga máxima.
Puntaje: 0.1167

ID-34
Descripción: Tabula de forma comparativa los indicadores de rendimiento mecánico/eléctrico logrados por la solución optimizada frente a sistemas de lazo abierto o configuraciones base tradicionales.
Puntaje: 0.1167

ID-35
Descripción: Demuestra la estabilidad técnica y la continuidad funcional del firmware mediante registros de ejecución continua y logs de depuración (debug logs) estructurados libres de desbordamientos o resets inesperados.
Puntaje: 0.1167

## Innovación

ID-36
Descripción: Propone una optimización, extensión cinemática o reconfiguración mecatrónica personalizada original sobre mecanismos articulados, actuadores o bucles de control clásico preexistentes.
Puntaje: 0.1167

ID-37
Descripción: Desarrolla o integra una lógica de control avanzada personalizada, método algorítmico de fusión de sensores (ej. Filtro de Kalman adaptativo) o heurística de diseño propietaria para el proyecto.
Puntaje: 0.1167

ID-38
Descripción: Implementa técnicas contemporáneas de automatización distribuida de manera justificada (ej. arquitecturas basadas en ROS2, gemelos digitales físicos sincronizados o nodos Edge de instrumentación inteligente).
Puntaje: 0.1167

ID-39
Descripción: Integra técnicas avanzadas de diagnóstico de fallos embebido (Fault Detection and Isolation - FDI) para auditar de forma transparente el estado funcional y salud de los componentes mecánicos/eléctricos.
Puntaje: 0.1167

ID-40
Descripción: Aporta un diseño de hardware de código abierto sustentado, un repositorio empaquetado de drivers propietarios o un framework de firmware reusable de utilidad directa para la sublínea.
Puntaje: 0.1167

## Escalabilidad

ID-41
Descripción: Define las configuraciones lógicas, topologías maestras/esclavas o políticas aplicadas para el procesamiento y control distribuido multi-nodo o multitarea con arquitecturas escalables.
Puntaje: 0.1167

ID-42
Descripción: Detalla estrategias avanzadas de particionamiento, secuenciación o almacenamiento de perfiles de movimiento a gran escala para evitar cuellos de botella en los buses de comunicación industrial.
Puntaje: 0.1167

ID-43
Descripción: Implementa técnicas de compresión del firmware o modularización física de bloques mecánicos para optimizar su ligereza computacional y velocidad de ensamblaje en producción.
Puntaje: 0.1167

ID-44
Descripción: Diseña cargadores de datos masivos o buffers de transmisión serial altamente eficientes capaces de realizar streaming continuo de telemetría de sensores sin ralentizar las interrupciones críticas de control.
Puntaje: 0.1167

ID-45
Sustenta el diseño de la arquitectura de automatización modular elástica o buses de campo distribuidos que permite clonar, añadir actuadores o expandir estaciones de trabajo de la planta bajo demanda operacional.
Puntaje: 0.1167

## Seguridad

ID-46
Descripción: Detalla la arquitectura de seguridad física y electrónica, circuitos dedicados de interrupción forzada, aislamientos por optoacopladores y encriptación o autenticación básica en enlaces inalámbricos de control.
Puntaje: 0.1167

ID-47
Descripción: Describe e implementa políticas técnicas estrictas para asegurar la protección, mitigación de picos de voltaje o aislamiento de tramas de control críticas frente a interfaces expuestas al usuario.
Puntaje: 0.1167

ID-48
Descripción: Diseña e implementa contramedidas electrónicas o de firmware robustas contra fallos físicos o perturbaciones inducidas (ej. filtros EMI para ruido electromagnético, rutinas de escape ante pérdidas de señal de red).
Puntaje: 0.1167

ID-49
Descripción: Especifica el uso de herramientas automáticas de simulación o instrumentación física de banco para escanear fallos en las pistas del circuito, caídas de voltaje en las líneas de potencia y protección galvánica.
Puntaje: 0.1167

ID-50
Descripción: Detalla pistas de auditoría inmutables (Audit Trails) o registros persistidos en memoria EEPROM/SD local que almacenen logs estructurados de paros de emergencia, alarmas térmicas y fallos del sistema.
Puntaje: 0.1167

## Mantenibilidad

ID-51
Descripción: Estructura una base de código embebido limpia y modularizada que separe estrictamente las rutinas de bajo nivel (HAL/Drivers), la lógica de control algorítmico y las subrutinas de comunicación serial.
Puntaje: 0.1167

ID-52
Descripción: Implementa canalizaciones organizadas de testing, compilación y subida automatizada de firmware (ej. PlatformIO pipelines o scripts embebidos) para realizar validaciones sintácticas automáticas.
Puntaje: 0.1167

ID-53
Descripción: Diseña una estrategia unificada para el manejo de excepciones de hardware (ej. desbordamiento de búfer serial, fallos de lectura I2C/SPI) y generación de logs estructurados legibles por puerto serial.
Puntaje: 0.1167

ID-54
Descripción: Documenta minuciosamente los esquemáticos electrónicos completos con listas de materiales (BOM), diagramas de flujo de la FSM, asignación exacta de pines de E/S (Pinout maps) y planos estructurales mecánicos.
Puntaje: 0.1167

ID-55
Descripción: Define estrategias de versionamiento formal aplicadas de manera estricta tanto a los archivos fuentes de configuración del firmware como a las revisiones de diseño de hardware físico (PCBs).
Puntaje: 0.1167

ID-56
Descripción: Describe e implementa sistemas automatizados de monitoreo y alerta física (ej. LEDs de estado, alarmas en HMI, telemetría serial) para detectar caídas críticas de voltaje o descalibración de sensores.
Puntaje: 0.1167

ID-57
Descripción: Demuestra la cobertura de pruebas funcionales automatizadas o en caliente implementadas directamente sobre las subrutinas de cálculo del controlador, lectura analógica o parsing de tramas.
Puntaje: 0.1167

ID-58
Descripción: Aplica patrones de abstracción de hardware o inversión de dependencias para desacoplar el core lógico y matemático del firmware de las APIs de hardware específicas de un fabricante o microcontrolador.
Puntaje: 0.1167

ID-59
Descripción: Organiza la estructura del repositorio de código fuente, archivos de configuración de compilación y layouts técnicos siguiendo las convenciones de diseño formal de la comunidad de sistemas embebidos.
Puntaje: 0.1167

ID-60
Descripción: Detalla planes técnicos de contingencia, políticas de respaldo físico de microcontroladores de repuesto, redundancia de energía, calibración rápida en frío y mecanismos de rollback seguro de firmware.
Puntaje: 0.1167

---

# FÓRMULA DE CÁLCULO

Nota = Σ(Ci × Wi)

Peso por criterio:
0.1167

Puntaje máximo de la matriz: 7

---

# UMBRALES DE EVALUACIÓN

Aprobado:
5.25 - 7.00

Observado:
3.50 - 5.24

Rechazado:
0.00 - 3.49

---

# INSTRUCCIONES PARA EL AGENTE TÉCNICO

1. Analizar la tesis completa con un enfoque centrado estrictamente en el diseño de hardware electrónico, la teoría de control y la programación embebida de bajo nivel, priorizando esquemáticos de circuitos impresos (PCBs), planos de diseño mecánico CAD, arquitecturas de firmware (ej. diagramas de estados, tareas de RTOS), fragmentos de código de control y reportes empíricos de telemetría física.
2. Evaluar de forma binaria y estricta cada uno de los 60 criterios de la sublínea de Robótica y Automatización Avanzada asignando exclusivamente 1 para Cumple o 0 para No cumple. Queda totalmente prohibido el uso de puntuaciones cualitativas o fracciones numéricas parciales.
3. Ejecutar validaciones de concordancia técnica cruzada obligatorias: si la tesis declara el uso de sistemas embebidos automáticos, robots móviles o lazos cerrados PID/avanzados, pero omite los fragmentos de código fuente críticos (ej. inicialización de timers, control PWM, cálculo del error), diagramas de conexionado o planos mecatrónicos estructurados en sus capítulos técnicos o anexos, el agente asignará de manera automática 0 en los bloques de Arquitectura de Solución (ID-06 a ID-10) y Diseño e Implementación (ID-16 a ID-20).
4. Verificar el soporte empírico y factual de las métricas de control y variables físicas reportadas. Si el documento afirma precisiones mm, tiempos de respuesta ultra-bajos del lazo o mitigación completa de ruido y perturbaciones, se exigirá la inclusión explícita de capturas legibles de pantallas de osciloscopios, analizadores lógicos, interfaces HMI/SCADA industriales, logs de terminales seriales o gráficas analíticas legibles de señales reales. Su ausencia invalidará por completo los criterios correspondientes de Validación Técnica y Resultados Técnicos.
5. Calcular el puntaje global multiplicando los criterios correctos por el peso fijo por criterio (0.1167).
6. Construir una lista indexada de observaciones técnicas detallando individualmente cada ID calificado con 0 junto al argumento formal mecatrónico que justifique la omisión o insuficiencia de diseño detectada.
7. Generar como salida final exclusiva un objeto JSON estructurado que contenga las propiedades del puntaje consolidado, el umbral de aprobación tecnológico alcanzado y la colección indexada de observaciones por ID para su integración directa y transparente en los flujos de la suite multiagente institucional.