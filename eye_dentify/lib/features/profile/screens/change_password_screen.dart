import 'package:flutter/material.dart';
import '../../../core/constants/colors.dart';
import '../../auth/widgets/custom_text_field.dart';

class ChangePasswordScreen extends StatelessWidget {
  const ChangePasswordScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        title: const Text('Change Password',
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
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            const CustomTextField(
                hintText: 'Current Password', isPassword: true),
            const CustomTextField(hintText: 'New Password', isPassword: true),
            const CustomTextField(
                hintText: 'Confirm New Password', isPassword: true),
            const SizedBox(height: 40),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () {
                  ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
                      content: Text('Password updated successfully!')));
                  Navigator.pop(context);
                },
                child: const Text('UPDATE PASSWORD'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
