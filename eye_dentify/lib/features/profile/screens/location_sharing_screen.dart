import 'package:flutter/material.dart';
import '../../../core/constants/colors.dart';

class LocationSharingScreen extends StatefulWidget {
  const LocationSharingScreen({super.key});

  @override
  State<LocationSharingScreen> createState() => _LocationSharingScreenState();
}

class _LocationSharingScreenState extends State<LocationSharingScreen> {
  bool _shareLiveLocation = false;
  bool _shareLastSeen = true;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        title: const Text('Location Sharing',
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
          _buildInfoBox(),
          const SizedBox(height: 30),
          _buildToggleTile(
              Icons.location_on_outlined,
              'Live Location',
              'Share your real-time position during active cases',
              _shareLiveLocation,
              (v) => setState(() => _shareLiveLocation = v)),
          _buildToggleTile(
              Icons.history_toggle_off,
              'Last Seen Location',
              'Store your last known location for emergency recovery',
              _shareLastSeen,
              (v) => setState(() => _shareLastSeen = v)),
          const SizedBox(height: 30),
          const Text('Trusted Contacts',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
          const Text(
              'Only these people can see your location even if sharing is off in emergency.',
              style: TextStyle(color: Colors.grey, fontSize: 12)),
          const SizedBox(height: 16),
          _buildTrustedContact('Home (Guardian)', 'Always Authorized'),
          _buildTrustedContact('Emergency Response', 'Authorized on Alert'),
        ],
      ),
    );
  }

  Widget _buildInfoBox() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.primaryBlue.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(15),
        border: Border.all(color: AppColors.primaryBlue.withValues(alpha: 0.1)),
      ),
      child: const Row(
        children: [
          Icon(Icons.shield_outlined, color: AppColors.primaryBlue),
          SizedBox(width: 12),
          Expanded(
            child: Text(
              'Your location data is encrypted and only shared with authorized responders during a valid search operation.',
              style: TextStyle(fontSize: 12, height: 1.4),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildToggleTile(IconData icon, String title, String subtitle,
      bool value, Function(bool) onChanged) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
          color: const Color(0xFFF8FAFC),
          borderRadius: BorderRadius.circular(15)),
      child: SwitchListTile(
        secondary: Icon(icon, color: AppColors.primaryBlue),
        title: Text(title,
            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
        subtitle: Text(subtitle, style: const TextStyle(fontSize: 12)),
        value: value,
        onChanged: onChanged,
        activeTrackColor: AppColors.primaryBlue,
      ),
    );
  }

  Widget _buildTrustedContact(String name, String status) {
    return ListTile(
      leading: const CircleAvatar(
          backgroundColor: Color(0xFFE2E8F0),
          child: Icon(Icons.person, color: Colors.grey)),
      title: Text(name,
          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
      subtitle: Text(status,
          style: const TextStyle(fontSize: 11, color: AppColors.primaryBlue)),
      trailing:
          const Icon(Icons.verified, color: AppColors.primaryBlue, size: 18),
    );
  }
}
