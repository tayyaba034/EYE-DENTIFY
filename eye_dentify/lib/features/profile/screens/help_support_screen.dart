import 'package:flutter/material.dart';
import '../../../core/constants/colors.dart';
import 'support_detail_screen.dart';
import 'live_chat_screen.dart';

class HelpSupportScreen extends StatelessWidget {
  const HelpSupportScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        title: const Text('Help & Support',
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
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'How can we help?',
              style: TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                  color: AppColors.bodyText),
            ),
            const SizedBox(height: 20),
            TextField(
              decoration: InputDecoration(
                hintText: 'Search for articles...',
                prefixIcon: const Icon(Icons.search),
                filled: true,
                fillColor: Colors.white,
                border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(15),
                    borderSide: BorderSide.none),
              ),
            ),
            const SizedBox(height: 30),
            _buildCategoryTile(Icons.report_problem_outlined,
                'Reporting Issues', 'Learn how to report effectively', context),
            _buildCategoryTile(Icons.assignment_outlined, 'Case Management',
                'Manage and track your search cases', context),
            _buildCategoryTile(Icons.security_outlined, 'Account & Security',
                'Protect your profile and data', context),
            _buildCategoryTile(
                Icons.notifications_active_outlined,
                'Alerts & Notifications',
                'Understand how matching works',
                context),
            const SizedBox(height: 40),
            const Text('Still need help?',
                style: TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            _buildContactButton(Icons.mail_outline, 'Email Support', () {
              ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Opening email client...')));
            }),
            _buildContactButton(Icons.chat_bubble_outline, 'Live Chat', () {
              Navigator.push(
                  context,
                  MaterialPageRoute(
                      builder: (context) => const LiveChatScreen()));
            }),
          ],
        ),
      ),
    );
  }

  Widget _buildCategoryTile(
      IconData icon, String title, String subtitle, BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
          color: Colors.white, borderRadius: BorderRadius.circular(15)),
      child: ListTile(
        leading: Icon(icon, color: AppColors.primaryBlue),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
        subtitle: Text(subtitle, style: const TextStyle(fontSize: 12)),
        trailing: const Icon(Icons.chevron_right, size: 18),
        onTap: () => Navigator.push(
            context,
            MaterialPageRoute(
                builder: (context) => SupportDetailScreen(title: title))),
      ),
    );
  }

  Widget _buildContactButton(IconData icon, String label, VoidCallback onTap) {
    return SizedBox(
      width: double.infinity,
      child: OutlinedButton.icon(
        onPressed: onTap,
        icon: Icon(icon, size: 18),
        label: Text(label),
        style: OutlinedButton.styleFrom(
          padding: const EdgeInsets.symmetric(vertical: 12),
          side: const BorderSide(color: AppColors.primaryBlue),
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        ),
      ),
    );
  }
}
