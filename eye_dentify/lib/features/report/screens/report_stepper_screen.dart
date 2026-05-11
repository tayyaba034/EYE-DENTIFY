import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../core/constants/colors.dart';
import '../../../models/missing_person_model.dart';
import '../../../models/enums.dart';
import '../../../providers/missing_person_provider.dart';
import '../../../providers/auth_provider.dart';

class ReportStepperScreen extends StatefulWidget {
  const ReportStepperScreen({super.key});

  @override
  State<ReportStepperScreen> createState() => _ReportStepperScreenState();
}

class _ReportStepperScreenState extends State<ReportStepperScreen> {
  int _currentStep = 0;

  // Controllers
  final _nameController = TextEditingController();
  final _ageController = TextEditingController();
  final _dateController = TextEditingController();
  final _locationController = TextEditingController();
  final _clothingController = TextEditingController();
  final _notesController = TextEditingController();

  Gender _selectedGender = Gender.male;
  File? _selectedPhoto; // In a real app, this would be from image_picker

  @override
  void dispose() {
    _nameController.dispose();
    _ageController.dispose();
    _dateController.dispose();
    _locationController.dispose();
    _clothingController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  bool _validateStep() {
    if (_currentStep == 0) {
      // Photo step - for demo, we'll allow proceeding without a photo if needed
      // but ideally we check if _selectedPhoto != null
      return true;
    } else if (_currentStep == 1) {
      return _nameController.text.isNotEmpty && _ageController.text.isNotEmpty;
    } else if (_currentStep == 2) {
      return _locationController.text.isNotEmpty;
    }
    return true;
  }

  Future<void> _handleSubmit() async {
    final authProvider = Provider.of<AuthProvider>(context, listen: false);
    final mpProvider =
        Provider.of<MissingPersonProvider>(context, listen: false);

    if (authProvider.currentUser == null) return;

    final newCase = MissingPersonModel(
      userId: authProvider.currentUser!.userId,
      fullName: _nameController.text.trim(),
      age: int.tryParse(_ageController.text),
      gender: _selectedGender,
      lastSeenLocation: _locationController.text.trim(),
      lastSeenDatetime:
          DateTime.tryParse(_dateController.text) ?? DateTime.now(),
      clothingDescription: _clothingController.text.trim(),
      additionalNotes: _notesController.text.trim(),
      status: CaseStatus.active,
    );

    // Simulation: photos would be uploaded here
    final success = await mpProvider.reportMissingPerson(
      missingPerson: newCase,
      photos: _selectedPhoto != null ? [_selectedPhoto!] : [],
    );

    if (success && mounted) {
      _showSuccessDialog();
    } else if (mounted && mpProvider.errorMessage != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(mpProvider.errorMessage!)),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final mpProvider = context.watch<MissingPersonProvider>();

    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        title: const Text('Report Missing Person',
            style: TextStyle(color: AppColors.bodyText)),
        backgroundColor: Colors.white,
        elevation: 0,
        iconTheme: const IconThemeData(color: AppColors.bodyText),
      ),
      body: mpProvider.isLoading
          ? const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  CircularProgressIndicator(),
                  SizedBox(height: 16),
                  Text('Uploading case data...'),
                ],
              ),
            )
          : Stepper(
              type: StepperType.horizontal,
              currentStep: _currentStep,
              onStepContinue: () {
                if (_validateStep()) {
                  if (_currentStep < 3) {
                    setState(() => _currentStep++);
                  } else {
                    _handleSubmit();
                  }
                } else {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                        content: Text('Please fill required fields')),
                  );
                }
              },
              onStepCancel: () {
                if (_currentStep > 0) {
                  setState(() => _currentStep--);
                }
              },
              elevation: 0,
              steps: [
                Step(
                  title: const Text('Photo'),
                  isActive: _currentStep >= 0,
                  content: _buildPhotoStep(),
                ),
                Step(
                  title: const Text('Personal'),
                  isActive: _currentStep >= 1,
                  content: _buildPersonalStep(),
                ),
                Step(
                  title: const Text('Seen'),
                  isActive: _currentStep >= 2,
                  content: _buildSeenStep(),
                ),
                Step(
                  title: const Text('Review'),
                  isActive: _currentStep >= 3,
                  content: _buildReviewStep(),
                ),
              ],
              controlsBuilder: (context, details) {
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 20),
                  child: Row(
                    children: [
                      if (_currentStep > 0)
                        Expanded(
                          child: OutlinedButton(
                            onPressed: details.onStepCancel,
                            style: OutlinedButton.styleFrom(
                              padding: const EdgeInsets.all(15),
                              side: const BorderSide(
                                  color: AppColors.primaryBlue),
                              shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(12)),
                            ),
                            child: const Text('BACK'),
                          ),
                        ),
                      if (_currentStep > 0) const SizedBox(width: 12),
                      Expanded(
                        child: ElevatedButton(
                          onPressed: details.onStepContinue,
                          style: ElevatedButton.styleFrom(
                            padding: const EdgeInsets.all(15),
                            shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(12)),
                          ),
                          child: Text(
                              _currentStep == 3 ? 'SUBMIT REPORT' : 'NEXT'),
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
    );
  }

  Widget _buildPhotoStep() {
    return Column(
      children: [
        const Text(
          'First, let\'s add a photo of the person.',
          style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 16),
        GestureDetector(
          onTap: () {
            // Simulation: Picking an image
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Image picking simulated')),
            );
          },
          child: Container(
            height: 220,
            width: double.infinity,
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(
                  color: AppColors.primaryBlue.withValues(alpha: 0.3),
                  width: 2),
              boxShadow: [
                BoxShadow(
                  color: AppColors.primaryBlue.withValues(alpha: 0.05),
                  blurRadius: 15,
                  offset: const Offset(0, 8),
                ),
              ],
            ),
            child: _selectedPhoto != null
                ? ClipRRect(
                    borderRadius: BorderRadius.circular(18),
                    child: Image.file(_selectedPhoto!, fit: BoxFit.cover),
                  )
                : Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Container(
                        padding: const EdgeInsets.all(20),
                        decoration: BoxDecoration(
                          color: AppColors.primaryBlue.withValues(alpha: 0.1),
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(Icons.add_a_photo_rounded,
                            size: 50, color: AppColors.primaryBlue),
                      ),
                      const SizedBox(height: 16),
                      const Text('Tap to Upload Photo',
                          style: TextStyle(
                              fontWeight: FontWeight.bold,
                              color: AppColors.primaryBlue)),
                      const SizedBox(height: 8),
                      Text('PNG, JPG up to 10MB',
                          style:
                              TextStyle(color: Colors.grey[400], fontSize: 12)),
                    ],
                  ),
          ),
        ),
        const SizedBox(height: 20),
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: AppColors.warningSoft.withValues(alpha: 0.5),
            borderRadius: BorderRadius.circular(12),
          ),
          child: const Row(
            children: [
              Icon(Icons.lightbulb_outline, color: AppColors.warning, size: 20),
              SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Tip: A clear face photo helps the AI find them much faster!',
                  style:
                      TextStyle(fontSize: 12, color: AppColors.secondaryGray),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildPersonalStep() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Tell us about the person',
          style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 16),
        _buildTextField('Full Name',
            controller: _nameController, icon: Icons.person_outline),
        _buildTextField('Age',
            controller: _ageController,
            keyboardType: TextInputType.number,
            icon: Icons.cake_outlined),
        const Padding(
          padding: EdgeInsets.symmetric(vertical: 8),
          child: Text('Gender',
              style: TextStyle(
                  fontWeight: FontWeight.w500, color: AppColors.bodyText)),
        ),
        Row(
          children: [
            _buildGenderOption('Male', Gender.male),
            const SizedBox(width: 16),
            _buildGenderOption('Female', Gender.female),
            const SizedBox(width: 16),
            _buildGenderOption('Other', Gender.other),
          ],
        ),
        const SizedBox(height: 12),
        _buildTextField('Additional Notes',
            controller: _notesController,
            maxLines: 3,
            icon: Icons.description_outlined),
      ],
    );
  }

  Widget _buildGenderOption(String label, Gender gender) {
    final isSelected = _selectedGender == gender;
    return GestureDetector(
      onTap: () => setState(() => _selectedGender = gender),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: isSelected
              ? AppColors.primaryBlue.withValues(alpha: 0.1)
              : Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
              color:
                  isSelected ? AppColors.primaryBlue : AppColors.inputBorder),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              gender == Gender.male
                  ? Icons.male
                  : (gender == Gender.female
                      ? Icons.female
                      : Icons.transgender),
              size: 18,
              color: isSelected ? AppColors.primaryBlue : Colors.grey,
            ),
            const SizedBox(width: 8),
            Text(label,
                style: TextStyle(
                  fontSize: 14,
                  color:
                      isSelected ? AppColors.primaryBlue : AppColors.bodyText,
                  fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                )),
          ],
        ),
      ),
    );
  }

  Widget _buildSeenStep() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'When and where were they last seen?',
          style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 16),
        _buildTextField('Last Seen Date (YYYY-MM-DD)',
            controller: _dateController, icon: Icons.calendar_today),
        _buildTextField('Last Seen Location',
            controller: _locationController, icon: Icons.location_on_outlined),
        _buildTextField('Clothing Description',
            controller: _clothingController,
            maxLines: 2,
            icon: Icons.checkroom_outlined),
      ],
    );
  }

  Widget _buildReviewStep() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Review the details',
          style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: AppColors.inputBorder),
          ),
          child: Column(
            children: [
              _buildReviewRow('Name', _nameController.text),
              _buildReviewRow('Age', '${_ageController.text} Years'),
              _buildReviewRow('Gender', _selectedGender.displayName),
              _buildReviewRow('Location', _locationController.text),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildReviewRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: Colors.grey)),
          Text(value, style: const TextStyle(fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }

  Widget _buildTextField(String label,
      {TextEditingController? controller,
      IconData? icon,
      TextInputType? keyboardType,
      int maxLines = 1}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: TextField(
        controller: controller,
        keyboardType: keyboardType,
        maxLines: maxLines,
        decoration: InputDecoration(
          labelText: label,
          suffixIcon: icon != null ? Icon(icon) : null,
          filled: true,
          fillColor: Colors.grey[50],
          border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: BorderSide.none),
        ),
      ),
    );
  }

  void _showSuccessDialog() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.check_circle_outline,
                color: AppColors.success, size: 80),
            const SizedBox(height: 20),
            const Text('Report Submitted!',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
            const SizedBox(height: 10),
            const Text(
                'The security team has been notified and the AI system is scanning feeds.',
                textAlign: TextAlign.center),
            const SizedBox(height: 20),
            ElevatedButton(
              onPressed: () {
                Navigator.pop(context); // Close dialog
                Navigator.pop(context); // Go back from stepper
              },
              child: const Text('OK'),
            ),
          ],
        ),
      ),
    );
  }
}
