import 'package:flutter/material.dart';
import '../../../core/constants/colors.dart';

class NotificationSettingsScreen extends StatefulWidget {
  const NotificationSettingsScreen({super.key});

  @override
  State<NotificationSettingsScreen> createState() =>
      _NotificationSettingsScreenState();
}

class _NotificationSettingsScreenState
    extends State<NotificationSettingsScreen> {
  bool _pushNotifications = true;
  bool _emailAlerts = false;
  bool _smsAlerts = true;
  double _threshold = 80;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        title: const Text('Notification Settings',
            style: TextStyle(color: AppColors.bodyText)),
        backgroundColor: Colors.white,
        elevation: 0,
        iconTheme: const IconThemeData(color: AppColors.bodyText),
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          _buildToggleTile('Push Notifications', _pushNotifications,
              (v) => setState(() => _pushNotifications = v)),
          _buildToggleTile('Email Alerts', _emailAlerts,
              (v) => setState(() => _emailAlerts = v)),
          _buildToggleTile(
              'SMS Alerts', _smsAlerts, (v) => setState(() => _smsAlerts = v)),
          const SizedBox(height: 30),
          const Text(
            'Alert Threshold',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
          ),
          const Text(
            'Only notify when facial match confidence is above:',
            style: TextStyle(fontSize: 12, color: Colors.grey),
          ),
          Slider(
            value: _threshold,
            min: 60,
            max: 95,
            divisions: 7,
            label: '${_threshold.round()}%',
            activeColor: AppColors.primaryBlue,
            onChanged: (v) => setState(() => _threshold = v),
          ),
          const Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('60%', style: TextStyle(fontSize: 12)),
              Text('95%', style: TextStyle(fontSize: 12)),
            ],
          ),
          const SizedBox(height: 40),
          ElevatedButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('SAVE SETTINGS'),
          ),
        ],
      ),
    );
  }

  Widget _buildToggleTile(String title, bool value, Function(bool) onChanged) {
    return SwitchListTile(
      title: Text(title, style: const TextStyle(fontWeight: FontWeight.w500)),
      value: value,
      onChanged: onChanged,
      activeTrackColor: AppColors.primaryBlue,
    );
  }
}
