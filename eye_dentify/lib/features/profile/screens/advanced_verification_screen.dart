import 'package:flutter/material.dart';
import '../../../core/constants/colors.dart';
import '../../auth/widgets/custom_text_field.dart';

class AdvancedVerificationScreen extends StatefulWidget {
  const AdvancedVerificationScreen({super.key});

  @override
  State<AdvancedVerificationScreen> createState() =>
      _AdvancedVerificationScreenState();
}

class _AdvancedVerificationScreenState
    extends State<AdvancedVerificationScreen> {
  bool _isBiometricEnabled = true;
  String _scanningHand = ''; // 'left' or 'right'
  bool _isScanning = false;

  void _simulateScan(String hand) async {
    setState(() {
      _scanningHand = hand;
      _isScanning = true;
    });

    await Future.delayed(const Duration(seconds: 3));

    if (mounted) {
      setState(() {
        _isScanning = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
            content: Text(
                '${hand == 'left' ? 'Left' : 'Right'} hand scan complete!')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        title: const Text('Advanced Verification',
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
            const Text('CNIC Details',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            const CustomTextField(
                hintText: 'CNIC Number (e.g. 42101-XXXXXXX-X)',
                keyboardType: TextInputType.number),
            const SizedBox(height: 20),
            Row(
              children: [
                Expanded(
                    child: _buildPhotoPicker(
                        'CNIC Front Side', Icons.badge_outlined)),
                const SizedBox(width: 12),
                Expanded(
                    child: _buildPhotoPicker(
                        'CNIC Back Side', Icons.badge_outlined)),
              ],
            ),
            const SizedBox(height: 32),
            const Text('Fingerprint Authentication',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const Text('Scan four fingers of each hand for enhanced security.',
                style: TextStyle(color: Colors.grey, fontSize: 13)),
            const SizedBox(height: 20),
            Row(
              children: [
                Expanded(
                    child: _buildScanButton(
                        'Left Hand',
                        Icons.front_hand_outlined,
                        _scanningHand == 'left' && _isScanning,
                        () => _simulateScan('left'))),
                const SizedBox(width: 12),
                Expanded(
                    child: _buildScanButton(
                        'Right Hand',
                        Icons.front_hand_outlined,
                        _scanningHand == 'right' && _isScanning,
                        () => _simulateScan('right'))),
              ],
            ),
            const SizedBox(height: 32),
            const Text('Biometric Security',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            SwitchListTile(
              title: const Text('Enable Face ID / Fingerprint'),
              subtitle:
                  const Text('Use system biometrics for faster reporting'),
              value: _isBiometricEnabled,
              onChanged: (v) => setState(() => _isBiometricEnabled = v),
              activeTrackColor: AppColors.primaryBlue,
              contentPadding: EdgeInsets.zero,
            ),
            const SizedBox(height: 40),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Verification data saved!')),
                  );
                  Navigator.pop(context);
                },
                child: const Text('COMPLETE VERIFICATION'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPhotoPicker(String label, IconData icon) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label,
            style: const TextStyle(
                fontSize: 12, fontWeight: FontWeight.w600, color: Colors.grey)),
        const SizedBox(height: 8),
        Container(
          height: 100,
          decoration: BoxDecoration(
            color: Colors.grey[50],
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: Colors.grey[200]!),
          ),
          child: const Center(
            child:
                Icon(Icons.add_a_photo_outlined, color: AppColors.primaryBlue),
          ),
        ),
      ],
    );
  }

  Widget _buildScanButton(
      String label, IconData icon, bool isScanning, VoidCallback onTap) {
    return Column(
      children: [
        Container(
          width: double.infinity,
          height: 120,
          decoration: BoxDecoration(
            color: isScanning
                ? AppColors.primaryBlue.withValues(alpha: 0.1)
                : Colors.grey[50],
            borderRadius: BorderRadius.circular(15),
            border: Border.all(
                color: isScanning ? AppColors.primaryBlue : Colors.grey[200]!),
          ),
          child: Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: isScanning ? null : onTap,
              borderRadius: BorderRadius.circular(15),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  if (isScanning)
                    const SizedBox(
                      width: 40,
                      height: 40,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: AppColors.primaryBlue),
                    )
                  else
                    Icon(icon, size: 40, color: AppColors.primaryBlue),
                  const SizedBox(height: 12),
                  Text(
                    isScanning ? 'Scanning...' : 'Tap to Scan',
                    style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: isScanning
                            ? AppColors.primaryBlue
                            : Colors.grey[600]),
                  ),
                ],
              ),
            ),
          ),
        ),
        const SizedBox(height: 8),
        Text(label,
            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
      ],
    );
  }
}
