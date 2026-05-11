import 'package:flutter/material.dart';
import '../../../core/constants/colors.dart';

class SupportDetailScreen extends StatelessWidget {
  final String title;

  const SupportDetailScreen({super.key, required this.title});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        title: Text(title,
            style: const TextStyle(
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
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppColors.primaryBlue.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(15),
              ),
              child: Row(
                children: [
                  const Icon(Icons.info_outline, color: AppColors.primaryBlue),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      'This section contains helpful information about $title to help you get the most out of EYE-DENTIFY.',
                      style: const TextStyle(
                          fontSize: 13, color: AppColors.bodyText),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 30),
            _buildFAQItem('How to use $title?',
                'You can access $title directly from your profile dashboard. Simply follow the on-screen instructions to manage your data.'),
            _buildFAQItem('Is my data secure?',
                'Yes, all information related to $title is encrypted and stored securely according to our privacy policy.'),
            _buildFAQItem('Can I change these settings?',
                'Most $title settings can be updated at any time. Some verification details may require administrator approval.'),
            const SizedBox(height: 40),
            const Center(
              child: Text(
                'Was this helpful?',
                style:
                    TextStyle(fontWeight: FontWeight.bold, color: Colors.grey),
              ),
            ),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                _buildFeedbackButton(Icons.thumb_up_alt_outlined, 'Yes'),
                const SizedBox(width: 20),
                _buildFeedbackButton(Icons.thumb_down_alt_outlined, 'No'),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFAQItem(String question, String answer) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(question,
              style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: AppColors.darkBlueShield)),
          const SizedBox(height: 8),
          Text(answer,
              style: const TextStyle(
                  fontSize: 14, color: Colors.grey, height: 1.5)),
        ],
      ),
    );
  }

  Widget _buildFeedbackButton(IconData icon, String label) {
    return OutlinedButton.icon(
      onPressed: () {},
      icon: Icon(icon, size: 18),
      label: Text(label),
      style: OutlinedButton.styleFrom(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        side: BorderSide(color: Colors.grey[300]!),
      ),
    );
  }
}
