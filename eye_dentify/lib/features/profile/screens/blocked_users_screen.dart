import 'package:flutter/material.dart';
import '../../../core/constants/colors.dart';

class BlockedUsersScreen extends StatelessWidget {
  const BlockedUsersScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        title: const Text('Blocked Users',
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
          const Text(
            'Managing your blocked list',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          const Text(
            'Blocked users won\'t be able to see your profile or interact with your search cases.',
            style: TextStyle(color: Colors.grey, fontSize: 13),
          ),
          const SizedBox(height: 30),
          _buildBlockedTile('User_9921', 'Blocked on 12 Jan'),
          _buildBlockedTile('Stranger_X', 'Blocked on 15 Jan'),
          const SizedBox(height: 50),
          const Center(
            child: Text('No other users are currently blocked.',
                style: TextStyle(color: Colors.grey, fontSize: 12)),
          ),
        ],
      ),
    );
  }

  Widget _buildBlockedTile(String name, String date) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        border: Border.all(color: const Color(0xFFE2E8F0)),
        borderRadius: BorderRadius.circular(15),
      ),
      child: ListTile(
        leading: const CircleAvatar(
            backgroundColor: Color(0xFFFEE2E2),
            child: Icon(Icons.block, color: Colors.red, size: 20)),
        title: Text(name, style: const TextStyle(fontWeight: FontWeight.bold)),
        subtitle: Text(date, style: const TextStyle(fontSize: 12)),
        trailing: TextButton(
          onPressed: () {},
          child: const Text('Unblock',
              style: TextStyle(
                  color: AppColors.primaryBlue, fontWeight: FontWeight.bold)),
        ),
      ),
    );
  }
}
