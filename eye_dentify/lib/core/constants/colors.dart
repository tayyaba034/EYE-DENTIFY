import 'package:flutter/material.dart';

class AppColors {
  //Brand Colors
  static const Color darkBlueShield = Color(0xFF1A4D7C); // #1A4D7C
  static const Color lightBlueIcon = Color(0xFF5CA3D9); // #5CA3D9

  //Background Gradients
  static const Color gradientTop = Color(0xFF87CEEB); // #87CEEB
  static const Color gradientBottom = Color(0xFFB0D7E8); // #B0D7E8
  static const Color solidLightBlue = Color(0xFFA8D5E8); // #A8D5E8 alternative

  //Primary Elements
  static const Color primaryBlue = Color(0xFF5CA3D9); // #5CA3D9
  static const Color secondaryGray = Color(0xFF4A5568); // #4A5568

  //UI States
  static const Color success = Color(0xFF10B981); // #10B981
  static const Color successSoft = Color(0xFFA7F3D0); // Soft Green
  static const Color warning = Color(0xFFF59E0B); // #F59E0B
  static const Color warningSoft = Color(0xFFFEF3C7); // Soft Amber
  static const Color error = Color(0xFFEF4444); // #EF4444
  static const Color errorSoft = Color(0xFFFEE2E2); // Soft Red
  static const Color accentCute = Color(0xFFFF7F7F); // Cute Coral Accent

  //Input & Text
  static const Color inputBorder = Color(0xFFE2E8F0);
  static const Color inputLabel = Color(0xFF6B7280);
  static const Color bodyText = Color(0xFF2C3E50); // #2C3E50
  static const Color linkBlue = Colors.white; // Changed to white for visibility

  static const LinearGradient backgroundGradient = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [gradientTop, gradientBottom],
  );
}
