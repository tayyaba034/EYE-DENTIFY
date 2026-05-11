import 'package:flutter/material.dart';
import '../../../core/constants/colors.dart';

class CaseDetailsScreen extends StatelessWidget {
  final String name;
  final String status;
  final String reportedDate;

  const CaseDetailsScreen({
    super.key,
    this.name = 'Sarah Khan',
    this.status = 'Active',
    this.reportedDate = 'Jan 20, 2026',
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        title: const Text('Case Profile',
            style: TextStyle(
                color: AppColors.bodyText, fontWeight: FontWeight.bold)),
        backgroundColor: Colors.white,
        elevation: 0,
        centerTitle: true,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded,
              color: AppColors.bodyText, size: 20),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            // Profile Header
            Center(
              child: Column(
                children: [
                  Stack(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(4),
                        decoration: const BoxDecoration(
                            color: Colors.white, shape: BoxShape.circle),
                        child: const CircleAvatar(
                          radius: 60,
                          backgroundColor: Color(0xFFF1F5F9),
                          child: Icon(Icons.person_rounded,
                              size: 60, color: Colors.grey),
                        ),
                      ),
                      Positioned(
                        bottom: 0,
                        right: 0,
                        child: Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                              color: AppColors.primaryBlue,
                              shape: BoxShape.circle,
                              border:
                                  Border.all(color: Colors.white, width: 2)),
                          child: const Icon(Icons.edit_rounded,
                              color: Colors.white, size: 16),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  Text(name,
                      style: const TextStyle(
                          fontSize: 24, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 4),
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                    decoration: BoxDecoration(
                      color: status == 'Active'
                          ? AppColors.warningSoft
                          : AppColors.successSoft,
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      status,
                      style: TextStyle(
                        color: status == 'Active'
                            ? AppColors.warning
                            : AppColors.success,
                        fontWeight: FontWeight.bold,
                        fontSize: 12,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 30),

            // Timeline
            const Text('Search Timeline',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
            const SizedBox(height: 16),
            _buildTimelineItem(
                'Report Filed',
                reportedDate,
                'Case successfully registered and AI models updated.',
                true,
                true),
            _buildTimelineItem(
                'AI Scanning',
                'Ongoing',
                'Multiple camera feeds are being analyzed in real-time.',
                true,
                false),
            _buildTimelineItem('Potential Match', '-',
                'Wait for alerts from nearby cameras.', false, false),

            const SizedBox(height: 24),

            // Details Card
            const Text('Person Details',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                  color: Colors.white, borderRadius: BorderRadius.circular(20)),
              child: Column(
                children: [
                  _buildDetailRow('Age', '10 Years'),
                  _buildDetailRow('Gender', 'Female'),
                  _buildDetailRow('Last Seen', 'Main Mall Parking'),
                  _buildDetailRow('Clothing', 'Red Jacket, Blue Jeans'),
                  _buildDetailRow('Height', '4\'5" approx.'),
                ],
              ),
            ),

            const SizedBox(height: 30),

            ElevatedButton.icon(
              onPressed: () {},
              icon: const Icon(Icons.share_rounded),
              label: const Text('SHARE CASE PROFILE'),
              style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.darkBlueShield),
            ),
            const SizedBox(height: 12),
            TextButton(
              onPressed: () {},
              child: const Text('Close Case (Person Found)',
                  style: TextStyle(
                      color: AppColors.success, fontWeight: FontWeight.bold)),
            ),
            const SizedBox(height: 40),
          ],
        ),
      ),
    );
  }

  Widget _buildTimelineItem(
      String title, String time, String desc, bool isCompleted, bool isFirst) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Column(
          children: [
            Container(
              width: 16,
              height: 16,
              decoration: BoxDecoration(
                color: isCompleted ? AppColors.primaryBlue : Colors.grey[300],
                shape: BoxShape.circle,
                border: Border.all(color: Colors.white, width: 2),
              ),
            ),
            Container(width: 2, height: 40, color: Colors.grey[200]),
          ],
        ),
        const SizedBox(width: 16),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(title,
                      style: TextStyle(
                          fontWeight: FontWeight.bold,
                          color:
                              isCompleted ? AppColors.bodyText : Colors.grey)),
                  Text(time,
                      style: TextStyle(fontSize: 12, color: Colors.grey[400])),
                ],
              ),
              const SizedBox(height: 4),
              Text(desc,
                  style: TextStyle(
                      fontSize: 12,
                      color:
                          isCompleted ? Colors.grey[600] : Colors.grey[400])),
              const SizedBox(height: 16),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildDetailRow(String label, String value) {
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
}
