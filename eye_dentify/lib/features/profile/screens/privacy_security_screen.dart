import 'package:flutter/material.dart';
import '../../../core/constants/colors.dart';
import 'change_password_screen.dart';
import 'two_factor_auth_screen.dart';
import 'location_sharing_screen.dart';
import 'blocked_users_screen.dart';

class PrivacySecurityScreen extends StatelessWidget {
  const PrivacySecurityScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        title: const Text('Privacy & Security',
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
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          _buildSectionHeader('Security Settings'),
          _buildSettingsTile(Icons.lock_outline, 'Change Password',
              'Update your login credentials', () {
            Navigator.push(
                context,
                MaterialPageRoute(
                    builder: (context) => const ChangePasswordScreen()));
          }),
          _buildSettingsTile(Icons.fingerprint, 'Biometric Login',
              'Use Fingerprint or Face ID', () {},
              isSwitch: true, switchValue: true),
          _buildSettingsTile(Icons.security_update_good, 'Two-Factor Auth',
              'Secure your account with 2FA', () {
            Navigator.push(
                context,
                MaterialPageRoute(
                    builder: (context) => const TwoFactorAuthScreen()));
          }),
          const SizedBox(height: 30),
          _buildSectionHeader('Privacy Options'),
          _buildSettingsTile(Icons.visibility_off_outlined, 'Private Account',
              'Only friends can see your cases', () {},
              isSwitch: true, switchValue: false),
          _buildSettingsTile(Icons.location_on_outlined, 'Location Sharing',
              'Control who sees your live location', () {
            Navigator.push(
                context,
                MaterialPageRoute(
                    builder: (context) => const LocationSharingScreen()));
          }),
          _buildSettingsTile(Icons.block_flipped, 'Blocked Users',
              'Manage users you\'ve restricted', () {
            Navigator.push(
                context,
                MaterialPageRoute(
                    builder: (context) => const BlockedUsersScreen()));
          }),
        ],
      ),
    );
  }

  Widget _buildSectionHeader(String title) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12, left: 4),
      child: Text(
        title,
        style: const TextStyle(
            fontSize: 14, fontWeight: FontWeight.bold, color: Colors.grey),
      ),
    );
  }

  Widget _buildSettingsTile(
      IconData icon, String title, String subtitle, VoidCallback onTap,
      {bool isSwitch = false, bool switchValue = false}) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(15),
        boxShadow: [
          BoxShadow(
              color: Colors.black.withValues(alpha: 0.02),
              blurRadius: 10,
              offset: const Offset(0, 4))
        ],
      ),
      child: ListTile(
        leading: Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
              color: AppColors.primaryBlue.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(10)),
          child: Icon(icon, color: AppColors.primaryBlue, size: 22),
        ),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text(subtitle,
            style: const TextStyle(fontSize: 12, color: Colors.grey)),
        trailing: isSwitch
            ? Switch(
                value: switchValue,
                onChanged: (v) {},
                activeTrackColor: AppColors.primaryBlue)
            : const Icon(Icons.chevron_right, size: 18),
        onTap: onTap,
      ),
    );
  }
}
