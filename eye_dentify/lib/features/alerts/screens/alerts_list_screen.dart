import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../core/constants/colors.dart';
import '../../../providers/alert_provider.dart';
import '../../../models/alert_model.dart';
import '../../../models/enums.dart';

class AlertsListScreen extends StatefulWidget {
  const AlertsListScreen({super.key});

  @override
  State<AlertsListScreen> createState() => _AlertsListScreenState();
}

class _AlertsListScreenState extends State<AlertsListScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final provider = context.read<AlertProvider>();
      provider.initializeRealtime();
      provider.fetchMyAlerts();
    });
  }

  @override
  Widget build(BuildContext context) {
    final alertProvider = context.watch<AlertProvider>();
    final errorMessage = alertProvider.errorMessage;

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        title: const Text('Alerts',
            style: TextStyle(
                color: AppColors.bodyText, fontWeight: FontWeight.bold)),
        backgroundColor: Colors.white,
        elevation: 0,
        centerTitle: true,
        actions: [
          IconButton(
              onPressed: () {
                alertProvider.fetchMyAlerts();
              },
              icon: const Icon(Icons.refresh, color: AppColors.bodyText)),
        ],
      ),
      body: StreamBuilder<List<AlertModel>>(
        stream: alertProvider.alertStream,
        initialData: alertProvider.alerts,
        builder: (context, snapshot) {
          final alerts = snapshot.data ?? alertProvider.alerts;

          if (alertProvider.isLoading) {
            return const Center(child: CircularProgressIndicator());
          }

          if (errorMessage != null) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Text(errorMessage,
                    textAlign: TextAlign.center,
                    style: const TextStyle(color: AppColors.error)),
              ),
            );
          }

          if (alerts.isEmpty) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.notifications_none_rounded,
                      size: 64, color: Colors.grey[400]),
                  const SizedBox(height: 16),
                  Text('No alerts found',
                      style: TextStyle(color: Colors.grey[600], fontSize: 16)),
                ],
              ),
            );
          }

          if (!alertProvider.isRealtimeConnected ||
              alertProvider.isSnapshotSyncing) {
            return Column(
              children: [
                Container(
                  width: double.infinity,
                  padding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                  color: AppColors.warning.withValues(alpha: 0.15),
                  child: Text(
                    'Realtime connection lost — syncing…',
                    style: const TextStyle(color: AppColors.warning),
                  ),
                ),
                Expanded(child: _buildAlertsBody(alertProvider, alerts)),
              ],
            );
          }

          return _buildAlertsBody(alertProvider, alerts);
        },
      ),
    );
  }

  Widget _buildAlertsBody(AlertProvider provider, List<AlertModel> alerts) {
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: alerts.length,
      itemBuilder: (context, index) {
        final alert = alerts[index];
        return _buildAlertCard(context, alert, provider);
      },
    );
  }

  Widget _buildAlertCard(
      BuildContext context, AlertModel alert, AlertProvider provider) {
    final priorityColor = _getPriorityColor(alert.alertLevel);
    final detection = alert.detection;
    final verificationState = provider.verificationState(alert);
    final statusColor = _getVerificationColor(verificationState);
    final isDecisionPending = provider.isDecisionPending(alert.alertId);

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(15),
        boxShadow: [
          BoxShadow(
              color: Colors.black.withValues(alpha: 0.05),
              blurRadius: 10,
              offset: const Offset(0, 4))
        ],
      ),
      child: Column(
        children: [
          Container(
            height: 4,
            width: double.infinity,
            decoration: BoxDecoration(
              color: priorityColor,
              borderRadius: const BorderRadius.only(
                  topLeft: Radius.circular(15), topRight: Radius.circular(15)),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(12),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    children: [
                      Container(
                        height: 80,
                        decoration: BoxDecoration(
                            color: Colors.grey[200],
                            borderRadius: BorderRadius.circular(10)),
                        child: detection?.originalPhotoUrl != null
                            ? ClipRRect(
                                borderRadius: BorderRadius.circular(10),
                                child: Image.network(
                                  detection!.originalPhotoUrl!,
                                  fit: BoxFit.cover,
                                  errorBuilder: (_, __, ___) => const Icon(
                                      Icons.person,
                                      color: Colors.grey),
                                ),
                              )
                            : const Center(
                                child: Text('Original',
                                    style: TextStyle(fontSize: 10))),
                      ),
                      const SizedBox(height: 4),
                      const Text('Reported',
                          style: TextStyle(fontSize: 10, color: Colors.grey)),
                    ],
                  ),
                ),
                const Padding(
                  padding: EdgeInsets.symmetric(horizontal: 8),
                  child:
                      Icon(Icons.compare_arrows, color: AppColors.primaryBlue),
                ),
                Expanded(
                  child: Column(
                    children: [
                      Container(
                        height: 80,
                        decoration: BoxDecoration(
                            color: Colors.grey[300],
                            borderRadius: BorderRadius.circular(10)),
                        child: detection?.snapshotUrl != null
                            ? ClipRRect(
                                borderRadius: BorderRadius.circular(10),
                                child: Image.network(
                                  detection!.snapshotUrl!,
                                  fit: BoxFit.cover,
                                  errorBuilder: (_, __, ___) => const Icon(
                                      Icons.camera_alt,
                                      color: Colors.grey),
                                ),
                              )
                            : const Center(
                                child: Text('Detected',
                                    style: TextStyle(fontSize: 10))),
                      ),
                      const SizedBox(height: 4),
                      const Text('Detection',
                          style: TextStyle(fontSize: 10, color: Colors.grey)),
                    ],
                  ),
                ),
              ],
            ),
          ),
          ListTile(
            title: Text(detection?.personName ?? 'Unknown Person',
                style:
                    const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            subtitle: Text(
                '${detection?.cameraLocation ?? 'Unknown Location'} • ${verificationState.displayName}',
                style: const TextStyle(fontSize: 12)),
            trailing: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: BoxDecoration(
                  color: priorityColor.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(20)),
              child: Text(
                  '${(detection?.combinedScore ?? 0).toStringAsFixed(0)}%',
                  style: TextStyle(
                      color: priorityColor, fontWeight: FontWeight.bold)),
            ),
            onTap: () => Navigator.pushNamed(context, '/alert-details',
                arguments: alert),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
            child: Row(
              children: [
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: statusColor.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    verificationState.displayName.toUpperCase(),
                    style: TextStyle(
                      color: statusColor,
                      fontWeight: FontWeight.bold,
                      fontSize: 10,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                if (verificationState == VerificationState.pendingVerification)
                  Text('Verifying with advanced AI…',
                      style: TextStyle(color: Colors.grey[600], fontSize: 11)),
                if (verificationState == VerificationState.preliminary)
                  Text('Single-frame detection — waiting for confirmation',
                      style: TextStyle(color: Colors.grey[600], fontSize: 11)),
                if (isDecisionPending)
                  Text('Decision pending finalization',
                      style: TextStyle(color: Colors.grey[600], fontSize: 11)),
                if (alert.sightingsCount > 1) ...[
                  const SizedBox(width: 8),
                  Text('Seen again (x${alert.sightingsCount})',
                      style: TextStyle(color: Colors.grey[600], fontSize: 11)),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Color _getPriorityColor(AlertLevel level) {
    switch (level) {
      case AlertLevel.critical:
        return Colors.red;
      case AlertLevel.strongMatch:
        return Colors.orange;
      case AlertLevel.tracking:
        return Colors.yellow[700]!;
      case AlertLevel.preliminary:
        return Colors.grey;
    }
  }

  Color _getVerificationColor(VerificationState state) {
    switch (state) {
      case VerificationState.confirmedMatch:
        return AppColors.success;
      case VerificationState.rejectedFalseAlarm:
        return AppColors.error;
      case VerificationState.needsReview:
        return AppColors.warning;
      case VerificationState.cloudTimeout:
        return AppColors.warning;
      case VerificationState.pendingVerification:
        return AppColors.primaryBlue;
      case VerificationState.preliminary:
        return AppColors.primaryBlue;
    }
  }
}
