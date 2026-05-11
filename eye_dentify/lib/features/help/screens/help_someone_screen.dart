import 'package:flutter/material.dart';
import '../../../core/constants/colors.dart';

class HelpSomeoneScreen extends StatelessWidget {
  const HelpSomeoneScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        title: const Text('Help Someone',
            style: TextStyle(
                color: AppColors.bodyText, fontWeight: FontWeight.bold)),
        backgroundColor: Colors.white,
        elevation: 0,
        centerTitle: true,
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          _buildAnonymousCard(
            context,
            'A. Khan',
            '8 Years',
            'Today, 2:00 PM',
            'Sector G-11, Islamabad',
            'Wearing a yellow t-shirt and blue shorts. Braces on teeth.',
          ),
          _buildAnonymousCard(
            context,
            'S. Ahmed',
            '12 Years',
            'Yesterday',
            'Centaurus Mall, Food Court',
            'Red hoodie, black trousers. Carrying a blue backpack.',
          ),
          _buildAnonymousCard(
            context,
            'M. Umar',
            '75 Years',
            '2 days ago',
            'F-6 Markaz Park',
            'White shalwar kameez, gray cardigan. Walks with a wooden cane.',
          ),
        ],
      ),
    );
  }

  Widget _buildAnonymousCard(
    BuildContext context,
    String name,
    String age,
    String time,
    String location,
    String description,
  ) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
              color: Colors.black.withValues(alpha: 0.05),
              blurRadius: 10,
              offset: const Offset(0, 4))
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                CircleAvatar(
                  radius: 25,
                  backgroundColor: AppColors.primaryBlue.withValues(alpha: 0.1),
                  child: const Icon(Icons.person_outline,
                      color: AppColors.primaryBlue),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(name,
                          style: const TextStyle(
                              fontWeight: FontWeight.bold, fontSize: 16)),
                      Text('Age: $age',
                          style: const TextStyle(
                              color: Colors.grey, fontSize: 13)),
                    ],
                  ),
                ),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                  decoration: BoxDecoration(
                      color: AppColors.warningSoft,
                      borderRadius: BorderRadius.circular(10)),
                  child: const Text('MISSING',
                      style: TextStyle(
                          color: AppColors.warning,
                          fontWeight: FontWeight.bold,
                          fontSize: 10)),
                ),
              ],
            ),
          ),
          const Divider(height: 1),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _buildInfoRow(Icons.access_time_rounded, 'Last Seen: $time'),
                const SizedBox(height: 8),
                _buildInfoRow(
                    Icons.location_on_outlined, 'Location: $location'),
                const SizedBox(height: 12),
                const Text('Physical Description:',
                    style:
                        TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                const SizedBox(height: 4),
                Text(description,
                    style: TextStyle(color: Colors.grey[700], fontSize: 14)),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.only(left: 16, right: 16, bottom: 16),
            child: SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: () => _showContactDialog(context, name),
                icon: const Icon(Icons.info_outline_rounded),
                label: const Text('I HAVE INFORMATION'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.darkBlueShield,
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12)),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoRow(IconData icon, String text) {
    return Row(
      children: [
        Icon(icon, size: 16, color: Colors.grey),
        const SizedBox(width: 8),
        Expanded(
            child: Text(text,
                style: const TextStyle(color: Colors.grey, fontSize: 13))),
      ],
    );
  }

  void _showContactDialog(BuildContext context, String name) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Information for $name'),
        content: const Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
                'Thank you for your help. Your information will be sent to the guardian and local security personnel anonymously.'),
            SizedBox(height: 16),
            TextField(
              maxLines: 3,
              decoration: InputDecoration(
                hintText: 'Describe where and when you saw this person...',
                border: OutlineInputBorder(),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('CANCEL')),
          ElevatedButton(
              onPressed: () {
                Navigator.pop(context);
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                      content:
                          Text('Information sent successfully. Thank you!')),
                );
              },
              child: const Text('SUBMIT')),
        ],
      ),
    );
  }
}
