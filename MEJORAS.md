# Plan de mejora de Finanzas

Recomendaciones ordenadas por impacto y esfuerzo. Las primeras son mejoras
pequeñas sobre lo que ya existe; las últimas son líneas de trabajo mayores.

## 1. Mejoras rápidas (implementadas)

Estas mejoras ya están integradas en la aplicación:

- **Deshacer en lugar de solo confirmar.** Las últimas 20 acciones (borrar o
  editar movimientos, archivar o eliminar categorías, eliminar cuentas) se
  guardan en memoria. Cada aviso incluye un enlace «Deshacer» y también funciona
  con `Ctrl+Z`. El historial se pierde al cerrar la aplicación y se limpia al
  restaurar un respaldo, borrar todos los datos o cargar datos de ejemplo.
- **Aviso de cambios sin guardar en Presupuestos.** Al cambiar de mes o salir de
  la vista con campos modificados se pide confirmación antes de descartarlos.
- **Rango de fechas libre en Movimientos.** Los filtros incluyen «Desde» y
  «Hasta» (dd/mm/aaaa) con validación y aviso de rangos invertidos, además de
  búsqueda, tipo, categoría y cuenta.
- **Ordenar la tabla por columna.** Un clic en cualquier encabezado ordena
  ascendentemente y otro clic invierte el orden; la flecha indica la columna
  activa. El orden se conserva junto con los filtros.
- **Paginación.** La tabla muestra 50 movimientos por página con flechas
  «Anterior / Siguiente» y el rango visible («Mostrando 1–50 de 320»).
- **Recordar la vista y los filtros.** La app vuelve a abrir la última sección y
  restaura búsqueda, tipo, categoría, cuenta, fechas y orden.
- **Confirmación al salir con diálogos abiertos.** Si hay una ventana de edición
  abierta, la ventana principal no se cierra y se enfoca el diálogo. También se
  avisa si hay presupuestos sin guardar.
- **Formato de moneda local.** En Ajustes se elige entre `1,234.56` (inglés) y
  `1.234,56` (español). Se aplica a toda la interfaz y a la exportación CSV.
- **Movimientos recurrentes.** Renta, salario, suscripciones y servicios con
  frecuencia mensual, quincenal, semanal o anual. Al abrir la app se crean las
  ocurrencias pendientes y el índice único `(recurring_id, date)` evita
  duplicados. También hay un botón para procesarlos manualmente.
- **Reglas automáticas.** Coincidencia por texto (sin distinguir mayúsculas) en
  descripción o notas; asignan categoría y/o cuenta al crear movimientos. Se
  aplican también a los existentes y respetan el tipo (ingreso/egreso) de la
  categoría.
- **Multi-moneda.** Cuentas con moneda propia, tipos de cambio por fecha (con la
  tasa más reciente anterior o igual al movimiento) y consolidación de saldos,
  presupuestos y reportes en una moneda base configurable.
- **Moneda de visualización.** El selector **Ver en** de la cabecera y de Ajustes
  permite ver los mismos datos en la moneda base o convertidos a una moneda
  extranjera con tasa registrada. La conversión es solo de presentación: no crea
  cuentas ni altera los montos guardados. Los presupuestos editables se capturan
  en la moneda elegida y se guardan convertidos a la moneda base.
- **Búsqueda avanzada.** Operadores `monto>100`, `categoria:Ocio`,
  `cuenta:Efectivo`, `tipo:ingreso`, `fecha:2026-05` y `texto:"..."` combinables
  con texto libre.
- **Modo oscuro/claro.** Tema conmutable desde Ajustes, persistido en la base de
  datos; la interfaz se reconstruye al instante.

## 2. Funciones que completarían el producto

- **Metas de ahorro y de deuda.** Objetivo con monto y fecha; progreso calculado
  a partir de una cuenta o categoría. Para deudas, tasa de interés y tabla de
  amortización.
- **Presupuestos flexibles.** Hoy el límite es mensual y se repite. Añadir
  presupuestos por quincena, por viaje o con prorrateo para categorías
  estacionales.
- **Importar extractos CSV/OFX.** La mayoría de bancos permiten descargar
  movimientos. Un asistente de importación con vista previa, detección de
  duplicados y mapeo de columnas ahorra horas de captura manual. Las reglas
  automáticas ya pueden aplicarse a los movimientos importados.
- **Etiquetas y gastos compartidos.** Etiquetas transversales a categorías y
  registro de quién pagó o cuánto corresponde a cada persona.
- **Adjuntar comprobantes.** Guardar imágenes o PDF junto al movimiento (ruta o
  blob) y abrirlos desde el detalle.

## 3. Experiencia de usuario y accesibilidad

- **Gráficas interactivas.** Tooltips al pasar el ratón por barras y dona, y
  clic para filtrar el año o la categoría.
- **Escalado DPI.** En pantallas HiDPI, ajustar `tk scaling` y tamaños de fuente
  según la pantalla; probar en 125 %, 150 % y 200 %.
- **Accesibilidad.** Navegación completa con teclado (Tab ordenado), etiquetas
  asociadas a campos y contraste verificado.
- **Estados vacíos más accionables.** En Movimientos ya se muestra un mensaje
  cuando no hay resultados; extenderlo a Reportes (invitar a registrar el primer
  movimiento) y a Presupuestos (sugerir límites según el gasto promedio).
- **Notificaciones y resumen mensual.** Aviso al superar un presupuesto y un
  correo/resumen local el día 1 con el cierre del mes anterior.
- **Iconos e imagen de la aplicación.** Un `.ico`/`.png` y un set de iconos
  coherente para el menú lateral y los botones.

## 4. Calidad técnica y robustez

- **Migraciones de esquema versionadas.** Ya existe una migración tolerante que
  añade columnas y tablas nuevas a bases antiguas (`PRAGMA table_info` +
  `ALTER TABLE`). Falta numerarlas con `PRAGMA user_version` para ordenarlas y
  poder revertirlas.
- **Separar dominio de interfaz.** `db.py` ya concentra el acceso a datos, pero
  las vistas contienen reglas (por ejemplo, cálculos de presupuesto). Extraer una
  capa `services/` (movimientos, presupuestos, reportes) facilita pruebas y
  reutilización.
- **Más pruebas.** `tests/test_core.py` ya cubre filtros combinados, búsqueda
  avanzada, conversión y visualización de moneda, reglas, recurrentes, tema y
  migración. Faltan casos de años bisiestos, respaldos dañados, importación CSV y
  pruebas de humo automatizadas de las vistas con un `Tk` oculto en CI.
- **Linting y tipos.** `ruff` para estilo y `mypy` para tipos; incluir ambos en
  `pyproject.toml` y en un hook de pre-commit.
- **Integración continua.** GitHub Actions ejecutando las pruebas en Linux,
  Windows y macOS con distintas versiones de Python.
- **Empaquetado.** Generar un ejecutable con PyInstaller (`--onefile`,
  `--windowed`) para usuarios sin Python, y publicar un instalador.
- **Registro de errores.** Guardar excepciones en un archivo de log rotativo en
  la carpeta de datos y mostrar un mensaje amable en vez de una traza.
- **Auditoría y copias automáticas.** Registrar cambios (quién/cuándo, si en el
  futuro hay varios usuarios) y crear un respaldo automático diario con rotación
  de los últimos 7.
- **Cifrado y contraseña.** SQLite no cifra por defecto. Para datos sensibles,
  SQLCipher o cifrado del archivo con una contraseña maestra; documentar la
  recuperación.
- **Sincronización opcional.** Si se quiere usar en varios equipos, sincronizar
  la base mediante un servicio en la nube o red local. Requiere resolución de
  conflictos; una alternativa simple es exportar/importar respaldos firmados.
- **Internacionalización.** Extraer textos a `gettext` y permitir inglés/español,
  además del formato regional de fechas y números.

## 5. Rendimiento

- **Índices y consultas.** Ya existen índices por fecha, categoría y cuenta.
  Revisar con `EXPLAIN QUERY PLAN` al crecer los datos; añadir índice compuesto
  `(date, kind)` y evitar subconsultas por cuenta si hay muchas cuentas.
- **Cálculo de saldos en una sola consulta.** `account_balances()` usa cuatro
  subconsultas por cuenta. Para decenas de cuentas es suficiente; con cientos,
  reescribirlo con `LEFT JOIN` + `GROUP BY` o una vista materializada.
- **Carga diferida de vistas.** Ya se crean al abrir cada sección. Mantener ese
  patrón y no precargar reportes pesados.
- **Virtualización de tablas.** Si se muestran miles de filas, considerar
  `ttk.Treeview` con carga por bloques o una tabla virtual propia.

## 6. Orden sugerido de trabajo

| Prioridad | Trabajo | Impacto | Esfuerzo |
| --- | --- | --- | --- |
| 1 | Importación CSV/OFX (las reglas ya existen) | Muy alto | Medio-alto |
| 2 | Metas de ahorro y deuda | Alto | Medio |
| 3 | Migraciones versionadas + CI | Alto (largo plazo) | Medio |
| 4 | Empaquetado e icono | Medio | Bajo |
| 5 | Cifrado y respaldo automático | Alto (seguridad) | Medio |
| 6 | Tooltips y escalado DPI | Medio | Bajo-medio |

## 7. Limitaciones actuales (para tener presentes)

- Un solo usuario y un solo equipo; no hay sincronización.
- Los presupuestos son mensuales y se repiten todos los meses.
- No hay importación bancaria automática (sí exportación CSV y reglas).
- El historial de deshacer vive en memoria (20 acciones) y se pierde al cerrar.
- Los tipos de cambio se introducen manualmente; no se descargan de internet.
- La base de datos no está cifrada.
