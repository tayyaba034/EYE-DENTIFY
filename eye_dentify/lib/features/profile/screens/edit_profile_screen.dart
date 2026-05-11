import 'package:flutter/material.dart';
import '../../../core/constants/colors.dart';
import '../../auth/widgets/custom_text_field.dart';
import 'advanced_verification_screen.dart';

class EditProfileScreen extends StatelessWidget {
  const EditProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        title: const Text('Edit Profile',
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
          children: [
            Stack(
              children: [
                const CircleAvatar(
                  radius: 50,
                  backgroundColor: Color(0xFFE2E8F0),
                  child: Icon(Icons.person, size: 50, color: Colors.grey),
                ),
                Positioned(
                  bottom: 0,
                  right: 0,
                  child: Container(
                    padding: const EdgeInsets.all(4),
                    decoration: const BoxDecoration(
                      color: AppColors.primaryBlue,
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(Icons.camera_alt,
                        color: Colors.white, size: 18),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 30),
            const CustomTextField(hintText: 'Full Name'),
            const CustomTextField(hintText: 'Email Address'),
            const CustomTextField(hintText: 'Phone Number'),
            const CustomTextField(hintText: 'Bio'),
            const SizedBox(height: 20),
            _buildAdvancedVerifyButton(context),
            const SizedBox(height: 40),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                        content: Text('Profile updated successfully!')),
                  );
                  Navigator.pop(context);
                },
                child: const Text('SAVE CHANGES'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAdvancedVerifyButton(BuildContext context) {
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: AppColors.primaryBlue.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(15),
        border: Border.all(color: AppColors.primaryBlue.withValues(alpha: 0.3)),
      ),
      child: ListTile(
        leading: const Icon(Icons.verified_user_outlined,
            color: AppColors.primaryBlue),
        title: const Text('Additional Authorization Details',
            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
        subtitle: const Text('CNIC, Fingerprints, Biometrics',
            style: TextStyle(fontSize: 11)),
        trailing: const Icon(Icons.chevron_right, size: 20),
        onTap: () => Navigator.push(
            context,
            MaterialPageRoute(
                builder: (context) => const AdvancedVerificationScreen())),
      ),
    );
  }
}
