import 'package:flutter/material.dart';
import '../constants/colors.dart';

class ShieldLogo extends StatelessWidget {
  final double size;
  const ShieldLogo({super.key, this.size = 120});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: AppColors.darkBlueShield,
        shape: BoxShape.circle,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.2),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Center(
        child: Container(
          width: size * 0.85,
          height: size * 0.85,
          decoration: const BoxDecoration(
            shape: BoxShape.circle,
            image: DecorationImage(
              image: AssetImage('assets/images/cropped_circle_image.png'),
              fit: BoxFit.cover,
            ),
          ),
        ),
      ),
    );
  }
}
