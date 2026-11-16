# Finanzas móvil

Aplicación nativa de **Flutter** para Android e iPhone. Funciona **100 % offline**:
la base de datos SQLite vive en el teléfono, no hay cuentas, servidores ni anuncios.

Comparte el modelo de datos del escritorio (`finanzas/`):

- montos en **centavos** y fechas en **ISO 8601** (`AAAA-MM-DD`);
- mismas tablas (`accounts`, `categories`, `transactions`, `budgets`, `fx_rates`,
  `recurring`, `rules`, `settings`);
- tasas de cambio en micros (`1 unidad extrajera = X moneda base`);
- el mismo formato de respaldo JSON, así que puedes mover tus datos entre la
  computadora y el teléfono.

## Qué incluye

- **Resumen**: balance total, ingresos, egresos, ahorro del mes, gráfica de flujo,
  presupuestos y últimos movimientos.
- **Movimientos**: ingresos, egresos y transferencias (también entre monedas),
  búsqueda, filtros y edición.
- **Cuentas** con moneda propia y saldo consolidado.
- **Presupuestos** mensuales por categoría con barra de avance y alertas.
- **Reportes** por mes o año con gráficas propias (sin paquetes externos).
- **Categorías**, **recurrentes** y **reglas automáticas**.
- **Ver en**: muestra todos los montos en otra moneda con tasa registrada, sin
  crear cuentas ni alterar los datos guardados.
- **Ajustes**: tema claro/oscuro, símbolo y formato de números, moneda base,
  tasas por fecha, respaldo, datos de ejemplo y borrado total.
- Interfaz en **español**, Material 3, adaptada a pantallas de teléfono.

## Requisitos

- [Flutter](https://docs.flutter.dev/get-started/install) **3.35 o superior**
  (probado con Flutter 3.50 / Dart 3.14).
- **Android**: Android Studio (o Android SDK + JDK 17). El proyecto usa
  Gradle 9.5 y Android Gradle Plugin 9.3, incluidos en el wrapper.
- **iPhone**: una Mac con **Xcode 16 o superior** y CocoaPods. En Linux o
  Windows no es posible compilar para iOS.

Comprueba el entorno con:

```bash
flutter doctor
```

Si `flutter` no está en el `PATH`, usa la ruta de tu instalación. En este equipo
de desarrollo el SDK está en `/tmp/opencode/flutter/bin/flutter`.

## Ejecutar en el teléfono

1. Activa las **Opciones de desarrollador** y la **Depuración USB** en Android,
   o conecta el iPhone y confía en la computadora.
2. Desde `mobile/`:

```bash
flutter pub get
flutter devices      # confirma que aparece tu teléfono
flutter run
```

Para una primera instalación también puedes usar un APK (ver abajo).

## Compilar para Android

```bash
cd mobile
flutter build apk --release
```

El archivo queda en:

```
build/app/outputs/flutter-apk/app-release.apk
```

Instálalo con `adb install -r build/app/outputs/flutter-apk/app-release.apk`,
cópialo al teléfono y ábrelo, o publícalo en Google Play con un `.aab`
(`flutter build appbundle --release`).

Para reducir el tamaño por arquitectura:

```bash
flutter build apk --release --split-per-abi
```

El identificador de la app es `com.finanzas.finanzas_mobile`; el nombre visible
es **Finanzas**. Puedes cambiarlo en `android/app/build.gradle.kts` y
`android/app/src/main/AndroidManifest.xml`.

El APK de release se firma con la clave de depuración para poder instalarlo
directamente (sideloading). Para publicar en Google Play, crea un keystore y
configura `signingConfigs` en `android/app/build.gradle.kts`.

## Compilar sin Android Studio (en la nube)

En el repositorio ya están los dos pipelines listos:

- `.github/workflows/android.yml` para **GitHub Actions**.
- `codemagic.yaml` para **Codemagic** (Android e iOS).

Sube la **carpeta completa del proyecto** (la que contiene `mobile/`,
`codemagic.yaml` y `.github/`), no solo `mobile/`.

### GitHub Actions

1. Crea un repositorio vacío en GitHub y sube el proyecto:

```bash
cd finanzas            # carpeta raíz del proyecto
git init
git add .
git commit -m "Finanzas escritorio y móvil"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/finanzas.git
git push -u origin main
```

2. En GitHub entra a **Actions → Android APK → Run workflow**.
3. Al terminar (unos 8–12 minutos) abre la ejecución y descarga el artefacto
   `finanzas-apk-N`. Dentro está `app-release.apk`.
4. Copia el APK al teléfono, ábrelo y permite la instalación de orígenes
   desconocidos. No hace falta `adb` ni Android Studio.

También se compila al publicar un tag:

```bash
git tag v1.0.0
git push origin v1.0.0
```

El workflow ejecuta `flutter analyze`, las 34 pruebas y `flutter build apk
--release`. En repos públicos los minutos son gratis; en privados se descuentan
de los 2 000 minutos mensuales incluidos.

### Codemagic

1. Crea una cuenta en [codemagic.io](https://codemagic.io) y conecta el mismo
   repositorio.
2. Codemagic detecta `codemagic.yaml` y permite elegir el workflow:
   - **Finanzas · Android APK**: genera el mismo APK instalable.
   - **Finanzas · iOS sin firma**: solo comprueba que iOS compila; el
     `Runner.app` resultante no se puede instalar en un iPhone.
   - **Finanzas · iOS TestFlight**: requiere cuenta de Apple Developer y una
     integración «App Store Connect» en Codemagic. Cambia
     `CAMBIA_ESTE_NOMBRE` en `codemagic.yaml` por el nombre de tu integración.
3. Descarga el artefacto desde la pantalla de la compilación.

El plan gratuito de Codemagic incluye minutos limitados al mes; para iOS firmado
hace falta además la cuenta de Apple Developer.

> Si Flutter 3.50.0 ya no está disponible en alguno de los servicios, cambia
> `flutter-version: '3.50.0'` (GitHub) o `flutter: 3.50.0` (Codemagic) por
> `stable`.

## Compilar para iPhone

Solo desde **macOS** con Xcode:

```bash
cd mobile
flutter pub get
open ios/Runner.xcworkspace
```

El proyecto usa Swift Package Manager, así que normalmente **no** necesitas
CocoaPods. Si al compilar Flutter genera un `ios/Podfile`, ejecuta
`cd ios && pod install` antes de abrir el workspace.

En Xcode elige el equipo de firma (*Signing & Capabilities* → *Team*), cambia el
*bundle identifier* si lo necesitas y ejecuta en el dispositivo. Para generar el
paquete de distribución:

```bash
flutter build ipa --release
```

El `.ipa` queda en `build/ios/ipa/`. Para instalarlo necesitas una cuenta de
Apple Developer (TestFlight/App Store) o firmar la app con tu cuenta gratuita,
que permite instalarla por 7 días y requiere renovarla.

## Pruebas y análisis

```bash
cd mobile
flutter test        # 34 pruebas de datos, utilidades e interfaz
flutter analyze     # solo avisos informativos de la API de Flutter 3.50
```

Las pruebas usan `sqflite_common_ffi` con una base temporal, así que no tocan
los datos del teléfono ni necesitan un emulador.

## Datos y respaldo

La base se guarda en el almacenamiento privado de la app
(`getDatabasesPath()/finanzas.db`). No se puede copiar desde fuera sin root o
sin las herramientas de desarrollo, por eso el respaldo es la vía recomendada:

- **Ajustes → Datos y respaldo → Exportar respaldo**: copia todo el contenido
  (cuentas, categorías, movimientos, presupuestos, recurrentes, reglas, tasas y
  ajustes) al portapapeles en JSON.
- Pega el texto en un archivo `finanzas-AAAA-MM-DD.json` para guardarlo.
- **Restaurar respaldo**: pega un JSON y confirma. Reemplaza todos los datos
  actuales.

El formato es el mismo del escritorio (`"app": "finanzas"`, `"version": 2`,
`"data": { ... }`). Para mover datos:

- **Teléfono → escritorio**: exporta, guarda el JSON y usa *Restaurar respaldo*
  en la app de escritorio.
- **Escritorio → teléfono**: abre el respaldo del escritorio, copia todo el
  texto y pégalo en *Restaurar respaldo*.

La app también acepta respaldos antiguos con la clave `tables`.

> Tras restaurar, cierra y vuelve a abrir la app si quieres que los
> recurrentes pendientes se generen de inmediato al arrancar.

## Estructura

```
mobile/
├── lib/
│   ├── main.dart              arranque, apertura de la base y recurrentes
│   ├── app.dart               AppState/AppScope, navegación, «Ver en»
│   ├── data/
│   │   ├── database.dart      schema SQLite y toda la lógica de datos
│   │   ├── models.dart        cuentas, movimientos, presupuestos, reglas…
│   │   └── utils.dart         montos, fechas, recurrentes y formato
│   └── ui/
│       ├── theme.dart         paleta clara/oscura del escritorio
│       ├── widgets.dart       tarjetas, gráficas y widgets compartidos
│       └── screens/           resumen, movimientos, cuentas, presupuestos,
│                              reportes, categorías, recurrentes, reglas, ajustes
├── test/                      pruebas de datos, utilidades e interfaz
├── tool/generate_icons.py     regenera los iconos Android/iOS
├── android/                   proyecto nativo Android
└── ios/                       proyecto nativo iOS (compilar en macOS)
```

Los iconos se generan con Pillow (`python3 -m pip install pillow`) y el script
`tool/generate_icons.py`.

## Notas y límites

- No hay sincronización automática entre teléfono y escritorio: usa el respaldo
  JSON.
- No hay bloqueo por PIN ni biometría; protege el teléfono con su propio bloqueo.
- La app no pide permisos de internet ni de almacenamiento.
- Al ser offline, los tipos de cambio se capturan a mano en Ajustes.
