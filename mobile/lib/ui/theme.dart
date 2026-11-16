import 'package:flutter/material.dart';

/// Colores semánticos que no vienen en [ColorScheme].
///
/// La app de escritorio usa una paleta propia; aquí se replica para que ambas
/// versiones se vean como la misma aplicación.
@immutable
class FinColors extends ThemeExtension<FinColors> {
  const FinColors({
    required this.bg,
    required this.card,
    required this.cardSoft,
    required this.border,
    required this.borderStrong,
    required this.text,
    required this.muted,
    required this.subtle,
    required this.primary,
    required this.primarySoft,
    required this.green,
    required this.greenSoft,
    required this.red,
    required this.redSoft,
    required this.amber,
    required this.amberSoft,
    required this.blue,
    required this.blueSoft,
    required this.purple,
    required this.purpleSoft,
    required this.grid,
  });

  final Color bg;
  final Color card;
  final Color cardSoft;
  final Color border;
  final Color borderStrong;
  final Color text;
  final Color muted;
  final Color subtle;
  final Color primary;
  final Color primarySoft;
  final Color green;
  final Color greenSoft;
  final Color red;
  final Color redSoft;
  final Color amber;
  final Color amberSoft;
  final Color blue;
  final Color blueSoft;
  final Color purple;
  final Color purpleSoft;
  final Color grid;

  static FinColors of(BuildContext context) =>
      Theme.of(context).extension<FinColors>() ?? light;

  static const FinColors light = FinColors(
    bg: Color(0xFFF3F4F6),
    card: Color(0xFFFFFFFF),
    cardSoft: Color(0xFFF9FAFB),
    border: Color(0xFFE5E7EB),
    borderStrong: Color(0xFFD1D5DB),
    text: Color(0xFF111827),
    muted: Color(0xFF6B7280),
    subtle: Color(0xFF9CA3AF),
    primary: Color(0xFF4F46E5),
    primarySoft: Color(0xFFEEF2FF),
    green: Color(0xFF059669),
    greenSoft: Color(0xFFECFDF5),
    red: Color(0xFFDC2626),
    redSoft: Color(0xFFFEF2F2),
    amber: Color(0xFFD97706),
    amberSoft: Color(0xFFFFFBEB),
    blue: Color(0xFF2563EB),
    blueSoft: Color(0xFFEFF6FF),
    purple: Color(0xFF7C3AED),
    purpleSoft: Color(0xFFF5F3FF),
    grid: Color(0xFFEEF0F3),
  );

  static const FinColors dark = FinColors(
    bg: Color(0xFF0B1220),
    card: Color(0xFF111827),
    cardSoft: Color(0xFF1A2334),
    border: Color(0xFF243044),
    borderStrong: Color(0xFF334155),
    text: Color(0xFFE5E7EB),
    muted: Color(0xFFA3B1C6),
    subtle: Color(0xFF7F8EA3),
    primary: Color(0xFF6366F1),
    primarySoft: Color(0xFF1E1B4B),
    green: Color(0xFF34D399),
    greenSoft: Color(0xFF052E2B),
    red: Color(0xFFF87171),
    redSoft: Color(0xFF3F1D1D),
    amber: Color(0xFFFBBF24),
    amberSoft: Color(0xFF3A2C08),
    blue: Color(0xFF60A5FA),
    blueSoft: Color(0xFF172554),
    purple: Color(0xFFC084FC),
    purpleSoft: Color(0xFF2E1065),
    grid: Color(0xFF1F2A3C),
  );

  @override
  FinColors copyWith({
    Color? bg,
    Color? card,
    Color? cardSoft,
    Color? border,
    Color? borderStrong,
    Color? text,
    Color? muted,
    Color? subtle,
    Color? primary,
    Color? primarySoft,
    Color? green,
    Color? greenSoft,
    Color? red,
    Color? redSoft,
    Color? amber,
    Color? amberSoft,
    Color? blue,
    Color? blueSoft,
    Color? purple,
    Color? purpleSoft,
    Color? grid,
  }) {
    return FinColors(
      bg: bg ?? this.bg,
      card: card ?? this.card,
      cardSoft: cardSoft ?? this.cardSoft,
      border: border ?? this.border,
      borderStrong: borderStrong ?? this.borderStrong,
      text: text ?? this.text,
      muted: muted ?? this.muted,
      subtle: subtle ?? this.subtle,
      primary: primary ?? this.primary,
      primarySoft: primarySoft ?? this.primarySoft,
      green: green ?? this.green,
      greenSoft: greenSoft ?? this.greenSoft,
      red: red ?? this.red,
      redSoft: redSoft ?? this.redSoft,
      amber: amber ?? this.amber,
      amberSoft: amberSoft ?? this.amberSoft,
      blue: blue ?? this.blue,
      blueSoft: blueSoft ?? this.blueSoft,
      purple: purple ?? this.purple,
      purpleSoft: purpleSoft ?? this.purpleSoft,
      grid: grid ?? this.grid,
    );
  }

  @override
  FinColors lerp(ThemeExtension<FinColors>? other, double t) {
    if (other is! FinColors) return this;
    return t < 0.5 ? this : other;
  }
}

ThemeData buildTheme(Brightness brightness) {
  final colors =
      brightness == Brightness.dark ? FinColors.dark : FinColors.light;
  final scheme = ColorScheme.fromSeed(
    seedColor: colors.primary,
    brightness: brightness,
  ).copyWith(
    primary: colors.primary,
    onPrimary: Colors.white,
    surface: colors.card,
    onSurface: colors.text,
    error: colors.red,
    outline: colors.borderStrong,
  );

  return ThemeData(
    useMaterial3: true,
    brightness: brightness,
    colorScheme: scheme,
    scaffoldBackgroundColor: colors.bg,
    dividerColor: colors.border,
    extensions: <ThemeExtension<dynamic>>[colors],
    splashFactory: InkSparkle.splashFactory,
    appBarTheme: AppBarTheme(
      backgroundColor: colors.bg,
      foregroundColor: colors.text,
      elevation: 0,
      scrolledUnderElevation: 0.5,
      centerTitle: false,
      titleTextStyle: TextStyle(
        color: colors.text,
        fontSize: 20,
        fontWeight: FontWeight.w700,
      ),
    ),
    cardTheme: CardThemeData(
      color: colors.card,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: colors.border),
      ),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: colors.card,
      indicatorColor: colors.primarySoft,
      elevation: 0,
      height: 68,
      labelTextStyle: WidgetStateProperty.resolveWith(
        (states) => TextStyle(
          fontSize: 11.5,
          fontWeight: states.contains(WidgetState.selected)
              ? FontWeight.w700
              : FontWeight.w500,
          color: states.contains(WidgetState.selected)
              ? colors.primary
              : colors.muted,
        ),
      ),
      iconTheme: WidgetStateProperty.resolveWith(
        (states) => IconThemeData(
          size: 23,
          color: states.contains(WidgetState.selected)
              ? colors.primary
              : colors.muted,
        ),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: colors.cardSoft,
      isDense: true,
      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
      hintStyle: TextStyle(color: colors.subtle, fontSize: 14),
      labelStyle: TextStyle(color: colors.muted, fontSize: 14),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: colors.border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: colors.border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: colors.primary, width: 1.6),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: colors.red),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size(0, 46),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        textStyle: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14.5),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        minimumSize: const Size(0, 46),
        foregroundColor: colors.text,
        side: BorderSide(color: colors.borderStrong),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        textStyle: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14.5),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(foregroundColor: colors.primary),
    ),
    dialogTheme: DialogThemeData(
      backgroundColor: colors.card,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
    ),
    bottomSheetTheme: BottomSheetThemeData(
      backgroundColor: colors.card,
      surfaceTintColor: Colors.transparent,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(22)),
      ),
    ),
    snackBarTheme: SnackBarThemeData(
      behavior: SnackBarBehavior.floating,
      backgroundColor: brightness == Brightness.dark
          ? const Color(0xFF1F2937)
          : const Color(0xFF111827),
      contentTextStyle: const TextStyle(color: Color(0xFFF9FAFB)),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
    ),
    chipTheme: ChipThemeData(
      backgroundColor: colors.cardSoft,
      side: BorderSide(color: colors.border),
      labelStyle: TextStyle(color: colors.text, fontSize: 12.5),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(999)),
    ),
    listTileTheme: ListTileThemeData(
      iconColor: colors.muted,
      textColor: colors.text,
    ),
  );
}
