import 'package:flutter/material.dart';
import '../../../core/constants/colors.dart';
import '../../../core/widgets/app_logo.dart';

class AboutScreen extends StatelessWidget {
  const AboutScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        title: const Text('About EYE-DENTIFY',
            style: TextStyle(
                color: AppColors.bodyText, fontWeight: FontWeight.bold)),
        backgroundColor: Colors.white,
        elevation: 0,
        centerTitle: true,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded,
              color: AppColors.bodyText),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(30),
        child: Column(
          children: [
            const AppLogo(size: 100),
            const SizedBox(height: 20),
            const Text(
              'EYE-DENTIFY',
              style: TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                  color: AppColors.darkBlueShield),
            ),
            const Text('Version 1.0.0', style: TextStyle(color: Colors.grey)),
            const SizedBox(height: 40),
            const Text(
              'Our Mission',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            const Text(
              'EYE-DENTIFY is a community-driven smart surveillance initiative designed to reunite missing individuals with their loved ones. By combining advanced AI matching with community vigilance, we aim to create a safer world for everyone.',
              textAlign: TextAlign.center,
              style: TextStyle(height: 1.5, color: AppColors.bodyText),
            ),
            const SizedBox(height: 40),
            _buildInfoRow('Developed by', 'EYE-DENTIFY Tech Team'),
            _buildInfoRow('Release Date', 'January 2026'),
            _buildInfoRow('Website', 'www.eye-dentify.pk'),
            const SizedBox(height: 60),
            const Text('© 2026 EYE-DENTIFY. All Rights Reserved.',
                style: TextStyle(fontSize: 10, color: Colors.grey)),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(fontWeight: FontWeight.w500)),
          Text(value, style: const TextStyle(color: Colors.grey)),
        ],
      ),
    );
  }
}
